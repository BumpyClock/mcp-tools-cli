"""Project directory detection and management for MCP Tools."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set
import structlog

from ..utils import load_json_file, save_json_file

logger = structlog.get_logger()


class ProjectDirectory:
    """Represents a project directory with Claude configuration."""
    
    def __init__(self, project_path: Path, claude_dir: Path):
        self.project_path = project_path
        self.claude_dir = claude_dir
        self.config_file = claude_dir / "claude.json"
        self.mcp_config_file = claude_dir / "mcp-servers.json"
    
    @property
    def name(self) -> str:
        """Get project name (directory name)."""
        return self.project_path.name
    
    @property
    def has_config(self) -> bool:
        """Check if project has Claude configuration."""
        return self.config_file.exists() or self.mcp_config_file.exists()
    
    @property
    def config_files(self) -> List[Path]:
        """Get list of existing config files."""
        files = []
        if self.config_file.exists():
            files.append(self.config_file)
        if self.mcp_config_file.exists():
            files.append(self.mcp_config_file)
        return files
    
    def get_servers(self) -> Dict[str, any]:
        """Get MCP servers configured for this project."""
        servers = {}
        
        # Check claude.json
        if self.config_file.exists():
            try:
                config = load_json_file(self.config_file)
                if "mcpServers" in config:
                    servers.update(config["mcpServers"])
            except Exception as e:
                logger.warning("Failed to read claude.json", project=self.name, error=str(e))
        
        # Check mcp-servers.json
        if self.mcp_config_file.exists():
            try:
                config = load_json_file(self.mcp_config_file)
                if "mcpServers" in config:
                    servers.update(config["mcpServers"])
            except Exception as e:
                logger.warning("Failed to read mcp-servers.json", project=self.name, error=str(e))
        
        return servers
    
    def set_servers(self, servers: Dict[str, any], use_mcp_file: bool = True) -> bool:
        """Set MCP servers for this project."""
        try:
            # Ensure .claude directory exists
            self.claude_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = self.mcp_config_file if use_mcp_file else self.config_file
            
            if use_mcp_file:
                # Use separate mcp-servers.json file
                config = {"mcpServers": servers}
            else:
                # Use claude.json file
                if self.config_file.exists():
                    config = load_json_file(self.config_file)
                else:
                    config = {}
                config["mcpServers"] = servers
            
            save_json_file(config_file, config)
            logger.info("Updated project servers", project=self.name, count=len(servers))
            return True
        except Exception as e:
            logger.error("Failed to update project servers", project=self.name, error=str(e))
            return False
    
    def add_server(self, name: str, server_config: Dict[str, any]) -> bool:
        """Add a single server to the project."""
        current_servers = self.get_servers()
        current_servers[name] = server_config
        return self.set_servers(current_servers)
    
    def remove_server(self, name: str) -> bool:
        """Remove a server from the project."""
        current_servers = self.get_servers()
        if name in current_servers:
            del current_servers[name]
            return self.set_servers(current_servers)
        return True  # Already removed
    
    def __str__(self) -> str:
        return f"ProjectDirectory({self.project_path})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ProjectDetector:
    """Detects and manages project directories with Claude configurations."""
    
    def __init__(self):
        self.cache = {}
    
    def find_projects_in_directory(self, root_dir: Path, max_depth: int = 3) -> List[ProjectDirectory]:
        """Find all projects in a directory tree."""
        projects = []
        
        def _scan_directory(current_dir: Path, depth: int):
            if depth > max_depth:
                return
            
            try:
                # Check if current directory has .claude subdirectory
                claude_dir = current_dir / ".claude"
                if claude_dir.exists() and claude_dir.is_dir():
                    project = ProjectDirectory(current_dir, claude_dir)
                    projects.append(project)
                
                # Recurse into subdirectories (but not .claude itself)
                for item in current_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.') and item.name != 'node_modules':
                        _scan_directory(item, depth + 1)
            except (PermissionError, OSError):
                # Skip directories we can't access
                pass
        
        _scan_directory(root_dir, 0)
        return projects
    
    def find_projects_in_common_locations(self) -> List[ProjectDirectory]:
        """Find projects in common development locations."""
        projects = []
        common_locations = []
        
        home = Path.home()
        
        # Common project directories
        potential_dirs = [
            home / "Projects",
            home / "Code", 
            home / "Development",
            home / "Dev",
            home / "src",
            home / "workspace",
            home / "repos",
            home / "Documents" / "Projects",
            home / "Desktop",  # Sometimes people put projects here
        ]
        
        # Also check current working directory and its parent
        cwd = Path.cwd()
        potential_dirs.extend([cwd, cwd.parent])
        
        for dir_path in potential_dirs:
            if dir_path.exists() and dir_path.is_dir():
                common_locations.append(dir_path)
        
        # Search each location
        for location in common_locations:
            try:
                found_projects = self.find_projects_in_directory(location, max_depth=2)
                projects.extend(found_projects)
                logger.debug("Searched for projects", location=str(location), found=len(found_projects))
            except Exception as e:
                logger.debug("Failed to search directory", location=str(location), error=str(e))
        
        # Remove duplicates (same project path)
        unique_projects = {}
        for project in projects:
            key = str(project.project_path.resolve())
            if key not in unique_projects:
                unique_projects[key] = project
        
        return list(unique_projects.values())
    
    def get_project_by_path(self, project_path: Path) -> Optional[ProjectDirectory]:
        """Get project directory for a specific path."""
        claude_dir = project_path / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            return ProjectDirectory(project_path, claude_dir)
        return None
    
    def create_project_config(self, project_path: Path) -> Optional[ProjectDirectory]:
        """Create a new Claude configuration for a project."""
        claude_dir = project_path / ".claude"
        
        try:
            claude_dir.mkdir(parents=True, exist_ok=True)
            project = ProjectDirectory(project_path, claude_dir)
            
            # Create empty mcp-servers.json
            empty_config = {"mcpServers": {}}
            save_json_file(project.mcp_config_file, empty_config)
            
            logger.info("Created project configuration", project=project.name)
            return project
        except Exception as e:
            logger.error("Failed to create project configuration", project=project_path.name, error=str(e))
            return None
    
    def get_project_stats(self, projects: List[ProjectDirectory]) -> Dict[str, any]:
        """Get statistics about the projects."""
        total_servers = 0
        projects_with_servers = 0
        server_types = {}
        
        for project in projects:
            servers = project.get_servers()
            if servers:
                projects_with_servers += 1
                total_servers += len(servers)
                
                for server_config in servers.values():
                    server_type = server_config.get("type", "unknown")
                    server_types[server_type] = server_types.get(server_type, 0) + 1
        
        return {
            "total_projects": len(projects),
            "projects_with_config": len([p for p in projects if p.has_config]),
            "projects_with_servers": projects_with_servers,
            "total_servers": total_servers,
            "server_types": server_types
        }


def find_current_project() -> Optional[ProjectDirectory]:
    """Find project in current working directory or its parents."""
    current = Path.cwd()
    
    # Check current directory and up to 5 parent directories
    for _ in range(5):
        claude_dir = current / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            return ProjectDirectory(current, claude_dir)
        
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    return None


def is_project_directory(path: Path) -> bool:
    """Check if a path is a project directory with Claude config."""
    claude_dir = path / ".claude"
    return claude_dir.exists() and claude_dir.is_dir()