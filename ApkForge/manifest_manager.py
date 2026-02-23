# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : manifest_manager.py
# Purpose : Utility functions for AndroidManifest.xml operations.
# =============================================================================

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple


class ManifestManager:
    ANDROID_NS = "http://schemas.android.com/apk/res/android"

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        ET.register_namespace("android", self.ANDROID_NS)

    def get_package_name(self) -> Optional[str]:
        if not self.manifest_path.exists():
            return None

        try:
            tree = ET.parse(self.manifest_path)
            root = tree.getroot()
            return root.get("package")
        except (ET.ParseError, OSError):
            return None

    def get_sdk_versions(self) -> Tuple[Optional[str], Optional[str]]:
        if not self.manifest_path.exists():
            return None, None

        try:
            tree = ET.parse(self.manifest_path)
            root = tree.getroot()
            uses_sdk = root.find(".//uses-sdk")
            if uses_sdk is not None:
                min_sdk = uses_sdk.get(f"{{{self.ANDROID_NS}}}minSdkVersion")
                target_sdk = uses_sdk.get(f"{{{self.ANDROID_NS}}}targetSdkVersion")
                return min_sdk, target_sdk
        except (ET.ParseError, OSError):
            pass

        return None, None

    def get_min_sdk(self) -> int:
        min_sdk, _ = self.get_sdk_versions()
        try:
            return int(min_sdk) if min_sdk and min_sdk.isdigit() else 21
        except (ValueError, TypeError):
            return 21

    def get_main_activity(self) -> Optional[str]:
        if not self.manifest_path.exists():
            return None

        try:
            tree = ET.parse(self.manifest_path)
            root = tree.getroot()

            application = root.find(".//application")
            if application is None:
                return None

            for activity in application.findall(".//activity"):
                if self._is_launcher_activity(activity):
                    return activity.get(f"{{{self.ANDROID_NS}}}name")

        except (ET.ParseError, OSError):
            pass

        return None

    def _is_launcher_activity(self, activity) -> bool:
        intent_filters = activity.findall("intent-filter")
        for intent_filter in intent_filters:
            if self._has_launcher_intent(intent_filter):
                return True
        return False

    def _has_launcher_intent(self, intent_filter) -> bool:
        actions = intent_filter.findall("action")
        categories = intent_filter.findall("category")

        has_main = False
        has_launcher = False

        for action in actions:
            if action.get(f"{{{self.ANDROID_NS}}}name") == "android.intent.action.MAIN":
                has_main = True

        for category in categories:
            if (
                    category.get(f"{{{self.ANDROID_NS}}}name")
                    == "android.intent.category.LAUNCHER"
            ):
                has_launcher = True

        return has_main and has_launcher
