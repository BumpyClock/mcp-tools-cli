"""Worker utilities for MCP Manager TUI operations."""

from typing import Dict, List, Any, Callable
from datetime import datetime
import time
import structlog

logger = structlog.get_logger()


class OperationProgress:
    """Tracks progress of long-running operations."""
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
        self.status_message = ""
        self.cancelled = False
    
    def update(self, step: int, message: str = ""):
        """Update progress."""
        self.current_step = step
        self.status_message = message
    
    def cancel(self):
        """Mark operation as cancelled."""
        self.cancelled = True
    
    @property
    def percentage(self) -> int:
        """Get progress as percentage."""
        if self.total_steps == 0:
            return 100
        return int((self.current_step / self.total_steps) * 100)


class WorkerOperation:
    """Represents a worker operation with progress tracking."""
    
    def __init__(self, name: str, operation_func: Callable, *args, **kwargs):
        self.name = name
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.progress = None
        self.result = None
        self.error = None
        self.completed = False
    
    def execute(self, progress_callback: Callable[[int, str], None] = None):
        """Execute the operation with progress tracking."""
        try:
            if progress_callback:
                progress_callback(0, f"Starting {self.name}...")
            
            # Execute the operation
            self.result = self.operation_func(
                *self.args, 
                progress_callback=progress_callback,
                **self.kwargs
            )
            
            if progress_callback:
                progress_callback(100, f"{self.name} completed")
                
            self.completed = True
            
        except Exception as e:
            self.error = str(e)
            logger.error(f"{self.name} failed", error=str(e))
            if progress_callback:
                progress_callback(-1, f"{self.name} failed: {str(e)}")


def simulate_deployment(server_names: List[str], target_keys: List[str], 
                       progress_callback: Callable[[int, str], None] = None) -> Dict[str, Any]:
    """Simulate deployment operation for testing worker threads."""
    results = {}
    total_operations = len(server_names) * len(target_keys)
    completed = 0
    
    for server_name in server_names:
        server_results = {}
        
        for target_key in target_keys:
            if progress_callback:
                progress = int((completed / total_operations) * 100)
                progress_callback(progress, f"Deploying {server_name} to {target_key}...")
            
            # Simulate work
            time.sleep(0.5)
            
            # Simulate success/failure (90% success rate)
            import random
            success = random.random() > 0.1
            server_results[target_key] = success
            
            completed += 1
        
        results[server_name] = server_results
    
    return {"results": results, "completed": True}


def simulate_health_check(server_names: List[str],
                         progress_callback: Callable[[int, str], None] = None) -> Dict[str, Any]:
    """Simulate health check operation for testing worker threads."""
    results = {}
    total_servers = len(server_names)
    
    for i, server_name in enumerate(server_names):
        if progress_callback:
            progress = int((i / total_servers) * 100)
            progress_callback(progress, f"Checking {server_name}...")
        
        # Simulate health check work
        time.sleep(0.3)
        
        # Simulate health status (80% healthy)
        import random
        healthy = random.random() > 0.2
        
        results[server_name] = {
            "healthy": healthy,
            "message": "OK" if healthy else "Service unavailable",
            "last_checked": datetime.now().isoformat()
        }
    
    return {"results": results, "completed": True}