# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : manifest_updater.py
# Purpose : Merges custom AndroidManifest.xml with the decompiled one,
#           updates package name and merges permissions/activities.
# =============================================================================

import re
import xml.etree.ElementTree as ET
from pathlib import Path


class ManifestUpdater:
    ANDROID_NS = "http://schemas.android.com/apk/res/android"
    RESOURCES_CLOSING_TAG = "</resources>"
    _ATTR_PATTERN_SUFFIX = r'[^"]*)(")'

    def __init__(self, manifest_path: Path, custom_manifest_path: Path):
        self.manifest_path = manifest_path
        self.custom_manifest_path = custom_manifest_path
        self.old_package = None
        ET.register_namespace("android", self.ANDROID_NS)

    @staticmethod
    def _read_xml(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        if content.startswith("\ufeff"):
            content = content[1:]

        return content

    def _write_xml(self, path, content):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            if not content.strip().startswith("<?xml"):
                content = '<?xml version="1.0" encoding="utf-8"?>\n' + content

            if "xmlns:android=" not in content:
                content = content.replace(
                    "<manifest", f'<manifest xmlns:android="{self.ANDROID_NS}"', 1
                )

            f.write(content)

    def _ns_tag(self, tag):
        return f".//{{{self.ANDROID_NS}}}{tag}" if ":" in tag else tag

    def _ns_attr(self, attr):
        return f"{{{self.ANDROID_NS}}}{attr}"

    def _find_with_ns(self, element, tag):
        results = []

        ns_tag = f"{{{self.ANDROID_NS}}}{tag}"
        results.extend(element.findall(f".//{ns_tag}"))

        results.extend(element.findall(f".//{tag}"))

        unique_results = []
        seen = set()
        for elem in results:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_results.append(elem)

        return unique_results

    def _replace_all_package_references(
            self, content: str, old_package: str, new_package: str
    ) -> str:
        old_package_escaped = re.escape(old_package)
        s = self._ATTR_PATTERN_SUFFIX

        def replace_attr(m):
            return (
                    m.group(1) + m.group(2).replace(old_package, new_package) + m.group(3)
            )

        patterns = [
            (r'(android:name=")([^"]*' + old_package_escaped + s, replace_attr),
            (r'(android:authorities=")([^"]*' + old_package_escaped + s, replace_attr),
            (
                r'(<uses-permission[^>]*android:name=")([^"]*'
                + old_package_escaped
                + s,
                replace_attr,
            ),
            (r'(<[^>]+android:name=")([^"]*' + old_package_escaped + s, replace_attr),
            (
                r"([^a-zA-Z0-9_])" + old_package_escaped + r"([^a-zA-Z0-9_])",
                lambda m: m.group(1) + new_package + m.group(2),
            ),
        ]

        modified_content = content
        for pattern, repl_func in patterns:
            modified_content = re.sub(pattern, repl_func, modified_content)

        tag_pattern = r'(<[^>]+name=")([^"]*' + old_package_escaped + s
        modified_content = re.sub(
            tag_pattern,
            replace_attr,
            modified_content,
        )

        return modified_content

    @staticmethod
    def _extract_old_package(manifest_root) -> str:
        return manifest_root.get("package", "")

    def _merge_string_resources(self):
        strings_path = self.manifest_path.parent / "res" / "values" / "strings.xml"
        if not strings_path.exists():
            return

        custom_content = self._read_xml(self.custom_manifest_path)

        string_refs = set(re.findall(r"@string/(?P<string_name>\w+)", custom_content))

        if not string_refs:
            return

        print(f"    Found {len(string_refs)} string references in custom manifest")

        with open(strings_path, "r", encoding="utf-8") as f:
            strings_content = f.read()

        existing_strings = {}

        name_pattern = r'<string\s+name="([^"]+)"'
        for match in re.finditer(name_pattern, strings_content):
            key = match.group(1)
            existing_strings[key] = True

        alt_pattern = r"<string\s+name=([^\s>]+)"
        for match in re.finditer(alt_pattern, strings_content):
            key = match.group(1).strip("\"'")
            existing_strings[key] = True

        missing_strings = string_refs - set(existing_strings.keys())

        if not missing_strings:
            print("    All required string resources already exist")
            return

        print(f"    Adding {len(missing_strings)} missing string resources")

        if self.RESOURCES_CLOSING_TAG in strings_content:
            new_strings = []
            for string_name in missing_strings:
                default_value = string_name.replace("_", " ").title()
                new_strings.append(
                    f'    <string name="{string_name}">{default_value}</string>'
                )

            if new_strings:
                insert_content = "\n" + "\n".join(new_strings) + "\n"
                strings_content = strings_content.replace(
                    self.RESOURCES_CLOSING_TAG,
                    insert_content + self.RESOURCES_CLOSING_TAG,
                )

        with open(strings_path, "w", encoding="utf-8") as f:
            f.write(strings_content)

    def update(self, application_id):
        print("  Loading main manifest...")
        main_content = self._read_xml(self.manifest_path)
        manifest_tree = ET.ElementTree(ET.fromstring(main_content))
        manifest_root = manifest_tree.getroot()

        self.old_package = self._extract_old_package(manifest_root)
        print(f"  Old package detected: {self.old_package}")

        print("  Loading custom manifest...")
        custom_content = self._read_xml(self.custom_manifest_path)
        custom_tree = ET.ElementTree(ET.fromstring(custom_content))
        custom_root = custom_tree.getroot()

        print(f"  Updating package to: {application_id}")
        self._update_package(manifest_root, application_id)

        print("  Copying manifest attributes...")
        self._copy_manifest_attributes(manifest_root, custom_root)

        main_app = self._get_application_element(manifest_root)
        custom_app = self._get_application_element(custom_root)

        if not main_app or not custom_app:
            raise ValueError("Application tag not found in one of the manifests")

        print("  Removing LAUNCHER intent-filters...")
        removed_count = self._remove_launcher_filters(main_app)
        print(f"    Removed {removed_count} LAUNCHER intent-filters")

        print("  Copying application attributes...")
        self._copy_application_attributes(main_app, custom_app)

        print("  Merging permissions...")
        perm_count = self._merge_permissions(manifest_root, custom_root)
        print(f"    Added {perm_count} permissions")

        print("  Merging features...")
        feature_count = self._merge_features(manifest_root, custom_root)
        print(f"    Added {feature_count} features")

        print("  Merging application elements...")
        element_count = self._merge_application_elements(main_app, custom_app)
        print(f"    Added {element_count} application elements")

        print("  Merging string resources...")
        self._merge_string_resources()

        print("  Saving merged manifest...")
        xml_str = ET.tostring(manifest_root, encoding="unicode")

        if self.old_package and self.old_package != application_id:
            print(
                f"  Replacing all occurrences of '{self.old_package}' with '{application_id}'..."
            )
            xml_str = self._replace_all_package_references(
                xml_str, self.old_package, application_id
            )
            print("    [OK] Package references updated throughout the manifest")

        if "xmlns:android" not in xml_str:
            xml_str = xml_str.replace(
                "<manifest", f'<manifest xmlns:android="{self.ANDROID_NS}"'
            )

        self._write_xml(self.manifest_path, xml_str)

        return True

    def _get_application_element(self, root):
        app = root.find("application")
        if app is None:
            app = root.find(f"{{{self.ANDROID_NS}}}application") or root.find(
                "application"
            )
        return app

    @staticmethod
    def _update_package(manifest_root, application_id):
        old_package = manifest_root.get("package", "Not set")
        manifest_root.set("package", application_id)
        print(f"    Package: {old_package} -> {application_id}")

    @staticmethod
    def _copy_manifest_attributes(target, source):
        copied = 0
        for attr_name, attr_value in source.attrib.items():
            if attr_name != "package" and not attr_name.startswith("xmlns:"):
                target.set(attr_name, attr_value)
                copied += 1
        return copied

    def _remove_launcher_filters(self, application):
        removed = 0
        activities = self._find_with_ns(application, "activity")

        for activity in activities:
            removed += self._remove_launcher_from_activity(activity)

        return removed

    def _remove_launcher_from_activity(self, activity):
        removed = 0
        intent_filters = self._find_with_ns(activity, "intent-filter")

        for intent_filter in intent_filters:
            if self._is_launcher_filter(intent_filter):
                activity_name = activity.get(self._ns_attr("name")) or activity.get(
                    "name", "Unknown"
                )
                activity.remove(intent_filter)
                removed += 1
                print(f"      Removed from activity: {activity_name}")

        return removed

    def _is_launcher_filter(self, intent_filter):
        has_launcher = self._has_category(
            intent_filter, "android.intent.category.LAUNCHER"
        )
        has_main = self._has_action(intent_filter, "android.intent.action.MAIN")
        return has_launcher and has_main

    def _has_category(self, intent_filter, category_name):
        categories = self._find_with_ns(intent_filter, "category")
        for category in categories:
            name = category.get(self._ns_attr("name")) or category.get("name")
            if name == category_name:
                return True
        return False

    def _has_action(self, intent_filter, action_name):
        actions = self._find_with_ns(intent_filter, "action")
        for action in actions:
            name = action.get(self._ns_attr("name")) or action.get("name")
            if name == action_name:
                return True
        return False

    @staticmethod
    def _copy_application_attributes(target, source):
        copied = 0
        for attr_name, attr_value in source.attrib.items():
            target_attr = target.get(attr_name)
            if target_attr is None:
                target.set(attr_name, attr_value)
                copied += 1
        return copied

    def _merge_permissions(self, target_root, source_root):
        added = 0
        source_perms = source_root.findall("uses-permission")

        for perm in source_perms:
            perm_name = perm.get(self._ns_attr("name")) or perm.get("name")

            if perm_name and not self._permission_exists(target_root, perm_name):
                target_root.append(perm)
                added += 1
                print(f"      Added permission: {perm_name}")

        return added

    def _permission_exists(self, target_root, perm_name):
        target_perms = target_root.findall("uses-permission")
        for target_perm in target_perms:
            target_name = target_perm.get(self._ns_attr("name")) or target_perm.get(
                "name"
            )
            if target_name == perm_name:
                return True
        return False

    def _merge_features(self, target_root, source_root):
        added = 0
        source_features = source_root.findall("uses-feature")

        for feature in source_features:
            feature_name = feature.get(self._ns_attr("name")) or feature.get("name")

            if feature_name:
                if not self._feature_exists(target_root, feature_name):
                    target_root.append(feature)
                    added += 1
                    print(f"      Added feature: {feature_name}")
            else:
                target_root.append(feature)
                added += 1
                print("      Added unnamed feature")

        return added

    def _feature_exists(self, target_root, feature_name):
        target_features = target_root.findall("uses-feature")
        for target_feature in target_features:
            target_name = target_feature.get(
                self._ns_attr("name")
            ) or target_feature.get("name")
            if target_name == feature_name:
                return True
        return False

    def _merge_application_elements(self, target_app, source_app):
        element_types = {"activity", "service", "receiver", "provider", "meta-data"}
        added = 0

        for child in source_app:
            tag_name = self._extract_tag_name(child.tag)

            if tag_name not in element_types:
                continue

            child_name = child.get(self._ns_attr("name")) or child.get("name")
            if not child_name:
                continue

            if not self._element_exists(target_app, tag_name, child_name):
                target_app.append(child)
                added += 1
                print(f"      Added {tag_name}: {child_name}")

        return added

    @staticmethod
    def _extract_tag_name(tag):
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    def _element_exists(self, target_app, tag_name, child_name):
        target_children = self._find_with_ns(target_app, tag_name)
        for elem in target_children:
            elem_name = elem.get(self._ns_attr("name")) or elem.get("name")
            if elem_name == child_name:
                return True
        return False
