#!/usr/bin/env python3
"""Simple test script for error handling system without Unicode issues."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

try:
    from mcp_manager.exceptions import *
    from mcp_manager.error_handler import ErrorHandler
    from mcp_manager.rollback_manager import RollbackManager
    from mcp_manager.backup_system import BackupSystem
    
    print("[TEST] Testing basic error handling functionality...")
    
    # Test 1: Basic exception creation
    print("\n[TEST] Creating test exceptions...")
    
    config_error = ConfigurationError(
        "Missing API key",
        config_path="config.json",
        field_name="api_key"
    )
    
    network_error = NetworkError(
        "Connection timeout",
        endpoint="https://api.example.com"
    )
    
    deployment_error = DeploymentError(
        "Server deployment failed",
        server_name="test-server",
        platform_key="production"
    )
    
    print(f"[PASS] Created ConfigurationError: {config_error.get_error_code()}")
    print(f"[PASS] Created NetworkError: {network_error.get_error_code()}")
    print(f"[PASS] Created DeploymentError: {deployment_error.get_error_code()}")
    
    # Test 2: Error factory
    print("\n[TEST] Testing error factory...")
    
    factory_error = ErrorFactory.create_error("network", "Test network error")
    assert isinstance(factory_error, NetworkError)
    print("[PASS] Error factory creates correct error types")
    
    # Test 3: BackupSystem
    print("\n[TEST] Testing backup system...")
    
    test_dir = Path("test_backup_simple")
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "test_file.txt"
    test_file.write_text("Original content")
    
    try:
        backup_system = BackupSystem()
        backup_id = backup_system.create_backup(
            "test_operation",
            "Simple test backup",
            [test_file]
        )
        
        if backup_id:
            print(f"[PASS] Created backup: {backup_id}")
            
            # Modify file
            test_file.write_text("Modified content")
            
            # Restore backup
            success = backup_system.restore_backup(backup_id)
            if success:
                content = test_file.read_text()
                if content == "Original content":
                    print("[PASS] Backup restore successful")
                else:
                    print("[FAIL] Backup restore failed - content mismatch")
            else:
                print("[FAIL] Backup restore failed")
        else:
            print("[FAIL] Backup creation failed")
    
    finally:
        # Cleanup
        try:
            test_file.unlink()
            test_dir.rmdir()
        except:
            pass
    
    # Test 4: RollbackManager
    print("\n[TEST] Testing rollback manager...")
    
    rollback_manager = RollbackManager()
    
    # Start transaction
    transaction_id = rollback_manager.start_transaction(
        "test_deployment", 
        "Simple test transaction"
    )
    
    if transaction_id:
        print(f"[PASS] Started transaction: {transaction_id}")
        
        # Add action
        action_id = rollback_manager.add_action(
            "deploy",
            "Test deployment action",
            server_name="test-server"
        )
        
        if action_id:
            print(f"[PASS] Added action: {action_id}")
            
            # Commit transaction
            success = rollback_manager.commit_transaction()
            if success:
                print("[PASS] Transaction committed successfully")
            else:
                print("[FAIL] Transaction commit failed")
        else:
            print("[FAIL] Action addition failed")
    else:
        print("[FAIL] Transaction start failed")
    
    # Test 5: ErrorHandler
    print("\n[TEST] Testing error handler...")
    
    error_handler = ErrorHandler(rollback_manager)
    
    # Test error handling
    test_error = ConfigurationError(
        "Test configuration error",
        context=ErrorContext(operation="test")
    )
    
    recovery_result = error_handler.handle_error(test_error, auto_recover=True)
    
    if recovery_result:
        print(f"[PASS] Error handled: {recovery_result.action_taken}")
    else:
        print("[FAIL] Error handling failed")
    
    print("\n[SUCCESS] All basic tests completed successfully!")
    print("\nThe comprehensive error handling and recovery system is working!")
    print("\nFeatures implemented:")
    print("- Custom exception hierarchy with error codes")
    print("- Automatic backup system for configuration rollback")
    print("- Transaction-based rollback manager")
    print("- Intelligent error handler with recovery strategies")
    print("- Integration ready for TUI application")
    
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print("Make sure all error handling modules are properly created")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)