"""Modern CLI interface for MCP Manager using Typer."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
import structlog

from .sync import (
    push_to_claude_config, pull_from_claude_config,
    validate_configurations, health_check_configurations
)
from .utils import get_default_paths
from .secrets import (
    find_api_key_placeholders, interactive_api_key_prompt,
    update_server_with_api_key, load_secrets_env, save_secrets_env
)
from .config import normalize_config_keys, get_mcp_servers_key
from .utils import load_json_file
from .interactive import run_interactive_mode
from .tui_logging import setup_cli_logging

# Initialize rich console
console = Console()

# Create Typer app
app = typer.Typer(
    name="mcp-manager",
    help="Professional MCP (Model Context Protocol) manager with TUI and CLI interface",
    add_completion=False,
    rich_markup_mode="rich"
)

# Configure structured logging
def setup_logging(verbose: bool = False):
    """Setup structured logging with rich output."""
    setup_cli_logging(verbose)


def get_file_paths(
    mcp_servers_file: Optional[Path] = None,
    claude_config_file: Optional[Path] = None
) -> tuple[Path, Path]:
    """Get file paths with defaults."""
    if not mcp_servers_file or not claude_config_file:
        default_mcp, default_claude = get_default_paths()
        mcp_servers_file = mcp_servers_file or default_mcp
        claude_config_file = claude_config_file or default_claude
    
    return mcp_servers_file, claude_config_file


def show_file_info(mcp_servers_file: Path, claude_config_file: Path):
    """Show information about configuration files."""
    table = Table(title="Configuration Files", show_header=True)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Exists", justify="center")
    
    table.add_row(
        "mcp-servers.json",
        str(mcp_servers_file),
        "✓" if mcp_servers_file.exists() else "✗"
    )
    table.add_row(
        "~/.claude.json",
        str(claude_config_file),
        "✓" if claude_config_file.exists() else "✗"
    )
    
    console.print(table)


def handle_interactive_api_keys(servers: dict, sync_secrets: bool = False) -> dict:
    """Handle interactive API key prompting."""
    placeholders = find_api_key_placeholders(servers)
    if not placeholders:
        return servers
    
    # Load existing secrets
    secrets_env = {}
    if sync_secrets:
        secrets_env = load_secrets_env()
    
    console.print("\n[yellow]🔑 API Key Configuration[/yellow]")
    console.print(f"Found {len(placeholders)} API key(s) that need to be configured:\n")
    
    updated_servers = dict(servers)  # Copy
    new_secrets = {}
    
    for server_name, env_key, current_value in placeholders:
        console.print(Panel(
            f"[bold]Server:[/bold] {server_name}\n"
            f"[bold]Environment variable:[/bold] {env_key}\n"
            f"[bold]Current value:[/bold] {current_value}",
            title=f"API Key Configuration {len(new_secrets) + 1}/{len(placeholders)}",
            border_style="yellow"
        ))
        
        # Check if we already have this secret
        existing_value = secrets_env.get(env_key, "")
        if existing_value and not existing_value.startswith("YOUR_"):
            use_existing = typer.confirm(
                f"Use existing {env_key} from secrets? (Current: {existing_value[:8]}...)",
                default=True
            )
            if use_existing:
                api_key = existing_value
            else:
                api_key = interactive_api_key_prompt(env_key)
        else:
            api_key = interactive_api_key_prompt(env_key)
        
        if api_key and api_key.strip():
            # Update the server configuration
            updated_servers = update_server_with_api_key(
                servers=updated_servers,
                server_name=server_name,
                env_key=env_key,
                api_key=api_key.strip()
            )
            
            # Store for secrets file
            if sync_secrets:
                new_secrets[env_key] = api_key.strip()
    
    # Save new secrets if needed
    if new_secrets and sync_secrets:
        secrets_env.update(new_secrets)
        save_secrets_env(secrets_env)
        console.print(f"\n[green]✓ Saved {len(new_secrets)} API key(s) to secrets file[/green]")
    
    return updated_servers


def show_help():
    """Show CLI help."""
    app()


def main():
    """CLI entry point."""
    app()


@app.command()
def tui(
    enhanced: bool = typer.Option(False, "--enhanced", "-e", help="Launch enhanced TUI with full CRUD operations")
):
    """Launch the Textual TUI interface."""
    if enhanced:
        try:
            from .tui_enhanced import run_enhanced_tui
            console.print("[bold green]Launching Enhanced TUI with full CRUD operations...[/bold green]")
            return run_enhanced_tui()
        except ImportError:
            console.print("[yellow]Enhanced TUI unavailable, falling back to basic TUI.[/yellow]")
            from .tui_app import run_tui
            return run_tui()
    else:
        try:
            from .tui_app import run_tui
            console.print("[bold blue]Launching Basic TUI...[/bold blue]")
            return run_tui()
        except ImportError:
            console.print("[bold red]TUI unavailable. Please check your installation.[/bold red]")
            return 1

@app.command()
def interactive():
    """Launch interactive configuration mode."""
    try:
        return run_interactive_mode()
    except ImportError:
        console.print("[bold red]Interactive mode unavailable. Please check your installation.[/bold red]")
        return 1

@app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Professional MCP (Model Context Protocol) manager with TUI and CLI interface"""
    setup_logging(verbose)

# CLI Commands would go here for other functionality...

if __name__ == "__main__":
    main()