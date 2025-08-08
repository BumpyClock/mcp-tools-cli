"""API key and secrets management for MCP server configurations."""

import json
import getpass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import structlog

from .config import is_api_key_placeholder

logger = structlog.get_logger()


def get_secrets_env_path() -> Path:
    """Get the path to the secrets environment file."""
    # Assume we're in a dotfiles directory structure
    current_dir = Path.cwd()
    
    # Try to find the dotfiles directory
    dotfiles_candidates = [
        current_dir,
        current_dir.parent,
        Path.home() / "dotfiles",
        Path(__file__).parent.parent.parent.parent  # From mcp-tools-cli/src/mcp_tools/
    ]
    
    for candidate in dotfiles_candidates:
        if (candidate / "mcp-servers.json").exists():
            dotfiles_dir = candidate
            break
    else:
        # Default to current directory if we can't find dotfiles
        dotfiles_dir = current_dir
    
    secrets_dir = dotfiles_dir / "secrets"
    api_keys_dir = secrets_dir / "api-keys"
    
    # Create api-keys directory if it doesn't exist
    api_keys_dir.mkdir(parents=True, exist_ok=True)
    
    return api_keys_dir / "mcp-env.json"


def load_secrets_env() -> Dict[str, Dict[str, str]]:
    """Load API keys from the secrets repository."""
    secrets_file = get_secrets_env_path()
    
    if not secrets_file.exists():
        logger.info("No secrets file found", path=str(secrets_file))
        return {}
    
    try:
        with open(secrets_file, 'r', encoding='utf-8') as f:
            secrets_data = json.load(f)
            # Filter out comment fields (keys starting with _)
            filtered_data = {k: v for k, v in secrets_data.items() if not k.startswith('_')}
            logger.info("Loaded secrets", servers=len(filtered_data), path=str(secrets_file))
            return filtered_data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning("Could not load secrets file", path=str(secrets_file), error=str(e))
        return {}


def save_secrets_env(secrets_env: Dict[str, Dict[str, str]]) -> None:
    """Save API keys to the secrets repository."""
    secrets_file = get_secrets_env_path()
    
    # Load existing data to preserve comments
    existing_data = {}
    if secrets_file.exists():
        try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    # Preserve comment fields (keys starting with _)
    final_data = {k: v for k, v in existing_data.items() if k.startswith('_')}
    final_data.update(secrets_env)
    
    # Write the updated secrets
    with open(secrets_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2)
    
    logger.info("Saved API keys to secrets file", servers=len(secrets_env), path=str(secrets_file))


def merge_secrets_with_servers(
    servers: Dict[str, Dict[str, Any]], 
    secrets_env: Dict[str, Dict[str, str]]
) -> Dict[str, Dict[str, Any]]:
    """Merge secrets environment variables into server configurations."""
    updated_servers = json.loads(json.dumps(servers))  # Deep copy
    loaded_count = 0
    
    for server_name, server_config in updated_servers.items():
        if server_name in secrets_env and 'env' in server_config:
            server_secrets = secrets_env[server_name]
            
            for env_key, env_value in server_config['env'].items():
                # If we have a secret for this env var and current value is placeholder
                if env_key in server_secrets and is_api_key_placeholder(str(env_value)):
                    secret_value = server_secrets[env_key]
                    # Only use the secret if it's not a placeholder itself
                    if not is_api_key_placeholder(str(secret_value)):
                        updated_servers[server_name]['env'][env_key] = secret_value
                        loaded_count += 1
                        logger.debug(
                            "Loaded secret for server", 
                            server=server_name, 
                            env_key=env_key
                        )
    
    if loaded_count > 0:
        logger.info("Merged secrets into server configurations", secrets_loaded=loaded_count)
    
    return updated_servers


