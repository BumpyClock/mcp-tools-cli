"""Configuration backup and restore system for MCP Manager."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import structlog
from dataclasses import dataclass, asdict

logger = structlog.get_logger()


@dataclass
class BackupMetadata:
    """Metadata for configuration backups."""
    backup_id: str
    timestamp: str
    operation: str
    description: str
    files_backed_up: List[str]
    user: str
    checksum: Optional[str] = None
    size_bytes: int = 0


class BackupSystem:
    """Manages configuration backups for rollback capabilities."""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path.home() / ".mcp_manager" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.max_backups = 50  # Keep last 50 backups
        self.load_metadata()
    
    def load_metadata(self) -> None:
        """Load backup metadata from disk."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.backups = [BackupMetadata(**backup) for backup in data]
            else:
                self.backups = []
        except Exception as e:
            logger.warning(f"Failed to load backup metadata: {e}")
            self.backups = []
    
    def save_metadata(self) -> None:
        """Save backup metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump([asdict(backup) for backup in self.backups], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    def create_backup(self, operation: str, description: str, 
                     files_to_backup: List[Path]) -> Optional[str]:
        """Create a backup of specified files before an operation."""
        try:
            # Generate backup ID
            timestamp = datetime.now()
            backup_id = f"{operation}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(exist_ok=True)
            
            # Copy files to backup directory
            backed_up_files = []
            total_size = 0
            
            for file_path in files_to_backup:
                if not file_path.exists():
                    logger.warning(f"File does not exist for backup: {file_path}")
                    continue
                
                try:
                    # Preserve directory structure
                    relative_path = file_path.relative_to(file_path.anchor)
                    backup_file_path = backup_path / relative_path
                    backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file_path, backup_file_path)
                    backed_up_files.append(str(file_path))
                    total_size += file_path.stat().st_size
                    
                    logger.debug(f"Backed up file: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to backup file {file_path}: {e}")
                    continue
            
            if not backed_up_files:
                logger.warning("No files were successfully backed up")
                backup_path.rmdir()  # Remove empty backup directory
                return None
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=timestamp.isoformat(),
                operation=operation,
                description=description,
                files_backed_up=backed_up_files,
                user=Path.home().name,  # Simple user identification
                size_bytes=total_size
            )
            
            self.backups.append(metadata)
            self.cleanup_old_backups()
            self.save_metadata()
            
            logger.info(f"Created backup {backup_id} with {len(backed_up_files)} files ({total_size} bytes)")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_id: str, target_paths: Optional[List[Path]] = None) -> bool:
        """Restore files from a backup."""
        try:
            # Find backup metadata
            backup_metadata = None
            for backup in self.backups:
                if backup.backup_id == backup_id:
                    backup_metadata = backup
                    break
            
            if not backup_metadata:
                logger.error(f"Backup {backup_id} not found")
                return False
            
            backup_path = self.backup_dir / backup_id
            if not backup_path.exists():
                logger.error(f"Backup directory {backup_path} does not exist")
                return False
            
            # Determine files to restore
            files_to_restore = backup_metadata.files_backed_up
            if target_paths:
                files_to_restore = [f for f in files_to_restore 
                                  if any(Path(f).is_relative_to(target) for target in target_paths)]
            
            restored_count = 0
            for file_path_str in files_to_restore:
                try:
                    original_path = Path(file_path_str)
                    relative_path = original_path.relative_to(original_path.anchor)
                    backup_file_path = backup_path / relative_path
                    
                    if not backup_file_path.exists():
                        logger.warning(f"Backup file does not exist: {backup_file_path}")
                        continue
                    
                    # Create target directory if needed
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Restore file
                    shutil.copy2(backup_file_path, original_path)
                    restored_count += 1
                    
                    logger.debug(f"Restored file: {original_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to restore file {file_path_str}: {e}")
                    continue
            
            logger.info(f"Restored {restored_count} files from backup {backup_id}")
            return restored_count > 0
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def list_backups(self, operation_filter: Optional[str] = None) -> List[BackupMetadata]:
        """List available backups, optionally filtered by operation."""
        backups = self.backups.copy()
        
        if operation_filter:
            backups = [b for b in backups if b.operation == operation_filter]
        
        # Sort by timestamp (most recent first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a specific backup."""
        try:
            # Remove from metadata
            self.backups = [b for b in self.backups if b.backup_id != backup_id]
            
            # Remove backup directory
            backup_path = self.backup_dir / backup_id
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            self.save_metadata()
            logger.info(f"Deleted backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    def cleanup_old_backups(self) -> None:
        """Remove old backups to stay within the limit."""
        if len(self.backups) <= self.max_backups:
            return
        
        # Sort by timestamp and remove oldest
        self.backups.sort(key=lambda x: x.timestamp)
        backups_to_remove = self.backups[:len(self.backups) - self.max_backups]
        
        for backup in backups_to_remove:
            try:
                backup_path = self.backup_dir / backup.backup_id
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                logger.info(f"Cleaned up old backup: {backup.backup_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup backup {backup.backup_id}: {e}")
        
        # Keep only the most recent backups
        self.backups = self.backups[-self.max_backups:]
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get detailed information about a specific backup."""
        for backup in self.backups:
            if backup.backup_id == backup_id:
                return backup
        return None
    
    def estimate_backup_size(self, files_to_backup: List[Path]) -> int:
        """Estimate the size of a backup operation."""
        total_size = 0
        for file_path in files_to_backup:
            try:
                if file_path.exists():
                    total_size += file_path.stat().st_size
            except Exception:
                pass  # Skip files we can't access
        return total_size
    
    def get_disk_usage(self) -> Tuple[int, int]:
        """Get total backup disk usage and number of backups."""
        total_size = 0
        backup_count = 0
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name != "backup_metadata.json":
                try:
                    for file_path in backup_path.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                    backup_count += 1
                except Exception:
                    pass
        
        return total_size, backup_count


class AutoBackupManager:
    """Automatically manages backups for specific operations."""
    
    def __init__(self, backup_system: BackupSystem):
        self.backup_system = backup_system
        self.auto_backup_operations = {
            "deployment",
            "configuration_change",
            "server_registration",
            "batch_operation"
        }
    
    def should_auto_backup(self, operation: str) -> bool:
        """Check if an operation should trigger an automatic backup."""
        return operation in self.auto_backup_operations
    
    def create_auto_backup(self, operation: str, affected_files: List[Path],
                          description: Optional[str] = None) -> Optional[str]:
        """Create an automatic backup for an operation."""
        if not self.should_auto_backup(operation):
            return None
        
        auto_description = description or f"Automatic backup before {operation}"
        return self.backup_system.create_backup(
            operation=f"auto_{operation}",
            description=auto_description,
            files_to_backup=affected_files
        )