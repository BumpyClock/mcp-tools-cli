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
    
    # Check for TUI variant flags
    if len(sys.argv) > 1:
        if '--enhanced' in sys.argv or '--tui-enhanced' in sys.argv:
            try:
                from .tui_enhanced import run_enhanced_tui
                return run_enhanced_tui()
            except ImportError:
                print("Enhanced TUI unavailable. Using basic TUI.")
                from .tui_app import run_tui
                return run_tui()
        elif '--tui' in sys.argv or '--basic' in sys.argv:
            try:
                from .tui_app import run_tui
                return run_tui()
            except ImportError:
                print("Basic TUI unavailable.")
                return 1
    
    # No arguments → Launch basic TUI by default
    if len(sys.argv) == 1:
        try:
            from .tui_app import run_tui
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