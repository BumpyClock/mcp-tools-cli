"""Tests for CLI interface."""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from mcp_manager.cli import app


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "MCP Tools" in result.stdout
        assert "push" in result.stdout
        assert "pull" in result.stdout
        assert "validate" in result.stdout
        assert "health" in result.stdout
    
    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.stdout
    
    def test_push_command_help(self):
        """Test push command help."""
        result = self.runner.invoke(app, ["push", "--help"])
        assert result.exit_code == 0
        assert "Push MCP servers" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--health-check" in result.stdout
    
    def test_pull_command_help(self):
        """Test pull command help."""
        result = self.runner.invoke(app, ["pull", "--help"])
        assert result.exit_code == 0
        assert "Pull MCP servers" in result.stdout
        assert "--sync-secrets" in result.stdout
    
    def test_validate_command_help(self):
        """Test validate command help."""
        result = self.runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate MCP server" in result.stdout
    
    def test_health_command_help(self):
        """Test health command help."""
        result = self.runner.invoke(app, ["health", "--help"])
        assert result.exit_code == 0
        assert "Check health" in result.stdout
    
    def test_status_command_help(self):
        """Test status command help."""
        result = self.runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show status" in result.stdout


class TestPushCommand:
    """Test push command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    def test_push_nonexistent_mcp_file(self):
        """Test push with non-existent mcp-servers.json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "nonexistent.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            result = self.runner.invoke(app, [
                "push",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 1
            assert "does not exist" in result.stdout
    
    @patch('mcp_tools.cli.push_to_claude_config')
    def test_push_dry_run(self, mock_push):
        """Test push command in dry run mode."""
        mock_push.return_value = True
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            # Create a valid mcp-servers.json
            mcp_data = {
                "mcpServers": {
                    "test-server": {
                        "type": "stdio",
                        "command": "npx"
                    }
                }
            }
            mcp_file.write_text(json.dumps(mcp_data))
            
            result = self.runner.invoke(app, [
                "push",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file),
                "--dry-run"
            ])
            
            assert result.exit_code == 0
            mock_push.assert_called_once()
            args, kwargs = mock_push.call_args
            assert kwargs["dry_run"] is True
    
    @patch('mcp_tools.cli.push_to_claude_config')
    def test_push_with_health_check(self, mock_push):
        """Test push command with health check."""
        mock_push.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            mcp_data = {
                "mcpServers": {
                    "test-server": {
                        "type": "stdio",
                        "command": "npx"
                    }
                }
            }
            mcp_file.write_text(json.dumps(mcp_data))
            
            result = self.runner.invoke(app, [
                "push",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file),
                "--health-check"
            ])
            
            assert result.exit_code == 0
            mock_push.assert_called_once()
            args, kwargs = mock_push.call_args
            assert kwargs["health_check"] is True


class TestPullCommand:
    """Test pull command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    def test_pull_nonexistent_claude_file(self):
        """Test pull with non-existent ~/.claude.json file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "nonexistent.json"
            
            result = self.runner.invoke(app, [
                "pull",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 1
            assert "does not exist" in result.stdout
    
    @patch('mcp_tools.cli.pull_from_claude_config')
    def test_pull_with_sync_secrets(self, mock_pull):
        """Test pull command with sync secrets."""
        mock_pull.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            # Create a valid claude.json
            claude_data = {
                "mcpServers": {
                    "test-server": {
                        "type": "stdio",
                        "command": "npx"
                    }
                }
            }
            claude_file.write_text(json.dumps(claude_data))
            
            result = self.runner.invoke(app, [
                "pull",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file),
                "--sync-secrets"
            ])
            
            assert result.exit_code == 0
            mock_pull.assert_called_once()
            args, kwargs = mock_pull.call_args
            assert kwargs["sync_secrets"] is True


class TestValidateCommand:
    """Test validate command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    @patch('mcp_tools.cli.validate_configurations')
    def test_validate_success(self, mock_validate):
        """Test successful validation."""
        mock_validate.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            result = self.runner.invoke(app, [
                "validate",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 0
            mock_validate.assert_called_once()
    
    @patch('mcp_tools.cli.validate_configurations')
    def test_validate_failure(self, mock_validate):
        """Test failed validation."""
        mock_validate.return_value = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            result = self.runner.invoke(app, [
                "validate",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 1
            mock_validate.assert_called_once()


class TestHealthCommand:
    """Test health command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    @patch('mcp_tools.cli.health_check_configurations')
    def test_health_check_success(self, mock_health):
        """Test successful health check."""
        mock_health.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            result = self.runner.invoke(app, [
                "health",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 0
            mock_health.assert_called_once()
    
    @patch('mcp_tools.cli.health_check_configurations')
    def test_health_check_issues(self, mock_health):
        """Test health check with issues."""
        mock_health.return_value = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            result = self.runner.invoke(app, [
                "health",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 0  # Health issues don't cause exit failure
            mock_health.assert_called_once()


class TestStatusCommand:
    """Test status command functionality."""
    
    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()
    
    def test_status_command(self):
        """Test status command output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp-servers.json"
            claude_file = Path(tmpdir) / "claude.json"
            
            # Create files with some data
            mcp_data = {
                "mcpServers": {
                    "server1": {"type": "stdio", "command": "npx"}
                }
            }
            mcp_file.write_text(json.dumps(mcp_data))
            
            claude_data = {
                "mcpServers": {
                    "server1": {"type": "stdio", "command": "npx"},
                    "server2": {"type": "http", "url": "https://api.example.com"}
                }
            }
            claude_file.write_text(json.dumps(claude_data))
            
            result = self.runner.invoke(app, [
                "status",
                "--mcp-file", str(mcp_file),
                "--claude-file", str(claude_file)
            ])
            
            assert result.exit_code == 0
            assert "Configuration Status" in result.stdout
            assert "mcp-servers.json" in result.stdout
            assert "~/.claude.json" in result.stdout