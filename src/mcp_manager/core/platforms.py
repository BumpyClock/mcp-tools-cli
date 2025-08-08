"""Platform-specific MCP server management for different Claude installations."""

import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import structlog

from ..utils import load_json_file, save_json_file
from ..config import normalize_config_keys

logger = structlog.get_logger()


class PlatformManager:
    """Manage MCP servers across different Claude platforms."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.platforms = self._detect_platforms()
    
    def _detect_platforms(self) -> Dict[str, Dict[str, any]]:
        """Detect available Claude platforms and their config locations."""
        platforms = {}
        
        # Claude Desktop
        claude_desktop_path = self._get_claude_desktop_config_path()
        if claude_desktop_path and claude_desktop_path.parent.exists():
            platforms['claude_desktop'] = {
                'name': 'Claude Desktop',
                'config_path': claude_desktop_path,
                'description': 'Anthropic Claude Desktop Application',
                'icon': '🖥️',
                'available': claude_desktop_path.exists()
            }
        
        # Claude Code (CLI)
        claude_code_path = self._get_claude_code_config_path()
        if claude_code_path and claude_code_path.parent.exists():
            platforms['claude_code'] = {
                'name': 'Claude Code',
                'config_path': claude_code_path,
                'description': 'Claude CLI Tool',
                'icon': '⚡',
                'available': claude_code_path.exists()
            }
        
        # VSCode Claude Extension
        vscode_claude_path = self._get_vscode_claude_config_path()
        if vscode_claude_path and vscode_claude_path.parent.exists():
            platforms['vscode_claude'] = {
                'name': 'VSCode Claude',
                'config_path': vscode_claude_path,
                'description': 'Claude Extension for VS Code',
                'icon': '📝',
                'available': vscode_claude_path.exists()
            }
        
        # Continue.dev (if using MCP)
        continue_dev_path = self._get_continue_dev_config_path()
        if continue_dev_path and continue_dev_path.parent.exists():
            platforms['continue_dev'] = {
                'name': 'Continue.dev',
                'config_path': continue_dev_path,
                'description': 'Continue.dev VS Code Extension',
                'icon': '🔄',
                'available': continue_dev_path.exists()
            }
        
        return platforms
    
    def _get_claude_desktop_config_path(self) -> Optional[Path]:
        """Get Claude Desktop configuration file path."""
        if self.system == 'windows':
            return Path.home() / 'AppData' / 'Roaming' / 'Claude' / 'claude_desktop_config.json'
        elif self.system == 'darwin':  # macOS
            return Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json'
        elif self.system == 'linux':
            return Path.home() / '.config' / 'Claude' / 'claude_desktop_config.json'
        return None
    
    def _get_claude_code_config_path(self) -> Optional[Path]:
        """Get Claude Code (CLI) configuration file path."""
        return Path.home() / '.claude.json'
    
    def _get_vscode_claude_config_path(self) -> Optional[Path]:
        """Get VSCode Claude extension configuration file path."""
        if self.system == 'windows':
            vscode_dir = Path.home() / 'AppData' / 'Roaming' / 'Code' / 'User'
        elif self.system == 'darwin':  # macOS
            vscode_dir = Path.home() / 'Library' / 'Application Support' / 'Code' / 'User'
        elif self.system == 'linux':
            vscode_dir = Path.home() / '.config' / 'Code' / 'User'
        else:
            return None
        
        # VSCode Claude extension might store config in settings.json or separate file
        settings_path = vscode_dir / 'settings.json'
        claude_config_path = vscode_dir / 'claude_config.json'
        
        # Return claude_config.json if it exists, otherwise settings.json
        if claude_config_path.exists():
            return claude_config_path
        elif settings_path.exists():
            return settings_path
        else:
            # Return claude_config.json as the preferred location even if it doesn't exist yet
            return claude_config_path
    
    def _get_continue_dev_config_path(self) -> Optional[Path]:
        """Get Continue.dev configuration file path."""
        if self.system == 'windows':
            return Path.home() / 'AppData' / 'Roaming' / 'continue' / 'config.json'
        elif self.system == 'darwin':  # macOS
            return Path.home() / 'Library' / 'Application Support' / 'continue' / 'config.json'
        elif self.system == 'linux':
            return Path.home() / '.continue' / 'config.json'
        return None
    
    def get_available_platforms(self) -> Dict[str, Dict[str, any]]:
        """Get all available platforms."""
        return self.platforms
    
    def get_platform_servers(self, platform_key: str) -> Dict[str, any]:
        """Get MCP servers for a specific platform."""
        if platform_key not in self.platforms:
            return {}
        
        config_path = self.platforms[platform_key]['config_path']
        if not config_path.exists():
            return {}
        
        config = load_json_file(config_path)
        
        # Handle different config formats per platform
        if platform_key == 'claude_desktop':
            return config.get('mcpServers', {})
        elif platform_key == 'claude_code':
            config = normalize_config_keys(config)
            return config.get('mcpServers', {})
        elif platform_key == 'vscode_claude':
            # VSCode settings might have claude.mcpServers or similar
            return config.get('claude', {}).get('mcpServers', {})
        elif platform_key == 'continue_dev':
            # Continue.dev might have different structure
            return config.get('mcpServers', {})
        
        return {}
    
    def add_server_to_platform(self, platform_key: str, server_name: str, server_config: Dict[str, any]) -> bool:
        """Add a server to a specific platform."""
        if platform_key not in self.platforms:
            logger.error("Unknown platform", platform=platform_key)
            return False
        
        config_path = self.platforms[platform_key]['config_path']
        
        # Load existing config or create new one
        if config_path.exists():
            config = load_json_file(config_path)
        else:
            config = {}
            # Create parent directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add server based on platform format
        if platform_key == 'claude_desktop':
            if 'mcpServers' not in config:
                config['mcpServers'] = {}
            config['mcpServers'][server_name] = server_config
        
        elif platform_key == 'claude_code':
            config = normalize_config_keys(config)
            if 'mcpServers' not in config:
                config['mcpServers'] = {}
            config['mcpServers'][server_name] = server_config
        
        elif platform_key == 'vscode_claude':
            if 'claude' not in config:
                config['claude'] = {}
            if 'mcpServers' not in config['claude']:
                config['claude']['mcpServers'] = {}
            config['claude']['mcpServers'][server_name] = server_config
        
        elif platform_key == 'continue_dev':
            if 'mcpServers' not in config:
                config['mcpServers'] = {}
            config['mcpServers'][server_name] = server_config
        
        try:
            save_json_file(config_path, config)
            logger.info("Added server to platform", server=server_name, platform=platform_key)
            return True
        except Exception as e:
            logger.error("Failed to save config", error=str(e), platform=platform_key)
            return False
    
    def remove_server_from_platform(self, platform_key: str, server_name: str) -> bool:
        """Remove a server from a specific platform."""
        if platform_key not in self.platforms:
            logger.error("Unknown platform", platform=platform_key)
            return False
        
        config_path = self.platforms[platform_key]['config_path']
        if not config_path.exists():
            logger.info("Config file doesn't exist", platform=platform_key)
            return True  # Nothing to remove
        
        config = load_json_file(config_path)
        
        # Remove server based on platform format
        removed = False
        if platform_key == 'claude_desktop':
            if 'mcpServers' in config and server_name in config['mcpServers']:
                del config['mcpServers'][server_name]
                removed = True
        
        elif platform_key == 'claude_code':
            config = normalize_config_keys(config)
            if 'mcpServers' in config and server_name in config['mcpServers']:
                del config['mcpServers'][server_name]
                removed = True
        
        elif platform_key == 'vscode_claude':
            if 'claude' in config and 'mcpServers' in config['claude'] and server_name in config['claude']['mcpServers']:
                del config['claude']['mcpServers'][server_name]
                removed = True
        
        elif platform_key == 'continue_dev':
            if 'mcpServers' in config and server_name in config['mcpServers']:
                del config['mcpServers'][server_name]
                removed = True
        
        if removed:
            try:
                save_json_file(config_path, config)
                logger.info("Removed server from platform", server=server_name, platform=platform_key)
                return True
            except Exception as e:
                logger.error("Failed to save config after removal", error=str(e), platform=platform_key)
                return False
        else:
            logger.info("Server not found on platform", server=server_name, platform=platform_key)
            return True  # Server wasn't there anyway
    
    def sync_server_to_platforms(self, server_name: str, server_config: Dict[str, any], target_platforms: List[str]) -> Dict[str, bool]:
        """Sync a server to multiple platforms."""
        results = {}
        
        for platform_key in target_platforms:
            if platform_key in self.platforms:
                success = self.add_server_to_platform(platform_key, server_name, server_config)
                results[platform_key] = success
            else:
                results[platform_key] = False
        
        return results
    
    def get_server_installation_status(self, server_name: str) -> Dict[str, bool]:
        """Check which platforms have a specific server installed."""
        status = {}
        
        for platform_key, platform_info in self.platforms.items():
            servers = self.get_platform_servers(platform_key)
            status[platform_key] = server_name in servers
        
        return status
    
    def get_all_unique_servers(self) -> Dict[str, Dict[str, any]]:
        """Get all unique servers from all platforms combined."""
        all_servers = {}
        
        for platform_key in self.platforms.keys():
            servers = self.get_platform_servers(platform_key)
            for server_name, server_config in servers.items():
                if server_name not in all_servers:
                    all_servers[server_name] = server_config
        
        return all_servers


