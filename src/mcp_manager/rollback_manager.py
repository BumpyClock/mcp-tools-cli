"""Rollback manager for MCP Manager operations with transaction-like capabilities."""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from .backup_system import BackupSystem, AutoBackupManager
from .exceptions import MCPManagerError, ErrorContext, ErrorSeverity

logger = structlog.get_logger()


class RollbackState(Enum):
    """States for rollback operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RollbackAction:
    """Individual action that can be rolled back."""
    action_id: str
    action_type: str  # "deploy", "config_change", "file_modify", etc.
    description: str
    server_name: Optional[str] = None
    platform_key: Optional[str] = None
    files_affected: List[str] = None
    backup_id: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.files_affected is None:
            self.files_affected = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RollbackTransaction:
    """A transaction containing multiple rollback actions."""
    transaction_id: str
    operation: str
    description: str
    actions: List[RollbackAction]
    state: RollbackState = RollbackState.PENDING
    created_at: str = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class RollbackManager:
    """Manages rollback operations with transaction-like capabilities."""
    
    def __init__(self, backup_system: Optional[BackupSystem] = None):
        self.backup_system = backup_system or BackupSystem()
        self.auto_backup_manager = AutoBackupManager(self.backup_system)
        
        self.state_dir = Path.home() / ".mcp_manager" / "rollback_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.transactions_file = self.state_dir / "transactions.json"
        
        self.current_transaction: Optional[RollbackTransaction] = None
        self.completed_transactions: List[RollbackTransaction] = []
        self.max_transactions = 20  # Keep last 20 transactions
        
        self.load_transaction_history()
    
    def load_transaction_history(self) -> None:
        """Load transaction history from disk."""
        try:
            if self.transactions_file.exists():
                with open(self.transactions_file, 'r') as f:
                    data = json.load(f)
                    transactions = []
                    for transaction in data:
                        # Convert state string back to enum
                        if 'state' in transaction and isinstance(transaction['state'], str):
                            transaction['state'] = RollbackState(transaction['state'])
                        transactions.append(RollbackTransaction(**transaction))
                    self.completed_transactions = transactions
            else:
                self.completed_transactions = []
        except Exception as e:
            logger.warning(f"Failed to load transaction history: {e}")
            self.completed_transactions = []
    
    def save_transaction_history(self) -> None:
        """Save transaction history to disk."""
        try:
            # Convert transactions to serializable format
            serializable_transactions = []
            for tx in self.completed_transactions:
                tx_dict = asdict(tx)
                # Convert enum to string
                if 'state' in tx_dict:
                    tx_dict['state'] = tx_dict['state'].value if hasattr(tx_dict['state'], 'value') else str(tx_dict['state'])
                serializable_transactions.append(tx_dict)
            
            with open(self.transactions_file, 'w') as f:
                json.dump(serializable_transactions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transaction history: {e}")
    
    def start_transaction(self, operation: str, description: str) -> str:
        """Start a new rollback transaction."""
        if self.current_transaction:
            self.abort_current_transaction()
            logger.warning("Aborted previous transaction to start new one")
        
        transaction_id = f"{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.current_transaction = RollbackTransaction(
            transaction_id=transaction_id,
            operation=operation,
            description=description,
            actions=[]
        )
        
        logger.info(f"Started rollback transaction: {transaction_id}")
        return transaction_id
    
    def add_action(self, action_type: str, description: str,
                   server_name: Optional[str] = None,
                   platform_key: Optional[str] = None,
                   files_affected: Optional[List[Path]] = None,
                   rollback_data: Optional[Dict[str, Any]] = None) -> str:
        """Add an action to the current transaction."""
        if not self.current_transaction:
            raise MCPManagerError("No active transaction to add action to")
        
        action_id = f"{action_type}_{len(self.current_transaction.actions)}"
        
        # Create backup if files are affected
        backup_id = None
        if files_affected:
            file_paths = [Path(f) if isinstance(f, str) else f for f in files_affected]
            backup_id = self.auto_backup_manager.create_auto_backup(
                operation=action_type,
                affected_files=file_paths,
                description=f"Backup for {description}"
            )
        
        action = RollbackAction(
            action_id=action_id,
            action_type=action_type,
            description=description,
            server_name=server_name,
            platform_key=platform_key,
            files_affected=[str(f) for f in files_affected] if files_affected else [],
            backup_id=backup_id,
            rollback_data=rollback_data
        )
        
        self.current_transaction.actions.append(action)
        logger.debug(f"Added action to transaction: {action_id}")
        return action_id
    
    def commit_transaction(self) -> bool:
        """Commit the current transaction (mark as completed)."""
        if not self.current_transaction:
            logger.warning("No transaction to commit")
            return False
        
        try:
            self.current_transaction.state = RollbackState.COMPLETED
            self.current_transaction.completed_at = datetime.now().isoformat()
            
            # Move to completed transactions
            self.completed_transactions.append(self.current_transaction)
            self.current_transaction = None
            
            # Cleanup old transactions
            self.cleanup_old_transactions()
            self.save_transaction_history()
            
            logger.info("Transaction committed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            return False
    
    def rollback_transaction(self, transaction_id: Optional[str] = None) -> bool:
        """Rollback a transaction (current or specified)."""
        transaction = None
        
        if transaction_id is None:
            # Rollback current transaction
            transaction = self.current_transaction
            if not transaction:
                logger.error("No current transaction to rollback")
                return False
        else:
            # Find transaction by ID
            for tx in self.completed_transactions:
                if tx.transaction_id == transaction_id:
                    transaction = tx
                    break
            
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found")
                return False
        
        try:
            transaction.state = RollbackState.IN_PROGRESS
            rollback_successful = True
            
            # Rollback actions in reverse order
            for action in reversed(transaction.actions):
                try:
                    success = self.rollback_action(action)
                    if not success:
                        rollback_successful = False
                        logger.error(f"Failed to rollback action: {action.action_id}")
                except Exception as e:
                    rollback_successful = False
                    logger.error(f"Error rolling back action {action.action_id}: {e}")
            
            if rollback_successful:
                transaction.state = RollbackState.COMPLETED
                logger.info(f"Transaction {transaction.transaction_id} rolled back successfully")
            else:
                transaction.state = RollbackState.FAILED
                transaction.error_message = "Partial rollback failure"
                logger.error(f"Transaction {transaction.transaction_id} rollback failed")
            
            # Clear current transaction if we rolled it back
            if transaction == self.current_transaction:
                self.current_transaction = None
            
            self.save_transaction_history()
            return rollback_successful
            
        except Exception as e:
            transaction.state = RollbackState.FAILED
            transaction.error_message = str(e)
            logger.error(f"Failed to rollback transaction {transaction.transaction_id}: {e}")
            return False
    
    def rollback_action(self, action: RollbackAction) -> bool:
        """Rollback a specific action."""
        try:
            if action.action_type == "deploy":
                return self.rollback_deployment(action)
            elif action.action_type == "config_change":
                return self.rollback_config_change(action)
            elif action.action_type == "file_modify":
                return self.rollback_file_modification(action)
            elif action.action_type == "server_registration":
                return self.rollback_server_registration(action)
            else:
                logger.warning(f"Unknown action type for rollback: {action.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback action {action.action_id}: {e}")
            return False
    
    def rollback_deployment(self, action: RollbackAction) -> bool:
        """Rollback a deployment action."""
        try:
            # This would integrate with the deployment manager
            # to undeploy the server from the platform
            logger.info(f"Rolling back deployment: {action.server_name} from {action.platform_key}")
            
            # For now, restore files from backup
            if action.backup_id:
                return self.backup_system.restore_backup(action.backup_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback deployment {action.action_id}: {e}")
            return False
    
    def rollback_config_change(self, action: RollbackAction) -> bool:
        """Rollback a configuration change."""
        try:
            if action.backup_id:
                files_to_restore = [Path(f) for f in action.files_affected]
                return self.backup_system.restore_backup(action.backup_id, files_to_restore)
            
            # If no backup, use rollback_data to restore previous state
            if action.rollback_data:
                for file_path, content in action.rollback_data.items():
                    with open(file_path, 'w') as f:
                        if isinstance(content, dict):
                            json.dump(content, f, indent=2)
                        else:
                            f.write(str(content))
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rollback config change {action.action_id}: {e}")
            return False
    
    def rollback_file_modification(self, action: RollbackAction) -> bool:
        """Rollback a file modification."""
        try:
            if action.backup_id:
                files_to_restore = [Path(f) for f in action.files_affected]
                return self.backup_system.restore_backup(action.backup_id, files_to_restore)
            return False
            
        except Exception as e:
            logger.error(f"Failed to rollback file modification {action.action_id}: {e}")
            return False
    
    def rollback_server_registration(self, action: RollbackAction) -> bool:
        """Rollback server registration changes."""
        try:
            # This would integrate with the server registry
            # to remove or restore server registrations
            logger.info(f"Rolling back server registration: {action.server_name}")
            
            if action.backup_id:
                return self.backup_system.restore_backup(action.backup_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback server registration {action.action_id}: {e}")
            return False
    
    def abort_current_transaction(self) -> bool:
        """Abort the current transaction without rollback."""
        if not self.current_transaction:
            return True
        
        self.current_transaction.state = RollbackState.CANCELLED
        self.current_transaction = None
        logger.info("Current transaction aborted")
        return True
    
    def get_last_transaction(self) -> Optional[RollbackTransaction]:
        """Get the most recent completed transaction."""
        if not self.completed_transactions:
            return None
        return max(self.completed_transactions, key=lambda x: x.created_at)
    
    def list_transactions(self, limit: int = 10) -> List[RollbackTransaction]:
        """List recent transactions."""
        transactions = sorted(self.completed_transactions, 
                            key=lambda x: x.created_at, reverse=True)
        return transactions[:limit]
    
    def can_rollback(self, transaction_id: Optional[str] = None) -> bool:
        """Check if a transaction can be rolled back."""
        transaction = None
        
        if transaction_id is None:
            transaction = self.get_last_transaction()
        else:
            for tx in self.completed_transactions:
                if tx.transaction_id == transaction_id:
                    transaction = tx
                    break
        
        if not transaction:
            return False
        
        return (transaction.state in [RollbackState.COMPLETED] and
                len(transaction.actions) > 0)
    
    def cleanup_old_transactions(self) -> None:
        """Remove old transactions to stay within limits."""
        if len(self.completed_transactions) <= self.max_transactions:
            return
        
        # Sort by creation time and keep most recent
        self.completed_transactions.sort(key=lambda x: x.created_at, reverse=True)
        self.completed_transactions = self.completed_transactions[:self.max_transactions]
    
    def get_transaction_summary(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a transaction."""
        for transaction in self.completed_transactions:
            if transaction.transaction_id == transaction_id:
                return {
                    "id": transaction.transaction_id,
                    "operation": transaction.operation,
                    "description": transaction.description,
                    "state": transaction.state.value,
                    "actions_count": len(transaction.actions),
                    "created_at": transaction.created_at,
                    "completed_at": transaction.completed_at,
                    "can_rollback": self.can_rollback(transaction_id)
                }
        return None