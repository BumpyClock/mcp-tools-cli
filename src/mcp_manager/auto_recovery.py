"""Automatic recovery system with exponential backoff for MCP Manager."""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime, timedelta

from .exceptions import MCPManagerError, RecoveryAction, ErrorSeverity
from .error_handler import RecoveryResult

logger = structlog.get_logger()


class BackoffStrategy(Enum):
    """Backoff strategies for retry operations."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    RANDOM_JITTER = "random_jitter"
    CUSTOM = "custom"


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    timeout: Optional[float] = None
    retry_on_exceptions: Optional[List[type]] = None
    stop_on_exceptions: Optional[List[type]] = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    timestamp: datetime
    error: Optional[Exception] = None
    success: bool = False
    duration: Optional[float] = None


class ExponentialBackoff:
    """Implements various backoff strategies with jitter."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempts: List[RetryAttempt] = []
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        
        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt)
        
        elif self.config.backoff_strategy == BackoffStrategy.RANDOM_JITTER:
            delay = self.config.base_delay + random.uniform(0, self.config.base_delay * attempt)
        
        else:  # Default to exponential
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        
        # Apply jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        return max(delay, 0.1)  # Minimum delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if we should retry based on attempt number and error type."""
        if attempt > self.config.max_attempts:
            return False
        
        # Check stop conditions
        if self.config.stop_on_exceptions:
            if any(isinstance(error, exc_type) for exc_type in self.config.stop_on_exceptions):
                return False
        
        # Check retry conditions
        if self.config.retry_on_exceptions:
            return any(isinstance(error, exc_type) for exc_type in self.config.retry_on_exceptions)
        
        return True
    
    def record_attempt(self, attempt_number: int, delay: float, 
                      error: Optional[Exception] = None, 
                      success: bool = False,
                      duration: Optional[float] = None) -> None:
        """Record information about a retry attempt."""
        attempt = RetryAttempt(
            attempt_number=attempt_number,
            delay=delay,
            timestamp=datetime.now(),
            error=error,
            success=success,
            duration=duration
        )
        self.attempts.append(attempt)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about retry attempts."""
        if not self.attempts:
            return {"total_attempts": 0}
        
        successful_attempts = [a for a in self.attempts if a.success]
        failed_attempts = [a for a in self.attempts if not a.success]
        
        return {
            "total_attempts": len(self.attempts),
            "successful_attempts": len(successful_attempts),
            "failed_attempts": len(failed_attempts),
            "success_rate": len(successful_attempts) / len(self.attempts) * 100,
            "total_delay": sum(a.delay for a in self.attempts),
            "average_delay": sum(a.delay for a in self.attempts) / len(self.attempts),
            "max_delay": max(a.delay for a in self.attempts),
            "total_duration": sum(a.duration for a in self.attempts if a.duration),
        }


class AutoRecoveryManager:
    """Manages automatic recovery operations with intelligent retry logic."""
    
    def __init__(self):
        self.recovery_configs: Dict[str, RetryConfig] = {}
        self.active_recoveries: Dict[str, 'RecoveryOperation'] = {}
        self.recovery_history: List['RecoveryOperation'] = []
        self.max_concurrent_recoveries = 5
        
        # Default configurations for different operation types
        self.setup_default_configs()
    
    def setup_default_configs(self) -> None:
        """Set up default retry configurations for different operations."""
        
        # Network operations - aggressive retry with exponential backoff
        self.recovery_configs["network"] = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter=True,
            timeout=300.0,  # 5 minutes total timeout
        )
        
        # Deployment operations - moderate retry with longer delays
        self.recovery_configs["deployment"] = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=60.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_multiplier=1.5,
            jitter=True,
            timeout=600.0,  # 10 minutes total timeout
        )
        
        # Configuration operations - quick retry with linear backoff
        self.recovery_configs["configuration"] = RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            max_delay=5.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=False,
            timeout=30.0,
        )
        
        # Health check operations - frequent retry with short delays
        self.recovery_configs["health_check"] = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=10.0,
            backoff_strategy=BackoffStrategy.FIBONACCI,
            jitter=True,
            timeout=60.0,
        )
        
        # File operations - quick retry with minimal delay
        self.recovery_configs["file_operation"] = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=2.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=False,
            timeout=10.0,
        )
    
    async def execute_with_recovery(self, 
                                  operation_id: str,
                                  operation_type: str,
                                  operation_func: Callable,
                                  *args,
                                  recovery_config: Optional[RetryConfig] = None,
                                  **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """Execute an operation with automatic recovery."""
        
        # Check if we're already at max concurrent recoveries
        if len(self.active_recoveries) >= self.max_concurrent_recoveries:
            logger.warning(f"Max concurrent recoveries reached, queuing operation {operation_id}")
            await self._wait_for_available_slot()
        
        # Get or create recovery configuration
        config = recovery_config or self.recovery_configs.get(operation_type, RetryConfig())
        
        # Create recovery operation
        recovery_op = RecoveryOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_func=operation_func,
            args=args,
            kwargs=kwargs,
            config=config
        )
        
        # Add to active recoveries
        self.active_recoveries[operation_id] = recovery_op
        
        try:
            # Execute with retry logic
            success, result, error = await recovery_op.execute()
            
            # Log result
            if success:
                logger.info(f"Operation {operation_id} completed successfully after {recovery_op.backoff.attempts[-1].attempt_number} attempts")
            else:
                logger.error(f"Operation {operation_id} failed after {len(recovery_op.backoff.attempts)} attempts: {error}")
            
            return success, result, error
            
        finally:
            # Remove from active recoveries and add to history
            self.active_recoveries.pop(operation_id, None)
            self.recovery_history.append(recovery_op)
            
            # Cleanup old history
            self._cleanup_recovery_history()
    
    async def _wait_for_available_slot(self) -> None:
        """Wait for an available recovery slot."""
        while len(self.active_recoveries) >= self.max_concurrent_recoveries:
            await asyncio.sleep(0.1)
    
    def _cleanup_recovery_history(self) -> None:
        """Clean up old recovery history entries."""
        max_history = 1000
        if len(self.recovery_history) > max_history:
            self.recovery_history = self.recovery_history[-max_history:]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about recovery operations."""
        if not self.recovery_history:
            return {"total_operations": 0}
        
        successful = [op for op in self.recovery_history if op.success]
        failed = [op for op in self.recovery_history if not op.success]
        
        # Operation type breakdown
        type_stats = {}
        for op in self.recovery_history:
            if op.operation_type not in type_stats:
                type_stats[op.operation_type] = {"total": 0, "successful": 0, "failed": 0}
            
            type_stats[op.operation_type]["total"] += 1
            if op.success:
                type_stats[op.operation_type]["successful"] += 1
            else:
                type_stats[op.operation_type]["failed"] += 1
        
        return {
            "total_operations": len(self.recovery_history),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "success_rate": len(successful) / len(self.recovery_history) * 100,
            "active_recoveries": len(self.active_recoveries),
            "operation_types": type_stats,
            "average_attempts": sum(len(op.backoff.attempts) for op in self.recovery_history) / len(self.recovery_history)
        }
    
    def cancel_recovery(self, operation_id: str) -> bool:
        """Cancel an active recovery operation."""
        if operation_id in self.active_recoveries:
            recovery_op = self.active_recoveries[operation_id]
            recovery_op.cancel()
            return True
        return False
    
    def cancel_all_recoveries(self) -> int:
        """Cancel all active recovery operations."""
        count = 0
        for operation_id in list(self.active_recoveries.keys()):
            if self.cancel_recovery(operation_id):
                count += 1
        return count


