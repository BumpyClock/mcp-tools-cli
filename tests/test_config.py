"""Tests for configuration models."""

import pytest
from pydantic import ValidationError

from mcp_manager.config import (
    STDIOMCPServer, HTTPMCPServer, DockerMCPServer, SSEMCPServer,
    parse_server_config, validate_mcp_servers_dict,
    is_api_key_placeholder, normalize_config_keys
)


class TestSTDIOMCPServer:
    """Test STDIO MCP server configuration."""
    
    def test_valid_stdio_server(self):
        """Test valid STDIO server configuration."""
        config = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
        server = STDIOMCPServer(**config)
        assert server.type == "stdio"
        assert server.command == "npx"
        assert server.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    
    def test_stdio_server_with_env(self):
        """Test STDIO server with environment variables."""
        config = {
            "type": "stdio",
            "command": "python",
            "args": ["server.py"],
            "env": {
                "API_KEY": "test-key",
                "DEBUG": True
            }
        }
        server = STDIOMCPServer(**config)
        assert server.env["API_KEY"] == "test-key"
        assert server.env["DEBUG"] is True
    
    def test_stdio_server_empty_command(self):
        """Test STDIO server with empty command fails validation."""
        config = {
            "type": "stdio",
            "command": ""
        }
        with pytest.raises(ValidationError):
            STDIOMCPServer(**config)
    
    def test_stdio_server_missing_command(self):
        """Test STDIO server without command fails validation."""
        config = {
            "type": "stdio"
        }
        with pytest.raises(ValidationError):
            STDIOMCPServer(**config)


class TestHTTPMCPServer:
    """Test HTTP MCP server configuration."""
    
    def test_valid_http_server(self):
        """Test valid HTTP server configuration."""
        config = {
            "type": "http", 
            "url": "https://api.example.com/mcp"
        }
        server = HTTPMCPServer(**config)
        assert server.type == "http"
        assert server.url == "https://api.example.com/mcp"
    
    def test_http_server_invalid_url(self):
        """Test HTTP server with invalid URL fails validation."""
        config = {
            "type": "http",
            "url": "not-a-url"
        }
        with pytest.raises(ValidationError):
            HTTPMCPServer(**config)
    
    def test_http_server_missing_url(self):
        """Test HTTP server without URL fails validation."""
        config = {
            "type": "http"
        }
        with pytest.raises(ValidationError):
            HTTPMCPServer(**config)


class TestDockerMCPServer:
    """Test Docker MCP server configuration."""
    
    def test_valid_docker_server(self):
        """Test valid Docker server configuration."""
        config = {
            "type": "docker",
            "command": "docker",
            "args": ["run", "mcp-server:latest"]
        }
        server = DockerMCPServer(**config)
        assert server.type == "docker"
        assert server.command == "docker"
        assert server.args == ["run", "mcp-server:latest"]


class TestSSEMCPServer:
    """Test SSE MCP server configuration."""
    
    def test_valid_sse_server(self):
        """Test valid SSE server configuration."""
        config = {
            "type": "sse",
            "url": "https://api.example.com/sse"
        }
        server = SSEMCPServer(**config)
        assert server.type == "sse"
        assert server.url == "https://api.example.com/sse"


class TestParseServerConfig:
    """Test server configuration parsing."""
    
    def test_parse_stdio_server(self):
        """Test parsing STDIO server configuration."""
        config = {
            "type": "stdio",
            "command": "npx"
        }
        server = parse_server_config("test-server", config)
        assert isinstance(server, STDIOMCPServer)
        assert server.command == "npx"
    
    def test_parse_http_server(self):
        """Test parsing HTTP server configuration."""
        config = {
            "type": "http",
            "url": "https://api.example.com"
        }
        server = parse_server_config("test-server", config)
        assert isinstance(server, HTTPMCPServer)
        assert server.url == "https://api.example.com"
    
    def test_parse_unknown_server_type(self):
        """Test parsing unknown server type fails."""
        config = {
            "type": "unknown"
        }
        with pytest.raises(ValueError, match="Unknown server type: unknown"):
            parse_server_config("test-server", config)


class TestValidateMCPServersDict:
    """Test validation of MCP servers dictionary."""
    
    def test_validate_valid_servers(self):
        """Test validation of valid servers dictionary."""
        servers = {
            "server1": {
                "type": "stdio",
                "command": "npx"
            },
            "server2": {
                "type": "http", 
                "url": "https://api.example.com"
            }
        }
        validated = validate_mcp_servers_dict(servers)
        assert len(validated) == 2
        assert isinstance(validated["server1"], STDIOMCPServer)
        assert isinstance(validated["server2"], HTTPMCPServer)
    
    def test_validate_invalid_server(self):
        """Test validation fails for invalid server."""
        servers = {
            "server1": {
                "type": "stdio"
                # Missing required command
            }
        }
        with pytest.raises(ValueError, match="Invalid configuration for server 'server1'"):
            validate_mcp_servers_dict(servers)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_is_api_key_placeholder(self):
        """Test API key placeholder detection."""
        assert is_api_key_placeholder("YOUR_API_KEY_HERE")
        assert is_api_key_placeholder("YOUR_TOKEN_HERE")
        assert is_api_key_placeholder("REPLACE_ME")
        assert is_api_key_placeholder("")
        assert is_api_key_placeholder("<YOUR_KEY>")
        assert is_api_key_placeholder("[YOUR_KEY]")
        
        assert not is_api_key_placeholder("actual-api-key-123")
        assert not is_api_key_placeholder("sk-1234567890abcdef")
        assert not is_api_key_placeholder(123)
        assert not is_api_key_placeholder(None)
    
    def test_normalize_config_keys(self):
        """Test configuration key normalization."""
        config = {
            "mcps": {
                "server1": {"type": "stdio", "command": "npx"}
            }
        }
        normalized = normalize_config_keys(config)
        assert "mcpServers" in normalized
        assert "mcps" not in normalized
        assert normalized["mcpServers"]["server1"]["command"] == "npx"
    
    def test_normalize_config_keys_already_normalized(self):
        """Test normalization of already normalized config."""
        config = {
            "mcpServers": {
                "server1": {"type": "stdio", "command": "npx"}
            }
        }
        normalized = normalize_config_keys(config)
        assert normalized == config