"""Core MCP Manager modules for programmatic access."""

from .registry import MCPServerRegistry
from .deployment import DeploymentManager
from .platforms import PlatformManager
from .projects import ProjectDetector

__all__ = [
    "MCPServerRegistry",
    "DeploymentManager",
    "PlatformManager", 
    "ProjectDetector"
]