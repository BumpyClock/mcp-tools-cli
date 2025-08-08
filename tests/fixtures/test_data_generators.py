# ABOUTME: Test data generators for creating realistic server configurations and scenarios
# ABOUTME: Provides factories for generating test servers, projects, and deployment states

import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid


class ServerConfigFactory:
    """Factory for generating realistic MCP server configurations."""
    
    SERVER_TYPES = [
        "database", "api", "file-manager", "search", "analytics", 
        "documentation", "development", "communication", "monitoring"
    ]
    
    SAMPLE_SERVERS = {
        "database": {
            "command": "node",
            "args": ["database-mcp-server.js"],
            "env": {"DATABASE_URL": "postgresql://localhost:5432/testdb"}
        },
        "api": {
            "command": "python",
            "args": ["-m", "api_mcp_server"],
            "env": {"API_KEY": "test-api-key-placeholder"}
        },
        "file-manager": {
            "command": "node",
            "args": ["file-mcp-server.js"],
            "env": {"ROOT_PATH": "/tmp/test-files"}
        },
        "search": {
            "command": "python",
            "args": ["-m", "search_mcp"],
            "env": {"SEARCH_INDEX": "/tmp/search-index"}
        },
        "analytics": {
            "command": "node",
            "args": ["analytics-server.js"],
            "env": {"ANALYTICS_TOKEN": "test-token"}
        }
    }
    
    @classmethod
    def create_server(cls, name: Optional[str] = None, server_type: Optional[str] = None) -> Dict[str, Any]:
        """Create a single test server configuration."""
        if not name:
            name = f"test-{server_type or random.choice(cls.SERVER_TYPES)}-{uuid.uuid4().hex[:8]}"
        
        if not server_type:
            server_type = random.choice(cls.SERVER_TYPES)
        
        base_config = cls.SAMPLE_SERVERS.get(server_type, cls.SAMPLE_SERVERS["api"])
        
        return {
            "name": name,
            "type": server_type,
            "description": f"Test {server_type} server for integration testing",
            "version": "1.0.0",
            "enabled": random.choice([True, True, True, False]),  # 75% enabled
            "config": base_config.copy(),
            "health_check_interval": 30,
            "retry_attempts": 3,
            "timeout": 10,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
    
    @classmethod
    def create_server_batch(cls, count: int, name_prefix: str = "batch") -> List[Dict[str, Any]]:
        """Create a batch of test servers."""
        servers = []
        for i in range(count):
            server_type = random.choice(cls.SERVER_TYPES)
            name = f"{name_prefix}-{server_type}-{i:03d}"
            servers.append(cls.create_server(name=name, server_type=server_type))
        return servers
    
    @classmethod
    def create_large_dataset(cls, count: int = 100) -> List[Dict[str, Any]]:
        """Create a large dataset for performance testing."""
        return cls.create_server_batch(count, name_prefix="perf-test")
    
    @classmethod
    def create_problematic_servers(cls) -> List[Dict[str, Any]]:
        """Create servers with various configuration problems for error testing."""
        problematic_configs = [
            # Missing command
            {
                "name": "broken-no-command",
                "type": "api",
                "config": {"args": ["server.js"], "env": {}},
                "enabled": True
            },
            # Missing required environment variable
            {
                "name": "broken-missing-env",
                "type": "database", 
                "config": {
                    "command": "node",
                    "args": ["db-server.js"],
                    "env": {}  # Missing DATABASE_URL
                },
                "enabled": True
            },
            # Invalid command path
            {
                "name": "broken-invalid-command",
                "type": "api",
                "config": {
                    "command": "/nonexistent/path/to/python",
                    "args": ["-m", "server"],
                    "env": {"API_KEY": "test-key"}
                },
                "enabled": True
            },
            # Placeholder API key
            {
                "name": "broken-placeholder-key", 
                "type": "api",
                "config": {
                    "command": "python",
                    "args": ["-m", "api_server"],
                    "env": {"API_KEY": "YOUR_API_KEY_HERE"}
                },
                "enabled": True
            },
            # Network timeout issues
            {
                "name": "broken-network-timeout",
                "type": "api",
                "config": {
                    "command": "python", 
                    "args": ["-m", "slow_server"],
                    "env": {"SLOW_RESPONSE": "true"}
                },
                "enabled": True,
                "timeout": 1  # Very short timeout
            }
        ]
        
        return [
            {
                **config,
                "description": "Problematic server for error testing",
                "version": "1.0.0",
                "health_check_interval": 30,
                "retry_attempts": 3,
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            }
            for config in problematic_configs
        ]


class ProjectConfigFactory:
    """Factory for generating test project configurations."""
    
    PROJECT_TYPES = ["vscode", "claude-desktop", "custom"]
    
    @classmethod
    def create_project(cls, name: str, project_type: str = "vscode") -> Dict[str, Any]:
        """Create a test project configuration."""
        return {
            "name": name,
            "type": project_type,
            "path": f"/tmp/test-projects/{name}",
            "config_file": f"/tmp/test-projects/{name}/.vscode/settings.json" if project_type == "vscode" else f"/tmp/test-projects/{name}/mcp-config.json",
            "servers": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    @classmethod
    def create_project_batch(cls, count: int) -> List[Dict[str, Any]]:
        """Create multiple test projects."""
        projects = []
        for i in range(count):
            project_type = random.choice(cls.PROJECT_TYPES)
            name = f"test-project-{i:03d}"
            projects.append(cls.create_project(name, project_type))
        return projects


class DeploymentStateFactory:
    """Factory for generating test deployment states."""
    
    @classmethod
    def create_deployment_state(cls, server_name: str, target_key: str, deployed: bool = True) -> Dict[str, Any]:
        """Create a deployment state record."""
        return {
            "server_name": server_name,
            "target_key": target_key,
            "deployed": deployed,
            "deployment_time": datetime.now().isoformat() if deployed else None,
            "version": "1.0.0" if deployed else None,
            "status": "active" if deployed else "inactive",
            "health_status": random.choice(["healthy", "healthy", "warning", "error"]) if deployed else "unknown"
        }
    
    @classmethod
    def create_deployment_matrix(cls, servers: List[str], targets: List[str], deployment_rate: float = 0.6) -> List[Dict[str, Any]]:
        """Create a deployment matrix with random deployments."""
        deployments = []
        for server_name in servers:
            for target_key in targets:
                deployed = random.random() < deployment_rate
                deployments.append(cls.create_deployment_state(server_name, target_key, deployed))
        return deployments


class TestScenarioFactory:
    """Factory for creating complete test scenarios."""
    
    @classmethod
    def create_empty_environment(cls) -> Dict[str, Any]:
        """Create an empty test environment."""
        return {
            "servers": [],
            "projects": [],
            "deployments": [],
            "description": "Empty environment for fresh start testing"
        }
    
    @classmethod
    def create_small_environment(cls) -> Dict[str, Any]:
        """Create a small test environment (5 servers, 3 projects)."""
        servers = ServerConfigFactory.create_server_batch(5, "small-env")
        projects = ProjectConfigFactory.create_project_batch(3)
        server_names = [s["name"] for s in servers]
        target_keys = [f"{p['name']}-{p['type']}" for p in projects]
        deployments = DeploymentStateFactory.create_deployment_matrix(server_names, target_keys, 0.5)
        
        return {
            "servers": servers,
            "projects": projects,
            "deployments": deployments,
            "description": "Small environment for basic workflow testing"
        }
    
    @classmethod
    def create_medium_environment(cls) -> Dict[str, Any]:
        """Create a medium test environment (20 servers, 8 projects)."""
        servers = ServerConfigFactory.create_server_batch(20, "medium-env")
        projects = ProjectConfigFactory.create_project_batch(8)
        server_names = [s["name"] for s in servers]
        target_keys = [f"{p['name']}-{p['type']}" for p in projects]
        deployments = DeploymentStateFactory.create_deployment_matrix(server_names, target_keys, 0.4)
        
        return {
            "servers": servers,
            "projects": projects,
            "deployments": deployments,
            "description": "Medium environment for comprehensive workflow testing"
        }
    
    @classmethod
    def create_large_environment(cls) -> Dict[str, Any]:
        """Create a large test environment (100+ servers, 15+ projects)."""
        servers = ServerConfigFactory.create_large_dataset(100)
        projects = ProjectConfigFactory.create_project_batch(15)
        server_names = [s["name"] for s in servers]
        target_keys = [f"{p['name']}-{p['type']}" for p in projects]
        deployments = DeploymentStateFactory.create_deployment_matrix(server_names, target_keys, 0.3)
        
        return {
            "servers": servers,
            "projects": projects,
            "deployments": deployments,
            "description": "Large environment for performance and stress testing"
        }
    
    @classmethod
    def create_problematic_environment(cls) -> Dict[str, Any]:
        """Create an environment with various problems for error testing."""
        good_servers = ServerConfigFactory.create_server_batch(3, "good")
        bad_servers = ServerConfigFactory.create_problematic_servers()
        servers = good_servers + bad_servers
        
        projects = ProjectConfigFactory.create_project_batch(4)
        server_names = [s["name"] for s in servers]
        target_keys = [f"{p['name']}-{p['type']}" for p in projects]
        deployments = DeploymentStateFactory.create_deployment_matrix(server_names, target_keys, 0.7)
        
        return {
            "servers": servers,
            "projects": projects,
            "deployments": deployments,
            "description": "Problematic environment for error handling and recovery testing"
        }


def save_test_scenario(scenario: Dict[str, Any], filename: str, base_path: Path = None) -> Path:
    """Save a test scenario to a JSON file."""
    if not base_path:
        base_path = Path(__file__).parent / "data"
    
    base_path.mkdir(exist_ok=True)
    file_path = base_path / f"{filename}.json"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(scenario, f, indent=2, ensure_ascii=False)
    
    return file_path


def load_test_scenario(filename: str, base_path: Path = None) -> Dict[str, Any]:
    """Load a test scenario from a JSON file."""
    if not base_path:
        base_path = Path(__file__).parent / "data"
    
    file_path = base_path / f"{filename}.json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Generate standard test data files when imported
if __name__ == "__main__":
    # Create standard test scenarios
    scenarios = {
        "empty": TestScenarioFactory.create_empty_environment(),
        "small": TestScenarioFactory.create_small_environment(),
        "medium": TestScenarioFactory.create_medium_environment(),
        "large": TestScenarioFactory.create_large_environment(),
        "problematic": TestScenarioFactory.create_problematic_environment()
    }
    
    for name, scenario in scenarios.items():
        save_test_scenario(scenario, name)
        print(f"Created test scenario: {name}")