"""Tests for utility functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from mcp_manager.utils import (
    load_json_file, save_json_file, backup_file,
    is_windows, wrap_command_for_windows, unwrap_command_from_windows,
    wrap_servers_for_windows, unwrap_servers_from_windows
)


class TestJSONFileOperations:
    """Test JSON file operations."""
    
    def test_load_existing_json_file(self):
        """Test loading an existing JSON file."""
        data = {"test": "data", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            filepath = Path(f.name)
        
        try:
            loaded_data = load_json_file(filepath)
            assert loaded_data == data
        finally:
            filepath.unlink()
    
    def test_load_nonexistent_json_file(self):
        """Test loading a non-existent JSON file returns empty dict."""
        filepath = Path("/nonexistent/file.json")
        loaded_data = load_json_file(filepath)
        assert loaded_data == {}
    
    def test_load_invalid_json_file(self):
        """Test loading invalid JSON returns empty dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            filepath = Path(f.name)
        
        try:
            loaded_data = load_json_file(filepath)
            assert loaded_data == {}
        finally:
            filepath.unlink()
    
    def test_save_json_file(self):
        """Test saving JSON file."""
        data = {"test": "data", "list": [1, 2, 3]}
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            filepath = Path(f.name)
        
        try:
            save_json_file(filepath, data)
            
            # Verify file was saved correctly
            with open(filepath, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == data
        finally:
            if filepath.exists():
                filepath.unlink()


class TestBackupFile:
    """Test file backup functionality."""
    
    def test_backup_existing_file(self):
        """Test backing up an existing file."""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            filepath = Path(f.name)
        
        try:
            backup_path = backup_file(filepath)
            
            assert backup_path is not None
            assert backup_path.exists()
            assert "backup" in backup_path.name
            
            # Verify backup has same content
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            assert backup_content == "test content"
            
        finally:
            filepath.unlink()
            if backup_path and backup_path.exists():
                backup_path.unlink()
    
    def test_backup_nonexistent_file(self):
        """Test backing up a non-existent file returns None."""
        filepath = Path("/nonexistent/file.txt")
        backup_path = backup_file(filepath)
        assert backup_path is None


class TestWindowsCompatibility:
    """Test Windows compatibility functions."""
    
    @patch('mcp_tools.utils.platform.system')
    def test_is_windows_true(self, mock_system):
        """Test is_windows returns True on Windows."""
        mock_system.return_value = "Windows"
        assert is_windows() is True
    
    @patch('mcp_tools.utils.platform.system')
    def test_is_windows_false(self, mock_system):
        """Test is_windows returns False on non-Windows."""
        mock_system.return_value = "Linux"
        assert is_windows() is False
    
    @patch('mcp_tools.utils.is_windows')
    def test_wrap_command_for_windows_npx(self, mock_is_windows):
        """Test wrapping npx command for Windows."""
        mock_is_windows.return_value = True
        
        server_config = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@example/package"]
        }
        
        wrapped = wrap_command_for_windows(server_config)
        
        assert wrapped["command"] == "cmd"
        assert wrapped["args"] == ["/c", "npx", "-y", "@example/package"]
    
    @patch('mcp_tools.utils.is_windows')
    def test_wrap_command_for_windows_not_windows(self, mock_is_windows):
        """Test wrapping command on non-Windows returns unchanged."""
        mock_is_windows.return_value = False
        
        server_config = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@example/package"]
        }
        
        wrapped = wrap_command_for_windows(server_config)
        
        assert wrapped == server_config
    
    @patch('mcp_tools.utils.is_windows')
    def test_wrap_command_for_windows_non_stdio(self, mock_is_windows):
        """Test wrapping non-stdio server returns unchanged."""
        mock_is_windows.return_value = True
        
        server_config = {
            "type": "http",
            "url": "https://api.example.com"
        }
        
        wrapped = wrap_command_for_windows(server_config)
        
        assert wrapped == server_config
    
    def test_unwrap_command_from_windows(self):
        """Test unwrapping Windows command."""
        server_config = {
            "type": "stdio",
            "command": "cmd",
            "args": ["/c", "npx", "-y", "@example/package"]
        }
        
        unwrapped = unwrap_command_from_windows(server_config)
        
        assert unwrapped["command"] == "npx"
        assert unwrapped["args"] == ["-y", "@example/package"]
    
    def test_unwrap_command_legacy_format(self):
        """Test unwrapping legacy cmd /c format."""
        server_config = {
            "type": "stdio",
            "command": "cmd /c npx"
        }
        
        unwrapped = unwrap_command_from_windows(server_config)
        
        assert unwrapped["command"] == "npx"
        assert "args" not in unwrapped
    
    @patch('mcp_tools.utils.is_windows')
    def test_wrap_servers_for_windows(self, mock_is_windows):
        """Test wrapping multiple servers for Windows."""
        mock_is_windows.return_value = True
        
        servers = {
            "server1": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@example/package1"]
            },
            "server2": {
                "type": "stdio", 
                "command": "uvx",
                "args": ["package2"]
            },
            "server3": {
                "type": "http",
                "url": "https://api.example.com"
            }
        }
        
        wrapped = wrap_servers_for_windows(servers)
        
        # npx and uvx should be wrapped
        assert wrapped["server1"]["command"] == "cmd"
        assert wrapped["server2"]["command"] == "cmd"
        
        # http server should be unchanged
        assert wrapped["server3"] == servers["server3"]
    
    def test_unwrap_servers_from_windows(self):
        """Test unwrapping multiple servers from Windows."""
        servers = {
            "server1": {
                "type": "stdio",
                "command": "cmd", 
                "args": ["/c", "npx", "-y", "@example/package"]
            },
            "server2": {
                "type": "stdio",
                "command": "python",
                "args": ["server.py"]
            }
        }
        
        unwrapped = unwrap_servers_from_windows(servers)
        
        # First server should be unwrapped
        assert unwrapped["server1"]["command"] == "npx"
        assert unwrapped["server1"]["args"] == ["-y", "@example/package"]
        
        # Second server should be unchanged
        assert unwrapped["server2"] == servers["server2"]


class TestDiffDisplay:
    """Test diff display functionality."""
    
    def test_show_diff_no_changes(self, capsys):
        """Test showing diff with no changes."""
        from mcp_tools.utils import show_diff
        
        servers1 = {
            "server1": {"type": "stdio", "command": "npx"}
        }
        servers2 = {
            "server1": {"type": "stdio", "command": "npx"}
        }
        
        show_diff(servers1, servers2, "test")
        
        captured = capsys.readouterr()
        assert "[OK] No changes detected" in captured.out
    
    def test_show_diff_additions(self, capsys):
        """Test showing diff with additions."""
        from mcp_tools.utils import show_diff
        
        old_servers = {}
        new_servers = {
            "server1": {"type": "stdio", "command": "npx"}
        }
        
        show_diff(old_servers, new_servers, "test")
        
        captured = capsys.readouterr()
        assert "SERVERS TO ADD" in captured.out
        assert "server1" in captured.out