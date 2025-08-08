"""Central MCP server registry management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import structlog
from pydantic import BaseModel, Field

from ..utils import load_json_file, save_json_file, backup_file
from ..config import STDIOMCPServer, HTTPMCPServer, SSEMCPServer, DockerMCPServer

logger = structlog.get_logger()


class ServerMetadata(BaseModel):
    """Metadata for a registered MCP server."""
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    enabled: bool = True
    last_modified: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])


class RegistryInfo(BaseModel):
    """Registry configuration and metadata."""
    version: str = "1.0"
    default_targets: List[str] = Field(default_factory=lambda: ["claude_desktop", "claude_code"])
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class ServerRegistryEntry(BaseModel):
    """Complete registry entry for an MCP server."""
    # Server configuration (one of these will be present)
    type: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    image: Optional[str] = None
    
    # Registry metadata
    metadata: ServerMetadata = Field(default_factory=ServerMetadata)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get the server config as a dict (without metadata)."""
        config = {"type": self.type}
        
        if self.command is not None:
            config["command"] = self.command
        if self.args is not None:
            config["args"] = self.args
        if self.env is not None:
            config["env"] = self.env
        if self.url is not None:
            config["url"] = self.url
        if self.image is not None:
            config["image"] = self.image
            
        return config


class MCPServerRegistry:
    """Central registry for managing MCP servers."""
    
    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or Path("mcp-servers.json")
        self._cache = None
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load the registry file."""
        if self._cache is None:
            if self.registry_file.exists():
                data = load_json_file(self.registry_file)
                # Handle legacy format
                if "registry" not in data:
                    data = self._migrate_legacy_format(data)
                self._cache = data
            else:
                self._cache = {
                    "mcpServers": {},
                    "registry": RegistryInfo().dict()
                }
        return self._cache
    
    def _save_registry(self) -> bool:
        """Save the registry file."""
        if self._cache is None:
            return False
        
        try:
            # Update last_updated timestamp
            self._cache["registry"]["last_updated"] = datetime.now().isoformat()
            
            # Create backup before saving
            if self.registry_file.exists():
                backup_file(self.registry_file)
            
            save_json_file(self.registry_file, self._cache)
            logger.info("Registry saved", file=str(self.registry_file))
            return True
        except Exception as e:
            logger.error("Failed to save registry", error=str(e))
            return False
    
    def _migrate_legacy_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy mcp-servers.json format to new registry format."""
        logger.info("Migrating legacy format to registry format")
        
        migrated_servers = {}
        legacy_servers = data.get("mcpServers", {})
        
        for server_name, server_config in legacy_servers.items():
            # Create registry entry with metadata
            entry_dict = dict(server_config)
            entry_dict["metadata"] = {
                "description": f"Migrated from legacy format",
                "tags": [],
                "created": datetime.now().isoformat()[:10],
                "enabled": True,
                "last_modified": datetime.now().isoformat()[:10]
            }
            migrated_servers[server_name] = entry_dict
        
        return {
            "mcpServers": migrated_servers,
            "registry": RegistryInfo().dict()
        }
    
    def list_servers(self, enabled_only: bool = False, tags: Optional[List[str]] = None) -> Dict[str, ServerRegistryEntry]:
        """List all servers in the registry."""
        registry = self._load_registry()
        servers = {}
        
        for name, server_data in registry["mcpServers"].items():
            try:
                entry = ServerRegistryEntry(**server_data)
                
                # Filter by enabled status
                if enabled_only and not entry.metadata.enabled:
                    continue
                
                # Filter by tags
                if tags:
                    if not any(tag in entry.metadata.tags for tag in tags):
                        continue
                
                servers[name] = entry
            except Exception as e:
                logger.warning("Invalid server entry", name=name, error=str(e))
                continue
        
        return servers
    
    def get_server(self, name: str) -> Optional[ServerRegistryEntry]:
        """Get a specific server from the registry."""
        servers = self.list_servers()
        return servers.get(name)
    
    def add_server(self, name: str, server_config: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a server to the registry."""
        registry = self._load_registry()
        
        # Create server entry
        entry_dict = dict(server_config)
        if metadata:
            entry_dict["metadata"] = metadata
        else:
            entry_dict["metadata"] = ServerMetadata().dict()
        
        try:
            # Validate the entry
            entry = ServerRegistryEntry(**entry_dict)
            registry["mcpServers"][name] = entry.dict()
            
            logger.info("Added server to registry", name=name)
            return self._save_registry()
        except Exception as e:
            logger.error("Failed to add server to registry", name=name, error=str(e))
            return False
    
    def update_server(self, name: str, server_config: Optional[Dict[str, Any]] = None, 
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a server in the registry."""
        registry = self._load_registry()
        
        if name not in registry["mcpServers"]:
            logger.error("Server not found in registry", name=name)
            return False
        
        try:
            current_entry = ServerRegistryEntry(**registry["mcpServers"][name])
            
            # Update server config if provided
            if server_config:
                entry_dict = dict(server_config)
                entry_dict["metadata"] = current_entry.metadata.dict()
            else:
                entry_dict = current_entry.dict()
            
            # Update metadata if provided
            if metadata:
                entry_dict["metadata"].update(metadata)
            
            # Update last_modified timestamp
            entry_dict["metadata"]["last_modified"] = datetime.now().isoformat()[:10]
            
            # Validate updated entry
            updated_entry = ServerRegistryEntry(**entry_dict)
            registry["mcpServers"][name] = updated_entry.dict()
            
            logger.info("Updated server in registry", name=name)
            return self._save_registry()
        except Exception as e:
            logger.error("Failed to update server in registry", name=name, error=str(e))
            return False
    
    def remove_server(self, name: str) -> bool:
        """Remove a server from the registry."""
        registry = self._load_registry()
        
        if name not in registry["mcpServers"]:
            logger.warning("Server not found in registry", name=name)
            return True  # Already removed
        
        del registry["mcpServers"][name]
        logger.info("Removed server from registry", name=name)
        return self._save_registry()
    
    def enable_server(self, name: str) -> bool:
        """Enable a server in the registry."""
        return self.update_server(name, metadata={"enabled": True})
    
    def disable_server(self, name: str) -> bool:
        """Disable a server in the registry."""
        return self.update_server(name, metadata={"enabled": False})
    
    def search_servers(self, query: str) -> Dict[str, ServerRegistryEntry]:
        """Search servers by name, description, or tags."""
        servers = self.list_servers()
        results = {}
        
        query_lower = query.lower()
        
        for name, entry in servers.items():
            # Search in name
            if query_lower in name.lower():
                results[name] = entry
                continue
            
            # Search in description
            if entry.metadata.description and query_lower in entry.metadata.description.lower():
                results[name] = entry
                continue
            
            # Search in tags
            if any(query_lower in tag.lower() for tag in entry.metadata.tags):
                results[name] = entry
                continue
        
        return results
    
    def get_servers_by_tags(self, tags: List[str]) -> Dict[str, ServerRegistryEntry]:
        """Get servers that have any of the specified tags."""
        return self.list_servers(tags=tags)
    
    def get_all_tags(self) -> Set[str]:
        """Get all tags used in the registry."""
        servers = self.list_servers()
        all_tags = set()
        
        for entry in servers.values():
            all_tags.update(entry.metadata.tags)
        
        return all_tags
    
    def get_registry_info(self) -> RegistryInfo:
        """Get registry information."""
        registry = self._load_registry()
        return RegistryInfo(**registry["registry"])
    
    def update_registry_info(self, **kwargs) -> bool:
        """Update registry information."""
        registry = self._load_registry()
        registry["registry"].update(kwargs)
        return self._save_registry()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        servers = self.list_servers()
        enabled_count = sum(1 for entry in servers.values() if entry.metadata.enabled)
        
        server_types = {}
        for entry in servers.values():
            server_type = entry.type
            server_types[server_type] = server_types.get(server_type, 0) + 1
        
        all_tags = self.get_all_tags()
        
        return {
            "total_servers": len(servers),
            "enabled_servers": enabled_count,
            "disabled_servers": len(servers) - enabled_count,
            "server_types": server_types,
            "total_tags": len(all_tags),
            "tags": sorted(list(all_tags))
        }
    
    def clear_cache(self):
        """Clear the internal cache to force reload."""
        self._cache = None