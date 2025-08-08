"""Validation functions for MCP server configurations."""

import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional, List
import structlog

from .config import MCPServer, parse_server_config

logger = structlog.get_logger()


def validate_mcp_server_config(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate MCP server configuration against expected schema."""
    try:
        # Use Pydantic model validation
        parse_server_config(server_name, server_config)
        return True, None
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error validating server '{server_name}': {e}"


def validate_all_servers(servers: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate all server configurations."""
    all_valid = True
    errors = []
    
    for server_name, server_config in servers.items():
        is_valid, error = validate_mcp_server_config(server_name, server_config)
        if not is_valid:
            all_valid = False
            errors.append(error)
            logger.error("Server validation failed", server=server_name, error=error)
    
    if all_valid:
        logger.info("All server configurations valid", count=len(servers))
    
    return all_valid, errors


def check_server_health(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check if an MCP server is accessible/valid."""
    server_type = server_config.get('type')
    logger.debug("Checking server health", server=server_name, type=server_type)
    
    if server_type == 'stdio':
        return _check_stdio_server_health(server_name, server_config)
    elif server_type == 'http':
        return _check_http_server_health(server_name, server_config)
    elif server_type == 'sse':
        return _check_sse_server_health(server_name, server_config)
    elif server_type == 'docker':
        return _check_docker_server_health(server_name, server_config)
    else:
        return False, f"Unknown server type: {server_type}"


def _check_stdio_server_health(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check health of STDIO server."""
    command = server_config.get('command')
    if not command:
        return False, "Missing command"
    
    if command == 'docker':
        return _check_docker_availability()
    elif command == 'npx':
        if shutil.which('npx') is None:
            return False, "npx not found in PATH"
    elif command == 'uvx':
        if shutil.which('uvx') is None:
            return False, "uvx not found in PATH"
    else:
        # Check if command exists in PATH
        if shutil.which(command) is None:
            return False, f"Command '{command}' not found in PATH"
    
    logger.debug("STDIO server health check passed", server=server_name, command=command)
    return True, None


def _check_http_server_health(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check health of HTTP server."""
    url = server_config.get('url')
    if not url:
        return False, "Missing URL"
    
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.debug("HTTP server health check passed", server=server_name, url=url, status=response.status)
            return True, None
    except urllib.error.URLError as e:
        error_msg = f"Cannot reach URL '{url}': {e}"
        logger.debug("HTTP server health check failed", server=server_name, url=url, error=str(e))
        return False, error_msg
    except Exception as e:
        error_msg = f"Error checking URL '{url}': {e}"
        logger.debug("HTTP server health check failed", server=server_name, url=url, error=str(e))
        return False, error_msg


def _check_sse_server_health(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check health of SSE server."""
    # For SSE servers, we can do a basic HTTP check
    return _check_http_server_health(server_name, server_config)


def _check_docker_server_health(server_name: str, server_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check health of Docker server."""
    return _check_docker_availability()


def _check_docker_availability() -> Tuple[bool, Optional[str]]:
    """Check if Docker is available and running."""
    if shutil.which('docker') is None:
        return False, "Docker not found in PATH"
    
    try:
        result = subprocess.run(
            ['docker', 'info'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode != 0:
            return False, "Docker is not running or not accessible"
        logger.debug("Docker availability check passed")
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except subprocess.CalledProcessError as e:
        return False, f"Docker command failed: {e}"
    except FileNotFoundError:
        return False, "Docker command not found"
    except Exception as e:
        return False, f"Error checking Docker: {e}"


def health_check_all_servers(servers: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    """Check health of all servers."""
    healthy_count = 0
    total_count = len(servers)
    issues = []
    
    logger.info("Starting health check for all servers", total=total_count)
    
    for server_name, server_config in servers.items():
        is_healthy, error = check_server_health(server_name, server_config)
        if is_healthy:
            healthy_count += 1
            logger.debug("Server health check passed", server=server_name)
        else:
            issues.append(f"{server_name}: {error}")
            logger.warning("Server health check failed", server=server_name, error=error)
    
    logger.info(
        "Health check completed", 
        healthy=healthy_count, 
        total=total_count,
        failed=len(issues)
    )
    
    return healthy_count, total_count, issues


def validate_and_health_check(servers: Dict[str, Any], do_health_check: bool = True) -> Tuple[bool, List[str]]:
    """Combined validation and health check."""
    logger.info("Starting validation and health check", servers=len(servers), health_check=do_health_check)
    
    # First validate configurations
    all_valid, validation_errors = validate_all_servers(servers)
    if not all_valid:
        logger.error("Configuration validation failed", errors=len(validation_errors))
        return False, [f"Validation: {error}" for error in validation_errors]
    
    # Then do health check if requested
    if do_health_check:
        healthy_count, total_count, health_issues = health_check_all_servers(servers)
        if health_issues:
            logger.warning("Health check issues found", issues=len(health_issues))
            return healthy_count > 0, [f"Health: {issue}" for issue in health_issues]
    
    logger.info("All validation and health checks passed")
    return True, []