class RecoveryOperation:
    """Represents a single recovery operation with retry logic."""
    
    def __init__(self, operation_id: str, operation_type: str, 
                 operation_func: Callable, args: tuple, kwargs: dict,
                 config: RetryConfig):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.config = config
        self.backoff = ExponentialBackoff(config)
        
        self.cancelled = False
        self.success = False
        self.final_result = None
        self.final_error = None
        self.start_time = None
        self.end_time = None
    
    async def execute(self) -> Tuple[bool, Any, Optional[Exception]]:
        """Execute the operation with retry logic."""
        self.start_time = datetime.now()
        attempt_number = 1
        
        while attempt_number <= self.config.max_attempts:
            if self.cancelled:
                logger.info(f"Recovery operation {self.operation_id} cancelled")
                break
            
            try:
                # Check timeout
                if self.config.timeout:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if elapsed > self.config.timeout:
                        raise TimeoutError(f"Operation timed out after {elapsed:.2f} seconds")
                
                # Execute the operation
                operation_start = time.time()
                
                if asyncio.iscoroutinefunction(self.operation_func):
                    result = await self.operation_func(*self.args, **self.kwargs)
                else:
                    result = self.operation_func(*self.args, **self.kwargs)
                
                operation_duration = time.time() - operation_start
                
                # Success!
                self.backoff.record_attempt(
                    attempt_number=attempt_number,
                    delay=0,
                    success=True,
                    duration=operation_duration
                )
                
                self.success = True
                self.final_result = result
                self.end_time = datetime.now()
                
                logger.info(f"Operation {self.operation_id} succeeded on attempt {attempt_number}")
                return True, result, None
                
            except Exception as error:
                operation_duration = time.time() - operation_start if 'operation_start' in locals() else 0
                
                logger.warning(f"Operation {self.operation_id} failed on attempt {attempt_number}: {error}")
                
                # Check if we should retry
                if not self.backoff.should_retry(attempt_number, error):
                    self.backoff.record_attempt(
                        attempt_number=attempt_number,
                        delay=0,
                        error=error,
                        success=False,
                        duration=operation_duration
                    )
                    break
                
                # Calculate delay for next attempt
                if attempt_number < self.config.max_attempts:
                    delay = self.backoff.calculate_delay(attempt_number)
                    
                    self.backoff.record_attempt(
                        attempt_number=attempt_number,
                        delay=delay,
                        error=error,
                        success=False,
                        duration=operation_duration
                    )
                    
                    logger.info(f"Retrying operation {self.operation_id} in {delay:.2f} seconds")
                    await asyncio.sleep(delay)
                else:
                    # Last attempt failed
                    self.backoff.record_attempt(
                        attempt_number=attempt_number,
                        delay=0,
                        error=error,
                        success=False,
                        duration=operation_duration
                    )
                
                self.final_error = error
                attempt_number += 1
        
        # Operation failed
        self.success = False
        self.end_time = datetime.now()
        
        logger.error(f"Operation {self.operation_id} failed after {len(self.backoff.attempts)} attempts")
        return False, None, self.final_error
    
    def cancel(self) -> None:
        """Cancel the recovery operation."""
        self.cancelled = True
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get progress information about the recovery operation."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "cancelled": self.cancelled,
            "success": self.success,
            "attempts": len(self.backoff.attempts),
            "max_attempts": self.config.max_attempts,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "backoff_statistics": self.backoff.get_statistics()
        }


# Global auto-recovery manager instance
_global_auto_recovery_manager: Optional[AutoRecoveryManager] = None


def get_auto_recovery_manager() -> AutoRecoveryManager:
    """Get the global auto-recovery manager instance."""
    global _global_auto_recovery_manager
    if _global_auto_recovery_manager is None:
        _global_auto_recovery_manager = AutoRecoveryManager()
    return _global_auto_recovery_manager


async def execute_with_recovery(operation_id: str, operation_type: str, 
                               operation_func: Callable, *args, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
    """Convenience function for executing operations with recovery."""
    manager = get_auto_recovery_manager()
    return await manager.execute_with_recovery(operation_id, operation_type, operation_func, *args, **kwargs)