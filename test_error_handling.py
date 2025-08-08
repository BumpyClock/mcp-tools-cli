#!/usr/bin/env python3
"""Test script for the comprehensive error handling and recovery system."""

import asyncio
import time
import random
from pathlib import Path

from src.mcp_manager.exceptions import *
from src.mcp_manager.error_handler import ErrorHandler, get_error_handler
from src.mcp_manager.rollback_manager import RollbackManager
from src.mcp_manager.backup_system import BackupSystem
from src.mcp_manager.error_logging import get_error_logger, generate_diagnostic_report
from src.mcp_manager.auto_recovery import get_auto_recovery_manager, RetryConfig, BackoffStrategy


def test_exception_hierarchy():
    """Test the custom exception hierarchy."""
    print("Testing exception hierarchy...")
    
    # Test basic error creation
    config_error = ConfigurationError(
        "Invalid configuration file",
        config_path="/path/to/config.json",
        field_name="api_key"
    )
    
    assert config_error.get_error_code() == "MCP_CONFIGURATIONERROR"
    assert config_error.config_path == "/path/to/config.json"
    assert RecoveryAction.MANUAL_FIX in config_error.suggested_actions
    
    # Test error factory
    network_error = ErrorFactory.create_error("network", "Connection timeout", endpoint="https://api.example.com")
    assert isinstance(network_error, NetworkError)
    assert RecoveryAction.RETRY in network_error.suggested_actions
    
    print("[PASS] Exception hierarchy tests passed!")


def test_backup_system():
    """Test the backup system functionality."""
    print("🧪 Testing backup system...")
    
    # Create test directory and files
    test_dir = Path("test_backup")
    test_dir.mkdir(exist_ok=True)
    
    test_files = []
    for i in range(3):
        file_path = test_dir / f"test_file_{i}.json"
        file_path.write_text(f'{{"test": "data_{i}", "version": {i}}}')
        test_files.append(file_path)
    
    try:
        # Test backup creation
        backup_system = BackupSystem()
        backup_id = backup_system.create_backup(
            "test_operation",
            "Testing backup functionality",
            test_files
        )
        
        assert backup_id is not None, "Backup creation failed"
        
        # Modify files
        for i, file_path in enumerate(test_files):
            file_path.write_text(f'{{"test": "modified_data_{i}", "version": {i + 10}}}')
        
        # Test restore
        success = backup_system.restore_backup(backup_id)
        assert success, "Backup restore failed"
        
        # Verify restoration
        for i, file_path in enumerate(test_files):
            content = file_path.read_text()
            assert f"data_{i}" in content, f"File {i} was not restored correctly"
        
        print("✅ Backup system tests passed!")
    
    finally:
        # Cleanup
        for file_path in test_files:
            try:
                file_path.unlink()
            except:
                pass
        try:
            test_dir.rmdir()
        except:
            pass


def test_rollback_manager():
    """Test the rollback manager functionality."""
    print("🧪 Testing rollback manager...")
    
    rollback_manager = RollbackManager()
    
    # Start a transaction
    transaction_id = rollback_manager.start_transaction(
        "test_deployment",
        "Testing rollback functionality"
    )
    
    assert transaction_id is not None
    assert rollback_manager.current_transaction is not None
    
    # Add some actions
    action_id_1 = rollback_manager.add_action(
        "deploy",
        "Deploy test server",
        server_name="test-server",
        platform_key="test-platform"
    )
    
    action_id_2 = rollback_manager.add_action(
        "config_change",
        "Update configuration",
        files_affected=[Path("test_config.json")],
        rollback_data={"original_value": "test"}
    )
    
    assert action_id_1 is not None
    assert action_id_2 is not None
    assert len(rollback_manager.current_transaction.actions) == 2
    
    # Commit transaction
    success = rollback_manager.commit_transaction()
    assert success, "Transaction commit failed"
    assert rollback_manager.current_transaction is None
    
    # Test rollback capability
    assert rollback_manager.can_rollback(), "Should be able to rollback"
    
    print("✅ Rollback manager tests passed!")


def test_error_handler():
    """Test the error handler with recovery strategies."""
    print("🧪 Testing error handler...")
    
    error_handler = get_error_handler()
    
    # Test configuration error handling
    config_error = ConfigurationError(
        "Missing API key",
        config_path="config.json",
        field_name="api_key",
        context=ErrorContext(operation="configuration_load")
    )
    
    recovery_result = error_handler.handle_error(config_error, auto_recover=True)
    
    assert recovery_result is not None
    assert not recovery_result.success  # Should require manual intervention
    assert recovery_result.manual_intervention_required
    
    # Test network error handling
    network_error = NetworkError(
        "Connection timeout",
        endpoint="https://api.example.com",
        context=ErrorContext(operation="api_call")
    )
    
    recovery_result = error_handler.handle_error(network_error, auto_recover=True)
    
    # Network errors should suggest retry
    assert recovery_result is not None
    
    print("✅ Error handler tests passed!")


