"""Configuration models for MCP servers using Pydantic."""

from typing import Dict, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator
from pathlib import Path


class MCPServerEnv(BaseModel):
    """Environment variables for MCP servers."""
    
    class Config:
        extra = "allow"  # Allow additional environment variables
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return getattr(self, key, None)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like setting."""
        setattr(self, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method."""
        return getattr(self, key, default)
    
    def items(self):
        """Dict-like items method."""
        return self.__dict__.items()
    
    def keys(self):
        """Dict-like keys method."""
        return self.__dict__.keys()


class STDIOMCPServer(BaseModel):
    """STDIO MCP server configuration."""
    
    type: Literal["stdio"] = "stdio"
    command: str = Field(..., description="Command to execute")
    args: Optional[List[str]] = Field(default=None, description="Command arguments")
    env: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        default=None, description="Environment variables"
    )
    packageOrCommand: Optional[str] = Field(
        default=None, description="Package or command for some servers"
    )
    
    @validator('command')
    def validate_command(cls, v):
        """Validate command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()


class HTTPMCPServer(BaseModel):
    """HTTP MCP server configuration."""
    
    type: Literal["http"] = "http"
    url: str = Field(..., description="HTTP endpoint URL")
    env: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        default=None, description="Environment variables"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class SSEMCPServer(BaseModel):
    """SSE MCP server configuration."""
    
    type: Literal["sse"] = "sse"
    url: str = Field(..., description="SSE endpoint URL")
    env: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        default=None, description="Environment variables"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class DockerMCPServer(BaseModel):
    """Docker MCP server configuration."""
    
    type: Literal["docker"] = "docker"
    command: str = Field(..., description="Docker command to execute")
    args: Optional[List[str]] = Field(default=None, description="Command arguments")
    env: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        default=None, description="Environment variables"
    )
    
    @validator('command')
    def validate_command(cls, v):
        """Validate command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()


# Union type for all server types
MCPServer = Union[STDIOMCPServer, HTTPMCPServer, SSEMCPServer, DockerMCPServer]


class MCPServersConfig(BaseModel):
    """Configuration for MCP servers."""
    
    mcpServers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="MCP server configurations"
    )
    
    @validator('mcpServers', pre=True)
    def normalize_servers_key(cls, v):
        """Normalize 'mcps' to 'mcpServers' for backward compatibility."""
        if isinstance(v, dict) and 'mcps' in v and 'mcpServers' not in v:
            return {'mcpServers': v['mcps']}
        return v
    
    def get_servers_key(self) -> Optional[str]:
        """Get the appropriate key for MCP servers."""
        if 'mcpServers' in self.__dict__:
            return 'mcpServers'
        elif 'mcps' in self.__dict__:
            return 'mcps'
        return None


class ClaudeConfig(BaseModel):
    """Complete Claude configuration file."""
    
    mcpServers: Optional[Dict[str, Dict[str, Any]]] = Field(
        default_factory=dict, description="MCP server configurations"
    )
    
    class Config:
        extra = "allow"  # Allow additional fields in Claude config
    
    @root_validator(pre=True)
    def normalize_keys(cls, values):
        """Normalize 'mcps' to 'mcpServers' for backward compatibility."""
        if isinstance(values, dict):
            if 'mcps' in values and 'mcpServers' not in values:
                values['mcpServers'] = values.pop('mcps')
        return values


class SecretsConfig(BaseModel):
    """Configuration for API secrets."""
    
    class Config:
        extra = "allow"  # Allow any server names as keys
    
    def get_server_secrets(self, server_name: str) -> Dict[str, str]:
        """Get secrets for a specific server."""
        return getattr(self, server_name, {})
    
    def set_server_secrets(self, server_name: str, secrets: Dict[str, str]) -> None:
        """Set secrets for a specific server."""
        setattr(self, server_name, secrets)


class SyncConfig(BaseModel):
    """Configuration for sync operations."""
    
    mcp_servers_file: Path = Field(..., description="Path to mcp-servers.json")
    claude_config_file: Path = Field(..., description="Path to ~/.claude.json")
    secrets_file: Optional[Path] = Field(
        default=None, description="Path to secrets file"
    )
    
    dry_run: bool = Field(default=False, description="Dry run mode")
    health_check: bool = Field(default=False, description="Perform health checks")
    sync_secrets: bool = Field(default=False, description="Sync API keys")
    
    @validator('mcp_servers_file', 'claude_config_file')
    def validate_paths_exist_or_creatable(cls, v):
        """Validate that paths exist or can be created."""
        if not isinstance(v, Path):
            v = Path(v)
        
        # For the parent directory to exist (file can be created)
        if not v.parent.exists():
            raise ValueError(f"Parent directory {v.parent} does not exist")
        
        return v


def parse_server_config(server_name: str, config_dict: Dict[str, Any]) -> MCPServer:
    """Parse a server configuration dictionary into the appropriate model."""
    server_type = config_dict.get('type', 'stdio')
    
    if server_type == 'stdio':
        return STDIOMCPServer(**config_dict)
    elif server_type == 'http':
        return HTTPMCPServer(**config_dict)
    elif server_type == 'sse':
        return SSEMCPServer(**config_dict)
    elif server_type == 'docker':
        return DockerMCPServer(**config_dict)
    else:
        raise ValueError(f"Unknown server type: {server_type}")


def validate_mcp_servers_dict(servers: Dict[str, Dict[str, Any]]) -> Dict[str, MCPServer]:
    """Validate a dictionary of MCP server configurations."""
    validated_servers = {}
    
    for server_name, server_config in servers.items():
        try:
            validated_servers[server_name] = parse_server_config(server_name, server_config)
        except Exception as e:
            raise ValueError(f"Invalid configuration for server '{server_name}': {e}")
    
    return validated_servers


# Utility functions for backward compatibility
def is_api_key_placeholder(value: Any) -> bool:
    """Check if a value is an API key placeholder that needs to be filled."""
    if not isinstance(value, str):
        return False
    
    placeholder_patterns = [
        'YOUR_API_KEY_HERE',
        'YOUR_',
        'REPLACE_ME', 
        'PLACEHOLDER',
        'API_KEY_HERE',
        '<YOUR_',
        '[YOUR_'
    ]
    
    value_upper = value.upper()
    return any(pattern in value_upper for pattern in placeholder_patterns) or value == ''


def get_mcp_servers_key(config: Dict[str, Any]) -> Optional[str]:
    """Get the appropriate key for MCP servers from config."""
    if 'mcpServers' in config:
        return 'mcpServers'
    elif 'mcps' in config:
        return 'mcps'
    return None


def normalize_config_keys(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize config to use 'mcpServers' key."""
    if 'mcps' in config and 'mcpServers' not in config:
        config['mcpServers'] = config.pop('mcps')
    return config