"""Core synchronization logic for MCP server configurations."""

import sys
from pathlib import Path
from typing import Dict, Any
import structlog

from .config import normalize_config_keys, get_mcp_servers_key
from .utils import (
    load_json_file, save_json_file, backup_file, show_diff, 
    wrap_servers_for_windows, unwrap_servers_from_windows,
    merge_server_config_preserve_api_keys
)
from .validators import validate_all_servers, health_check_all_servers
from .secrets import (
    load_secrets_env, save_secrets_env, merge_secrets_with_servers,
    extract_secrets_from_servers, sanitize_api_keys, find_api_key_placeholders
)

logger = structlog.get_logger()


def merge_mcp_servers(
    source_servers: Dict[str, Any], 
    target_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge MCP servers from source into target configuration, preserving existing API keys."""
    # Initialize mcpServers if it doesn't exist
    if 'mcpServers' not in target_config:
        target_config['mcpServers'] = {}
    
    # Get existing servers
    existing_servers = target_config['mcpServers']
    merged_count = 0
    new_count = 0
    
    # Merge each server from source
    for server_name, server_config in source_servers.items():
        if server_name in existing_servers:
            logger.debug("Updating existing server", server=server_name)
            # Preserve existing API keys when merging
            merged_config = merge_server_config_preserve_api_keys(
                source_config=server_config,
                existing_config=existing_servers[server_name]
            )
            existing_servers[server_name] = merged_config
            merged_count += 1
        else:
            logger.debug("Adding new server", server=server_name)
            existing_servers[server_name] = server_config
            new_count += 1
    
    logger.info("Merged MCP servers", new=new_count, updated=merged_count, total=len(source_servers))
    return target_config


def push_to_claude_config(
    mcp_servers_file: Path, 
    claude_config_file: Path, 
    dry_run: bool = False,
    health_check: bool = False, 
    sync_secrets: bool = False
) -> bool:
    """Push MCP servers from mcp-servers.json to ~/.claude.json."""
    logger.info(
        "Starting push operation", 
        source=str(mcp_servers_file),
        target=str(claude_config_file),
        dry_run=dry_run,
        health_check=health_check,
        sync_secrets=sync_secrets
    )
    
    # Load MCP servers configuration
    mcp_config = load_json_file(mcp_servers_file)
    mcp_config = normalize_config_keys(mcp_config)
    
    servers_key = get_mcp_servers_key(mcp_config)
    if not servers_key:
        logger.error("mcp-servers.json must contain 'mcpServers' or 'mcps' key")
        return False
    
    source_servers = mcp_config[servers_key]
    logger.info("Found MCP servers to push", count=len(source_servers))
    
    # Validate configurations
    logger.info("Validating server configurations")
    all_valid, errors = validate_all_servers(source_servers)
    if not all_valid:
        logger.error("Configuration validation failed", errors=errors)
        for error in errors:
            print(f"  • {error}")
        return False
    
    logger.info("All server configurations are valid")
    
    # Load and merge secrets if enabled
    if sync_secrets and not dry_run:
        logger.info("Loading existing secrets")
        secrets_env = load_secrets_env()
        if secrets_env:
            source_servers = merge_secrets_with_servers(source_servers, secrets_env)
    
    # Apply Windows command wrapping if on Windows
    source_servers = wrap_servers_for_windows(source_servers)
    
    # Health check if requested
    if health_check:
        logger.info("Performing health check on servers")
        healthy_count, total_count, issues = health_check_all_servers(source_servers)
        if issues:
            logger.warning("Health check found issues", issues=len(issues), healthy=healthy_count, total=total_count)
            for issue in issues:
                print(f"  • {issue}")
            
            if healthy_count == 0:
                logger.error("No servers are healthy, aborting")
                return False
        else:
            logger.info("All servers passed health check")
    
    # Load existing Claude configuration
    claude_config = load_json_file(claude_config_file)
    current_servers = claude_config.get('mcpServers', {})
    
    # Show diff
    show_diff(current_servers, source_servers, 'push')
    
    if dry_run:
        logger.info("Dry run complete, no changes made")
        return True
    
    # Check for API key placeholders
    placeholders = find_api_key_placeholders(source_servers)
    if placeholders:
        logger.warning("Found API key placeholders that need to be filled", count=len(placeholders))
        print("\nAPI key placeholders found:")
        for server_name, env_key, current_value in placeholders:
            print(f"  • {server_name}.{env_key}: {current_value}")
        print("\nUse --sync-secrets to automatically load API keys from secrets repository,")
        print("or fill them manually in the configuration file.")
    
    # Create backup if file exists
    if claude_config_file.exists():
        backup_path = backup_file(claude_config_file)
        if backup_path:
            logger.info("Created backup", path=str(backup_path))
    
    # Merge configurations
    logger.info("Merging configurations")
    updated_config = merge_mcp_servers(source_servers, claude_config)
    
    # Write updated configuration
    try:
        save_json_file(claude_config_file, updated_config)
        logger.info("Successfully updated Claude configuration", 
                   file=str(claude_config_file),
                   total_servers=len(updated_config.get('mcpServers', {})))
        return True
    except Exception as e:
        logger.error("Failed to save Claude configuration", error=str(e))
        return False


def pull_from_claude_config(
    mcp_servers_file: Path,
    claude_config_file: Path,
    dry_run: bool = False,
    health_check: bool = False,
    sync_secrets: bool = False
) -> bool:
    """Pull MCP servers from ~/.claude.json to mcp-servers.json."""
    logger.info(
        "Starting pull operation",
        source=str(claude_config_file),
        target=str(mcp_servers_file),
        dry_run=dry_run,
        health_check=health_check,
        sync_secrets=sync_secrets
    )
    
    # Load existing Claude configuration
    claude_config = load_json_file(claude_config_file)
    claude_config = normalize_config_keys(claude_config)
    
    servers_key = get_mcp_servers_key(claude_config)
    if not servers_key or not claude_config.get(servers_key):
        logger.info("No MCP servers found in Claude configuration")
        return True
    
    claude_servers = claude_config[servers_key]
    logger.info("Found MCP servers in Claude config", count=len(claude_servers))
    
    # Validate configurations
    logger.info("Validating server configurations")
    all_valid, errors = validate_all_servers(claude_servers)
    if not all_valid:
        logger.error("Configuration validation failed", errors=errors)
        for error in errors:
            print(f"  • {error}")
        return False
    
    logger.info("All server configurations are valid")
    
    # Health check if requested
    if health_check:
        logger.info("Performing health check on servers")
        healthy_count, total_count, issues = health_check_all_servers(claude_servers)
        if issues:
            logger.warning("Health check found issues", issues=len(issues))
            for issue in issues:
                print(f"  • {issue}")
            
            if healthy_count == 0:
                logger.error("No servers are healthy, aborting")
                return False
        else:
            logger.info("All servers passed health check")
    
    # Load existing mcp-servers.json
    mcp_config = load_json_file(mcp_servers_file)
    mcp_config = normalize_config_keys(mcp_config)
    
    # Ensure we have the right key structure
    if 'mcpServers' not in mcp_config:
        mcp_config = {'mcpServers': {}}
    
    current_servers = mcp_config['mcpServers']
    
    # Unwrap Windows commands for portability
    logger.info("Unwrapping Windows commands for cross-platform compatibility")
    claude_servers = unwrap_servers_from_windows(claude_servers)
    
    # Extract and save secrets if sync_secrets is enabled
    if sync_secrets and not dry_run:
        logger.info("Extracting secrets from Claude configuration")
        extracted_secrets = extract_secrets_from_servers(claude_servers)
        if extracted_secrets:
            # Load existing secrets and merge
            existing_secrets = load_secrets_env()
            merged_secrets = dict(existing_secrets)
            for server_name, server_secrets in extracted_secrets.items():
                if server_name not in merged_secrets:
                    merged_secrets[server_name] = {}
                merged_secrets[server_name].update(server_secrets)
            
            save_secrets_env(merged_secrets)
            logger.info("Extracted and saved secrets", servers=len(extracted_secrets))
        else:
            logger.info("No secrets found to extract")
    
    # Sanitize API keys for security
    logger.info("Replacing API keys with placeholders for version control safety")
    claude_servers = sanitize_api_keys(claude_servers)
    
    # Show diff
    show_diff(current_servers, claude_servers, 'pull')
    
    if dry_run:
        logger.info("Dry run complete, no changes made")
        return True
    
    # Merge servers from Claude config
    new_servers = []
    updated_servers = []
    
    for server_name, server_config in claude_servers.items():
        if server_name in current_servers:
            if current_servers[server_name] != server_config:
                updated_servers.append(server_name)
        else:
            new_servers.append(server_name)
        current_servers[server_name] = server_config
    
    # Create backup if file exists
    if mcp_servers_file.exists():
        backup_path = backup_file(mcp_servers_file)
        if backup_path:
            logger.info("Created backup", path=str(backup_path))
    
    # Write updated mcp-servers.json
    try:
        save_json_file(mcp_servers_file, mcp_config, indent=4)
        
        logger.info("Successfully updated mcp-servers.json",
                   file=str(mcp_servers_file),
                   new_servers=len(new_servers),
                   updated_servers=len(updated_servers),
                   total_servers=len(current_servers))
        
        if new_servers:
            logger.info("Added new servers", servers=new_servers)
        if updated_servers:
            logger.info("Updated existing servers", servers=updated_servers)
        
        return True
    except Exception as e:
        logger.error("Failed to save mcp-servers.json", error=str(e))
        return False


def validate_configurations(
    mcp_servers_file: Path,
    claude_config_file: Path
) -> bool:
    """Validate both configuration files."""
    logger.info("Validating configuration files")
    
    all_valid = True
    
    # Validate mcp-servers.json
    if mcp_servers_file.exists():
        logger.info("Validating mcp-servers.json", file=str(mcp_servers_file))
        mcp_config = load_json_file(mcp_servers_file)
        mcp_config = normalize_config_keys(mcp_config)
        
        servers_key = get_mcp_servers_key(mcp_config)
        if servers_key:
            source_servers = mcp_config[servers_key]
            valid, errors = validate_all_servers(source_servers)
            if not valid:
                logger.error("mcp-servers.json validation failed", errors=errors)
                print(f"mcp-servers.json validation errors:")
                for error in errors:
                    print(f"  • {error}")
                all_valid = False
            else:
                logger.info("mcp-servers.json validation passed", servers=len(source_servers))
        else:
            logger.warning("No MCP servers found in mcp-servers.json")
    else:
        logger.warning("mcp-servers.json does not exist")
    
    # Validate ~/.claude.json
    if claude_config_file.exists():
        logger.info("Validating Claude configuration", file=str(claude_config_file))
        claude_config = load_json_file(claude_config_file)
        claude_config = normalize_config_keys(claude_config)
        
        servers_key = get_mcp_servers_key(claude_config)
        if servers_key and claude_config.get(servers_key):
            claude_servers = claude_config[servers_key]
            valid, errors = validate_all_servers(claude_servers)
            if not valid:
                logger.error("Claude configuration validation failed", errors=errors)
                print(f"~/.claude.json validation errors:")
                for error in errors:
                    print(f"  • {error}")
                all_valid = False
            else:
                logger.info("Claude configuration validation passed", servers=len(claude_servers))
        else:
            logger.info("No MCP servers found in Claude configuration")
    else:
        logger.warning("Claude configuration file does not exist")
    
    if all_valid:
        logger.info("All configuration files are valid")
        print("✓ All configuration files are valid")
    
    return all_valid


def health_check_configurations(
    mcp_servers_file: Path,
    claude_config_file: Path
) -> bool:
    """Perform health check on both configuration files."""
    logger.info("Performing health check on configuration files")
    
    all_healthy = True
    
    # Health check mcp-servers.json
    if mcp_servers_file.exists():
        logger.info("Health checking mcp-servers.json", file=str(mcp_servers_file))
        mcp_config = load_json_file(mcp_servers_file)
        mcp_config = normalize_config_keys(mcp_config)
        
        servers_key = get_mcp_servers_key(mcp_config)
        if servers_key:
            source_servers = mcp_config[servers_key]
            healthy_count, total_count, issues = health_check_all_servers(source_servers)
            
            print(f"\nmcp-servers.json health check:")
            print(f"  Healthy servers: {healthy_count}/{total_count}")
            
            if issues:
                print("  Issues found:")
                for issue in issues:
                    print(f"    • {issue}")
                all_healthy = False
            else:
                print("  ✓ All servers are healthy")
        else:
            logger.info("No MCP servers found in mcp-servers.json")
    
    # Health check ~/.claude.json
    if claude_config_file.exists():
        logger.info("Health checking Claude configuration", file=str(claude_config_file))
        claude_config = load_json_file(claude_config_file)
        claude_config = normalize_config_keys(claude_config)
        
        servers_key = get_mcp_servers_key(claude_config)
        if servers_key and claude_config.get(servers_key):
            claude_servers = claude_config[servers_key]
            healthy_count, total_count, issues = health_check_all_servers(claude_servers)
            
            print(f"\n~/.claude.json health check:")
            print(f"  Healthy servers: {healthy_count}/{total_count}")
            
            if issues:
                print("  Issues found:")
                for issue in issues:
                    print(f"    • {issue}")
                all_healthy = False
            else:
                print("  ✓ All servers are healthy")
        else:
            logger.info("No MCP servers found in Claude configuration")
    
    if all_healthy:
        logger.info("All servers passed health check")
        print("\n✓ All servers passed health check")
    
    return all_healthy