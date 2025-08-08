"""Intelligent auto-repair system for MCP server configurations."""

import os
import json
import shutil
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import structlog

from .config_validator import ValidationIssue, ValidationResult, ValidationTemplate

logger = structlog.get_logger()


@dataclass
class RepairAction:
    """Represents a single repair action that can be taken."""
    action_id: str
    title: str
    description: str
    confidence: float  # 0.0 to 1.0
    auto_applicable: bool = False
    destructive: bool = False  # Requires user confirmation
    
    # The actual repair function
    repair_func: Optional[Callable] = None
    repair_args: Dict[str, Any] = field(default_factory=dict)
    
    # Preview of changes
    preview: Optional[str] = None
    before_value: Optional[Any] = None
    after_value: Optional[Any] = None


@dataclass  
class RepairSuggestion:
    """A complete repair suggestion for one or more issues."""
    suggestion_id: str
    title: str
    description: str
    issues_addressed: List[ValidationIssue]
    actions: List[RepairAction]
    estimated_time: str  # Human-readable time estimate
    success_rate: float  # Historical success rate
    
    def get_total_confidence(self) -> float:
        """Calculate average confidence across all actions."""
        if not self.actions:
            return 0.0
        return sum(action.confidence for action in self.actions) / len(self.actions)


class RepairStrategy(ABC):
    """Base class for repair strategies."""
    
    @abstractmethod
    def can_handle(self, issue: ValidationIssue) -> bool:
        """Check if this strategy can handle the given issue."""
        pass
    
    @abstractmethod
    def create_repair_action(
        self, 
        issue: ValidationIssue, 
        server_name: str, 
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create a repair action for the given issue."""
        pass


class RequiredFieldRepairStrategy(RepairStrategy):
    """Strategy for fixing missing required fields."""
    
    def can_handle(self, issue: ValidationIssue) -> bool:
        return issue.category == "required_field"
    
    def create_repair_action(
        self, 
        issue: ValidationIssue, 
        server_name: str, 
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create action to add missing required field."""
        field = issue.field
        
        if field == "command":
            return RepairAction(
                action_id="add_command",
                title="Add command field",
                description="Add a command to execute for this server",
                confidence=0.3,  # Requires user input
                auto_applicable=False,
                repair_func=self._add_command_field,
                repair_args={"field": field},
                preview="Will prompt for command to add"
            )
        
        elif field == "url":
            return RepairAction(
                action_id="add_url",
                title="Add URL field", 
                description="Add a URL for this HTTP/SSE server",
                confidence=0.3,  # Requires user input
                auto_applicable=False,
                repair_func=self._add_url_field,
                repair_args={"field": field},
                preview="Will prompt for URL to add"
            )
        
        elif field == "type":
            suggested_type = issue.suggested_value or "stdio"
            return RepairAction(
                action_id="set_server_type",
                title=f"Set server type to '{suggested_type}'",
                description=f"Set the server type to {suggested_type}",
                confidence=0.8,
                auto_applicable=True,
                repair_func=self._set_field_value,
                repair_args={"field": field, "value": suggested_type},
                before_value=server_config.get(field),
                after_value=suggested_type,
                preview=f"type: '{suggested_type}'"
            )
        
        return None
    
    def _add_command_field(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Add command field with placeholder."""
        config["command"] = "npx"  # Common default
        config.setdefault("args", ["-y", "mcp-server-example"])
        return config
    
    def _add_url_field(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Add URL field with placeholder."""
        config["url"] = "https://example.com/mcp"
        return config
    
    def _set_field_value(self, config: Dict[str, Any], field: str, value: Any, **kwargs) -> Dict[str, Any]:
        """Set a field to a specific value."""
        config[field] = value
        return config


class ApiKeyRepairStrategy(RepairStrategy):
    """Strategy for fixing API key issues."""
    
    def can_handle(self, issue: ValidationIssue) -> bool:
        return issue.category == "api_key"
    
    def create_repair_action(
        self,
        issue: ValidationIssue,
        server_name: str, 
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create action to fix API key issue."""
        field = issue.field
        
        if not field or not field.startswith("env."):
            return None
        
        env_key = field[4:]  # Remove "env." prefix
        current_value = server_config.get("env", {}).get(env_key, "")
        
        if "placeholder" in issue.message.lower():
            return RepairAction(
                action_id="set_api_key",
                title=f"Set {env_key}",
                description=f"Set the actual API key for {env_key}",
                confidence=0.2,  # Requires user input
                auto_applicable=False,
                repair_func=self._set_api_key,
                repair_args={"env_key": env_key},
                before_value=current_value,
                preview=f"Will prompt for {env_key} value"
            )
        
        elif "format" in issue.message.lower():
            # Try to suggest correct format
            suggested_format = self._get_api_key_format(env_key)
            if suggested_format:
                return RepairAction(
                    action_id="fix_api_key_format",
                    title=f"Fix {env_key} format",
                    description=f"Ensure {env_key} follows the correct format",
                    confidence=0.6,
                    auto_applicable=False,
                    repair_func=self._fix_api_key_format,
                    repair_args={"env_key": env_key, "expected_format": suggested_format},
                    preview=f"Expected format: {suggested_format}"
                )
        
        return None
    
    def _set_api_key(self, config: Dict[str, Any], env_key: str, **kwargs) -> Dict[str, Any]:
        """Set API key value (placeholder for user input)."""
        config.setdefault("env", {})[env_key] = f"<SET_{env_key}_HERE>"
        return config
    
    def _fix_api_key_format(
        self, 
        config: Dict[str, Any], 
        env_key: str, 
        expected_format: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Fix API key format."""
        config.setdefault("env", {})[env_key] = f"<{expected_format}>"
        return config
    
    def _get_api_key_format(self, env_key: str) -> Optional[str]:
        """Get expected format for known API keys."""
        formats = {
            "OPENAI_API_KEY": "sk-proj-...",
            "ANTHROPIC_API_KEY": "sk-ant-api03-...", 
            "GITHUB_TOKEN": "ghp_...",
            "GOOGLE_API_KEY": "AIza..."
        }
        return formats.get(env_key.upper())


class FormatRepairStrategy(RepairStrategy):
    """Strategy for fixing format issues."""
    
    def can_handle(self, issue: ValidationIssue) -> bool:
        return issue.category == "format"
    
    def create_repair_action(
        self,
        issue: ValidationIssue,
        server_name: str,
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create action to fix format issue."""
        field = issue.field
        
        if field == "args" and "list" in issue.message.lower():
            current_value = server_config.get("args")
            if isinstance(current_value, str):
                # Convert string to list
                args_list = [arg.strip() for arg in current_value.split()]
                return RepairAction(
                    action_id="fix_args_format",
                    title="Convert args to list format",
                    description="Convert args from string to list format",
                    confidence=0.9,
                    auto_applicable=True,
                    repair_func=self._convert_args_to_list,
                    repair_args={"current_value": current_value},
                    before_value=current_value,
                    after_value=args_list,
                    preview=f"args: {args_list}"
                )
        
        elif field == "url" and "protocol" in issue.message.lower():
            current_url = server_config.get("url", "")
            if not current_url.startswith(('http://', 'https://')):
                fixed_url = f"https://{current_url}"
                return RepairAction(
                    action_id="fix_url_protocol",
                    title="Add HTTPS protocol to URL",
                    description="Add https:// prefix to the URL",
                    confidence=0.8,
                    auto_applicable=True,
                    repair_func=self._fix_url_protocol,
                    repair_args={"current_url": current_url},
                    before_value=current_url,
                    after_value=fixed_url,
                    preview=f"url: '{fixed_url}'"
                )
        
        elif field == "env" and "dictionary" in issue.message.lower():
            return RepairAction(
                action_id="fix_env_format",
                title="Convert env to dictionary format",
                description="Convert environment variables to dictionary format",
                confidence=0.7,
                auto_applicable=True,
                repair_func=self._convert_env_to_dict,
                repair_args={},
                preview="Convert env to proper dictionary format"
            )
        
        return None
    
    def _convert_args_to_list(self, config: Dict[str, Any], current_value: str, **kwargs) -> Dict[str, Any]:
        """Convert args string to list."""
        config["args"] = [arg.strip() for arg in current_value.split()]
        return config
    
    def _fix_url_protocol(self, config: Dict[str, Any], current_url: str, **kwargs) -> Dict[str, Any]:
        """Add https protocol to URL."""
        config["url"] = f"https://{current_url}"
        return config
    
    def _convert_env_to_dict(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Convert env to dictionary format."""
        if not isinstance(config.get("env"), dict):
            config["env"] = {}
        return config


class TypoRepairStrategy(RepairStrategy):
    """Strategy for fixing common typos."""
    
    def can_handle(self, issue: ValidationIssue) -> bool:
        return issue.category == "common_typo"
    
    def create_repair_action(
        self,
        issue: ValidationIssue,
        server_name: str,
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create action to fix typo."""
        field = issue.field
        suggested_value = issue.suggested_value
        
        if not field or not suggested_value:
            return None
        
        current_value = server_config.get(field)
        
        return RepairAction(
            action_id="fix_field_name",
            title=f"Rename '{field}' to '{suggested_value}'",
            description=f"Fix typo: rename '{field}' to '{suggested_value}'",
            confidence=0.9,
            auto_applicable=True,
            repair_func=self._rename_field,
            repair_args={"old_field": field, "new_field": suggested_value},
            before_value=f"{field}: {current_value}",
            after_value=f"{suggested_value}: {current_value}",
            preview=f"Rename field: {field} → {suggested_value}"
        )
    
    def _rename_field(
        self, 
        config: Dict[str, Any], 
        old_field: str, 
        new_field: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Rename a field in the configuration."""
        if old_field in config:
            value = config.pop(old_field)
            config[new_field] = value
        return config


class PathRepairStrategy(RepairStrategy):
    """Strategy for fixing path issues."""
    
    def can_handle(self, issue: ValidationIssue) -> bool:
        return issue.category == "path"
    
    def create_repair_action(
        self,
        issue: ValidationIssue,
        server_name: str,
        server_config: Dict[str, Any]
    ) -> Optional[RepairAction]:
        """Create action to fix path issue."""
        field = issue.field
        
        if field == "command" and "not found" in issue.message.lower():
            current_command = server_config.get("command", "")
            
            # Try to find the command in common locations
            suggested_path = self._find_command_path(current_command)
            if suggested_path:
                return RepairAction(
                    action_id="fix_command_path",
                    title=f"Use full path for {current_command}",
                    description=f"Use the full path to the {current_command} executable",
                    confidence=0.7,
                    auto_applicable=True,
                    repair_func=self._set_command_path,
                    repair_args={"command_path": suggested_path},
                    before_value=current_command,
                    after_value=suggested_path,
                    preview=f"command: '{suggested_path}'"
                )
            else:
                return RepairAction(
                    action_id="browse_for_command",
                    title=f"Locate {current_command}",
                    description=f"Browse for the {current_command} executable",
                    confidence=0.3,
                    auto_applicable=False,
                    repair_func=self._browse_for_command,
                    repair_args={"command_name": current_command},
                    preview=f"Will open file browser to find {current_command}"
                )
        
        elif "permissions" in issue.message.lower():
            file_path = server_config.get(field, "")
            return RepairAction(
                action_id="fix_permissions",
                title="Fix file permissions",
                description="Make the file executable",
                confidence=0.8,
                auto_applicable=True,
                destructive=True,  # Modifies file system
                repair_func=self._fix_file_permissions,
                repair_args={"file_path": file_path},
                preview=f"chmod +x {file_path}"
            )
        
        return None
    
    def _find_command_path(self, command: str) -> Optional[str]:
        """Try to find the full path to a command."""
        # Check if it's already in PATH
        full_path = shutil.which(command)
        if full_path:
            return full_path
        
        # Check common locations
        common_paths = [
            f"/usr/local/bin/{command}",
            f"/usr/bin/{command}", 
            f"/opt/homebrew/bin/{command}",
            f"C:\\Program Files\\{command}.exe",
            f"C:\\Program Files (x86)\\{command}.exe"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def _set_command_path(self, config: Dict[str, Any], command_path: str, **kwargs) -> Dict[str, Any]:
        """Set the command to use full path."""
        config["command"] = command_path
        return config
    
    def _browse_for_command(self, config: Dict[str, Any], command_name: str, **kwargs) -> Dict[str, Any]:
        """Placeholder for browsing for command (requires UI integration)."""
        # This would need to integrate with the TUI to show a file browser
        config["command"] = f"<BROWSE_FOR_{command_name.upper()}>"
        return config
    
    def _fix_file_permissions(self, config: Dict[str, Any], file_path: str, **kwargs) -> Dict[str, Any]:
        """Fix file permissions to make executable."""
        try:
            path = Path(file_path)
            if path.exists():
                # Make file executable
                current_mode = path.stat().st_mode
                path.chmod(current_mode | 0o111)
                logger.info("Fixed file permissions", path=file_path)
        except Exception as e:
            logger.error("Failed to fix permissions", path=file_path, error=str(e))
        
        return config  # Config doesn't change


class AutoRepair:
    """Main auto-repair system that coordinates all repair strategies."""
    
    def __init__(self):
        self.strategies: List[RepairStrategy] = [
            RequiredFieldRepairStrategy(),
            ApiKeyRepairStrategy(),
            FormatRepairStrategy(),
            TypoRepairStrategy(),
            PathRepairStrategy(),
        ]
        
        # Track repair history for learning
        self.repair_history: List[Dict[str, Any]] = []
    
    def analyze_issues(
        self, 
        validation_result: ValidationResult,
        server_config: Dict[str, Any]
    ) -> List[RepairSuggestion]:
        """Analyze validation issues and create repair suggestions."""
        suggestions = []
        
        # Group issues by category and severity
        issue_groups = self._group_issues(validation_result.issues)
        
        # Create repair suggestions for each group
        for group_key, issues in issue_groups.items():
            suggestion = self._create_repair_suggestion(
                group_key, issues, validation_result.server_name, server_config
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Sort by confidence and impact
        suggestions.sort(key=lambda s: (s.get_total_confidence(), len(s.issues_addressed)), reverse=True)
        
        return suggestions
    
    def apply_repair_action(
        self,
        action: RepairAction,
        server_config: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Apply a single repair action to the configuration."""
        if not action.repair_func:
            return False, server_config, "No repair function available"
        
        try:
            # Create a copy of the config to avoid modifying original
            new_config = json.loads(json.dumps(server_config, default=str))
            
            # Apply the repair
            repaired_config = action.repair_func(new_config, **action.repair_args)
            
            # Log the repair
            self._log_repair_action(action, server_config, repaired_config)
            
            return True, repaired_config, None
        
        except Exception as e:
            error_msg = f"Failed to apply repair action '{action.action_id}': {e}"
            logger.error("Repair action failed", action=action.action_id, error=str(e))
            return False, server_config, error_msg
    
    def apply_repair_suggestion(
        self,
        suggestion: RepairSuggestion,
        server_config: Dict[str, Any],
        skip_confirmations: bool = False
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Apply all actions in a repair suggestion."""
        current_config = server_config.copy()
        errors = []
        applied_actions = []
        
        for action in suggestion.actions:
            # Skip destructive actions unless confirmed
            if action.destructive and not skip_confirmations:
                errors.append(f"Skipped destructive action: {action.title}")
                continue
            
            # Skip non-auto actions unless specifically requested
            if not action.auto_applicable and not skip_confirmations:
                errors.append(f"Skipped manual action: {action.title}")
                continue
            
            success, new_config, error = self.apply_repair_action(action, current_config)
            
            if success:
                current_config = new_config
                applied_actions.append(action)
            else:
                errors.append(error or f"Failed to apply {action.title}")
        
        success = len(applied_actions) > 0 and len(errors) == 0
        
        # Log the full suggestion result
        self._log_repair_suggestion(suggestion, success, applied_actions, errors)
        
        return success, current_config, errors
    
    def get_repair_templates(self, issue_categories: Set[str]) -> List[ValidationTemplate]:
        """Get repair templates for common configuration patterns."""
        templates = []
        
        # Add templates based on issue categories
        if "api_key" in issue_categories:
            templates.extend([
                ValidationTemplate(
                    name="OpenAI Server Template",
                    description="Complete OpenAI MCP server configuration",
                    server_type="stdio",
                    config_template={
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@openai/mcp-server-openai"],
                        "env": {"OPENAI_API_KEY": "sk-proj-YOUR_KEY_HERE"}
                    }
                ),
                ValidationTemplate(
                    name="Anthropic Server Template",
                    description="Complete Anthropic MCP server configuration",
                    server_type="stdio",
                    config_template={
                        "type": "stdio",
                        "command": "npx", 
                        "args": ["-y", "@anthropic/mcp-server"],
                        "env": {"ANTHROPIC_API_KEY": "sk-ant-api03-YOUR_KEY_HERE"}
                    }
                )
            ])
        
        return templates
    
    def _group_issues(self, issues: List[ValidationIssue]) -> Dict[str, List[ValidationIssue]]:
        """Group issues by category and severity for better repair suggestions."""
        groups = {}
        
        for issue in issues:
            # Group by category first, then severity
            group_key = f"{issue.category}_{issue.severity}"
            groups.setdefault(group_key, []).append(issue)
        
        return groups
    
    def _create_repair_suggestion(
        self,
        group_key: str,
        issues: List[ValidationIssue],
        server_name: str,
        server_config: Dict[str, Any]
    ) -> Optional[RepairSuggestion]:
        """Create a repair suggestion for a group of issues."""
        actions = []
        
        # Find repair actions for each issue
        for issue in issues:
            for strategy in self.strategies:
                if strategy.can_handle(issue):
                    action = strategy.create_repair_action(issue, server_name, server_config)
                    if action:
                        actions.append(action)
                        break  # Use first matching strategy
        
        if not actions:
            return None
        
        # Determine success rate based on historical data
        success_rate = self._calculate_success_rate(group_key)
        
        # Estimate time based on action types
        estimated_time = self._estimate_repair_time(actions)
        
        category, severity = group_key.split('_', 1)
        
        return RepairSuggestion(
            suggestion_id=f"{server_name}_{group_key}_{len(issues)}",
            title=f"Fix {len(issues)} {severity} {category} issue(s)",
            description=f"Address {category} issues in {server_name}",
            issues_addressed=issues,
            actions=actions,
            estimated_time=estimated_time,
            success_rate=success_rate
        )
    
    def _calculate_success_rate(self, group_key: str) -> float:
        """Calculate historical success rate for this type of repair."""
        # In a real implementation, this would analyze repair_history
        # For now, use heuristics based on issue type
        category = group_key.split('_')[0]
        
        success_rates = {
            "format": 0.9,
            "common_typo": 0.95,
            "required_field": 0.6,
            "api_key": 0.4,  # Often requires user input
            "path": 0.7,
            "suggestion": 0.8
        }
        
        return success_rates.get(category, 0.5)
    
    def _estimate_repair_time(self, actions: List[RepairAction]) -> str:
        """Estimate time required to complete all repair actions."""
        total_seconds = 0
        
        for action in actions:
            if action.auto_applicable:
                total_seconds += 5  # 5 seconds for auto repairs
            else:
                total_seconds += 60  # 1 minute for manual repairs
        
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        else:
            minutes = total_seconds // 60
            return f"{minutes} minute(s)"
    
    def _log_repair_action(
        self,
        action: RepairAction,
        before_config: Dict[str, Any],
        after_config: Dict[str, Any]
    ):
        """Log a repair action for learning purposes."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action.action_id,
            "action_title": action.title,
            "confidence": action.confidence,
            "auto_applicable": action.auto_applicable,
            "before_config": before_config,
            "after_config": after_config
        }
        
        self.repair_history.append(log_entry)
        logger.info("Applied repair action", action=action.action_id, title=action.title)
    
    def _log_repair_suggestion(
        self,
        suggestion: RepairSuggestion,
        success: bool,
        applied_actions: List[RepairAction],
        errors: List[str]
    ):
        """Log the result of applying a repair suggestion."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "suggestion_id": suggestion.suggestion_id,
            "success": success,
            "applied_actions": len(applied_actions),
            "total_actions": len(suggestion.actions),
            "errors": errors
        }
        
        self.repair_history.append(log_entry)
        logger.info(
            "Applied repair suggestion",
            suggestion=suggestion.suggestion_id,
            success=success,
            applied=len(applied_actions),
            total=len(suggestion.actions)
        )