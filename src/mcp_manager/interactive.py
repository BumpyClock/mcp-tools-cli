"""Interactive CLI functionality for MCP Tools."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import structlog
import msvcrt  # Windows-specific for single key press

from .utils import get_default_paths, load_json_file
from .config import normalize_config_keys, get_mcp_servers_key
from .core.platforms import PlatformManager
from .tui_logging import setup_tui_logging, TUILogger
from .core.registry import MCPServerRegistry
from .core.deployment import DeploymentManager
from .core.projects import ProjectDetector, find_current_project

logger = structlog.get_logger()
console = Console()

class InteractiveMenu:
    """Interactive menu system for MCP Tools."""
    
    def __init__(self):
        self.mcp_servers_file, self.claude_config_file = get_default_paths()
        self.current_config = None
        self.secrets_env = {}
        self.platform_manager = PlatformManager()
        self.tui_logger = setup_tui_logging(console)
        self.show_debug = False
        
        # New registry-based system
        self.registry = MCPServerRegistry(self.mcp_servers_file)
        self.deployment_manager = DeploymentManager(self.registry)
        self.project_detector = ProjectDetector()
    
    def clear_screen(self):
        """Clear the screen for a clean TUI experience."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def safe_questionary_ask(self, questionary_obj, allow_none=False):
        """Safely ask questionary questions with ESC/Ctrl+C handling."""
        try:
            result = questionary_obj.ask()
            if result is None and not allow_none:
                # User pressed ESC - go back to previous menu
                return None
            return result
        except (KeyboardInterrupt, EOFError):
            # User pressed Ctrl+C or ESC - exit gracefully
            console.print("\n👋 Goodbye!")
            sys.exit(0)
    
    def get_single_key_choice(self, choices_list, key_mappings, question="Select option:", is_main_menu=False):
        """Get single key press choice with Windows support."""
        if is_main_menu:
            console.print("[dim]Press a key for instant selection. 'q' to quit, ESC to exit[/dim]\n")
        else:
            console.print("[dim]Press a key for instant selection. 'q' to quit, ESC to go back[/dim]\n")
        
        # Show options
        for choice_text in choices_list:
            console.print(f"  {choice_text}")
        
        console.print(f"\n[bold]{question}[/bold] [dim](Press a key)[/dim]")
        
        try:
            if hasattr(msvcrt, 'getch'):  # Windows
                while True:  # Loop until we get a valid key or exit command
                    try:
                        key_bytes = msvcrt.getch()
                        
                        # Handle special multi-byte keys (like arrow keys)
                        if key_bytes == b'\xe0' or key_bytes == b'\x00':
                            # This is a special key prefix, read the next byte
                            special_key = msvcrt.getch()
                            # Ignore special keys like arrow keys - just continue the loop
                            console.print("[dim](Invalid key, try a number key)[/dim]", end="\r")
                            continue
                        
                        # Try to decode as UTF-8
                        key = key_bytes.decode('utf-8').lower()
                        
                        # Handle special keys
                        if key == 'q':  # 'q' always quits immediately
                            console.print("\n👋 Goodbye!")
                            sys.exit(0)
                        elif key == '\x1b':  # ESC
                            if is_main_menu:
                                console.print("\n👋 Goodbye!")
                                sys.exit(0)
                            else:
                                console.print("\n[yellow]← Going back...[/yellow]")
                                return None  # Signal to go back
                        elif key == '\x03':  # Ctrl+C
                            console.print("\n👋 Goodbye!")
                            sys.exit(0)
                        elif key in key_mappings:
                            choice = key_mappings[key]
                            console.print(f"\n[green]→[/green] {choice}")
                            return choice
                        else:
                            # Invalid key, show message and continue loop
                            console.print(f"[yellow]Invalid key '{key}'. Try a number key or 'q' to quit.[/yellow]", end="\r")
                            continue
                            
                    except UnicodeDecodeError:
                        # Handle non-UTF8 keys (like some special keys)
                        console.print("[dim](Invalid key, try a number key)[/dim]", end="\r")
                        continue
                        
            else:
                # Not Windows, use questionary
                return self.safe_questionary_ask(
                    questionary.select(
                        question,
                        choices=choices_list
                    )
                )
        except Exception:
            # Fallback to questionary
            return self.safe_questionary_ask(
                questionary.select(
                    question,
                    choices=choices_list
                )
            )

    def welcome(self):
        """Show welcome screen."""
        self.clear_screen()
        welcome_text = Text()
        welcome_text.append("🔧 ", style="bright_blue")
        welcome_text.append("MCP Tools", style="bold bright_blue")
        welcome_text.append(" - Interactive Mode\n", style="bright_blue")
        welcome_text.append("Manage your MCP server configurations with ease", style="dim")
        
        console.print(Panel(
            welcome_text,
            title="Welcome",
            border_style="bright_blue",
            padding=(1, 2)
        ))
        console.print()
    
    def show_current_status(self):
        """Show current configuration status."""
        table = Table(title="📊 Configuration Status", show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Path", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Servers", justify="center")
        
        # Check mcp-servers.json
        mcp_exists = self.mcp_servers_file.exists()
        mcp_servers_count = 0
        if mcp_exists:
            try:
                mcp_config = load_json_file(self.mcp_servers_file)
                mcp_config = normalize_config_keys(mcp_config)
                servers_key = get_mcp_servers_key(mcp_config)
                mcp_servers_count = len(mcp_config.get(servers_key, {})) if servers_key else 0
            except:
                pass
        
        table.add_row(
            "mcp-servers.json",
            str(self.mcp_servers_file),
            "✓ Found" if mcp_exists else "❌ Missing",
            str(mcp_servers_count)
        )
        
        # Check ~/.claude.json
        claude_exists = self.claude_config_file.exists()
        claude_servers_count = 0
        if claude_exists:
            try:
                claude_config = load_json_file(self.claude_config_file)
                claude_config = normalize_config_keys(claude_config)
                servers_key = get_mcp_servers_key(claude_config)
                claude_servers_count = len(claude_config.get(servers_key, {})) if servers_key else 0
            except:
                pass
        
        table.add_row(
            "~/.claude.json",
            str(self.claude_config_file),
            "✓ Found" if claude_exists else "❌ Missing",
            str(claude_servers_count)
        )
        
        console.print(table)
        console.print()
    
    def main_menu(self):
        """Show main interactive menu."""
        while True:
            self.clear_screen()
            
            # Show header
            header_text = Text()
            header_text.append("🔧 MCP Tools", style="bold bright_blue")
            header_text.append(" - Interactive Configuration Manager", style="bright_blue")
            console.print(Panel(header_text, border_style="bright_blue"))
            console.print()
            
            self.show_current_status()
            
            choices = [
                "1. 📦 Manage Server Registry",
                "2. 🚀 Deploy Servers to Platforms/Projects", 
                "3. 📋 View Deployment Status",
                "4. 📁 Change file paths",
                f"d. 🐛 Debug messages: {'ON' if self.show_debug else 'OFF'}",
                "q. ❌ Exit"
            ]
            
            # Create key mappings for main menu
            key_mappings = {
                '1': "1. 📦 Manage Server Registry",
                '2': "2. 🚀 Deploy Servers to Platforms/Projects",
                '3': "3. 📋 View Deployment Status",
                '4': "4. 📁 Change file paths",
                'd': f"d. 🐛 Debug messages: {'ON' if self.show_debug else 'OFF'}"
            }
            
            choice = self.get_single_key_choice(choices, key_mappings, "What would you like to do?", is_main_menu=True)
            
            if not choice:  # User pressed ESC or Ctrl+C
                console.print("\n👋 Goodbye!")
                sys.exit(0)
            
            if choice.startswith("1.") or choice.startswith("📦"):
                self.interactive_registry_management()
            elif choice.startswith("2.") or choice.startswith("🚀"):
                self.interactive_deployment()
            elif choice.startswith("3.") or choice.startswith("📋"):
                self.interactive_deployment_status()
            elif choice.startswith("4.") or choice.startswith("📁"):
                self.interactive_file_paths()
            elif choice.startswith("d.") or choice.startswith("🐛"):
                self.toggle_debug_display()
            elif choice.startswith("q.") or choice.startswith("❌"):
                console.print("\n👋 Goodbye!")
                break

    def interactive_file_paths(self):
        """Interactive file path configuration."""
        self.clear_screen()
        
        console.print(Panel(
            "[bold blue]📁 File Path Configuration[/bold blue]\n"
            "Customize configuration file locations",
            title="File Path Configuration",
            border_style="cyan"
        ))
        console.print()
        
        console.print(f"Current mcp-servers.json path: [cyan]{self.mcp_servers_file}[/cyan]")
        console.print(f"Current ~/.claude.json path: [cyan]{self.claude_config_file}[/cyan]")
        
        if questionary.confirm("Change mcp-servers.json path?", default=False).ask():
            new_path = questionary.path("Enter new mcp-servers.json path:").ask()
            if new_path:
                self.mcp_servers_file = Path(new_path)
                console.print(f"[green]✅ Updated mcp-servers.json path to: {self.mcp_servers_file}[/green]")
        
        if questionary.confirm("Change ~/.claude.json path?", default=False).ask():
            new_path = questionary.path("Enter new ~/.claude.json path:").ask()
            if new_path:
                self.claude_config_file = Path(new_path)
                console.print(f"[green]✅ Updated ~/.claude.json path to: {self.claude_config_file}[/green]")
        
        questionary.press_any_key_to_continue().ask()

    def toggle_debug_display(self):
        """Toggle debug message display."""
        self.show_debug = self.tui_logger.toggle_debug_visibility()
        
        status = "enabled" if self.show_debug else "disabled"
        console.print(f"\n[cyan]Debug messages {status}[/cyan]")
        
        if self.show_debug:
            console.print("[dim]Debug messages will appear at the bottom of screens[/dim]")
            # Show current messages
            self.tui_logger.show_debug_panel()
        else:
            console.print("[dim]Debug messages are now hidden[/dim]")
        
        questionary.press_any_key_to_continue().ask()

    def interactive_registry_management(self):
        """Interactive MCP server registry management."""
        while True:
            self.clear_screen()
            
            console.print(Panel(
                "[bold blue]📦 MCP Server Registry[/bold blue]\n"
                "Manage your central collection of MCP servers",
                title="Server Registry",
                border_style="blue"
            ))
            console.print()
            
            # Show registry stats
            stats = self.registry.get_stats()
            console.print(f"[cyan]📊 Registry Stats:[/cyan]")
            console.print(f"  Total servers: {stats['total_servers']}")
            console.print(f"  Enabled: {stats['enabled_servers']}, Disabled: {stats['disabled_servers']}")
            if stats['server_types']:
                types_str = ", ".join(f"{k}: {v}" for k, v in stats['server_types'].items())
                console.print(f"  Types: {types_str}")
            console.print()
            
            choices = [
                "1. 📋 Browse servers in registry",
                "2. ➕ Add server to registry",
                "3. ✏️ Edit server in registry",
                "4. 🗑️ Remove server from registry",
                "b. 🔙 Back to main menu"
            ]
            
            # Create key mappings for instant selection
            key_mappings = {
                '1': "1. 📋 Browse servers in registry",
                '2': "2. ➕ Add server to registry",
                '3': "3. ✏️ Edit server in registry",
                '4': "4. 🗑️ Remove server from registry",
                'b': "b. 🔙 Back to main menu"
            }
            
            choice = self.get_single_key_choice(choices, key_mappings, "Registry Management Options:")
            
            if not choice or choice is None or choice.startswith("b.") or choice.startswith("🔙"):
                break
            elif choice.startswith("1.") or choice.startswith("📋"):
                self.browse_registry()
            elif choice.startswith("2.") or choice.startswith("➕"):
                self.add_server_to_registry()
            elif choice.startswith("3.") or choice.startswith("✏️"):
                self.edit_server_in_registry()
            elif choice.startswith("4.") or choice.startswith("🗑️"):
                self.remove_server_from_registry()
    
    def browse_registry(self):
        """Browse servers in the registry."""
        self.clear_screen()
        
        console.print(Panel(
            "[cyan]📋 Browse Server Registry[/cyan]\n"
            "View all servers in your registry",
            title="Registry Browser",
            border_style="cyan"
        ))
        console.print()
        
        servers = self.registry.list_servers()
        
        if not servers:
            console.print("[yellow]⚠️ No servers in registry[/yellow]")
            console.print("Use the main menu to add servers to your registry.")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Show servers in a table
        table = Table(title="Servers in Registry", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Description", style="dim")
        table.add_column("Tags", style="dim")
        
        for name, entry in servers.items():
            status = "✅ Enabled" if entry.metadata.enabled else "❌ Disabled"
            description = entry.metadata.description or "No description"
            tags = ", ".join(entry.metadata.tags) if entry.metadata.tags else "None"
            
            table.add_row(
                name,
                entry.type,
                status,
                description[:50] + "..." if len(description) > 50 else description,
                tags
            )
        
        console.print(table)
        
        # Show debug messages if enabled
        if self.show_debug:
            self.tui_logger.show_debug_panel()
        
        questionary.press_any_key_to_continue().ask()
    
    def add_server_to_registry(self):
        """Add a new server to the registry."""
        self.clear_screen()
        
        console.print(Panel(
            "[green]➕ Add Server to Registry[/green]\n"
            "Add a new MCP server to your central registry",
            title="Add Server",
            border_style="green"
        ))
        console.print()
        
        # Get server name
        server_name = questionary.text(
            "Enter server name:",
            validate=lambda x: len(x.strip()) > 0 or "Server name cannot be empty"
        ).ask()
        
        if not server_name:
            return
        
        server_name = server_name.strip()
        
        # Check if server already exists
        if self.registry.get_server(server_name):
            console.print(f"[red]❌ Server '{server_name}' already exists in registry[/red]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Get server configuration (reuse existing logic)
        server_config = self._get_server_config_interactive()
        if not server_config:
            return
        
        # Get metadata
        description = questionary.text(
            "Enter description (optional):",
            default=""
        ).ask() or None
        
        tags_input = questionary.text(
            "Enter tags (comma-separated, optional):",
            default=""
        ).ask()
        
        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
        
        metadata = {
            "description": description,
            "tags": tags,
            "enabled": True
        }
        
        # Add to registry
        success = self.registry.add_server(server_name, server_config, metadata)
        
        if success:
            console.print(f"[green]✅ Added '{server_name}' to registry[/green]")
            
            # Ask if user wants to deploy immediately
            if questionary.confirm("Deploy this server to platforms/projects now?", default=False).ask():
                self._deploy_server_interactive(server_name)
        else:
            console.print(f"[red]❌ Failed to add '{server_name}' to registry[/red]")
        
        # Show debug messages if enabled
        if self.show_debug:
            self.tui_logger.show_debug_panel()
        
        questionary.press_any_key_to_continue().ask()
    
    def _get_server_config_interactive(self) -> Optional[Dict[str, Any]]:
        """Get server configuration interactively."""
        # Get server type
        server_type = questionary.select(
            "Select server type:",
            choices=["stdio", "http", "sse", "docker"]
        ).ask()
        
        if not server_type:
            return None
        
        server_config = {"type": server_type}
        
        # Configure based on server type
        if server_type == "stdio":
            command = questionary.text(
                "Enter command (e.g., 'npx', 'python', 'uvx'):",
                validate=lambda x: len(x.strip()) > 0 or "Command cannot be empty"
            ).ask()
            
            if not command:
                return None
            
            server_config["command"] = command.strip()
            
            # Optional args
            if questionary.confirm("Add command arguments?", default=False).ask():
                args_input = questionary.text(
                    "Enter arguments (space-separated):",
                    default=""
                ).ask()
                
                if args_input:
                    server_config["args"] = args_input.split()
            
            # Optional environment variables
            if questionary.confirm("Add environment variables?", default=False).ask():
                env_vars = {}
                while True:
                    env_key = questionary.text(
                        "Environment variable name (empty to finish):",
                        default=""
                    ).ask()
                    
                    if not env_key or not env_key.strip():
                        break
                    
                    env_value = questionary.text(
                        f"Value for {env_key.strip()} (store real API keys here):",
                        default=""
                    ).ask()
                    
                    env_vars[env_key.strip()] = env_value or ""
                
                if env_vars:
                    server_config["env"] = env_vars
        
        elif server_type in ["http", "sse"]:
            url = questionary.text(
                "Enter server URL:",
                validate=lambda x: x.startswith(('http://', 'https://')) or "URL must start with http:// or https://"
            ).ask()
            
            if not url:
                return None
            
            server_config["url"] = url
        
        elif server_type == "docker":
            image = questionary.text(
                "Enter Docker image name:",
                validate=lambda x: len(x.strip()) > 0 or "Image name cannot be empty"
            ).ask()
            
            if not image:
                return None
            
            server_config["image"] = image.strip()
        
        return server_config
    
    def interactive_deployment(self):
        """Interactive server deployment to platforms and projects."""
        self.clear_screen()
        
        console.print(Panel(
            "[bold blue]🚀 Deploy Servers[/bold blue]\n"
            "Deploy servers from registry to platforms and projects",
            title="Server Deployment",
            border_style="blue"
        ))
        console.print()
        
        # Show available servers
        servers = self.registry.list_servers(enabled_only=True)
        if not servers:
            console.print("[yellow]⚠️ No enabled servers in registry[/yellow]")
            console.print("Add servers to your registry first.")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Select servers to deploy
        server_choices = [f"{name} ({entry.type})" for name, entry in servers.items()]
        selected_servers = questionary.checkbox(
            "Select servers to deploy:",
            choices=server_choices
        ).ask()
        
        if not selected_servers:
            return
        
        # Extract server names
        server_names = [choice.split(" (")[0] for choice in selected_servers]
        
        # Select deployment targets
        console.print("\n[cyan]Select deployment targets:[/cyan]")
        # Get platform targets
        platform_targets = self.deployment_manager.get_platform_targets()
        platform_choices = [f"{target.name}" for target in platform_targets.values()]
        
        selected_platforms = []
        if platform_choices:
            selected_platforms = self.safe_questionary_ask(
                questionary.checkbox(
                    "📱 Select platforms:",
                    choices=platform_choices
                ), allow_none=True
            ) or []
        
        # Get project targets - show current directory and ~/Projects/ by default
        project_choices = self._get_project_directory_choices()
        
        selected_projects = questionary.checkbox(
            "📁 Select existing projects (or choose 'Add custom path' to type your own):",
            choices=project_choices + ["➕ Add custom project path"]
        ).ask() or []
        
        # Handle custom project path
        custom_projects = []
        if "➕ Add custom project path" in selected_projects:
            selected_projects.remove("➕ Add custom project path")
            while True:
                custom_path = questionary.path(
                    "Enter project directory path (empty to finish):",
                    default=""
                ).ask()
                
                if not custom_path or not custom_path.strip():
                    break
                    
                custom_path = Path(custom_path.strip()).resolve()
                if custom_path.exists() and custom_path.is_dir():
                    custom_projects.append(str(custom_path))
                    console.print(f"[green]✅ Added: {custom_path}[/green]")
                else:
                    console.print(f"[red]❌ Directory not found: {custom_path}[/red]")
        
        # Combine all selections
        all_selected_targets = selected_platforms + selected_projects + custom_projects
        
        if not all_selected_targets:
            return
        
        # Convert selections back to target keys
        target_keys = []
        all_targets = self.deployment_manager.get_all_targets()
        
        for selection in all_selected_targets:
            # Find matching target key
            for key, target in all_targets.items():
                if (selection in target.name or 
                    selection == str(target.path)):
                    target_keys.append(key)
                    break
            else:
                # Handle custom project paths
                if selection not in selected_platforms:
                    target_keys.append(f"project:{selection}")
        
        # Deployment options
        console.print("\n[cyan]Deployment Options:[/cyan]")
        use_placeholders = questionary.confirm(
            "Replace API keys with placeholders for platform deployments?",
            default=True
        ).ask()
        
        use_real_keys = questionary.confirm(
            "Use real API keys for project deployments?",
            default=True
        ).ask()
        
        deployment_options = {
            "use_placeholders": use_placeholders,
            "use_real_keys": use_real_keys
        }
        
        # Confirm deployment
        console.print(f"\n[yellow]About to deploy {len(server_names)} server(s) to {len(all_selected_targets)} target(s)[/yellow]")
        if not questionary.confirm("Proceed with deployment?", default=True).ask():
            return
        
        # Perform deployment
        console.print(f"\n[cyan]Deploying servers...[/cyan]")
        results = self.deployment_manager.deploy_servers_bulk(server_names, target_keys, deployment_options)
        
        # Show results
        console.print("\n[bold]Deployment Results:[/bold]")
        for server_name, server_results in results.items():
            console.print(f"\n[bold cyan]{server_name}:[/bold cyan]")
            for target_key, success in server_results.items():
                if target_key.startswith("platform:"):
                    platform_key = target_key.split(":", 1)[1]
                    platforms = self.platform_manager.get_available_platforms()
                    if platform_key in platforms:
                        platform_name = platforms[platform_key]["name"]
                        status = "✅ Success" if success else "❌ Failed"
                        console.print(f"  📱 {platform_name}: {status}")
                elif target_key.startswith("project:"):
                    project_path = target_key.split(":", 1)[1]
                    project_name = Path(project_path).name
                    status = "✅ Success" if success else "❌ Failed"
                    console.print(f"  📁 {project_name}: {status}")
        
        # Show debug messages if enabled
        if self.show_debug:
            self.tui_logger.show_debug_panel()
        
        questionary.press_any_key_to_continue().ask()
    
    def interactive_deployment_status(self):
        """Show deployment status of all servers."""
        self.clear_screen()
        
        console.print(Panel(
            "[cyan]📋 Deployment Status[/cyan]\n"
            "View where your servers are deployed",
            title="Deployment Status",
            border_style="cyan"
        ))
        console.print()
        
        servers = self.registry.list_servers()
        if not servers:
            console.print("[yellow]⚠️ No servers in registry[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Get deployment matrix
        console.print("[dim]Analyzing deployments...[/dim]")
        matrix = self.deployment_manager.get_deployment_matrix()
        platforms = self.platform_manager.get_available_platforms()
        
        if not matrix:
            console.print("[yellow]⚠️ No deployment data available[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Create deployment status table
        table = Table(title="Server Deployment Status", show_header=True, header_style="bold magenta")
        table.add_column("Server", style="cyan", no_wrap=True, width=20)
        table.add_column("Type", style="white", width=8)
        
        # Add platform columns
        platform_columns = {}
        for platform_key, platform_info in platforms.items():
            if platform_info["available"]:
                col_name = f"{platform_info['icon']} {platform_info['name']}"
                table.add_column(col_name, justify="center", width=10)
                platform_columns[platform_key] = col_name
        
        # Add projects column
        table.add_column("Projects", style="dim", width=30)
        
        # Fill table rows
        for server_name, deployment_status in matrix.items():
            server_entry = servers.get(server_name)
            if not server_entry:
                continue
            
            row = [server_name, server_entry.type]
            
            # Add platform status
            for platform_key in platform_columns.keys():
                target_key = f"platform:{platform_key}"
                deployed = deployment_status.get(target_key, False)
                status = "✅" if deployed else "❌"
                row.append(status)
            
            # Add deployed projects summary
            project_deployments = {k: v for k, v in deployment_status.items() if k.startswith("project:") and v}
            if project_deployments:
                project_names = []
                for target_key in project_deployments.keys():
                    project_path = Path(target_key.split(":", 1)[1])
                    project_names.append(project_path.name)
                
                if len(project_names) > 3:
                    projects_text = ", ".join(project_names[:3]) + f" (+{len(project_names)-3} more)"
                else:
                    projects_text = ", ".join(project_names)
            else:
                projects_text = "None"
            
            row.append(projects_text)
            table.add_row(*row)
        
        console.print(table)
        console.print()
        
        # Show summary
        total_servers = len(matrix)
        deployed_platforms = 0
        deployed_projects = 0
        
        for deployment_status in matrix.values():
            for target_key, deployed in deployment_status.items():
                if deployed:
                    if target_key.startswith("platform:"):
                        deployed_platforms += 1
                    elif target_key.startswith("project:"):
                        deployed_projects += 1
        
        console.print(f"[dim]Summary: {total_servers} servers • {deployed_platforms} platform deployments • {deployed_projects} project deployments[/dim]")
        
        # Show debug messages if enabled
        if self.show_debug:
            self.tui_logger.show_debug_panel()
        
        questionary.press_any_key_to_continue().ask()
    
    def _edit_server_config(self, server_name: str):
        """Edit basic server configuration."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            return
        
        self.clear_screen()
        console.print(Panel(
            f"[yellow]✏️ Edit Configuration: {server_name}[/yellow]",
            title="Edit Config",
            border_style="yellow"
        ))
        console.print()
        
        # Show current configuration
        config = server_entry.get_config_dict()
        console.print("[bold]Current Configuration:[/bold]")
        import json
        console.print(json.dumps(config, indent=2))
        console.print()
        
        if server_entry.type == "stdio":
            if questionary.confirm("Edit command?", default=False).ask():
                new_command = questionary.text(
                    "Enter new command:",
                    default=config.get("command", "")
                ).ask()
                if new_command and new_command.strip():
                    config["command"] = new_command.strip()
            
            if questionary.confirm("Edit arguments?", default=False).ask():
                current_args = " ".join(config.get("args", []))
                new_args = questionary.text(
                    "Enter arguments (space-separated):",
                    default=current_args
                ).ask()
                if new_args is not None:
                    config["args"] = new_args.split() if new_args.strip() else []
        
        elif server_entry.type in ["http", "sse"]:
            if questionary.confirm("Edit URL?", default=False).ask():
                new_url = questionary.text(
                    "Enter new URL:",
                    default=config.get("url", ""),
                    validate=lambda x: x.startswith(('http://', 'https://')) or "URL must start with http:// or https://"
                ).ask()
                if new_url and new_url.strip():
                    config["url"] = new_url.strip()
        
        elif server_entry.type == "docker":
            if questionary.confirm("Edit Docker image?", default=False).ask():
                new_image = questionary.text(
                    "Enter new Docker image:",
                    default=config.get("image", "")
                ).ask()
                if new_image and new_image.strip():
                    config["image"] = new_image.strip()
        
        # Update server
        success = self.registry.update_server(server_name, server_config=config)
        
        if success:
            console.print(f"[green]✅ Updated configuration for '{server_name}'[/green]")
        else:
            console.print(f"[red]❌ Failed to update configuration for '{server_name}'[/red]")
        
        questionary.press_any_key_to_continue().ask()
    
    def _edit_server_env_vars(self, server_name: str):
        """Edit server environment variables (API keys)."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            return
        
        config = server_entry.get_config_dict()
        env_vars = config.get("env", {}).copy()
        
        while True:
            self.clear_screen()
            console.print(Panel(
                f"[yellow]🔐 Environment Variables: {server_name}[/yellow]",
                title="Manage API Keys",
                border_style="yellow"
            ))
            console.print()
            
            # Show current environment variables
            if env_vars:
                table = Table(title="Current Environment Variables", show_header=True)
                table.add_column("Variable", style="cyan")
                table.add_column("Value", style="white")
                
                for key, value in env_vars.items():
                    # Mask potential API keys for display
                    if any(keyword in key.upper() for keyword in ['API', 'KEY', 'TOKEN', 'SECRET', 'PASSWORD']):
                        if value and len(str(value)) > 10 and not str(value).startswith("YOUR_"):
                            display_value = "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
                        else:
                            display_value = str(value)
                    else:
                        display_value = str(value)
                    
                    table.add_row(key, display_value)
                
                console.print(table)
            else:
                console.print("[dim]No environment variables configured[/dim]")
            
            console.print()
            
            choices = [
                "1. ➕ Add new environment variable",
                "2. ✏️ Edit existing variable",
                "3. 🗑️ Remove variable",
                "4. 💾 Save changes",
                "b. 🔙 Back without saving"
            ]
            
            key_mappings = {
                '1': "1. ➕ Add new environment variable",
                '2': "2. ✏️ Edit existing variable",
                '3': "3. 🗑️ Remove variable",
                '4': "4. 💾 Save changes",
                'b': "b. 🔙 Back without saving"
            }
            
            choice = self.get_single_key_choice(choices, key_mappings, "Environment Variable Options:")
            
            if not choice or choice.startswith("b."):
                break
            elif choice.startswith("1."):  # Add new
                var_name = questionary.text(
                    "Environment variable name (e.g., API_KEY, OPENAI_API_KEY):",
                    validate=lambda x: len(x.strip()) > 0 or "Variable name cannot be empty"
                ).ask()
                
                if var_name and var_name.strip():
                    var_name = var_name.strip()
                    var_value = questionary.text(
                        f"Value for {var_name} (store your real API key here):",
                        default=""
                    ).ask()
                    
                    env_vars[var_name] = var_value or ""
            
            elif choice.startswith("2.") and env_vars:  # Edit existing
                var_choices = list(env_vars.keys()) + ["🔙 Cancel"]
                selected_var = questionary.select(
                    "Select variable to edit:",
                    choices=var_choices
                ).ask()
                
                if selected_var and not selected_var.startswith("🔙"):
                    current_value = env_vars[selected_var]
                    new_value = questionary.text(
                        f"New value for {selected_var}:",
                        default=str(current_value)
                    ).ask()
                    
                    if new_value is not None:
                        env_vars[selected_var] = new_value
            
            elif choice.startswith("3.") and env_vars:  # Remove
                var_choices = list(env_vars.keys()) + ["🔙 Cancel"]
                selected_var = questionary.select(
                    "Select variable to remove:",
                    choices=var_choices
                ).ask()
                
                if selected_var and not selected_var.startswith("🔙"):
                    if questionary.confirm(f"Remove {selected_var}?", default=False).ask():
                        del env_vars[selected_var]
            
            elif choice.startswith("4."):  # Save changes
                config["env"] = env_vars if env_vars else {}
                success = self.registry.update_server(server_name, server_config=config)
                
                if success:
                    console.print(f"[green]✅ Updated environment variables for '{server_name}'[/green]")
                else:
                    console.print(f"[red]❌ Failed to update environment variables for '{server_name}'[/red]")
                
                questionary.press_any_key_to_continue().ask()
                break
    
    def _edit_server_metadata(self, server_name: str):
        """Edit server metadata (description, tags)."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            return
        
        self.clear_screen()
        console.print(Panel(
            f"[yellow]📋 Edit Metadata: {server_name}[/yellow]",
            title="Edit Metadata",
            border_style="yellow"
        ))
        console.print()
        
        # Show current metadata
        console.print("[bold]Current Metadata:[/bold]")
        console.print(f"[cyan]Description:[/cyan] {server_entry.metadata.description or 'None'}")
        console.print(f"[cyan]Tags:[/cyan] {', '.join(server_entry.metadata.tags) or 'None'}")
        console.print(f"[cyan]Created:[/cyan] {server_entry.metadata.created}")
        console.print(f"[cyan]Status:[/cyan] {'Enabled' if server_entry.metadata.enabled else 'Disabled'}")
        console.print()
        
        # Edit description
        if questionary.confirm("Edit description?", default=False).ask():
            new_description = questionary.text(
                "Enter new description:",
                default=server_entry.metadata.description or ""
            ).ask()
        else:
            new_description = server_entry.metadata.description
        
        # Edit tags
        if questionary.confirm("Edit tags?", default=False).ask():
            current_tags = ", ".join(server_entry.metadata.tags)
            new_tags_input = questionary.text(
                "Enter tags (comma-separated):",
                default=current_tags
            ).ask()
            
            if new_tags_input is not None:
                new_tags = [tag.strip() for tag in new_tags_input.split(",") if tag.strip()]
            else:
                new_tags = server_entry.metadata.tags
        else:
            new_tags = server_entry.metadata.tags
        
        # Update metadata
        metadata_updates = {
            "description": new_description if new_description else None,
            "tags": new_tags
        }
        
        success = self.registry.update_server(server_name, metadata=metadata_updates)
        
        if success:
            console.print(f"[green]✅ Updated metadata for '{server_name}'[/green]")
        else:
            console.print(f"[red]❌ Failed to update metadata for '{server_name}'[/red]")
        
        questionary.press_any_key_to_continue().ask()
    
    def _toggle_server_status(self, server_name: str):
        """Toggle server enabled/disabled status."""
        server_entry = self.registry.get_server(server_name)
        if not server_entry:
            return
        
        current_status = server_entry.metadata.enabled
        new_status = not current_status
        
        if new_status:
            success = self.registry.enable_server(server_name)
            status_text = "enabled"
        else:
            success = self.registry.disable_server(server_name)
            status_text = "disabled"
        
        if success:
            console.print(f"[green]✅ Server '{server_name}' {status_text}[/green]")
        else:
            console.print(f"[red]❌ Failed to {status_text.replace('d', '')} server '{server_name}'[/red]")
        
        questionary.press_any_key_to_continue().ask()
    
    def _deploy_server_interactive(self, server_name: str):
        """Deploy a specific server interactively."""
        # This is a simplified version - could be expanded
        targets = self.deployment_manager.get_all_targets()
        if not targets:
            console.print("[yellow]⚠️ No deployment targets available[/yellow]")
            return
        
        target_choices = [f"{target.name} ({target.target_type})" for target in targets.values()]
        selected_targets = questionary.checkbox(
            f"Deploy '{server_name}' to:",
            choices=target_choices
        ).ask()
        
        if not selected_targets:
            return
        
        # Extract target keys
        target_keys = []
        for choice in selected_targets:
            for key, target in targets.items():
                if choice.startswith(target.name):
                    target_keys.append(key)
                    break
        
        # Deploy
        results = self.deployment_manager.deploy_servers_bulk([server_name], target_keys)
        
        # Show results
        server_results = results.get(server_name, {})
        for target_key, success in server_results.items():
            target = targets[target_key]
            status = "✅ Success" if success else "❌ Failed"
            console.print(f"  {target.name}: {status}")
    
    def search_registry(self):
        """Search servers in registry."""
        console.print("[cyan]Search feature coming soon![/cyan]")
        questionary.press_any_key_to_continue().ask()
    
    def edit_server_in_registry(self):
        """Edit server in registry."""
        self.clear_screen()
        
        console.print(Panel(
            "[yellow]✏️ Edit Server[/yellow]\n"
            "Modify server configuration and metadata",
            title="Edit Server",
            border_style="yellow"
        ))
        console.print()
        
        servers = self.registry.list_servers()
        if not servers:
            console.print("[yellow]⚠️ No servers in registry[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Select server to edit
        server_choices = [f"{name} ({entry.type})" for name, entry in servers.items()]
        server_choices.append("🔙 Back")
        
        selected = questionary.select(
            "Select server to edit:",
            choices=server_choices
        ).ask()
        
        if not selected or selected.startswith("🔙"):
            return
        
        # Extract server name
        server_name = selected.split(" (")[0]
        server_entry = servers[server_name]
        
        # Edit options
        while True:
            self.clear_screen()
            
            console.print(Panel(
                f"[yellow]✏️ Editing: {server_name}[/yellow]\n"
                f"Type: {server_entry.type}",
                title="Edit Server",
                border_style="yellow"
            ))
            console.print()
            
            choices = [
                "1. 📝 Edit server configuration",
                "2. 🔐 Manage environment variables (API keys)",
                "3. 📋 Edit metadata (description, tags)",
                "4. 🔄 Toggle enabled/disabled status",
                "b. 🔙 Back to registry menu"
            ]
            
            key_mappings = {
                '1': "1. 📝 Edit server configuration",
                '2': "2. 🔐 Manage environment variables (API keys)",
                '3': "3. 📋 Edit metadata (description, tags)",
                '4': "4. 🔄 Toggle enabled/disabled status",
                'b': "b. 🔙 Back to registry menu"
            }
            
            choice = self.get_single_key_choice(choices, key_mappings, "Edit Options:")
            
            if not choice or choice.startswith("b."):
                break
            elif choice.startswith("1."):
                self._edit_server_config(server_name)
                server_entry = self.registry.get_server(server_name)  # Refresh
            elif choice.startswith("2."):
                self._edit_server_env_vars(server_name)
                server_entry = self.registry.get_server(server_name)  # Refresh
            elif choice.startswith("3."):
                self._edit_server_metadata(server_name)
                server_entry = self.registry.get_server(server_name)  # Refresh
            elif choice.startswith("4."):
                self._toggle_server_status(server_name)
                server_entry = self.registry.get_server(server_name)  # Refresh
    
    def manage_server_tags(self):
        """Manage server tags."""
        console.print("[cyan]Tag management coming soon![/cyan]")
        questionary.press_any_key_to_continue().ask()
    
    def _get_project_directory_choices(self) -> List[str]:
        """Get list of project directory choices from current dir and ~/Projects/."""
        choices = []
        
        # Add current directory subdirectories
        cwd = Path.cwd()
        try:
            for item in cwd.iterdir():
                if item.is_dir() and not item.name.startswith('.') and item.name != 'node_modules':
                    choices.append(f"{item.name} (current dir)")
        except (PermissionError, OSError):
            pass
        
        # Add ~/Projects/ subdirectories
        projects_dir = Path.home() / "Projects"
        if projects_dir.exists():
            try:
                for item in projects_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        choices.append(f"{item.name} (~/Projects)")
            except (PermissionError, OSError):
                pass
        
        # Add any existing projects with .claude directories
        existing_projects = self.project_detector.find_projects_in_common_locations()
        for project in existing_projects[:5]:  # Limit to 5 existing projects
            choice_name = f"📁 {project.name} (has .claude config)"
            if choice_name not in choices:
                choices.append(choice_name)
        
        return sorted(choices)
    
    def remove_server_from_registry(self):
        """Remove server from registry."""
        self.clear_screen()
        
        console.print(Panel(
            "[red]🗑️ Remove Server[/red]\n"
            "Delete a server from your registry",
            title="Remove Server",
            border_style="red"
        ))
        console.print()
        
        servers = self.registry.list_servers()
        if not servers:
            console.print("[yellow]⚠️ No servers in registry[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Select server to remove
        server_choices = []
        for name, entry in servers.items():
            status = "✅ Enabled" if entry.metadata.enabled else "❌ Disabled"
            description = entry.metadata.description or "No description"
            server_choices.append(f"{name} ({entry.type}) - {status} - {description[:30]}...")
        
        server_choices.append("🔙 Back")
        
        selected = questionary.select(
            "Select server to remove:",
            choices=server_choices
        ).ask()
        
        if not selected or selected.startswith("🔙"):
            return
        
        # Extract server name
        server_name = selected.split(" (")[0]
        server_entry = servers[server_name]
        
        # Show server details and confirm removal
        console.print(f"\n[bold red]⚠️ You are about to remove:[/bold red]")
        console.print(f"[cyan]Name:[/cyan] {server_name}")
        console.print(f"[cyan]Type:[/cyan] {server_entry.type}")
        console.print(f"[cyan]Description:[/cyan] {server_entry.metadata.description or 'None'}")
        console.print(f"[cyan]Tags:[/cyan] {', '.join(server_entry.metadata.tags) or 'None'}")
        
        # Check if server is deployed anywhere
        deployment_status = self.deployment_manager.get_server_deployment_status(server_name)
        deployed_targets = [target for target, deployed in deployment_status.items() if deployed]
        
        if deployed_targets:
            console.print(f"\n[yellow]⚠️ This server is currently deployed to {len(deployed_targets)} target(s):[/yellow]")
            platforms = self.platform_manager.get_available_platforms()
            for target in deployed_targets[:5]:  # Show first 5
                if target.startswith("platform:"):
                    platform_key = target.split(":", 1)[1]
                    if platform_key in platforms:
                        console.print(f"  📱 {platforms[platform_key]['name']}")
                elif target.startswith("project:"):
                    project_path = Path(target.split(":", 1)[1])
                    console.print(f"  📁 {project_path.name}")
            
            if len(deployed_targets) > 5:
                console.print(f"  ... and {len(deployed_targets) - 5} more")
            
            console.print("[red]Removing from registry will not undeploy from these targets.[/red]")
        
        console.print()
        if not questionary.confirm(
            f"Are you sure you want to remove '{server_name}' from the registry?",
            default=False
        ).ask():
            return
        
        # Remove server
        success = self.registry.remove_server(server_name)
        
        if success:
            console.print(f"[green]✅ Removed '{server_name}' from registry[/green]")
        else:
            console.print(f"[red]❌ Failed to remove '{server_name}' from registry[/red]")
        
        # Show debug messages if enabled
        if self.show_debug:
            self.tui_logger.show_debug_panel()
        
        questionary.press_any_key_to_continue().ask()
    
    def interactive_platform_management(self):
        """Interactive MCP server platform management."""
        while True:
            self.clear_screen()
            
            console.print(Panel(
                "[bold blue]🌐 MCP Server Platform Management[/bold blue]\n"
                "Install, remove, and sync servers across Claude platforms",
                title="Platform Management",
                border_style="blue"
            ))
            console.print()
            
            choices = [
                "📊 View platform status",
                "➕ Add custom MCP server", 
                "🔄 Sync server to platforms",
                "❌ Remove server from platforms",
                "📋 Server installation status",
                "🔙 Back to main menu"
            ]
            
            choice = questionary.select(
                "Platform Management Options:",
                choices=choices
            ).ask()
            
            if not choice or choice.startswith("🔙"):
                break
            elif choice.startswith("📊"):
                self.show_platform_status()
            elif choice.startswith("➕"):
                self.add_custom_server()
            elif choice.startswith("🔄"):
                self.sync_server_to_platforms()
            elif choice.startswith("❌"):
                self.remove_server_from_platforms()
            elif choice.startswith("📋"):
                self.show_server_installation_status()
    
    def show_platform_status(self):
        """Show status of all detected platforms."""
        self.clear_screen()
        
        console.print(Panel(
            "[cyan]📊 Platform Status[/cyan]\n"
            "Overview of detected Claude platforms",
            title="Platform Status",
            border_style="cyan"
        ))
        console.print()
        
        platforms = self.platform_manager.get_available_platforms()
        
        if not platforms:
            console.print("[yellow]⚠️ No Claude platforms detected[/yellow]")
            console.print("\nMake sure you have Claude Desktop, Claude Code, or VSCode with Claude extension installed.")
            questionary.press_any_key_to_continue().ask()
            return
        
        table = Table(title="Detected Claude Platforms", show_header=True)
        table.add_column("Platform", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Config Path", style="dim")
        table.add_column("Servers", justify="center")
        
        for platform_key, platform_info in platforms.items():
            servers = self.platform_manager.get_platform_servers(platform_key)
            server_count = len(servers)
            
            status = "✅ Active" if platform_info['available'] else "❌ No Config"
            icon = platform_info['icon']
            name = f"{icon} {platform_info['name']}"
            
            table.add_row(
                name,
                status,
                str(platform_info['config_path']),
                str(server_count)
            )
        
        console.print(table)
        console.print()
        
        # Show detailed server info for each platform
        for platform_key, platform_info in platforms.items():
            if not platform_info['available']:
                continue
                
            servers = self.platform_manager.get_platform_servers(platform_key)
            if servers:
                console.print(f"\n[bold]{platform_info['icon']} {platform_info['name']} Servers:[/bold]")
                for server_name, server_config in servers.items():
                    server_type = server_config.get('type', 'unknown')
                    console.print(f"  • {server_name} ({server_type})")
        
        questionary.press_any_key_to_continue().ask()
    
    def add_custom_server(self):
        """Interactive addition of custom MCP servers."""
        self.clear_screen()
        
        console.print(Panel(
            "[green]➕ Add Custom MCP Server[/green]\n"
            "Manually add your own MCP server configuration",
            title="Add Custom Server",
            border_style="green"
        ))
        console.print()
        
        # Get server name
        server_name = questionary.text(
            "Enter server name:",
            validate=lambda x: len(x.strip()) > 0 or "Server name cannot be empty"
        ).ask()
        
        if not server_name:
            return
        
        server_name = server_name.strip()
        
        # Get server type
        server_type = questionary.select(
            "Select server type:",
            choices=["stdio", "http", "sse", "docker"]
        ).ask()
        
        if not server_type:
            return
        
        server_config = {"type": server_type}
        
        # Configure based on server type
        if server_type == "stdio":
            command = questionary.text(
                "Enter command (e.g., 'npx', 'python', 'uvx'):",
                validate=lambda x: len(x.strip()) > 0 or "Command cannot be empty"
            ).ask()
            
            if not command:
                return
            
            server_config["command"] = command.strip()
            
            # Optional args
            if questionary.confirm("Add command arguments?", default=False).ask():
                args_input = questionary.text(
                    "Enter arguments (space-separated):",
                    default=""
                ).ask()
                
                if args_input:
                    # Simple space-based splitting - user can refine later
                    server_config["args"] = args_input.split()
            
            # Optional environment variables
            if questionary.confirm("Add environment variables?", default=False).ask():
                env_vars = {}
                while True:
                    env_key = questionary.text(
                        "Environment variable name (empty to finish):",
                        default=""
                    ).ask()
                    
                    if not env_key or not env_key.strip():
                        break
                    
                    env_value = questionary.text(
                        f"Value for {env_key.strip()}:",
                        default=""
                    ).ask()
                    
                    env_vars[env_key.strip()] = env_value or "YOUR_VALUE_HERE"
                
                if env_vars:
                    server_config["env"] = env_vars
        
        elif server_type in ["http", "sse"]:
            url = questionary.text(
                "Enter server URL:",
                validate=lambda x: x.startswith(('http://', 'https://')) or "URL must start with http:// or https://"
            ).ask()
            
            if not url:
                return
            
            server_config["url"] = url
        
        elif server_type == "docker":
            image = questionary.text(
                "Enter Docker image name:",
                validate=lambda x: len(x.strip()) > 0 or "Image name cannot be empty"
            ).ask()
            
            if not image:
                return
            
            server_config["image"] = image.strip()
        
        # Show configuration preview
        console.print(f"\n[bold cyan]📦 {server_name}[/bold cyan]")
        console.print(f"\n[bold]Configuration:[/bold]")
        import json
        console.print(json.dumps(server_config, indent=2))
        console.print()
        
        if not questionary.confirm("Add this server?").ask():
            return
        
        # Select target platforms
        platforms = self.platform_manager.get_available_platforms()
        platform_choices = []
        
        for platform_key, platform_info in platforms.items():
            icon = platform_info['icon']
            name = platform_info['name']
            status = "✅" if platform_info['available'] else "❌"
            platform_choices.append(f"{icon} {name} {status}")
        
        if not platform_choices:
            console.print("[red]❌ No platforms available for installation[/red]")
            questionary.press_any_key_to_continue().ask()
            return
        
        selected_platforms = questionary.checkbox(
            "Select platforms to add server to:",
            choices=platform_choices
        ).ask()
        
        if not selected_platforms:
            return
        
        # Extract platform keys from selections
        target_platforms = []
        for selection in selected_platforms:
            for platform_key, platform_info in platforms.items():
                if f"{platform_info['icon']} {platform_info['name']}" in selection:
                    target_platforms.append(platform_key)
                    break
        
        # Install to selected platforms
        console.print(f"\n[cyan]Adding {server_name} to selected platforms...[/cyan]")
        
        results = self.platform_manager.sync_server_to_platforms(
            server_name, 
            server_config, 
            target_platforms
        )
        
        console.print("\n[bold]Installation Results:[/bold]")
        for platform_key, success in results.items():
            platform_info = platforms[platform_key]
            icon = platform_info['icon']
            name = platform_info['name']
            status = "✅ Success" if success else "❌ Failed"
            console.print(f"  {icon} {name}: {status}")
        
        questionary.press_any_key_to_continue().ask()

    def sync_server_to_platforms(self):
        """Sync an existing server to multiple platforms."""
        self.clear_screen()
        
        console.print(Panel(
            "[blue]🔄 Sync Server to Platforms[/blue]\n"
            "Copy a server from one platform to others",
            title="Server Sync",
            border_style="blue"
        ))
        console.print()
        
        # Get all unique servers from all platforms
        all_servers = self.platform_manager.get_all_unique_servers()
        platforms = self.platform_manager.get_available_platforms()
        
        # Build server info with platform tracking
        server_info = {}
        for server_name, server_config in all_servers.items():
            server_info[server_name] = {
                'config': server_config,
                'platforms': []
            }
            
            # Find which platforms have this server
            for platform_key, platform_data in platforms.items():
                if platform_data['available']:
                    platform_servers = self.platform_manager.get_platform_servers(platform_key)
                    if server_name in platform_servers:
                        server_info[server_name]['platforms'].append(platform_key)
        
        if not server_info:
            console.print("[yellow]⚠️ No servers found on any platform[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Select server to sync
        server_choices = []
        for server_name, info in server_info.items():
            platforms_str = ", ".join([platforms[p]['name'] for p in info['platforms']])
            server_choices.append(f"{server_name} (on: {platforms_str})")
        
        server_choices.append("🔙 Back")
        
        selected = questionary.select(
            "Select server to sync:",
            choices=server_choices
        ).ask()
        
        if not selected or selected.startswith("🔙"):
            return
        
        # Extract server name
        server_name = selected.split(" (on:")[0]
        server_config = server_info[server_name]['config']
        current_platforms = server_info[server_name]['platforms']
        
        # Select target platforms (excluding current ones)
        available_targets = []
        for platform_key, platform_info in platforms.items():
            if platform_key not in current_platforms:
                icon = platform_info['icon']
                name = platform_info['name'] 
                status = "✅" if platform_info['available'] else "❌"
                available_targets.append(f"{icon} {name} {status}")
        
        if not available_targets:
            console.print(f"[yellow]⚠️ {server_name} is already installed on all available platforms[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        selected_platforms = questionary.checkbox(
            f"Select platforms to sync '{server_name}' to:",
            choices=available_targets
        ).ask()
        
        if not selected_platforms:
            return
        
        # Extract platform keys
        target_platforms = []
        for selection in selected_platforms:
            for platform_key, platform_info in platforms.items():
                if f"{platform_info['icon']} {platform_info['name']}" in selection:
                    target_platforms.append(platform_key)
                    break
        
        # Perform sync
        console.print(f"\n[cyan]Syncing {server_name} to selected platforms...[/cyan]")
        
        results = self.platform_manager.sync_server_to_platforms(
            server_name, 
            server_config, 
            target_platforms
        )
        
        console.print("\n[bold]Sync Results:[/bold]")
        for platform_key, success in results.items():
            platform_info = platforms[platform_key]
            icon = platform_info['icon']
            name = platform_info['name']
            status = "✅ Success" if success else "❌ Failed"
            console.print(f"  {icon} {name}: {status}")
        
        questionary.press_any_key_to_continue().ask()
    
    def remove_server_from_platforms(self):
        """Remove a server from selected platforms."""
        self.clear_screen()
        
        console.print(Panel(
            "[red]❌ Remove Server from Platforms[/red]\n"
            "Uninstall servers from selected platforms",
            title="Server Removal",
            border_style="red"
        ))
        console.print()
        
        # Get all servers from all platforms
        all_servers = {}
        platforms = self.platform_manager.get_available_platforms()
        
        for platform_key, platform_info in platforms.items():
            if platform_info['available']:
                servers = self.platform_manager.get_platform_servers(platform_key)
                for server_name in servers.keys():
                    if server_name not in all_servers:
                        all_servers[server_name] = []
                    all_servers[server_name].append(platform_key)
        
        if not all_servers:
            console.print("[yellow]⚠️ No servers found on any platform[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Select server to remove
        server_choices = []
        for server_name, server_platforms in all_servers.items():
            platforms_str = ", ".join([platforms[p]['name'] for p in server_platforms])
            server_choices.append(f"{server_name} (on: {platforms_str})")
        
        server_choices.append("🔙 Back")
        
        selected = questionary.select(
            "Select server to remove:",
            choices=server_choices
        ).ask()
        
        if not selected or selected.startswith("🔙"):
            return
        
        # Extract server name
        server_name = selected.split(" (on:")[0]
        server_platforms = all_servers[server_name]
        
        # Select platforms to remove from
        platform_choices = []
        for platform_key in server_platforms:
            platform_info = platforms[platform_key]
            icon = platform_info['icon']
            name = platform_info['name']
            platform_choices.append(f"{icon} {name}")
        
        selected_platforms = questionary.checkbox(
            f"Select platforms to remove '{server_name}' from:",
            choices=platform_choices
        ).ask()
        
        if not selected_platforms:
            return
        
        # Confirm removal
        if not questionary.confirm(
            f"Are you sure you want to remove '{server_name}' from {len(selected_platforms)} platform(s)?",
            default=False
        ).ask():
            return
        
        # Extract platform keys
        target_platforms = []
        for selection in selected_platforms:
            for platform_key, platform_info in platforms.items():
                if f"{platform_info['icon']} {platform_info['name']}" in selection:
                    target_platforms.append(platform_key)
                    break
        
        # Perform removal
        console.print(f"\n[cyan]Removing {server_name} from selected platforms...[/cyan]")
        
        results = {}
        for platform_key in target_platforms:
            success = self.platform_manager.remove_server_from_platform(platform_key, server_name)
            results[platform_key] = success
        
        console.print("\n[bold]Removal Results:[/bold]")
        for platform_key, success in results.items():
            platform_info = platforms[platform_key]
            icon = platform_info['icon']
            name = platform_info['name']
            status = "✅ Removed" if success else "❌ Failed"
            console.print(f"  {icon} {name}: {status}")
        
        questionary.press_any_key_to_continue().ask()
    
    def show_server_installation_status(self):
        """Show installation status of all servers across platforms."""
        self.clear_screen()
        
        console.print(Panel(
            "[cyan]📋 Server Installation Status[/cyan]\n"
            "Overview of which servers are installed where",
            title="Installation Status",
            border_style="cyan"
        ))
        console.print()
        
        platforms = self.platform_manager.get_available_platforms()
        
        # Get all unique servers
        all_servers = set()
        for platform_key, platform_info in platforms.items():
            if platform_info['available']:
                servers = self.platform_manager.get_platform_servers(platform_key)
                all_servers.update(servers.keys())
        
        if not all_servers:
            console.print("[yellow]⚠️ No servers found on any platform[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return
        
        # Create status table
        table = Table(title="Server Installation Matrix", show_header=True)
        table.add_column("Server", style="cyan")
        
        for platform_key, platform_info in platforms.items():
            if platform_info['available']:
                table.add_column(f"{platform_info['icon']} {platform_info['name']}", justify="center")
        
        # Fill table
        for server_name in sorted(all_servers):
            row = [server_name]
            
            for platform_key, platform_info in platforms.items():
                if platform_info['available']:
                    status = self.platform_manager.get_server_installation_status(server_name)
                    installed = status.get(platform_key, False)
                    row.append("✅" if installed else "❌")
            
            table.add_row(*row)
        
        console.print(table)
        questionary.press_any_key_to_continue().ask()

def run_interactive_mode():
    """Run the interactive CLI mode."""
    menu = InteractiveMenu()
    menu.welcome()
    try:
        menu.main_menu()
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n👋 Goodbye!")
        sys.exit(0)