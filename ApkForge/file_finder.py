# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : file_finder.py
# Purpose : Locates required JAR files (apktool, baksmali, smali) and source APK.
# =============================================================================


class FileFinder:
    def __init__(self, paths: dict):
        self.paths = paths
        self.found_files = {}

    def find_all(self):
        print("  Searching for required files...")

        self.found_files = {
            "apktool_jar": self.paths.get("apktool_jar"),
            "baksmali_jar": self.paths.get("baksmali_jar"),
            "smali_jar": self.paths.get("smali_jar"),
            "source_apk": self._find_source_apk(),
        }

        self._validate_found()
        return self.found_files

    def _find_source_apk(self):
        original_dir = self.paths.get("original_game_dir")
        if not original_dir:
            return None

        if not original_dir.exists():
            print(f"    Original game directory not found: {original_dir}")
            return None

        apks = list(original_dir.glob("*.apk"))
        if apks:
            print(f"    Found source APK: {apks[0].name}")
            return apks[0]

        print(f"    No APK files found in {original_dir}")
        return None

    def _validate_found(self):
        errors = []

        if not self.found_files.get("source_apk"):
            errors.append("Source APK not found in OriginalGame directory")

        for tool in ["apktool_jar", "baksmali_jar", "smali_jar"]:
            if tool in self.paths and not self.found_files.get(tool):
                print(
                    f"  [Warning] Configured {tool} not found: {self.paths.get(tool)}"
                )

        if errors:
            error_msg = "Required files are missing:\n"
            for error in errors:
                error_msg += f"  - {error}\n"
            raise FileNotFoundError(error_msg)
