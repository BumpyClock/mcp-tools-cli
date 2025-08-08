#!/usr/bin/env python3
"""Test script for the MCP configuration validation system."""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from src.mcp_manager.config_validator import ConfigValidator
from src.mcp_manager.auto_repair import AutoRepair


def create_test_configurations() -> Dict[str, Dict[str, Any]]:
    """Create test server configurations with various issues."""
    
    return {
        # Perfect configuration
        "openai-server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@openai/mcp-server-openai"],
            "env": {
                "OPENAI_API_KEY": "sk-proj-abcd1234567890abcd1234567890abcd1234567890abcd1234567890"
            },
            "metadata": {
                "description": "OpenAI MCP server",
                "tags": ["ai", "openai"],
                "enabled": True
            }
        },
        
        # Missing required fields
        "broken-server": {
            "type": "stdio"
            # Missing command!
        },
        
        # API key placeholders
        "placeholder-server": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-server"],
            "env": {
                "ANTHROPIC_API_KEY": "YOUR_API_KEY_HERE"
            }
        },
        
        # Format issues
        "format-issues": {
            "type": "http",
            "url": "example.com/api",  # Missing protocol
            "env": "not-a-dict",  # Should be dict
            "args": "should be array"  # Should be array
        },
        
        # Common typos
        "typo-server": {
            "type": "stdio",
            "cmd": "npx",  # Should be "command"
            "arguments": ["-y", "some-server"],  # Should be "args"
            "environmental": {  # Should be "env"
                "API_KEY": "test"
            }
        },
        
        # Path issues
        "path-server": {
            "type": "stdio",
            "command": "/nonexistent/path/to/server",
            "args": ["--config", "/also/nonexistent/config.json"]
        }
    }


def test_validation_system():
    """Test the configuration validation system."""
    print("Testing MCP Configuration Validation System")
    print("=" * 50)
    
    # Initialize validation system
    validator = ConfigValidator()
    auto_repair = AutoRepair()
    
    # Create test configurations
    test_configs = create_test_configurations()
    
    print(f"Testing {len(test_configs)} server configurations...\n")
    
    for server_name, config in test_configs.items():
        print(f"Testing: {server_name}")
        print("-" * 30)
        
        # Validate configuration
        result = validator.validate_server_config(
            server_name, config, check_health=False
        )
        
        # Display validation results
        score_icon = "PASS" if result.score >= 90 else "WARN" if result.score >= 70 else "FAIL"
        print(f"   {score_icon} Score: {result.score}% ({'VALID' if result.valid else 'INVALID'})")
        
        # Display issues
        if result.issues:
            print(f"   Issues ({len(result.issues)}):")
            for issue in result.issues:
                severity_icon = {"error": "ERR", "warning": "WARN", "info": "INFO"}.get(issue.severity, "?")
                print(f"      [{severity_icon}] {issue.severity.upper()}: {issue.message}")
                if issue.field:
                    print(f"         Field: {issue.field}")
                if issue.suggested_value:
                    print(f"         Suggestion: {issue.suggested_value}")
                if issue.auto_fixable:
                    print(f"         [AUTO-FIX] Available")
                print()
        else:
            print("   [PASS] No issues found!")
        
        # Test auto-repair suggestions
        suggestions = auto_repair.analyze_issues(result, config)
        if suggestions:
            print(f"   Repair Suggestions ({len(suggestions)}):")
            for i, suggestion in enumerate(suggestions, 1):
                confidence = suggestion.get_total_confidence()
                confidence_text = "HIGH" if confidence > 0.7 else "MED" if confidence > 0.4 else "LOW"
                print(f"      {i}. {suggestion.title}")
                print(f"         Confidence: {confidence_text} ({confidence:.0%})")
                print(f"         Time: {suggestion.estimated_time}")
                print(f"         Success rate: {suggestion.success_rate:.0%}")
                
                # Show auto-fixable actions
                auto_actions = [a for a in suggestion.actions if a.auto_applicable]
                if auto_actions:
                    print(f"         Auto-fixable actions: {len(auto_actions)}/{len(suggestion.actions)}")
                print()
        else:
            print("   [INFO] No repair suggestions available")
        
        print()
    
    # Test validation summary
    print("Validation Summary")
    print("-" * 20)
    
    all_results = {}
    for server_name, config in test_configs.items():
        result = validator.validate_server_config(server_name, config)
        all_results[server_name] = result
    
    summary = validator.get_validation_summary(all_results)
    
    print(f"Total servers: {summary['total_servers']}")
    print(f"Valid servers: {summary['valid_servers']}")
    print(f"Invalid servers: {summary['invalid_servers']}")
    print(f"Average score: {summary['average_score']}%")
    
    print("\nIssues by category:")
    for category, count in summary['issues_by_category'].items():
        print(f"  {category}: {count}")
    
    print("\nIssues by severity:")
    for severity, count in summary['issues_by_severity'].items():
        icon = {"error": "ERR", "warning": "WARN", "info": "INFO"}.get(severity, "?")
        print(f"  [{icon}] {severity}: {count}")
    
    print("\n[PASS] Validation system test complete!")


def test_auto_repair():
    """Test the auto-repair system."""
    print("\nTesting Auto-Repair System")
    print("=" * 30)
    
    validator = ConfigValidator()
    auto_repair = AutoRepair()
    
    # Test with typo server
    config = {
        "type": "stdio",
        "cmd": "npx",  # Should be "command"
        "arguments": ["-y", "some-server"],  # Should be "args" 
        "env": {"API_KEY": "test"}
    }
    
    print("Original config:")
    print(json.dumps(config, indent=2))
    
    # Validate
    result = validator.validate_server_config("test-server", config)
    print(f"\nValidation score: {result.score}%")
    print(f"Issues found: {len(result.issues)}")
    
    # Get repair suggestions
    suggestions = auto_repair.analyze_issues(result, config)
    print(f"Repair suggestions: {len(suggestions)}")
    
    # Apply auto-fixes
    repaired_config = config.copy()
    applied_fixes = 0
    
    for suggestion in suggestions:
        success, new_config, errors = auto_repair.apply_repair_suggestion(
            suggestion, repaired_config, skip_confirmations=True
        )
        
        if success:
            repaired_config = new_config
            applied_fixes += 1
            print(f"[PASS] Applied: {suggestion.title}")
        else:
            print(f"[FAIL] Failed: {suggestion.title}")
            for error in errors:
                print(f"   Error: {error}")
    
    print(f"\nApplied {applied_fixes} fixes")
    print("\nRepaired config:")
    print(json.dumps(repaired_config, indent=2))
    
    # Re-validate
    new_result = validator.validate_server_config("test-server", repaired_config)
    print(f"\nNew validation score: {new_result.score}%")
    print(f"Remaining issues: {len(new_result.issues)}")
    
    print("[PASS] Auto-repair test complete!")


if __name__ == "__main__":
    try:
        test_validation_system()
        test_auto_repair()
    except KeyboardInterrupt:
        print("\n\n[STOP] Test interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()