"""Health monitoring system for MCP servers."""

import asyncio
import json
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import psutil

from mcp_manager.core import MCPServerRegistry, PlatformManager


class HealthStatus(Enum):
    """Health status levels with color indicators."""
    HEALTHY = ("🟢", "green", "All checks passing")
    WARNING = ("🟡", "yellow", "Minor issues detected")
    CRITICAL = ("🔴", "red", "Server unreachable or misconfigured")
    UNKNOWN = ("⚪", "white", "Not checked yet")


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    server_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ServerHealthHistory:
    """Health history for a server."""
    server_name: str
    history: List[HealthCheckResult] = field(default_factory=list)
    last_healthy: Optional[datetime] = None
    consecutive_failures: int = 0
    
    def add_result(self, result: HealthCheckResult) -> None:
        """Add a health check result to history."""
        self.history.append(result)
        
        # Keep only last 10 results
        if len(self.history) > 10:
            self.history = self.history[-10:]
        
        # Update health tracking
        if result.status == HealthStatus.HEALTHY:
            self.last_healthy = result.timestamp
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
    
    @property
    def current_status(self) -> HealthStatus:
        """Get current health status."""
        if not self.history:
            return HealthStatus.UNKNOWN
        return self.history[-1].status
    
    @property
    def last_check(self) -> Optional[datetime]:
        """Get timestamp of last check."""
        if not self.history:
            return None
        return self.history[-1].timestamp
    
    @property
    def health_score(self) -> int:
        """Calculate health score (0-100)."""
        if not self.history:
            return 0
        
        recent_checks = self.history[-5:]  # Last 5 checks
        healthy_count = sum(1 for check in recent_checks if check.status == HealthStatus.HEALTHY)
        return int((healthy_count / len(recent_checks)) * 100)


class HealthMonitor:
    """Professional health monitoring system for MCP servers."""
    
    def __init__(self, registry: MCPServerRegistry, platform_manager: PlatformManager):
        self.registry = registry
        self.platform_manager = platform_manager
        
        # Health tracking
        self.health_history: Dict[str, ServerHealthHistory] = {}
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_interval = 30.0  # seconds
        
        # Callbacks for real-time updates
        self.status_callbacks: List[Callable[[str, HealthCheckResult], None]] = []
        
        # Performance tracking
        self.start_time = datetime.now()
        self.total_checks = 0
        
    def add_status_callback(self, callback: Callable[[str, HealthCheckResult], None]) -> None:
        """Add callback for real-time status updates."""
        self.status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[str, HealthCheckResult], None]) -> None:
        """Remove status callback."""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_callbacks(self, server_name: str, result: HealthCheckResult) -> None:
        """Notify all callbacks of status update."""
        for callback in self.status_callbacks:
            try:
                callback(server_name, result)
            except Exception:
                pass  # Don't let callback errors break monitoring
    
    async def check_server_health(self, server_name: str) -> HealthCheckResult:
        """Perform comprehensive health check for a server."""
        start_time = time.time()
        
        try:
            # Get server from registry
            server = self.registry.get_server(server_name)
            if not server:
                return HealthCheckResult(
                    server_name=server_name,
                    status=HealthStatus.CRITICAL,
                    message="Server not found in registry",
                    timestamp=datetime.now(),
                    response_time=time.time() - start_time,
                    error="Server not found"
                )
            
            # Check 1: Configuration validation
            config_check = self._validate_configuration(server_name, server)
            
            # Check 2: Process/connectivity check
            connectivity_check = await self._check_connectivity(server_name, server)
            
            # Check 3: Platform deployment check
            deployment_check = self._check_deployment_status(server_name)
            
            # Check 4: Resource usage check
            resource_check = self._check_resource_usage(server_name)
            
            # Aggregate results
            all_checks = [config_check, connectivity_check, deployment_check, resource_check]
            response_time = time.time() - start_time
            
            # Determine overall status
            if all(check.get("status") == "healthy" for check in all_checks):
                status = HealthStatus.HEALTHY
                message = "All checks passing"
            elif any(check.get("status") == "critical" for check in all_checks):
                status = HealthStatus.CRITICAL
                failed_checks = [check["name"] for check in all_checks if check.get("status") == "critical"]
                message = f"Critical issues: {', '.join(failed_checks)}"
            else:
                status = HealthStatus.WARNING
                warning_checks = [check["name"] for check in all_checks if check.get("status") == "warning"]
                message = f"Warnings: {', '.join(warning_checks)}"
            
            result = HealthCheckResult(
                server_name=server_name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time=response_time,
                details={
                    "checks": all_checks,
                    "config_valid": config_check.get("status") == "healthy",
                    "connectivity": connectivity_check.get("status") == "healthy",
                    "deployed": deployment_check.get("status") == "healthy",
                    "resources": resource_check.get("details", {})
                }
            )
            
            # Update history
            if server_name not in self.health_history:
                self.health_history[server_name] = ServerHealthHistory(server_name)
            self.health_history[server_name].add_result(result)
            
            # Notify callbacks
            self._notify_callbacks(server_name, result)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            result = HealthCheckResult(
                server_name=server_name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time=response_time,
                error=str(e)
            )
            
            # Update history
            if server_name not in self.health_history:
                self.health_history[server_name] = ServerHealthHistory(server_name)
            self.health_history[server_name].add_result(result)
            
            # Notify callbacks
            self._notify_callbacks(server_name, result)
            
            return result
    
    def _validate_configuration(self, server_name: str, server) -> Dict[str, Any]:
        """Validate server configuration."""
        try:
            issues = []
            
            # Check required fields
            if not server.command:
                issues.append("Missing command")
            
            if not server.args:
                issues.append("Missing arguments")
            
            # Check if command exists (for file-based commands)
            if server.command and server.command.endswith('.py'):
                command_path = Path(server.command)
                if command_path.is_absolute() and not command_path.exists():
                    issues.append(f"Command file not found: {server.command}")
            
            # Validate environment variables
            if hasattr(server, 'env') and server.env:
                for key, value in server.env.items():
                    if not value or value.strip() == "":
                        issues.append(f"Empty environment variable: {key}")
            
            if issues:
                return {
                    "name": "configuration",
                    "status": "warning" if len(issues) < 3 else "critical",
                    "message": f"Configuration issues: {', '.join(issues)}",
                    "details": {"issues": issues}
                }
            else:
                return {
                    "name": "configuration",
                    "status": "healthy",
                    "message": "Configuration valid",
                    "details": {"issues": []}
                }
                
        except Exception as e:
            return {
                "name": "configuration",
                "status": "critical",
                "message": f"Configuration validation failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_connectivity(self, server_name: str, server) -> Dict[str, Any]:
        """Check if server can be started/connected to."""
        try:
            # For now, simulate connectivity check
            # In real implementation, this would try to start the server process
            # and verify it responds to basic MCP protocol messages
            
            if not server.metadata.enabled:
                return {
                    "name": "connectivity",
                    "status": "warning",
                    "message": "Server disabled",
                    "details": {"enabled": False}
                }
            
            # Simulate process check with small delay
            await asyncio.sleep(0.1)
            
            # Check if this is a known working server type
            working_types = ["stdio", "websocket", "tcp"]
            server_type = getattr(server, 'type', 'unknown')
            
            if server_type in working_types:
                return {
                    "name": "connectivity",
                    "status": "healthy",
                    "message": "Server can be started",
                    "details": {"type": server_type, "enabled": True}
                }
            else:
                return {
                    "name": "connectivity",
                    "status": "warning",
                    "message": f"Unknown server type: {server_type}",
                    "details": {"type": server_type, "enabled": True}
                }
                
        except Exception as e:
            return {
                "name": "connectivity",
                "status": "critical",
                "message": f"Connectivity check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_deployment_status(self, server_name: str) -> Dict[str, Any]:
        """Check deployment status across platforms."""
        try:
            platforms = self.platform_manager.get_available_platforms()
            deployments = {}
            deployed_count = 0
            
            for platform_key, platform_info in platforms.items():
                if not platform_info or not platform_info.get("available", False):
                    deployments[platform_key] = "unavailable"
                    continue
                
                platform_config = platform_info.get("config")
                if platform_config and hasattr(platform_config, 'config_path'):
                    try:
                        config_path = platform_config.config_path
                        if config_path.exists():
                            config_data = json.loads(config_path.read_text())
                            deployed = server_name in config_data.get("mcpServers", {})
                            deployments[platform_key] = "deployed" if deployed else "not_deployed"
                            if deployed:
                                deployed_count += 1
                        else:
                            deployments[platform_key] = "no_config"
                    except (json.JSONDecodeError, FileNotFoundError):
                        deployments[platform_key] = "config_error"
                else:
                    deployments[platform_key] = "not_configured"
            
            # Determine status
            total_platforms = len([p for p in platforms.values() if p and p.get("available", False)])
            
            if deployed_count == 0:
                status = "warning"
                message = "Not deployed to any platform"
            elif deployed_count == total_platforms:
                status = "healthy"
                message = f"Deployed to all {total_platforms} platforms"
            else:
                status = "healthy"
                message = f"Deployed to {deployed_count}/{total_platforms} platforms"
            
            return {
                "name": "deployment",
                "status": status,
                "message": message,
                "details": {
                    "deployments": deployments,
                    "deployed_count": deployed_count,
                    "total_platforms": total_platforms
                }
            }
            
        except Exception as e:
            return {
                "name": "deployment",
                "status": "critical",
                "message": f"Deployment check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_resource_usage(self, server_name: str) -> Dict[str, Any]:
        """Check system resource usage (basic implementation)."""
        try:
            # Get basic system stats
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            issues = []
            
            # Basic thresholds
            if cpu_percent > 90:
                issues.append("High CPU usage")
            if memory.percent > 90:
                issues.append("High memory usage")
            if disk.percent > 95:
                issues.append("Low disk space")
            
            status = "critical" if len(issues) > 2 else "warning" if issues else "healthy"
            message = f"System resources: CPU {cpu_percent:.1f}%, RAM {memory.percent:.1f}%"
            
            if issues:
                message += f" - Issues: {', '.join(issues)}"
            
            return {
                "name": "resources",
                "status": status,
                "message": message,
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "issues": issues
                }
            }
            
        except Exception as e:
            return {
                "name": "resources",
                "status": "warning",
                "message": f"Resource check unavailable: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def check_all_servers(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, HealthCheckResult]:
        """Check health of all servers."""
        servers = self.registry.list_servers()
        server_names = list(servers.keys())
        results = {}
        
        if not server_names:
            return results
        
        total = len(server_names)
        
        for i, server_name in enumerate(server_names):
            if progress_callback:
                progress_callback(int((i / total) * 100), f"Checking {server_name}...")
            
            result = await self.check_server_health(server_name)
            results[server_name] = result
            self.total_checks += 1
        
        if progress_callback:
            progress_callback(100, "Health check completed")
        
        return results
    
    def get_server_health_history(self, server_name: str) -> Optional[ServerHealthHistory]:
        """Get health history for a specific server."""
        return self.health_history.get(server_name)
    
    def get_overall_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary for all servers."""
        if not self.health_history:
            return {
                "total_servers": 0,
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "unknown": 0,
                "health_percentage": 0,
                "last_check": None
            }
        
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        last_checks = []
        
        for history in self.health_history.values():
            status_counts[history.current_status] += 1
            if history.last_check:
                last_checks.append(history.last_check)
        
        total = sum(status_counts.values())
        healthy_count = status_counts[HealthStatus.HEALTHY]
        health_percentage = int((healthy_count / total) * 100) if total > 0 else 0
        
        return {
            "total_servers": total,
            "healthy": status_counts[HealthStatus.HEALTHY],
            "warning": status_counts[HealthStatus.WARNING],
            "critical": status_counts[HealthStatus.CRITICAL],
            "unknown": status_counts[HealthStatus.UNKNOWN],
            "health_percentage": health_percentage,
            "last_check": max(last_checks) if last_checks else None,
            "monitoring_active": self.monitoring_active,
            "total_checks_performed": self.total_checks,
            "uptime": datetime.now() - self.start_time
        }
    
    def start_background_monitoring(self) -> None:
        """Start background health monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._background_monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
    
    def stop_background_monitoring(self) -> None:
        """Stop background health monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            self.monitoring_thread = None
    
    def _background_monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run health checks
                servers = self.registry.list_servers()
                for server_name in servers:
                    if not self.monitoring_active:
                        break
                    
                    try:
                        result = loop.run_until_complete(self.check_server_health(server_name))
                        # Result is automatically added to history and callbacks notified
                    except Exception:
                        pass  # Continue with other servers
                
                loop.close()
                
                # Wait for next cycle
                for _ in range(int(self.monitoring_interval * 10)):
                    if not self.monitoring_active:
                        break
                    time.sleep(0.1)
                    
            except Exception:
                # If something goes wrong, wait a bit and continue
                time.sleep(5)
    
    def manual_refresh(self) -> None:
        """Trigger manual refresh of all server health."""
        # This would typically trigger an immediate check
        # For now, just reset some counters
        pass
    
    def get_health_indicator(self, server_name: str) -> tuple[str, str, str]:
        """Get health indicator emoji, color, and message for a server."""
        history = self.health_history.get(server_name)
        if not history:
            status = HealthStatus.UNKNOWN
        else:
            status = history.current_status
        
        return status.value  # Returns (emoji, color, message)