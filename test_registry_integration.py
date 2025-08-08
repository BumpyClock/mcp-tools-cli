#!/usr/bin/env python3
"""Test script to verify Registry Integration in the TUI."""

import sys
from pathlib import Path
import json
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_manager.core import MCPServerRegistry

def test_registry_integration():
    """Test that the registry can be created, populated, and read."""
    
    # Create a temporary registry file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_registry = Path(f.name)
    
    try:
        print("Testing Registry Integration...")
        
        # Initialize registry
        registry = MCPServerRegistry(temp_registry)
        
        # Add a test server
        test_config = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "test_server"]
        }
        
        test_metadata = {
            "description": "Test server for registry integration",
            "tags": ["test", "example"]
        }
        
        print("Adding test server...")
        success = registry.add_server("test-server", test_config, test_metadata)
        assert success, "Failed to add test server"
        
        # List servers
        print("Listing servers...")
        servers = registry.list_servers()
        assert "test-server" in servers, "Test server not found in registry"
        
        # Get server details
        print("Getting server details...")
        server = registry.get_server("test-server")
        assert server is not None, "Failed to get test server"
        assert server.type == "stdio", f"Expected stdio, got {server.type}"
        assert server.metadata.description == test_metadata["description"], "Description mismatch"
        assert server.metadata.enabled == True, "Server should be enabled by default"
        
        # Toggle server status
        print("Testing enable/disable...")
        success = registry.disable_server("test-server")
        assert success, "Failed to disable server"
        
        server = registry.get_server("test-server")
        assert not server.metadata.enabled, "Server should be disabled"
        
        success = registry.enable_server("test-server")
        assert success, "Failed to enable server"
        
        server = registry.get_server("test-server")
        assert server.metadata.enabled, "Server should be enabled"
        
        # Test stats
        print("Testing stats...")
        stats = registry.get_stats()
        assert stats["total_servers"] == 1, f"Expected 1 server, got {stats['total_servers']}"
        assert stats["enabled_servers"] == 1, f"Expected 1 enabled server, got {stats['enabled_servers']}"
        
        # Test file persistence
        print("Testing file persistence...")
        registry_data = json.loads(temp_registry.read_text())
        assert "mcpServers" in registry_data, "Missing mcpServers section"
        assert "test-server" in registry_data["mcpServers"], "Test server not persisted"
        
        print("All registry integration tests passed!")
        
        # Test TUI classes can be imported
        print("Testing TUI imports...")
        from mcp_manager.tui_app import MCPManagerTUI
        from mcp_manager.tui_enhanced import MCPManagerEnhanced
        
        # Create TUI instances (don't run them)
        basic_tui = MCPManagerTUI()
        enhanced_tui = MCPManagerEnhanced()
        
        print("TUI classes imported successfully!")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False
        
    finally:
        # Cleanup
        if temp_registry.exists():
            temp_registry.unlink()

if __name__ == "__main__":
    success = test_registry_integration()
    sys.exit(0 if success else 1)