def extract_secrets_from_servers(servers: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Extract environment variables from servers to create secrets structure."""
    secrets_env = {}
    extracted_count = 0
    
    for server_name, server_config in servers.items():
        if 'env' in server_config and isinstance(server_config['env'], dict):
            server_env = {}
            for env_key, env_value in server_config['env'].items():
                # Only extract if it looks like an API key and is not a placeholder
                if (any(keyword in env_key.upper() for keyword in ['API', 'KEY', 'TOKEN', 'SECRET', 'PASS']) and
                    not is_api_key_placeholder(str(env_value))):
                    server_env[env_key] = str(env_value)
                    extracted_count += 1
            
            if server_env:
                secrets_env[server_name] = server_env
    
    if extracted_count > 0:
        logger.info("Extracted secrets from server configurations", secrets=extracted_count)
    
    return secrets_env


def sanitize_api_keys(servers: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Replace actual API keys with placeholders for security."""
    sanitized_servers = json.loads(json.dumps(servers))  # Deep copy
    sanitized_count = 0
    
    for server_name, server_config in sanitized_servers.items():
        if 'env' in server_config and isinstance(server_config['env'], dict):
            for env_key, env_value in server_config['env'].items():
                # Check if this looks like an API key environment variable
                if any(keyword in env_key.upper() for keyword in ['API', 'KEY', 'TOKEN', 'SECRET', 'PASS']):
                    # Don't sanitize if it's already a placeholder
                    if not is_api_key_placeholder(str(env_value)):
                        # Create a descriptive placeholder based on the env var name
                        if 'API_KEY' in env_key:
                            sanitized_servers[server_name]['env'][env_key] = 'YOUR_API_KEY_HERE'
                        elif 'TOKEN' in env_key:
                            sanitized_servers[server_name]['env'][env_key] = 'YOUR_TOKEN_HERE'
                        elif 'SECRET' in env_key:
                            sanitized_servers[server_name]['env'][env_key] = 'YOUR_SECRET_HERE'
                        else:
                            sanitized_servers[server_name]['env'][env_key] = f'YOUR_{env_key}_HERE'
                        
                        sanitized_count += 1
                        logger.debug(
                            "Sanitized API key", 
                            server=server_name, 
                            env_key=env_key
                        )
    
    if sanitized_count > 0:
        logger.info("Sanitized API keys for security", sanitized=sanitized_count)
    
    return sanitized_servers


def prompt_for_api_keys(
    servers: Dict[str, Dict[str, Any]], 
    sync_secrets: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Prompt user to enter API keys for any placeholders found."""
    # Load existing secrets first if sync_secrets is enabled
    secrets_env = {}
    if sync_secrets:
        logger.info("Loading existing secrets")
        secrets_env = load_secrets_env()
        if secrets_env:
            logger.info("Found existing secrets", servers=len(secrets_env))
            # Merge existing secrets into servers
            servers = merge_secrets_with_servers(servers, secrets_env)
        else:
            logger.info("No existing secrets found")
    
    # Find all API key placeholders (after loading secrets)
    api_keys_needed = []
    for server_name, server_config in servers.items():
        if 'env' in server_config and isinstance(server_config['env'], dict):
            for env_key, env_value in server_config['env'].items():
                if is_api_key_placeholder(str(env_value)):
                    api_keys_needed.append((server_name, env_key, env_value))
    
    if not api_keys_needed:
        logger.info("No API keys needed")
        return servers
    
    logger.info("Found API keys that need configuration", count=len(api_keys_needed))
    
    updated_servers = json.loads(json.dumps(servers))  # Deep copy
    new_secrets = {}
    
    for server_name, env_key, current_value in api_keys_needed:
        logger.info(
            "Requesting API key input", 
            server=server_name, 
            env_key=env_key, 
            current_value=current_value
        )
        
        # Use typer.prompt in the CLI layer instead of getpass here
        # This function will be called from CLI with proper prompting
        # For now, we'll just log and continue
        logger.warning(
            "API key placeholder found but interactive prompting should be handled in CLI layer",
            server=server_name,
            env_key=env_key
        )
    
    return updated_servers


def interactive_api_key_prompt(server_name: str, env_key: str, current_value: str) -> Optional[str]:
    """Interactive prompt for a single API key."""
    print(f"\nServer: {server_name}")
    print(f"Environment variable: {env_key}")
    print(f"Current value: {current_value}")
    
    while True:
        api_key = getpass.getpass(f"Enter API key for {env_key} (or press Enter to skip): ").strip()
        
        if not api_key:
            print("Skipping...")
            return None
        
        # Basic validation
        if len(api_key) < 10:
            print("API key seems too short. Please enter a valid API key.")
            continue
        
        print("[OK] API key updated")
        return api_key


def update_server_with_api_key(
    servers: Dict[str, Dict[str, Any]],
    server_name: str,
    env_key: str,
    api_key: str,
    secrets_env: Dict[str, Dict[str, str]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, str]]]:
    """Update server configuration and secrets with new API key."""
    # Update the server config
    servers[server_name]['env'][env_key] = api_key
    
    # Track new secrets for saving
    if server_name not in secrets_env:
        secrets_env[server_name] = {}
    secrets_env[server_name][env_key] = api_key
    
    logger.info("Updated server with API key", server=server_name, env_key=env_key)
    
    return servers, secrets_env


def find_api_key_placeholders(servers: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """Find all API key placeholders in server configurations."""
    placeholders = []
    
    for server_name, server_config in servers.items():
        if 'env' in server_config and isinstance(server_config['env'], dict):
            for env_key, env_value in server_config['env'].items():
                if is_api_key_placeholder(str(env_value)):
                    placeholders.append((server_name, env_key, str(env_value)))
    
    return placeholders