async def test_auto_recovery():
    """Test the automatic recovery system."""
    print("🧪 Testing auto recovery system...")
    
    auto_recovery = get_auto_recovery_manager()
    
    # Test successful operation (no recovery needed)
    def successful_operation(data):
        return f"Success: {data}"
    
    success, result, error = await auto_recovery.execute_with_recovery(
        "test_success",
        "test",
        successful_operation,
        "test_data"
    )
    
    assert success, "Successful operation should succeed"
    assert result == "Success: test_data"
    assert error is None
    
    # Test operation that fails once then succeeds
    call_count = {"count": 0}
    
    def flaky_operation():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise Exception("First attempt fails")
        return "Success on second attempt"
    
    success, result, error = await auto_recovery.execute_with_recovery(
        "test_flaky",
        "test",
        flaky_operation
    )
    
    assert success, "Flaky operation should succeed on retry"
    assert result == "Success on second attempt"
    assert error is None
    
    # Test operation that always fails
    def failing_operation():
        raise Exception("This always fails")
    
    success, result, error = await auto_recovery.execute_with_recovery(
        "test_fail",
        "test", 
        failing_operation
    )
    
    assert not success, "Failing operation should fail"
    assert result is None
    assert error is not None
    
    print("✅ Auto recovery tests passed!")


def test_error_logging():
    """Test the error logging system."""
    print("🧪 Testing error logging...")
    
    error_logger = get_error_logger()
    
    # Log some test errors
    test_errors = [
        ConfigurationError("Test config error 1", config_path="test1.json"),
        NetworkError("Test network error 1", endpoint="test.example.com"),
        DeploymentError("Test deployment error 1", server_name="test-server"),
    ]
    
    for error in test_errors:
        error_logger.log_error(error, recovery_attempted=True, recovery_successful=False)
    
    # Test error statistics
    stats = error_logger.get_error_summary()
    assert stats["total_errors"] >= 3, "Should have at least 3 errors logged"
    
    # Test diagnostic report generation
    report = generate_diagnostic_report()
    assert report is not None
    assert report.report_id is not None
    assert len(report.recent_errors) >= 3
    
    print("✅ Error logging tests passed!")


async def simulate_real_world_scenario():
    """Simulate a real-world error scenario."""
    print("🎭 Simulating real-world error scenario...")
    
    rollback_manager = RollbackManager()
    error_handler = ErrorHandler(rollback_manager)
    auto_recovery = get_auto_recovery_manager()
    
    # Start a deployment transaction
    transaction_id = rollback_manager.start_transaction(
        "multi_server_deployment",
        "Deploy multiple servers to production"
    )
    
    # Simulate deployment of multiple servers
    servers = ["server-1", "server-2", "server-3"]
    deployment_results = []
    
    for i, server in enumerate(servers):
        rollback_manager.add_action(
            "deploy",
            f"Deploy {server}",
            server_name=server,
            platform_key="production"
        )
        
        # Simulate deployment operation that might fail
        async def deploy_server(server_name):
            await asyncio.sleep(0.1)  # Simulate work
            if random.random() < 0.3:  # 30% failure rate
                raise DeploymentError(
                    f"Failed to deploy {server_name}",
                    server_name=server_name,
                    platform_key="production"
                )
            return f"Successfully deployed {server_name}"
        
        try:
            success, result, error = await auto_recovery.execute_with_recovery(
                f"deploy_{server}",
                "deployment",
                deploy_server,
                server
            )
            
            if success:
                deployment_results.append(f"✅ {result}")
            else:
                deployment_results.append(f"❌ {server}: {error}")
                
                # Handle the error
                if error:
                    context = ErrorContext(
                        operation="deployment",
                        server_name=server,
                        platform_key="production"
                    )
                    recovery_result = error_handler.handle_error(error, context)
                    
                    if not recovery_result.success:
                        print(f"⚠️  Failed to recover from error deploying {server}")
                        # In a real scenario, this might trigger rollback
                        
        except Exception as e:
            deployment_results.append(f"❌ {server}: Unexpected error - {e}")
    
    # Commit or rollback transaction based on results
    failed_deployments = [r for r in deployment_results if r.startswith("❌")]
    
    if len(failed_deployments) > len(servers) / 2:
        print("🔄 Too many failures, initiating rollback...")
        rollback_success = rollback_manager.rollback_transaction()
        if rollback_success:
            print("✅ Rollback completed successfully")
        else:
            print("❌ Rollback failed")
    else:
        rollback_manager.commit_transaction()
        print("✅ Deployment transaction committed")
    
    print("\n📊 Deployment Results:")
    for result in deployment_results:
        print(f"   {result}")
    
    # Show recovery statistics
    recovery_stats = auto_recovery.get_recovery_statistics()
    print(f"\n📈 Recovery Statistics:")
    print(f"   Total operations: {recovery_stats['total_operations']}")
    print(f"   Success rate: {recovery_stats['success_rate']:.1f}%")
    print(f"   Average attempts: {recovery_stats['average_attempts']:.1f}")
    
    print("✅ Real-world scenario simulation completed!")


async def main():
    """Run all tests."""
    print("🚀 Starting Error Handling & Recovery System Tests\n")
    
    try:
        # Run individual component tests
        test_exception_hierarchy()
        test_backup_system()
        test_rollback_manager()
        test_error_handler()
        await test_auto_recovery()
        test_error_logging()
        
        # Run integrated scenario
        await simulate_real_world_scenario()
        
        print("\n[SUCCESS] All tests completed successfully!")
        
        # Generate final diagnostic report
        print("\n📋 Generating final diagnostic report...")
        report = generate_diagnostic_report()
        print(f"   Report ID: {report.report_id}")
        print(f"   Total errors logged: {report.error_summary['total_errors']}")
        print(f"   Recovery rate: {report.error_summary['recovery_rate']:.1f}%")
        print(f"   Most common error: {report.error_summary.get('most_common_error', 'None')}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)