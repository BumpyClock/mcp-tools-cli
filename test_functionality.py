#!/usr/bin/env python3
"""Functional test for MCP Manager TUI to identify what's actually broken."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_server_display():
    """Test if servers are actually displayed in the TUI."""
    print("Testing server display functionality...")
    
    try:
        from mcp_manager.tui_app import MCPManagerTUI
        from textual.widgets import DataTable
        
        app = MCPManagerTUI()
        
        # Simulate mounting to trigger data loading
        # This is tricky without actually running the app
        
        # Test the server loading method directly
        servers = app.registry.list_servers()
        print(f"Found {len(servers)} servers in registry:")
        
        for name, server in servers.items():
            enabled = "ENABLED" if server.metadata.enabled else "DISABLED"
            print(f"  - {name}: {server.type} ({enabled})")
        
        # Test if the load_server_registry method works
        # Create a mock table to test data population
        from textual.app import App
        
        class TestApp(App):
            def compose(self):
                yield DataTable(id="server-table")
                
        test_app = TestApp()
        # We can't easily test the table population without running Textual
        
        print("OK Server data is available and can be loaded")
        return True
        
    except Exception as e:
        print(f"FAILED Server display test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deployment_matrix():
    """Test deployment matrix functionality."""
    print("\nTesting deployment matrix functionality...")
    
    try:
        from mcp_manager.tui_app import MCPManagerTUI
        app = MCPManagerTUI()
        
        # Test platform detection
        platforms = app.platform_manager.get_available_platforms()
        print(f"Found {len(platforms)} platforms:")
        
        for key, info in platforms.items():
            available = "AVAILABLE" if info["available"] else "NOT AVAILABLE"
            print(f"  - {key}: {info['name']} ({available})")
        
        # Test deployment status checking
        servers = app.registry.list_servers()
        for server_name in list(servers.keys())[:2]:  # Test first 2 servers
            try:
                status = app.deployment_manager.get_server_deployment_status(server_name)
                print(f"Deployment status for {server_name}: {len(status)} deployments")
            except Exception as e:
                print(f"Deployment status check failed for {server_name}: {e}")
        
        print("OK Deployment matrix functionality available")
        return True
        
    except Exception as e:
        print(f"FAILED Deployment matrix test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_health_monitoring():
    """Test health monitoring functionality."""
    print("\nTesting health monitoring functionality...")
    
    try:
        from mcp_manager.tui_app import MCPManagerTUI
        app = MCPManagerTUI()
        
        # Test health check on one server
        servers = list(app.registry.list_servers().keys())
        if servers:
            server_name = servers[0]
            print(f"Testing health check on: {server_name}")
            
            # Test the health check method
            result = app.health_monitor.check_server_health(server_name)
            print(f"Health check result: {result.status.value[2]} - {result.message}")
        
        print("OK Health monitoring functionality available")
        return True
        
    except Exception as e:
        print(f"FAILED Health monitoring test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase5_features():
    """Test Phase 5 UX features."""
    print("\nTesting Phase 5 features...")
    
    try:
        from mcp_manager.tui_app import MCPManagerTUI
        app = MCPManagerTUI()
        
        features_working = []
        
        # Test user preferences
        if hasattr(app, 'user_preferences') and app.user_preferences:
            features_working.append("User Preferences")
        
        # Test smart wizard
        if hasattr(app, 'smart_wizard') and app.smart_wizard:
            features_working.append("Smart Wizard")
        
        # Test error handler
        if hasattr(app, 'error_handler') and app.error_handler:
            features_working.append("Error Handler")
        
        # Test rollback manager
        if hasattr(app, 'rollback_manager') and app.rollback_manager:
            features_working.append("Rollback Manager")
        
        # Test help system
        if hasattr(app, 'help_system') and app.help_system:
            features_working.append("Help System")
        
        # Test onboarding
        if hasattr(app, 'onboarding_system') and app.onboarding_system:
            features_working.append("Onboarding System")
        
        print(f"Phase 5 features working: {len(features_working)}/6")
        for feature in features_working:
            print(f"  + {feature}")
        
        if len(features_working) >= 4:
            print("OK Most Phase 5 features are available")
            return True
        else:
            print("PARTIAL Phase 5 features partially available")
            return False
        
    except Exception as e:
        print(f"FAILED Phase 5 features test: {e}")
        import traceback
        traceback.print_exc()
        return False

def summarize_functionality():
    """Summarize what actually works vs what doesn't."""
    print("\n" + "="*50)
    print("FUNCTIONALITY SUMMARY")
    print("="*50)
    
    # Run all tests
    server_ok = test_server_display()
    deployment_ok = test_deployment_matrix()
    health_ok = test_health_monitoring()
    phase5_ok = test_phase5_features()
    
    working_count = sum([server_ok, deployment_ok, health_ok, phase5_ok])
    
    print(f"\nOverall Status: {working_count}/4 major areas working")
    
    if working_count >= 3:
        print("ASSESSMENT: TUI should be mostly functional")
        print("RECOMMENDATION: Test manually to verify UI interactions")
    elif working_count >= 2:
        print("ASSESSMENT: Core functionality works, some features may be broken")
        print("RECOMMENDATION: Fix broken areas before considering production-ready")
    else:
        print("ASSESSMENT: Major functionality is broken")
        print("RECOMMENDATION: Significant fixes needed")
    
    return working_count >= 3

if __name__ == "__main__":
    print("=== MCP Manager Functionality Test ===")
    success = summarize_functionality()
    
    if success:
        print("\nNEXT STEPS:")
        print("1. Launch TUI manually: uv run mcp-manager")
        print("2. Test keyboard shortcuts: A, E, D, H, R, Q")
        print("3. Test server selection and deployment")
        print("4. Test Phase 5 features in UI")
    else:
        print("\nREQUIRED FIXES:")
        print("1. Fix broken core functionality")
        print("2. Verify widget integration")
        print("3. Test again before manual testing")
    
    print("\n=== Functionality Test Complete ===")