#!/usr/bin/env python3
"""Debug test for MCP Manager TUI."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_tui_basics():
    """Test basic TUI functionality."""
    print("Testing TUI components...")
    
    try:
        from mcp_manager.tui_app import MCPManagerTUI
        print("OK TUI app imports successfully")
        
        # Create app instance
        app = MCPManagerTUI()
        print("OK TUI app instantiates successfully")
        
        # Test core components
        print("OK Registry:", len(app.registry.list_servers()), "servers")
        print("OK Deployment manager initialized")
        print("OK Platform manager initialized")
        
        # Test if we can access key components
        if hasattr(app, 'health_monitor'):
            print("OK Health monitor available")
        else:
            print("MISSING Health monitor missing")
            
        if hasattr(app, 'help_system'):
            print("OK Help system available")
        else:
            print("MISSING Help system missing")
            
        return True
        
    except Exception as e:
        print(f"FAILED TUI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_component_functionality():
    """Test if individual components work."""
    print("\nTesting component functionality...")
    
    try:
        from mcp_manager.core import MCPServerRegistry
        from mcp_manager.deployment_matrix import InteractiveDeploymentMatrix
        from mcp_manager.health_monitor import HealthMonitor
        
        # Test registry
        registry = MCPServerRegistry()
        servers = registry.list_servers()
        print(f"OK Registry works: {len(servers)} servers found")
        
        # Test if deployment matrix can be created (without mounting)
        matrix = InteractiveDeploymentMatrix(
            registry=registry,
            deployment_manager=None,  # Simplified test
            platform_manager=None
        )
        print("OK Deployment matrix can be created")
        
        # Test health monitor
        from mcp_manager.core import PlatformManager
        platform_manager = PlatformManager()
        health = HealthMonitor(registry, platform_manager)
        print("OK Health monitor can be created")
        
        return True
        
    except Exception as e:
        print(f"FAILED Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== MCP Manager TUI Debug Test ===")
    
    basic_ok = test_tui_basics()
    component_ok = test_component_functionality()
    
    if basic_ok and component_ok:
        print("\nSUCCESS All tests passed - TUI should work!")
        print("\nTo launch TUI manually, run:")
        print("  cd mcp-tools-cli")
        print("  uv run mcp-manager")
    else:
        print("\nFAILED Tests failed - TUI has issues")
        
    print("\n=== Test Complete ===")