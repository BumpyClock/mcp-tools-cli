"""User Preferences Management System for MCP Manager."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeploymentPattern:
    """Represents a deployment pattern learned from user behavior."""
    server_name: str
    platforms: List[str]
    frequency: int
    last_used: str
    success_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentPattern':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class PlatformPreference:
    """User's preference for a specific platform."""
    name: str
    priority: int  # 1=highest, higher numbers = lower priority
    enabled: bool = True
    config_path: Optional[str] = None
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformPreference':
        """Create from dictionary."""
        return cls(**data)


class UserPreferences:
    """Manages user preferences and smart deployment patterns."""
    
    DEFAULT_PLATFORMS = [
        PlatformPreference("claude-desktop", 1),
        PlatformPreference("claude-code", 2),
        PlatformPreference("vscode", 3),
        PlatformPreference("cursor", 4),
        PlatformPreference("other", 5),
    ]
    
    def __init__(self):
        """Initialize user preferences system."""
        self.config_dir = Path.home() / ".mcp-manager"
        self.config_file = self.config_dir / "preferences.json"
        self.preferences = self._load_preferences()
        self._ensure_defaults()
    
    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create config directory: {e}")
            raise
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from JSON file."""
        if not self.config_file.exists():
            return self._create_default_preferences()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Migrate old format if needed
                return self._migrate_preferences(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load preferences, using defaults: {e}")
            return self._create_default_preferences()
        except Exception as e:
            logger.error(f"Unexpected error loading preferences: {e}")
            return self._create_default_preferences()
    
    def _create_default_preferences(self) -> Dict[str, Any]:
        """Create default preferences structure."""
        return {
            "version": "1.0",
            "setup_completed": False,
            "first_launch": True,
            "platforms": {p.name: p.to_dict() for p in self.DEFAULT_PLATFORMS},
            "deployment_patterns": {},
            "deployment_history": [],
            "quick_deploy_enabled": True,
            "auto_suggest": True,
            "learning_enabled": True,
            "batch_deploy_size": 5,
            "remember_selections": True,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
    
    def _migrate_preferences(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate preferences from older versions."""
        # Handle version migrations here
        current_version = data.get("version", "0.1")
        
        if current_version == "0.1":
            # Migrate from old format
            data["version"] = "1.0"
            data["last_updated"] = datetime.now().isoformat()
        
        return data
    
    def _ensure_defaults(self) -> None:
        """Ensure all required preference keys exist."""
        defaults = self._create_default_preferences()
        updated = False
        
        for key, value in defaults.items():
            if key not in self.preferences:
                self.preferences[key] = value
                updated = True
        
        if updated:
            self.save_preferences()
    
    def save_preferences(self) -> None:
        """Save preferences to JSON file."""
        self._ensure_config_dir()
        self.preferences["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            raise
    
    def is_first_launch(self) -> bool:
        """Check if this is the first launch."""
        return self.preferences.get("first_launch", True)
    
    def is_setup_completed(self) -> bool:
        """Check if initial setup is completed."""
        return self.preferences.get("setup_completed", False)
    
    def mark_setup_completed(self) -> None:
        """Mark initial setup as completed."""
        self.preferences["setup_completed"] = True
        self.preferences["first_launch"] = False
        self.save_preferences()
    
    def get_platform_preferences(self) -> List[PlatformPreference]:
        """Get all platform preferences, sorted by priority."""
        platforms = []
        
        for name, data in self.preferences.get("platforms", {}).items():
            try:
                platforms.append(PlatformPreference.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load platform preference {name}: {e}")
        
        return sorted(platforms, key=lambda p: p.priority)
    
    def get_enabled_platforms(self) -> List[PlatformPreference]:
        """Get only enabled platforms, sorted by priority."""
        return [p for p in self.get_platform_preferences() if p.enabled]
    
    def update_platform_preferences(self, platforms: List[PlatformPreference]) -> None:
        """Update platform preferences."""
        self.preferences["platforms"] = {p.name: p.to_dict() for p in platforms}
        self.save_preferences()
    
    def record_deployment(self, server_name: str, platforms: List[str], success: bool = True) -> None:
        """Record a deployment for learning purposes."""
        if not self.preferences.get("learning_enabled", True):
            return
        
        deployment_record = {
            "server_name": server_name,
            "platforms": platforms,
            "timestamp": datetime.now().isoformat(),
            "success": success,
        }
        
        # Add to history
        history = self.preferences.get("deployment_history", [])
        history.append(deployment_record)
        
        # Keep only last 100 deployments
        if len(history) > 100:
            history = history[-100:]
        
        self.preferences["deployment_history"] = history
        
        # Update deployment patterns
        self._update_deployment_pattern(server_name, platforms, success)
        self.save_preferences()
    
    def _update_deployment_pattern(self, server_name: str, platforms: List[str], success: bool) -> None:
        """Update deployment patterns based on usage."""
        patterns = self.preferences.get("deployment_patterns", {})
        
        pattern_key = f"{server_name}::{','.join(sorted(platforms))}"
        
        if pattern_key in patterns:
            pattern_data = patterns[pattern_key]
            pattern = DeploymentPattern.from_dict(pattern_data)
            pattern.frequency += 1
            pattern.last_used = datetime.now().isoformat()
            if success:
                # Update success rate with exponential moving average
                pattern.success_rate = 0.9 * pattern.success_rate + 0.1 * 1.0
            else:
                pattern.success_rate = 0.9 * pattern.success_rate + 0.1 * 0.0
        else:
            pattern = DeploymentPattern(
                server_name=server_name,
                platforms=platforms,
                frequency=1,
                last_used=datetime.now().isoformat(),
                success_rate=1.0 if success else 0.5
            )
        
        patterns[pattern_key] = pattern.to_dict()
        self.preferences["deployment_patterns"] = patterns
    
    def get_deployment_suggestions(self, server_name: str, limit: int = 3) -> List[DeploymentPattern]:
        """Get deployment suggestions for a server based on history."""
        if not self.preferences.get("auto_suggest", True):
            return []
        
        patterns = []
        for pattern_data in self.preferences.get("deployment_patterns", {}).values():
            try:
                pattern = DeploymentPattern.from_dict(pattern_data)
                if pattern.server_name == server_name and pattern.success_rate > 0.5:
                    patterns.append(pattern)
            except Exception as e:
                logger.warning(f"Failed to load deployment pattern: {e}")
        
        # Sort by frequency and recency
        def score_pattern(pattern: DeploymentPattern) -> float:
            recency_days = (datetime.now() - datetime.fromisoformat(pattern.last_used)).days
            recency_factor = max(0.1, 1.0 - (recency_days / 30))  # Decay over 30 days
            return pattern.frequency * pattern.success_rate * recency_factor
        
        patterns.sort(key=score_pattern, reverse=True)
        return patterns[:limit]
    
    def get_favorite_platforms_for_server(self, server_name: str) -> List[str]:
        """Get the most commonly used platforms for a server."""
        suggestions = self.get_deployment_suggestions(server_name)
        if not suggestions:
            # Return default enabled platforms
            return [p.name for p in self.get_enabled_platforms()[:2]]
        
        # Return platforms from the most frequent pattern
        return suggestions[0].platforms
    
    def get_quick_deploy_targets(self, server_name: str) -> Optional[List[str]]:
        """Get quick deploy targets for a server."""
        if not self.preferences.get("quick_deploy_enabled", True):
            return None
        
        suggestions = self.get_deployment_suggestions(server_name, limit=1)
        if suggestions and suggestions[0].frequency >= 3:  # Must be used at least 3 times
            return suggestions[0].platforms
        
        return None
    
    def enable_learning(self, enabled: bool) -> None:
        """Enable or disable learning from user behavior."""
        self.preferences["learning_enabled"] = enabled
        self.save_preferences()
    
    def clear_deployment_history(self) -> None:
        """Clear deployment history and patterns."""
        self.preferences["deployment_history"] = []
        self.preferences["deployment_patterns"] = {}
        self.save_preferences()
    
    def export_preferences(self) -> Dict[str, Any]:
        """Export preferences for backup or sharing."""
        return self.preferences.copy()
    
    def import_preferences(self, data: Dict[str, Any]) -> None:
        """Import preferences from backup."""
        try:
            # Validate the data structure
            migrated = self._migrate_preferences(data)
            self.preferences = migrated
            self._ensure_defaults()
            self.save_preferences()
        except Exception as e:
            logger.error(f"Failed to import preferences: {e}")
            raise ValueError(f"Invalid preferences data: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        history = self.preferences.get("deployment_history", [])
        patterns = self.preferences.get("deployment_patterns", {})
        
        if not history:
            return {
                "total_deployments": 0,
                "success_rate": 0.0,
                "most_deployed_server": None,
                "favorite_platform": None,
                "patterns_learned": 0,
            }
        
        total = len(history)
        successful = sum(1 for h in history if h.get("success", True))
        success_rate = successful / total if total > 0 else 0.0
        
        # Most deployed server
        server_counts = {}
        platform_counts = {}
        
        for record in history:
            server = record.get("server_name", "unknown")
            server_counts[server] = server_counts.get(server, 0) + 1
            
            for platform in record.get("platforms", []):
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        most_deployed = max(server_counts.items(), key=lambda x: x[1])[0] if server_counts else None
        favorite_platform = max(platform_counts.items(), key=lambda x: x[1])[0] if platform_counts else None
        
        return {
            "total_deployments": total,
            "success_rate": success_rate,
            "most_deployed_server": most_deployed,
            "favorite_platform": favorite_platform,
            "patterns_learned": len(patterns),
        }