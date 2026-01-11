"""Configuration management with preservation and backup."""

import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import ruamel.yaml, fall back to pyyaml
try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False

import yaml as yaml_module


class ConfigManager:
    """Manage configuration files with preservation and backup."""

    def __init__(self, config_path: str = "config.yaml", max_backups: int = 5):
        """
        Initialize config manager.

        Parameters
        ----------
        config_path : str
            Path to configuration file
        max_backups : int
            Maximum number of backup files to keep
        """
        self.config_path = config_path
        self.max_backups = max_backups
        self.backup_dir = Path(config_path).parent / ".config_backups"
        self.backup_dir.mkdir(exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns
        -------
        Dict[str, Any]
            Loaded configuration dictionary

        Raises
        ------
        FileNotFoundError
            If configuration file doesn't exist
        yaml.YAMLError
            If configuration file is invalid YAML
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            if HAS_RUAMEL:
                yaml_handler = YAML()
                yaml_handler.preserve_quotes = True
                yaml_handler.default_flow_style = False
                with open(self.config_path, "r") as f:
                    config = yaml_handler.load(f)
            else:
                with open(self.config_path, "r") as f:
                    config = yaml_module.safe_load(f)
            
            logger.debug(f"Configuration loaded from {self.config_path}")
            return config or {}
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def save_config(self, config: Dict[str, Any], create_backup: bool = True) -> None:
        """
        Save configuration to file with optional backup.

        Parameters
        ----------
        config : Dict[str, Any]
            Configuration dictionary to save
        create_backup : bool
            Whether to create a backup before saving

        Raises
        ------
        IOError
            If save operation fails
        """
        try:
            # Create backup if requested and file exists
            if create_backup and os.path.exists(self.config_path):
                self._create_backup()

            # Save configuration
            if HAS_RUAMEL:
                yaml_handler = YAML()
                yaml_handler.preserve_quotes = True
                yaml_handler.default_flow_style = False
                with open(self.config_path, "w") as f:
                    yaml_handler.dump(config, f)
            else:
                with open(self.config_path, "w") as f:
                    yaml_module.dump(config, f, default_flow_style=False)

            logger.info(f"Configuration saved to {self.config_path}")
            
            # Clean up old backups
            self._cleanup_old_backups()
        except IOError as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def _create_backup(self) -> str:
        """
        Create a backup of the current configuration file.

        Returns
        -------
        str
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config.yaml.backup.{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"Configuration backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def _cleanup_old_backups(self) -> None:
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backups = sorted(
                self.backup_dir.glob("config.yaml.backup.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for old_backup in backups[self.max_backups :]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    def update_config(
        self,
        config: Dict[str, Any],
        updates: Dict[str, Any],
        create_backup: bool = True,
    ) -> Dict[str, Any]:
        """
        Update configuration with new values.

        Only specified keys are updated. Unspecified keys are preserved.

        Parameters
        ----------
        config : Dict[str, Any]
            Current configuration dictionary
        updates : Dict[str, Any]
            Dictionary of updates to apply
        create_backup : bool
            Whether to create a backup before saving

        Returns
        -------
        Dict[str, Any]
            Updated configuration dictionary
        """
        # Update only specified keys
        for key, value in updates.items():
            config[key] = value

        # Save with backup
        self.save_config(config, create_backup=create_backup)
        return config

    def get_backups(self) -> list:
        """
        Get list of available backup files.

        Returns
        -------
        list
            List of backup file paths, sorted by creation time (newest first)
        """
        backups = sorted(
            self.backup_dir.glob("config.yaml.backup.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [str(b) for b in backups]

    def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Restore configuration from a backup file.

        Parameters
        ----------
        backup_path : str
            Path to the backup file to restore

        Returns
        -------
        Dict[str, Any]
            Restored configuration dictionary

        Raises
        ------
        FileNotFoundError
            If backup file doesn't exist
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Create a backup of current config before restoring
            if os.path.exists(self.config_path):
                self._create_backup()

            # Copy backup to current config
            shutil.copy2(backup_path, self.config_path)
            logger.info(f"Configuration restored from: {backup_path}")

            # Load and return the restored configuration
            return self.load_config()
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise
