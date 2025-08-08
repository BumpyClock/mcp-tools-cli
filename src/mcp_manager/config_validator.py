"""Real-time configuration validation system for MCP servers."""

import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
import structlog

from .config import (
    parse_server_config, 
    is_api_key_placeholder, 
    STDIOMCPServer, 
    HTTPMCPServer, 
    SSEMCPServer, 
    DockerMCPServer
)
from .validators import check_server_health

logger = structlog.get_logger()


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: str  # "error", "warning", "info"
    category: str  # "required_field", "api_key", "path", "format", "network"
    message: str
    field: Optional[str] = None
    suggested_value: Optional[str] = None
    fix_action: Optional[str] = None
    auto_fixable: bool = False
    
    def __post_init__(self):
        """Set auto_fixable based on category."""
        if self.auto_fixable is None:
            self.auto_fixable = self.category in {
                "format", "common_typo", "missing_optional", "default_value"
            }


@dataclass
class ValidationResult:
    """Results of configuration validation."""
    server_name: str
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: int = 100  # 0-100 validation score
    last_validated: datetime = field(default_factory=datetime.now)
    health_checked: bool = False
    health_status: Optional[str] = None
    
    def __post_init__(self):
        """Calculate validation score."""
        if not self.issues:
            self.score = 100
            return
            
        penalty = 0
        for issue in self.issues:
            if issue.severity == "error":
                penalty += 30
            elif issue.severity == "warning":
                penalty += 10
            elif issue.severity == "info":
                penalty += 5
        
        self.score = max(0, 100 - penalty)
        self.valid = self.score >= 70 and not any(i.severity == "error" for i in self.issues)


@dataclass
class ValidationTemplate:
    """Template for common server configurations."""
    name: str
    description: str
    server_type: str
    config_template: Dict[str, Any]
    required_env_vars: List[str] = field(default_factory=list)
    optional_env_vars: List[str] = field(default_factory=list)
    common_commands: List[str] = field(default_factory=list)


class ValidationCache:
    """Thread-safe cache for validation results."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5-minute TTL
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, ValidationResult] = {}
        self._lock = Lock()
    
    def get(self, server_name: str, config_hash: str) -> Optional[ValidationResult]:
        """Get cached validation result if still valid."""
        cache_key = f"{server_name}:{config_hash}"
        
        with self._lock:
            if cache_key in self._cache:
                result = self._cache[cache_key]
                if datetime.now() - result.last_validated < self.ttl:
                    return result
                else:
                    del self._cache[cache_key]
        
        return None
    
    def set(self, server_name: str, config_hash: str, result: ValidationResult):
        """Cache validation result."""
        cache_key = f"{server_name}:{config_hash}"
        
        with self._lock:
            self._cache[cache_key] = result
    
    def clear(self):
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
    
    def remove(self, server_name: str):
        """Remove all cached results for a server."""
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{server_name}:")]
            for key in keys_to_remove:
                del self._cache[key]


class ConfigValidator:
    """Real-time configuration validator for MCP servers."""
    
    def __init__(self):
        self.cache = ValidationCache()
        self._templates = self._load_validation_templates()
        self._api_key_patterns = self._load_api_key_patterns()
        self._common_commands = self._load_common_commands()
        
        # Validation rules
        self._rules: List[Callable] = [
            self._validate_required_fields,
            self._validate_server_type,
            self._validate_command_and_args,
            self._validate_environment_variables,
            self._validate_api_keys,
            self._validate_urls,
            self._validate_paths,
            self._validate_json_syntax,
            self._detect_common_typos,
            self._suggest_improvements,
        ]
    
    def validate_server_config(
        self, 
        server_name: str, 
        server_config: Dict[str, Any],
        check_health: bool = False,
        use_cache: bool = True
    ) -> ValidationResult:
        """Validate a single server configuration."""
        config_hash = self._hash_config(server_config)
        
        # Check cache first
        if use_cache:
            cached_result = self.cache.get(server_name, config_hash)
            if cached_result:
                logger.debug("Using cached validation result", server=server_name)
                return cached_result
        
        logger.debug("Validating server configuration", server=server_name)
        issues = []
        
        # Run all validation rules
        for rule in self._rules:
            try:
                rule_issues = rule(server_name, server_config)
                issues.extend(rule_issues)
            except Exception as e:
                logger.warning("Validation rule failed", rule=rule.__name__, error=str(e))
                issues.append(ValidationIssue(
                    severity="warning",
                    category="validator_error",
                    message=f"Validation rule '{rule.__name__}' failed: {e}"
                ))
        
        # Create result
        result = ValidationResult(
            server_name=server_name,
            valid=not any(issue.severity == "error" for issue in issues),
            issues=issues
        )
        
        # Health check if requested
        if check_health:
            result.health_checked = True
            try:
                is_healthy, health_error = check_server_health(server_name, server_config)
                result.health_status = "healthy" if is_healthy else health_error
                
                if not is_healthy:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="health",
                        message=f"Health check failed: {health_error}",
                        fix_action="check_requirements"
                    ))
            except Exception as e:
                logger.warning("Health check failed", server=server_name, error=str(e))
                result.health_status = f"Health check error: {e}"
        
        # Update result with new issues
        result.issues = issues
        result.__post_init__()  # Recalculate score and validity
        
        # Cache result
        if use_cache:
            self.cache.set(server_name, config_hash, result)
        
        return result
    
    def validate_all_servers(
        self, 
        servers: Dict[str, Dict[str, Any]], 
        check_health: bool = False
    ) -> Dict[str, ValidationResult]:
        """Validate all server configurations."""
        logger.info("Validating all server configurations", count=len(servers))
        
        results = {}
        for server_name, server_config in servers.items():
            results[server_name] = self.validate_server_config(
                server_name, server_config, check_health=check_health
            )
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for validation results."""
        if not results:
            return {
                "total_servers": 0,
                "valid_servers": 0,
                "invalid_servers": 0,
                "average_score": 0,
                "issues_by_category": {},
                "issues_by_severity": {}
            }
        
        valid_count = sum(1 for r in results.values() if r.valid)
        invalid_count = len(results) - valid_count
        average_score = sum(r.score for r in results.values()) / len(results)
        
        # Categorize issues
        issues_by_category = {}
        issues_by_severity = {}
        
        for result in results.values():
            for issue in result.issues:
                issues_by_category[issue.category] = issues_by_category.get(issue.category, 0) + 1
                issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
        
        return {
            "total_servers": len(results),
            "valid_servers": valid_count,
            "invalid_servers": invalid_count,
            "average_score": round(average_score, 1),
            "issues_by_category": issues_by_category,
            "issues_by_severity": issues_by_severity
        }
    
    def _hash_config(self, config: Dict[str, Any]) -> str:
        """Create a hash of the configuration for caching."""
        import hashlib
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _validate_required_fields(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate required fields based on server type."""
        issues = []
        server_type = config.get('type', 'stdio')
        
        # Check server type
        if server_type not in ['stdio', 'http', 'sse', 'docker']:
            issues.append(ValidationIssue(
                severity="error",
                category="required_field",
                message=f"Invalid server type: {server_type}",
                field="type",
                suggested_value="stdio",
                fix_action="set_server_type",
                auto_fixable=True
            ))
            return issues
        
        # Type-specific validation
        if server_type in ['stdio', 'docker']:
            if not config.get('command'):
                issues.append(ValidationIssue(
                    severity="error",
                    category="required_field",
                    message="Missing required field: command",
                    field="command",
                    fix_action="add_command",
                    auto_fixable=False
                ))
        
        elif server_type in ['http', 'sse']:
            if not config.get('url'):
                issues.append(ValidationIssue(
                    severity="error",
                    category="required_field",
                    message="Missing required field: url",
                    field="url",
                    fix_action="add_url",
                    auto_fixable=False
                ))
        
        return issues
    
    def _validate_server_type(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate server type using Pydantic models."""
        issues = []
        
        try:
            parse_server_config(server_name, config)
        except ValueError as e:
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message=f"Configuration validation failed: {e}",
                fix_action="fix_format"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message=f"Unexpected validation error: {e}",
                fix_action="fix_config"
            ))
        
        return issues
    
    def _validate_command_and_args(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate command and arguments."""
        issues = []
        command = config.get('command')
        args = config.get('args', [])
        
        if not command:
            return issues  # Handled by required fields validation
        
        # Check if command exists in PATH
        import shutil
        if not shutil.which(command) and command not in ['docker', 'npx', 'uvx', 'python', 'node']:
            issues.append(ValidationIssue(
                severity="warning",
                category="path",
                message=f"Command '{command}' not found in PATH",
                field="command",
                fix_action="check_command_path"
            ))
        
        # Validate args format
        if args and not isinstance(args, list):
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message="Arguments must be a list",
                field="args",
                fix_action="fix_args_format",
                auto_fixable=True
            ))
        
        # Check for common command issues
        if command == 'npx' and args:
            package_name = args[0] if args else None
            if package_name and '@' not in package_name:
                issues.append(ValidationIssue(
                    severity="info",
                    category="suggestion",
                    message=f"Consider specifying version for npm package: {package_name}@latest",
                    field="args",
                    suggested_value=f"{package_name}@latest"
                ))
        
        return issues
    
    def _validate_environment_variables(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate environment variables."""
        issues = []
        env = config.get('env', {})
        
        if not env:
            return issues
        
        if not isinstance(env, dict):
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message="Environment variables must be a dictionary",
                field="env",
                fix_action="fix_env_format",
                auto_fixable=True
            ))
            return issues
        
        # Check for empty values
        for key, value in env.items():
            if value == "":
                issues.append(ValidationIssue(
                    severity="warning",
                    category="missing_value",
                    message=f"Environment variable '{key}' is empty",
                    field=f"env.{key}",
                    fix_action="set_env_value"
                ))
        
        return issues
    
    def _validate_api_keys(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate API keys and detect placeholders."""
        issues = []
        env = config.get('env', {})
        
        for key, value in env.items():
            # Check if it's an API key field
            if any(pattern in key.upper() for pattern in ['API_KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'AUTH']):
                if is_api_key_placeholder(value):
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="api_key",
                        message=f"API key placeholder detected: {key}",
                        field=f"env.{key}",
                        fix_action="set_api_key",
                        suggested_value="<Set your API key here>"
                    ))
                elif isinstance(value, str) and len(value) < 8:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="api_key",
                        message=f"API key '{key}' seems too short",
                        field=f"env.{key}",
                        fix_action="verify_api_key"
                    ))
                
                # Check for known API key formats
                if key.upper() == 'OPENAI_API_KEY' and isinstance(value, str):
                    if not (value.startswith('sk-') or is_api_key_placeholder(value)):
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="api_key",
                            message="OpenAI API key should start with 'sk-'",
                            field=f"env.{key}",
                            fix_action="verify_openai_key"
                        ))
                
                elif key.upper() == 'ANTHROPIC_API_KEY' and isinstance(value, str):
                    if not (value.startswith('sk-ant-') or is_api_key_placeholder(value)):
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="api_key",
                            message="Anthropic API key should start with 'sk-ant-'",
                            field=f"env.{key}",
                            fix_action="verify_anthropic_key"
                        ))
        
        return issues
    
    def _validate_urls(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate URLs for HTTP/SSE servers."""
        issues = []
        url = config.get('url')
        
        if not url:
            return issues
        
        if not isinstance(url, str):
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message="URL must be a string",
                field="url",
                fix_action="fix_url_format",
                auto_fixable=True
            ))
            return issues
        
        # URL format validation
        if not url.startswith(('http://', 'https://')):
            issues.append(ValidationIssue(
                severity="error",
                category="format",
                message="URL must start with http:// or https://",
                field="url",
                suggested_value=f"https://{url}" if not url.startswith('http') else url,
                fix_action="fix_url_protocol",
                auto_fixable=True
            ))
        
        # Security warning for HTTP
        if url.startswith('http://') and not url.startswith('http://localhost'):
            issues.append(ValidationIssue(
                severity="warning",
                category="security",
                message="Using HTTP instead of HTTPS may be insecure",
                field="url",
                suggested_value=url.replace('http://', 'https://'),
                fix_action="upgrade_to_https"
            ))
        
        return issues
    
    def _validate_paths(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate file paths and directories."""
        issues = []
        
        # Check command path for STDIO servers
        command = config.get('command')
        if command and '/' in command or '\\' in command:
            # It's a path, not just a command name
            path = Path(command)
            if not path.exists():
                issues.append(ValidationIssue(
                    severity="error",
                    category="path",
                    message=f"Command path does not exist: {command}",
                    field="command",
                    fix_action="browse_for_command"
                ))
            elif not path.is_file():
                issues.append(ValidationIssue(
                    severity="error",
                    category="path",
                    message=f"Command path is not a file: {command}",
                    field="command",
                    fix_action="browse_for_command"
                ))
            elif not os.access(path, os.X_OK):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="path",
                    message=f"Command file is not executable: {command}",
                    field="command",
                    fix_action="fix_permissions"
                ))
        
        return issues
    
    def _validate_json_syntax(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate JSON syntax in configuration values."""
        issues = []
        
        def check_json_value(key: str, value: Any, path: str = ""):
            if isinstance(value, str):
                # Check if it looks like JSON but isn't parsed
                if value.strip().startswith(('{', '[')) and value.strip().endswith(('}', ']')):
                    try:
                        json.loads(value)
                        issues.append(ValidationIssue(
                            severity="info",
                            category="format",
                            message=f"Value appears to be JSON string, consider parsing: {path or key}",
                            field=path or key,
                            fix_action="parse_json_value"
                        ))
                    except json.JSONDecodeError as e:
                        issues.append(ValidationIssue(
                            severity="error",
                            category="format",
                            message=f"Invalid JSON syntax in {path or key}: {e}",
                            field=path or key,
                            fix_action="fix_json_syntax"
                        ))
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    check_json_value(sub_key, sub_value, f"{path}.{sub_key}" if path else sub_key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_json_value(f"[{i}]", item, f"{path}[{i}]" if path else f"{key}[{i}]")
        
        for key, value in config.items():
            check_json_value(key, value)
        
        return issues
    
    def _detect_common_typos(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Detect and suggest fixes for common typos."""
        issues = []
        
        # Common field name typos
        typo_fixes = {
            'cmd': 'command',
            'arguments': 'args',
            'environment': 'env',
            'envs': 'env',
            'environmental': 'env',
            'variables': 'env'
        }
        
        for typo, correct in typo_fixes.items():
            if typo in config and correct not in config:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="common_typo",
                    message=f"Did you mean '{correct}' instead of '{typo}'?",
                    field=typo,
                    suggested_value=correct,
                    fix_action="fix_field_name",
                    auto_fixable=True
                ))
        
        # Common command typos
        command = config.get('command', '')
        command_fixes = {
            'nodejs': 'node',
            'py': 'python',
            'pip': 'python',
            'npm': 'npx'
        }
        
        if command in command_fixes:
            issues.append(ValidationIssue(
                severity="info",
                category="suggestion",
                message=f"Consider using '{command_fixes[command]}' instead of '{command}'",
                field="command",
                suggested_value=command_fixes[command],
                fix_action="fix_command_name"
            ))
        
        return issues
    
    def _suggest_improvements(self, server_name: str, config: Dict[str, Any]) -> List[ValidationIssue]:
        """Suggest configuration improvements."""
        issues = []
        
        # Suggest adding description for servers without metadata
        if 'metadata' not in config and 'description' not in config:
            issues.append(ValidationIssue(
                severity="info",
                category="suggestion",
                message="Consider adding a description to help identify this server",
                field="metadata.description",
                fix_action="add_description"
            ))
        
        # Suggest tags for better organization
        metadata = config.get('metadata', {})
        if not metadata.get('tags'):
            issues.append(ValidationIssue(
                severity="info",
                category="suggestion", 
                message="Consider adding tags for better server organization",
                field="metadata.tags",
                fix_action="add_tags"
            ))
        
        # Suggest environment variable organization
        env = config.get('env', {})
        if len(env) > 5:
            issues.append(ValidationIssue(
                severity="info",
                category="suggestion",
                message="Consider using a .env file for better environment variable management",
                field="env",
                fix_action="suggest_env_file"
            ))
        
        return issues
    
    def _load_validation_templates(self) -> List[ValidationTemplate]:
        """Load common server configuration templates."""
        return [
            ValidationTemplate(
                name="OpenAI MCP Server",
                description="Standard OpenAI MCP server configuration",
                server_type="stdio",
                config_template={
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@openai/mcp-server-openai"],
                    "env": {"OPENAI_API_KEY": "YOUR_OPENAI_API_KEY"}
                },
                required_env_vars=["OPENAI_API_KEY"]
            ),
            ValidationTemplate(
                name="Anthropic MCP Server",
                description="Standard Anthropic MCP server configuration",
                server_type="stdio",
                config_template={
                    "type": "stdio", 
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server"],
                    "env": {"ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY"}
                },
                required_env_vars=["ANTHROPIC_API_KEY"]
            )
        ]
    
    def _load_api_key_patterns(self) -> Dict[str, str]:
        """Load API key format patterns."""
        return {
            "OPENAI_API_KEY": r"sk-[A-Za-z0-9]{48,}",
            "ANTHROPIC_API_KEY": r"sk-ant-api03-[A-Za-z0-9\-_]{95}",
            "GITHUB_TOKEN": r"gh[pousr]_[A-Za-z0-9]{36}",
            "GOOGLE_API_KEY": r"AIza[A-Za-z0-9\-_]{35}"
        }
    
    def _load_common_commands(self) -> List[str]:
        """Load list of common MCP server commands."""
        return [
            "npx", "uvx", "python", "node", "docker",
            "mcp-server-git", "mcp-server-filesystem",
            "mcp-server-brave-search", "mcp-server-sqlite"
        ]
    
    def get_template_suggestions(self, server_config: Dict[str, Any]) -> List[ValidationTemplate]:
        """Get template suggestions based on current configuration."""
        suggestions = []
        
        # Simple matching based on command and args
        command = server_config.get('command', '')
        args = server_config.get('args', [])
        env = server_config.get('env', {})
        
        # OpenAI server detection
        if 'openai' in str(args).lower() or 'OPENAI_API_KEY' in env:
            for template in self._templates:
                if template.name == "OpenAI MCP Server":
                    suggestions.append(template)
        
        # Anthropic server detection
        if 'anthropic' in str(args).lower() or 'ANTHROPIC_API_KEY' in env:
            for template in self._templates:
                if template.name == "Anthropic MCP Server":
                    suggestions.append(template)
        
        return suggestions
    
    def clear_cache_for_server(self, server_name: str):
        """Clear cached validation results for a specific server."""
        self.cache.remove(server_name)
    
    def clear_all_cache(self):
        """Clear all cached validation results."""
        self.cache.clear()