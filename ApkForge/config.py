# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : config.py
# Purpose : Handles keystore configuration loading and validation for APK signing.
# =============================================================================

import json
from pathlib import Path


class KeystoreConfig:
    def __init__(self, config_path: Path, project_root: Path):
        self.config_path = config_path
        self.project_root = project_root
        self.path = None
        self.alias = None
        self.password = None
        self.key_password = None

    def load(self):
        if not self.config_path.exists():
            raise FileNotFoundError(
                "keystore.json not found at: {}".format(self.config_path)
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.path = Path(config.get("keystore_path") or "")
            self.alias = config.get("keystore_alias")
            self.password = config.get("keystore_password")
            self.key_password = config.get("key_password")

        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON in {}: {}".format(self.config_path, e))

    def validate(self):
        missing = []
        if not self.path:
            missing.append("keystore_path")
        if not self.alias:
            missing.append("keystore_alias")
        if not self.password:
            missing.append("keystore_password")
        if not self.key_password:
            missing.append("key_password")

        if missing:
            raise ValueError("Missing required fields: {}".format(", ".join(missing)))

        if not self.path.is_absolute():
            self.path = self.project_root / str(self.path)

        self.path = self.path.resolve()

        if not self.path.exists():
            raise FileNotFoundError("Keystore file not found: {}".format(self.path))

        return True
