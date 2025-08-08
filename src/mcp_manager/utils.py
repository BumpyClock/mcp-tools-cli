"""Utility functions for MCP tools."""

import json
import os
import shutil
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import structlog

logger = structlog.get_logger()


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON from file, return empty dict if file doesn't exist or is invalid."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)
            logger.debug("Loaded JSON file", path=str(filepath), keys=len(content) if isinstance(content, dict) else "non-dict")
            return content
    except FileNotFoundError:
        logger.info("JSON file not found", path=str(filepath))
        return {}
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON in file", path=str(filepath), error=str(e))
        return {}
    except Exception as e:
        logger.error("Error loading JSON file", path=str(filepath), error=str(e))
        return {}


def save_json_file(filepath: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """Save data to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.info("Saved JSON file", path=str(filepath))
    except Exception as e:
        logger.error("Error saving JSON file", path=str(filepath), error=str(e))
        raise


def backup_file(filepath: Path) -> Optional[Path]:
    """Create a backup of the file with timestamp."""
    if not filepath.exists():
        logger.debug("No file to backup", path=str(filepath))
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.with_suffix(f"{filepath.suffix}.backup.{timestamp}")
    
    try:
        shutil.copy2(filepath, backup_path)
        logger.info("Created backup", original=str(filepath), backup=str(backup_path))
        return backup_path
    except Exception as e:
        logger.error("Error creating backup", path=str(filepath), error=str(e))
        return None


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system().lower() == 'windows'


def wrap_command_for_windows(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap commands with cmd /c for Windows if needed."""
    if not is_windows():
        return server_config
    
    # Only process stdio type servers
    if server_config.get('type') != 'stdio':
        return server_config
    
    command = server_config.get('command', '')
    
    # Skip if already wrapped with cmd
    if command.lower() == 'cmd':
        return server_config
    
    # List of commands that need cmd /c wrapper on Windows
    commands_needing_wrapper = ['npx', 'uvx', 'node', 'python', 'py']
    
    if command.lower() in commands_needing_wrapper:
        # Create a deep copy to avoid modifying the original
        wrapped_config = json.loads(json.dumps(server_config))
        wrapped_config['command'] = 'cmd'
        
        # Handle packageOrCommand field (used by some servers like context7)
        if 'packageOrCommand' in wrapped_config and 'args' not in wrapped_config:
            package = wrapped_config.pop('packageOrCommand')
            wrapped_config['args'] = ['/c', command, package]
        else:
            # Prepare new args with /c wrapper
            original_args = wrapped_config.get('args', [])
            wrapped_config['args'] = ['/c', command] + original_args
        
        logger.debug("Wrapped command for Windows", command=command, server=server_config.get('name'))
        return wrapped_config
    
    return server_config


def wrap_servers_for_windows(servers: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Apply Windows command wrapping to all servers."""
    if not is_windows():
        logger.debug("Not Windows, skipping command wrapping")
        return servers
    
    wrapped_servers = {}
    wrapped_count = 0
    
    for server_name, server_config in servers.items():
        wrapped_config = wrap_command_for_windows(server_config)
        wrapped_servers[server_name] = wrapped_config
        
        if wrapped_config != server_config:
            wrapped_count += 1
    
    if wrapped_count > 0:
        logger.info("Wrapped commands for Windows compatibility", count=wrapped_count)
    
    return wrapped_servers


def unwrap_command_from_windows(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """Unwrap cmd /c wrapper to restore original command."""
    # Only process stdio type servers
    if server_config.get('type') != 'stdio':
        return server_config
    
    command = server_config.get('command', '')
    args = server_config.get('args', [])
    
    # Check if it's wrapped with cmd /c
    if command.lower() == 'cmd' and len(args) >= 2 and args[0] == '/c':
        # Create a deep copy to avoid modifying the original
        unwrapped_config = json.loads(json.dumps(server_config))
        
        # Extract the original command and args
        unwrapped_config['command'] = args[1]
        unwrapped_config['args'] = args[2:] if len(args) > 2 else []
        
        # Remove empty args list if no args remain
        if not unwrapped_config['args']:
            unwrapped_config.pop('args', None)
        
        logger.debug("Unwrapped Windows command", original_command=args[1])
        return unwrapped_config
    
    # Handle legacy "cmd /c npx" format in command field
    if command.lower().startswith('cmd /c '):
        unwrapped_config = json.loads(json.dumps(server_config))
        original_command = command[7:]  # Remove "cmd /c "
        unwrapped_config['command'] = original_command
        logger.debug("Unwrapped legacy Windows command", original_command=original_command)
        return unwrapped_config
    
    return server_config


def unwrap_servers_from_windows(servers: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Remove Windows command wrapping from all servers."""
    unwrapped_servers = {}
    unwrapped_count = 0
    
    for server_name, server_config in servers.items():
        unwrapped_config = unwrap_command_from_windows(server_config)
        unwrapped_servers[server_name] = unwrapped_config
        
        if unwrapped_config != server_config:
            unwrapped_count += 1
    
    if unwrapped_count > 0:
        logger.info("Unwrapped Windows commands for portability", count=unwrapped_count)
    
    return unwrapped_servers


def show_diff(
    old_servers: Dict[str, Any], 
    new_servers: Dict[str, Any], 
    mode: str
) -> None:
    """Display differences between server configurations."""
    logger.info("Showing configuration diff", mode=mode)
    
    print(f"\n=== CHANGES PREVIEW ({mode.upper()} MODE) ===")
    
    # Find additions
    added = set(new_servers.keys()) - set(old_servers.keys())
    if added:
        print(f"\n+ SERVERS TO ADD ({len(added)}):")
        for server in sorted(added):
            server_type = new_servers[server].get('type', 'unknown')
            print(f"  + {server} ({server_type})")
            logger.debug("Server to be added", server=server, type=server_type)
    
    # Find removals
    removed = set(old_servers.keys()) - set(new_servers.keys())
    if removed:
        print(f"\n- SERVERS TO REMOVE ({len(removed)}):")
        for server in sorted(removed):
            server_type = old_servers[server].get('type', 'unknown')
            print(f"  - {server} ({server_type})")
            logger.debug("Server to be removed", server=server, type=server_type)
    
    # Find modifications
    modified = []
    for server in set(old_servers.keys()) & set(new_servers.keys()):
        if old_servers[server] != new_servers[server]:
            modified.append(server)
    
    if modified:
        print(f"\n~ SERVERS TO UPDATE ({len(modified)}):")
        for server in sorted(modified):
            server_type = new_servers[server].get('type', 'unknown')
            print(f"  ~ {server} ({server_type})")
            logger.debug("Server to be modified", server=server, type=server_type)
            
            # Show detailed changes
            old_config = old_servers[server]
            new_config = new_servers[server]
            
            for key in set(old_config.keys()) | set(new_config.keys()):
                if key not in old_config:
                    print(f"    + {key}: {new_config[key]}")
                elif key not in new_config:
                    print(f"    - {key}: {old_config[key]}")
                elif old_config[key] != new_config[key]:
                    # For env variables, show a more readable diff
                    if key == 'env' and isinstance(old_config[key], dict) and isinstance(new_config[key], dict):
                        for env_key in set(old_config[key].keys()) | set(new_config[key].keys()):
                            if env_key not in old_config[key]:
                                print(f"      + env.{env_key}: {new_config[key][env_key]}")
                            elif env_key not in new_config[key]:
                                print(f"      - env.{env_key}: {old_config[key][env_key]}")
                            elif old_config[key][env_key] != new_config[key][env_key]:
                                # Hide actual API key values for security
                                old_val = old_config[key][env_key]
                                new_val = new_config[key][env_key]
                                if any(keyword in env_key.upper() for keyword in ['API', 'KEY', 'TOKEN', 'SECRET']):
                                    old_display = "***" if len(str(old_val)) > 10 else str(old_val)
                                    new_display = "***" if len(str(new_val)) > 10 else str(new_val)
                                    print(f"      ~ env.{env_key}: {old_display} -> {new_display}")
                                else:
                                    print(f"      ~ env.{env_key}: {old_val} -> {new_val}")
                    else:
                        print(f"    ~ {key}: {old_config[key]} -> {new_config[key]}")
    
    if not added and not removed and not modified:
        print("\n[OK] No changes detected")
        logger.info("No changes detected in diff")


def merge_server_config_preserve_api_keys(
    source_config: Dict[str, Any], 
    existing_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge server configs, preserving existing API keys if source has placeholders."""
    import copy
    from .config import is_api_key_placeholder
    
    # Start with a deep copy of the source config
    merged_config = copy.deepcopy(source_config)
    preserved_count = 0
    
    # If both configs have env sections, merge them intelligently
    if 'env' in source_config and 'env' in existing_config:
        source_env = source_config['env']
        existing_env = existing_config['env']
        
        # For each environment variable in the source
        for env_key, source_value in source_env.items():
            # If the source value is a placeholder and we have a real value in existing config
            if (env_key in existing_env and 
                is_api_key_placeholder(str(source_value)) and 
                not is_api_key_placeholder(str(existing_env[env_key]))):
                
                logger.debug("Preserving existing API key", env_key=env_key)
                merged_config['env'][env_key] = existing_env[env_key]
                preserved_count += 1
    
    if preserved_count > 0:
        logger.info("Preserved existing API keys during merge", count=preserved_count)
    
    return merged_config


def find_dotfiles_directory() -> Path:
    """Find the dotfiles directory in common locations."""
    candidates = [
        Path.cwd(),
        Path.cwd().parent,
        Path.home() / "dotfiles",
        Path(__file__).parent.parent.parent.parent  # From mcp-tools-cli/src/mcp_tools/
    ]
    
    for candidate in candidates:
        if (candidate / "mcp-servers.json").exists():
            logger.debug("Found dotfiles directory", path=str(candidate))
            return candidate
    
    # Default to current directory
    logger.warning("Could not find dotfiles directory, using current directory")
    return Path.cwd()


def ensure_directory_exists(path: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.info("Created directory", path=str(path))


def get_default_paths() -> Tuple[Path, Path]:
    """Get default paths for mcp-servers.json and ~/.claude.json."""
    dotfiles_dir = find_dotfiles_directory()
    mcp_servers_file = dotfiles_dir / "mcp-servers.json"
    claude_config_file = Path.home() / ".claude.json"
    
    return mcp_servers_file, claude_config_file