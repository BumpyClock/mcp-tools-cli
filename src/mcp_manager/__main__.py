"""Entry point for MCP Manager - TUI-first approach."""

import sys
from typing import Optional

def main() -> Optional[int]:
    """Main entry point with TUI-first approach."""
    # Check for help arguments first
    help_args = {'-h', '--help', '-?', 'help'}
    if any(arg in help_args for arg in sys.argv[1:]):
        from .cli import show_help
        show_help()
        return 0
    
    # No arguments → Launch Textual TUI  
    if len(sys.argv) == 1:
        try:
            from .tui import run_tui
            return run_tui()
        except ImportError:
            print("TUI unavailable. Use 'mcp-manager -h' for CLI help")
            return 1
    else:
        # Arguments provided → Use CLI
        from .cli import main as cli_main
        return cli_main()

if __name__ == "__main__":
    sys.exit(main() or 0)