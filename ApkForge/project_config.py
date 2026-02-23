# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : project_config.py
# Purpose : Loads and validates build configuration from build_config.json.
# =============================================================================

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProjectConfig:
    version_code: int
    version_name: str

    app_name: str
    application_id: str

    build_type: str
    target_dex_index: int
    auto_multidex: bool

    prefer_existing_dex: bool
    create_new_dex_if_full: bool
    max_files_per_dex: int

    skip_files: List[str]
    force_multidex: bool
    min_sdk_version: int

    additional_smali_dirs: List[str]
    keystore_path: str

    abi_keep_only: List[str]
    abi_remove_others: bool
    abi_warn_if_missing: bool

    build_abis: List[str] = field(default_factory=list)

    raw_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, project_root: Path) -> "ProjectConfig":
        config_path = project_root / "build_config.json"

        if not config_path.exists():
            raise FileNotFoundError(
                f"build_config.json not found at {config_path}\n"
                "Please create build_config.json in the project root directory."
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            abi_config = data.get("abi", {})

            config = cls(
                version_code=data["version"]["code"],
                version_name=data["version"]["name"],
                app_name=data["app"]["name"],
                application_id=data["app"]["package_id"],
                build_type=data["build"]["type"],
                target_dex_index=data["build"]["target_dex_index"],
                auto_multidex=data["build"]["auto_multidex"],
                prefer_existing_dex=data["dex_placement"]["prefer_existing"],
                create_new_dex_if_full=data["dex_placement"]["create_new_if_full"],
                max_files_per_dex=data["dex_placement"]["max_files_per_dex"],
                skip_files=data["custom_rules"]["skip_files"],
                force_multidex=data["custom_rules"]["force_multidex"],
                min_sdk_version=data["custom_rules"]["min_sdk_version"],
                additional_smali_dirs=data["paths"]["additional_smali_dirs"],
                keystore_path=data["paths"]["keystore"],
                abi_keep_only=abi_config.get("keep_only", []),
                abi_remove_others=abi_config.get("remove_others", True),
                abi_warn_if_missing=abi_config.get("warn_if_missing", True),
                build_abis=abi_config.get("build_abis", []),
                raw_config=data,
            )

            print(f"  Loaded config from {config_path}")
            config._print_summary()
            return config

        except KeyError as e:
            raise KeyError(f"Missing required key in build_config.json: {e}")
        except Exception as e:
            raise RuntimeError(f"Could not load config: {e}")

    def _print_summary(self):
        print(f"    Version: {self.version_name} (code: {self.version_code})")
        print(f"    App: {self.app_name} ({self.application_id})")
        print(f"    Build: {self.build_type}, target DEX: {self.target_dex_index}")
        print(f"    Auto multidex: {self.auto_multidex}")

        if self.abi_keep_only:
            print(f"    Keeping ABIs: {', '.join(self.abi_keep_only)}")

        if self.build_abis:
            print(f"    Building ABIs: {', '.join(self.build_abis)}")

        if self.additional_smali_dirs:
            print(f"    Additional smali dirs: {len(self.additional_smali_dirs)}")

    def get_absolute_paths(self, project_root: Path) -> List[Path]:
        paths = []
        for rel_path in self.additional_smali_dirs:
            full_path = project_root / rel_path
            if full_path.exists():
                paths.append(full_path)
            else:
                print(f"  Warning: Additional smali dir not found: {full_path}")
        return paths

    def should_skip_file(self, filename: str) -> bool:
        return filename in self.skip_files

    def get_keystore_config_path(self, project_root: Path) -> Path:
        return project_root / self.keystore_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_code": self.version_code,
            "version_name": self.version_name,
            "app_name": self.app_name,
            "application_id": self.application_id,
            "build_type": self.build_type,
            "target_dex_index": self.target_dex_index,
            "auto_multidex": self.auto_multidex,
        }

    def update_from_env(self):
        env_mappings = [
            ("BUILD_VERSION_CODE", "version_code", int),
            ("BUILD_VERSION_NAME", "version_name", str),
            ("BUILD_APP_NAME", "app_name", str),
            ("BUILD_PACKAGE_ID", "application_id", str),
            ("BUILD_TYPE", "build_type", str),
            ("BUILD_TARGET_DEX", "target_dex_index", int),
            ("BUILD_AUTO_MULTIDEX", "auto_multidex", lambda x: x.lower() == "true"),
        ]

        updated = False
        for env_var, config_attr, converter in env_mappings:
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    setattr(self, config_attr, converter(env_value))
                    print(f"  Set {config_attr} = {env_value} from environment")
                    updated = True
                except Exception as e:
                    print(f"  Warning: Could not set {config_attr} from env: {e}")

        return updated


_project_config: Optional[ProjectConfig] = None


def init_project_config(project_root: Path) -> ProjectConfig:
    global _project_config
    _project_config = ProjectConfig.load(project_root)
    return _project_config


def get_config() -> ProjectConfig:
    global _project_config
    if _project_config is None:
        raise RuntimeError(
            "Project config not initialized. Call init_project_config first."
        )
    return _project_config