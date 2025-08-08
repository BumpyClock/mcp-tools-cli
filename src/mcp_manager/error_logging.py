"""Comprehensive error logging and diagnostics system for MCP Manager."""

import json
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any, TextIO
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from enum import Enum

from .exceptions import MCPManagerError, ErrorSeverity


class LogLevel(Enum):
    """Extended log levels for error tracking."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    RECOVERY = "recovery"  # Special level for recovery actions
    AUDIT = "audit"        # Special level for audit trail


@dataclass
class ErrorLogEntry:
    """Structured error log entry."""
    timestamp: str
    level: str
    error_type: str
    error_code: str
    message: str
    user_message: str
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_action: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    system_info: Optional[Dict[str, Any]] = None


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report for troubleshooting."""
    report_id: str
    generated_at: str
    error_summary: Dict[str, Any]
    system_state: Dict[str, Any]
    recent_errors: List[ErrorLogEntry]
    error_patterns: List[Dict[str, Any]]
    suggestions: List[str]
    environment_info: Dict[str, Any]


class ErrorLogger:
    """Advanced error logging system with structured logging and analytics."""
    
    def __init__(self, log_dir: Optional[Path] = None, max_log_size_mb: int = 100):
        self.log_dir = log_dir or Path.home() / ".mcp_manager" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_log_size = max_log_size_mb * 1024 * 1024  # Convert to bytes
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up structured logging
        self.setup_structured_logging()
        
        # Error tracking
        self.error_entries: List[ErrorLogEntry] = []
        self.error_patterns: Dict[str, int] = {}
        
        # Log files
        self.error_log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.audit_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.performance_log_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def setup_structured_logging(self) -> None:
        """Set up structured logging with structlog."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Set up standard Python logging
        logging.basicConfig(
            level=logging.INFO,
            handlers=[
                logging.FileHandler(self.log_dir / "mcp_manager.log"),
                logging.StreamHandler()
            ],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.logger = structlog.get_logger("mcp_manager")
    
    def log_error(self, error: MCPManagerError, recovery_attempted: bool = False,
                  recovery_successful: bool = False, recovery_action: Optional[str] = None) -> None:
        """Log an error with full context and recovery information."""
        # Create error log entry
        entry = ErrorLogEntry(
            timestamp=datetime.now().isoformat(),
            level=error.severity.value,
            error_type=error.__class__.__name__,
            error_code=error.get_error_code(),
            message=str(error),
            user_message=error.user_message,
            stack_trace=traceback.format_exc() if error.__traceback__ else None,
            context=asdict(error.context) if error.context else None,
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful,
            recovery_action=recovery_action,
            session_id=self.session_id,
            user_id=Path.home().name,  # Simple user identification
            system_info=self.get_system_info()
        )
        
        # Add to in-memory tracking
        self.error_entries.append(entry)
        self.track_error_pattern(entry)
        
        # Write to log file
        self.write_log_entry(entry, self.error_log_file)
        
        # Log with structlog for structured output
        self.logger.error(
            "Error occurred",
            error_type=entry.error_type,
            error_code=entry.error_code,
            message=entry.message,
            context=entry.context,
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful
        )
    
    def log_recovery_action(self, action: str, success: bool, message: str,
                           error_context: Optional[Dict[str, Any]] = None) -> None:
        """Log recovery action attempts and results."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "recovery",
            "action": action,
            "success": success,
            "message": message,
            "error_context": error_context,
            "session_id": self.session_id
        }
        
        # Write to audit log
        self.write_json_log(entry, self.audit_log_file)
        
        # Log with structlog
        if success:
            self.logger.info("Recovery action successful", **entry)
        else:
            self.logger.warning("Recovery action failed", **entry)
    
    def log_performance_metric(self, operation: str, duration: float,
                             success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """Log performance metrics for operations."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_seconds": duration,
            "success": success,
            "details": details or {},
            "session_id": self.session_id
        }
        
        self.write_json_log(entry, self.performance_log_file)
    
    def track_error_pattern(self, entry: ErrorLogEntry) -> None:
        """Track error patterns for analytics."""
        pattern_key = f"{entry.error_type}:{entry.error_code}"
        self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
    
    def write_log_entry(self, entry: ErrorLogEntry, log_file: Path) -> None:
        """Write an error log entry to file."""
        try:
            # Rotate log if it's too large
            if log_file.exists() and log_file.stat().st_size > self.max_log_size:
                self.rotate_log_file(log_file)
            
            # Write entry as JSON line
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(entry), default=str) + '\n')
                
        except Exception as e:
            # Fallback logging if structured logging fails
            print(f"Failed to write error log: {e}")
    
    def write_json_log(self, entry: Dict[str, Any], log_file: Path) -> None:
        """Write a JSON log entry to file."""
        try:
            # Rotate log if it's too large
            if log_file.exists() and log_file.stat().st_size > self.max_log_size:
                self.rotate_log_file(log_file)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, default=str) + '\n')
                
        except Exception as e:
            print(f"Failed to write JSON log: {e}")
    
    def rotate_log_file(self, log_file: Path) -> None:
        """Rotate a log file when it gets too large."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = log_file.with_suffix(f".{timestamp}.bak")
            log_file.rename(backup_file)
            
            # Compress old log if possible
            try:
                import gzip
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                backup_file.unlink()  # Remove uncompressed backup
            except ImportError:
                pass  # gzip not available, keep uncompressed backup
                
        except Exception as e:
            print(f"Failed to rotate log file {log_file}: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for diagnostics."""
        import platform
        import sys
        import psutil
        
        try:
            return {
                "platform": platform.platform(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": dict(psutil.disk_usage(Path.cwd())._asdict()),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to gather system info: {str(e)}",
                "platform": platform.platform(),
                "python_version": sys.version,
                "timestamp": datetime.now().isoformat()
            }
    
    def generate_diagnostic_report(self, error_id: Optional[str] = None) -> DiagnosticReport:
        """Generate a comprehensive diagnostic report."""
        report_id = f"diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get recent errors (last 24 hours)
        recent_errors = self.get_recent_errors(hours=24)
        
        # Analyze error patterns
        error_patterns = self.analyze_error_patterns()
        
        # Generate suggestions based on patterns
        suggestions = self.generate_suggestions(error_patterns, recent_errors)
        
        report = DiagnosticReport(
            report_id=report_id,
            generated_at=datetime.now().isoformat(),
            error_summary=self.get_error_summary(),
            system_state=self.get_system_state(),
            recent_errors=recent_errors,
            error_patterns=error_patterns,
            suggestions=suggestions,
            environment_info=self.get_environment_info()
        )
        
        # Save report to file
        report_file = self.log_dir / f"{report_id}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save diagnostic report: {e}")
        
        return report
    
    def get_recent_errors(self, hours: int = 24) -> List[ErrorLogEntry]:
        """Get errors from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for entry in self.error_entries:
            try:
                entry_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00').replace('T', ' '))
                if entry_time > cutoff:
                    recent.append(entry)
            except Exception:
                continue  # Skip entries with invalid timestamps
        
        return sorted(recent, key=lambda x: x.timestamp, reverse=True)
    
    def analyze_error_patterns(self) -> List[Dict[str, Any]]:
        """Analyze error patterns for common issues."""
        patterns = []
        
        for pattern_key, count in self.error_patterns.items():
            error_type, error_code = pattern_key.split(':', 1)
            patterns.append({
                "error_type": error_type,
                "error_code": error_code,
                "occurrences": count,
                "pattern_key": pattern_key
            })
        
        # Sort by frequency
        patterns.sort(key=lambda x: x["occurrences"], reverse=True)
        return patterns[:10]  # Top 10 patterns
    
    def generate_suggestions(self, patterns: List[Dict[str, Any]], 
                           recent_errors: List[ErrorLogEntry]) -> List[str]:
        """Generate suggestions based on error patterns."""
        suggestions = []
        
        # Pattern-based suggestions
        for pattern in patterns[:3]:  # Top 3 patterns
            if pattern["occurrences"] > 1:
                if "NetworkError" in pattern["error_type"]:
                    suggestions.append("Check network connectivity and firewall settings")
                elif "ConfigurationError" in pattern["error_type"]:
                    suggestions.append("Review configuration files for syntax errors")
                elif "DeploymentError" in pattern["error_type"]:
                    suggestions.append("Verify deployment target availability and permissions")
                elif "PermissionError" in pattern["error_type"]:
                    suggestions.append("Check file and directory permissions")
        
        # Recent error analysis
        if len(recent_errors) > 10:
            suggestions.append("High error rate detected - consider system health check")
        
        # Recovery success rate
        attempted = sum(1 for e in recent_errors if e.recovery_attempted)
        successful = sum(1 for e in recent_errors if e.recovery_successful)
        if attempted > 0 and successful / attempted < 0.5:
            suggestions.append("Low recovery success rate - review error handling strategies")
        
        return suggestions or ["System appears to be functioning normally"]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary statistics of errors."""
        recent = self.get_recent_errors(24)
        
        return {
            "total_errors": len(self.error_entries),
            "recent_errors_24h": len(recent),
            "error_types": dict(self.error_patterns),
            "recovery_rate": self.calculate_recovery_rate(),
            "most_common_error": max(self.error_patterns.items(), key=lambda x: x[1])[0] if self.error_patterns else None
        }
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get current system state for diagnostics."""
        return {
            "session_id": self.session_id,
            "log_directory": str(self.log_dir),
            "log_files": [f.name for f in self.log_dir.glob("*.log*")],
            "system_info": self.get_system_info(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        import os
        
        return {
            "python_path": sys.executable,
            "working_directory": str(Path.cwd()),
            "user_home": str(Path.home()),
            "environment_variables": {k: v for k, v in os.environ.items() 
                                    if k.startswith(('MCP_', 'PYTHON_', 'PATH'))},
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_recovery_rate(self) -> float:
        """Calculate the success rate of recovery attempts."""
        attempted = sum(1 for e in self.error_entries if e.recovery_attempted)
        successful = sum(1 for e in self.error_entries if e.recovery_successful)
        
        return (successful / attempted * 100) if attempted > 0 else 0.0
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """Clean up log files older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff.timestamp():
                    log_file.unlink()
                    self.logger.info(f"Cleaned up old log file: {log_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up log file {log_file}: {e}")


# Global logger instance
_global_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> ErrorLogger:
    """Get the global error logger instance."""
    global _global_error_logger
    if _global_error_logger is None:
        _global_error_logger = ErrorLogger()
    return _global_error_logger


def log_error(error: MCPManagerError, **kwargs) -> None:
    """Convenience function for logging errors."""
    get_error_logger().log_error(error, **kwargs)


def log_recovery_action(action: str, success: bool, message: str, **kwargs) -> None:
    """Convenience function for logging recovery actions."""
    get_error_logger().log_recovery_action(action, success, message, **kwargs)


def generate_diagnostic_report() -> DiagnosticReport:
    """Convenience function for generating diagnostic reports."""
    return get_error_logger().generate_diagnostic_report()