"""MCP server deployment logic for managing servers across platforms and projects."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import structlog

from .registry import MCPServerRegistry, ServerRegistryEntry
from .platforms import PlatformManager
from .projects import ProjectDetector, ProjectDirectory
from ..utils import load_json_file, save_json_file

logger = structlog.get_logger()


class DeploymentTarget:
    """Represents a deployment target (platform or project)."""
    
    def __init__(self, target_type: str, name: str, path: Path, description: str = ""):
        self.target_type = target_type  # "platform" or "project"
        self.name = name
        self.path = path
        self.description = description
        self.available = path.exists() if target_type == "platform" else True
    
    def __str__(self) -> str:
        return f"{self.target_type}:{self.name}"
    
    def __repr__(self) -> str:
        return f"DeploymentTarget({self.target_type}, {self.name}, {self.path})"


class DeploymentManager:
    """Manages deployment of MCP servers from registry to various targets."""
    
    def __init__(self, registry: Optional[MCPServerRegistry] = None):
        self.registry = registry or MCPServerRegistry()
        self.platform_manager = PlatformManager()
        self.project_detector = ProjectDetector()
    
    def get_all_targets(self) -> Dict[str, DeploymentTarget]:
        """Get all available deployment targets (platforms + projects)."""
        targets = {}
        
        # Get platform targets
        platforms = self.platform_manager.get_available_platforms()
        for platform_key, platform_info in platforms.items():
            target = DeploymentTarget(
                target_type="platform",
                name=f"{platform_info['icon']} {platform_info['name']}",
                path=platform_info['config_path'],
                description=platform_info['description']
            )
            targets[f"platform:{platform_key}"] = target
        
        # Get project targets
        projects = self.project_detector.find_projects_in_common_locations()
        for project in projects:
            target = DeploymentTarget(
                target_type="project",
                name=f"📁 {project.name}",
                path=project.project_path,
                description=f"Project: {project.project_path}"
            )
            targets[f"project:{project.project_path}"] = target
        
        return targets
    
    def get_platform_targets(self) -> Dict[str, DeploymentTarget]:
        """Get only platform targets."""
        targets = self.get_all_targets()
        return {k: v for k, v in targets.items() if v.target_type == "platform"}
    
    def get_project_targets(self) -> Dict[str, DeploymentTarget]:
        """Get only project targets."""
        targets = self.get_all_targets()
        return {k: v for k, v in targets.items() if v.target_type == "project"}
    
    def deploy_server_to_platform(self, server_name: str, platform_key: str, 
                                 use_placeholders: bool = True) -> bool:
        """Deploy a server to a specific platform."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            logger.error("Server not found in registry", server=server_name)
            return False
        
        # Get server config
        server_config = server_entry.get_config_dict()
        
        # Replace API keys with placeholders if requested
        if use_placeholders and server_config.get("env"):
            server_config = self._replace_api_keys_with_placeholders(server_config)
        
        # Deploy using platform manager
        success = self.platform_manager.add_server_to_platform(platform_key, server_name, server_config)
        
        if success:
            logger.info("Deployed server to platform", server=server_name, platform=platform_key)
        else:
            logger.error("Failed to deploy server to platform", server=server_name, platform=platform_key)
        
        return success
    
    def deploy_server_to_project(self, server_name: str, project_path: Path, 
                               use_real_keys: bool = True) -> bool:
        """Deploy a server to a specific project."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            logger.error("Server not found in registry", server=server_name)
            return False
        
        # Get or create project
        project = self.project_detector.get_project_by_path(project_path)
        if not project:
            project = self.project_detector.create_project_config(project_path)
            if not project:
                logger.error("Failed to create project config", project=project_path)
                return False
        
        # Get server config (with real API keys if requested)
        server_config = server_entry.get_config_dict()
        if not use_real_keys and server_config.get("env"):
            server_config = self._replace_api_keys_with_placeholders(server_config)
        
        # Deploy to project
        success = project.add_server(server_name, server_config)
        
        if success:
            logger.info("Deployed server to project", server=server_name, project=project.name)
        else:
            logger.error("Failed to deploy server to project", server=server_name, project=project.name)
        
        return success
    
    def deploy_servers_bulk(self, server_names: List[str], target_keys: List[str], 
                          deployment_options: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, bool]]:
        """Deploy multiple servers to multiple targets."""
        options = deployment_options or {}
        results = {}
        
        for server_name in server_names:
            results[server_name] = {}
            
            for target_key in target_keys:
                if target_key.startswith("platform:"):
                    platform_key = target_key.split(":", 1)[1]
                    use_placeholders = options.get("use_placeholders", True)
                    success = self.deploy_server_to_platform(server_name, platform_key, use_placeholders)
                
                elif target_key.startswith("project:"):
                    project_path = Path(target_key.split(":", 1)[1])
                    use_real_keys = options.get("use_real_keys", True)
                    success = self.deploy_server_to_project(server_name, project_path, use_real_keys)
                
                else:
                    logger.error("Unknown target type", target=target_key)
                    success = False
                
                results[server_name][target_key] = success
        
        return results
    
    def undeploy_server_from_platform(self, server_name: str, platform_key: str) -> bool:
        """Remove a server from a platform."""
        success = self.platform_manager.remove_server_from_platform(platform_key, server_name)
        
        if success:
            logger.info("Undeployed server from platform", server=server_name, platform=platform_key)
        else:
            logger.error("Failed to undeploy server from platform", server=server_name, platform=platform_key)
        
        return success
    
    def undeploy_server_from_project(self, server_name: str, project_path: Path) -> bool:
        """Remove a server from a project."""
        project = self.project_detector.get_project_by_path(project_path)
        if not project:
            logger.warning("Project not found", project=project_path)
            return True  # Already not deployed
        
        success = project.remove_server(server_name)
        
        if success:
            logger.info("Undeployed server from project", server=server_name, project=project.name)
        else:
            logger.error("Failed to undeploy server from project", server=server_name, project=project.name)
        
        return success
    
    def get_server_deployment_status(self, server_name: str) -> Dict[str, bool]:
        """Get deployment status of a server across all targets."""
        status = {}
        
        # Check platform deployments
        platform_status = self.platform_manager.get_server_installation_status(server_name)
        for platform_key, installed in platform_status.items():
            status[f"platform:{platform_key}"] = installed
        
        # Check project deployments
        projects = self.project_detector.find_projects_in_common_locations()
        for project in projects:
            servers = project.get_servers()
            is_deployed = server_name in servers
            status[f"project:{project.project_path}"] = is_deployed
        
        return status
    
    def get_deployment_matrix(self) -> Dict[str, Dict[str, bool]]:
        """Get full deployment matrix (all servers x all targets)."""
        servers = self.registry.list_servers()
        matrix = {}
        
        for server_name in servers.keys():
            matrix[server_name] = self.get_server_deployment_status(server_name)
        
        return matrix
    
    def sync_server_deployments(self, server_name: str, source_target: str, 
                              destination_targets: List[str]) -> Dict[str, bool]:
        """Sync a server from one target to multiple other targets."""
        results = {}
        
        # Get server config from source
        server_config = None
        
        if source_target.startswith("platform:"):
            platform_key = source_target.split(":", 1)[1]
            platform_servers = self.platform_manager.get_platform_servers(platform_key)
            server_config = platform_servers.get(server_name)
        
        elif source_target.startswith("project:"):
            project_path = Path(source_target.split(":", 1)[1])
            project = self.project_detector.get_project_by_path(project_path)
            if project:
                project_servers = project.get_servers()
                server_config = project_servers.get(server_name)
        
        if not server_config:
            logger.error("Server not found at source target", server=server_name, source=source_target)
            return {target: False for target in destination_targets}
        
        # Deploy to destination targets
        for target_key in destination_targets:
            if target_key.startswith("platform:"):
                platform_key = target_key.split(":", 1)[1]
                success = self.platform_manager.add_server_to_platform(platform_key, server_name, server_config)
            
            elif target_key.startswith("project:"):
                project_path = Path(target_key.split(":", 1)[1])
                project = self.project_detector.get_project_by_path(project_path)
                if not project:
                    project = self.project_detector.create_project_config(project_path)
                
                if project:
                    success = project.add_server(server_name, server_config)
                else:
                    success = False
            
            else:
                success = False
            
            results[target_key] = success
        
        return results
    
    def _replace_api_keys_with_placeholders(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace real API key values with placeholders."""
        config_copy = dict(server_config)
        
        if "env" in config_copy and config_copy["env"]:
            env_copy = dict(config_copy["env"])
            
            for key, value in env_copy.items():
                # Common API key patterns
                if any(pattern in key.upper() for pattern in ["KEY", "TOKEN", "SECRET", "PASSWORD"]):
                    if value and value != f"YOUR_{key.upper()}_HERE":
                        env_copy[key] = f"YOUR_{key.upper()}_HERE"
            
            config_copy["env"] = env_copy
        
        return config_copy
    
    def get_deployment_suggestions(self, server_name: str) -> Dict[str, List[str]]:
        """Get suggested deployment targets for a server based on its type and tags."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            return {"platforms": [], "projects": []}
        
        suggestions = {"platforms": [], "projects": []}
        
        # Get registry defaults
        registry_info = self.registry.get_registry_info()
        default_platforms = registry_info.default_targets
        
        # Suggest default platforms
        platforms = self.platform_manager.get_available_platforms()
        for platform_key in default_platforms:
            if platform_key in platforms and platforms[platform_key]["available"]:
                suggestions["platforms"].append(platform_key)
        
        # Suggest projects based on server tags
        if "development" in server_entry.metadata.tags or "dev" in server_entry.metadata.tags:
            # Suggest all projects for development-tagged servers
            projects = self.project_detector.find_projects_in_common_locations()
            suggestions["projects"] = [str(p.project_path) for p in projects[:5]]  # Limit to 5
        
        return suggestions