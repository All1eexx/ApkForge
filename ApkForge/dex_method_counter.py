# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : dex_method_counter.py
# Purpose : Counts methods in smali files and manages DEX splitting based on
#           method count limits.
# =============================================================================

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging


class DexMethodCounter:

    METHOD_PATTERNS = [
        r'\.method\s+(?:public|private|protected|static|final|synchronized|bridge|varargs|native|abstract|strictfp|'
        r'synthetic|constructor)?\s*(?:public|private|protected|static|final|synchronized|bridge|'
        r'varargs|native|abstract|strictfp|synthetic|constructor)?\s*([^(]+)\([^)]*\)[^\n]*',

        r'\.method\s+.*?\([^)]*\).*?(?=\n\.end method)',
    ]

    AVG_METHOD_SIZE = 100

    def __init__(self, modded_dir: Path, logger: Optional[logging.Logger] = None):
        self.modded_dir = modded_dir
        self.logger = logger or logging.getLogger(__name__)

    def count_methods_in_smali_file(self, smali_file: Path) -> int:
        try:
            with open(smali_file, 'r', encoding='utf-8') as f:
                content = f.read()

            method_count = 0
            for pattern in self.METHOD_PATTERNS:
                matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
                method_count += len(matches)

            if method_count == 0:
                method_count = len(re.findall(r'^\.method', content, re.MULTILINE))

            return method_count

        except Exception as e:
            self.logger.warning(f"  Could not count methods in {smali_file}: {e}")
            file_size = smali_file.stat().st_size
            return max(1, file_size // self.AVG_METHOD_SIZE)

    def count_methods_in_directory(self, smali_dir: Path) -> Dict[str, int]:
        method_counts = {}
        total_methods = 0

        smali_files = list(smali_dir.rglob("*.smali"))

        for smali_file in smali_files:
            rel_path = str(smali_file.relative_to(smali_dir))
            count = self.count_methods_in_smali_file(smali_file)
            method_counts[rel_path] = count
            total_methods += count

        return {
            'files': method_counts,
            'total': total_methods,
            'file_count': len(smali_files)
        }

    def analyze_all_dex_directories(self) -> Dict[str, Dict]:
        results = {}

        for item in self.modded_dir.iterdir():
            if item.is_dir() and item.name.startswith('smali'):
                self.logger.info(f"  Analyzing {item.name}...")
                results[item.name] = self.count_methods_in_directory(item)

        return results

    def find_dex_for_new_files(self,
                               new_smali_files: List[Path],
                               existing_dex_info: Dict[str, Dict],
                               config) -> Tuple[Path, str]:
        if not existing_dex_info:
            return self._create_new_dex_directory(1)

        new_methods = 0
        for smali_file in new_smali_files:
            new_methods += self.count_methods_in_smali_file(smali_file)

        self.logger.info(f"  New files add approximately {new_methods} methods")

        dex_loads = []
        for dex_name, info in existing_dex_info.items():
            dex_index = 1 if dex_name == 'smali' else int(dex_name.replace('smali_classes', ''))
            current_methods = info['total']
            current_files = info['file_count']

            remaining = max(0, config.max_methods_per_dex - current_methods)

            dex_loads.append({
                'name': dex_name,
                'index': dex_index,
                'methods': current_methods,
                'files': current_files,
                'remaining': remaining,
                'path': self.modded_dir / dex_name
            })

        dex_loads.sort(key=lambda x: x['remaining'], reverse=True)

        loads_str = ", ".join([f"{d['name']}({d['methods']}/{config.max_methods_per_dex})" for d in dex_loads])
        self.logger.info(f"  DEX method loads: {loads_str}")

        for dex_info in dex_loads:
            if dex_info['remaining'] >= new_methods:
                self.logger.info(f"  Selected {dex_info['name']} (fits {new_methods} methods)")
                return dex_info['path'], dex_info['name']

        if config.auto_split_dex:
            next_index = max(d['index'] for d in dex_loads) + 1
            self.logger.info(f"  No existing DEX has space for {new_methods} methods")
            self.logger.info(f"  Creating new DEX directory smali_classes{next_index}")
            return self._create_new_dex_directory(next_index)
        else:
            best_fit = dex_loads[0]
            self.logger.warning(f"  WARNING: {best_fit['name']} may exceed method limit ({best_fit['methods']} + "
                                f"{new_methods} > {config.max_methods_per_dex})")
            return best_fit['path'], best_fit['name']

    def _create_new_dex_directory(self, index: int) -> Tuple[Path, str]:
        if index == 1:
            dir_name = "smali"
        else:
            dir_name = f"smali_classes{index}"

        new_dir = self.modded_dir / dir_name
        new_dir.mkdir(exist_ok=True, parents=True)
        return new_dir, dir_name

    @staticmethod
    def validate_dex_method_counts(analysis: Dict[str, Dict], config) -> List[str]:
        warnings = []

        for dex_name, info in analysis.items():
            if info['total'] > config.max_methods_per_dex:
                warnings.append(
                    f"  {dex_name} has {info['total']} methods, "
                    f"exceeding limit of {config.max_methods_per_dex}"
                )

        return warnings

    @staticmethod
    def print_method_summary(analysis: Dict[str, Dict]):
        if not analysis:
            return

        print("\n  DEX Method Counts Summary:")
        print("  " + "-" * 50)

        total_methods = 0
        for dex_name, info in sorted(analysis.items()):
            print(f"    {dex_name:<15}: {info['total']:6d} methods in {info['file_count']:5d} files")
            total_methods += info['total']

        print("  " + "-" * 50)
        print(f"    TOTAL          : {total_methods:6d} methods")