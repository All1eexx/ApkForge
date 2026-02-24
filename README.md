<div style="text-align: center;">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0a,50:00ff88,100:0a0a0a&height=200&section=header&text=ApkForge&fontSize=70&fontColor=00ff88&fontAlignY=38&desc=Android%20APK%20Construction%20Toolkit&descAlignY=58&descSize=20&descColor=ffffff&animation=fadeIn" width="100%" alt="ApkForge Header"/>

<br/>

<a href="https://github.com/All1eexx/ApkForge"><img src="https://img.shields.io/badge/version-2.0.0-00ff88?style=for-the-badge&logo=github&logoColor=white&labelColor=0d0d0d" /></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-00ff88?style=for-the-badge&logo=open-source-initiative&logoColor=white&labelColor=0d0d0d" /></a>
<a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.8%2B-00ff88?style=for-the-badge&logo=python&logoColor=white&labelColor=0d0d0d" /></a>
<img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-00ff88?style=for-the-badge&logo=linux&logoColor=white&labelColor=0d0d0d" />

<br/><br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=800&color=00FF88&center=true&vCenter=true&multiline=false&width=700&lines=Decompile+%E2%86%92+Modify+%E2%86%92+Sign;Java+%2F+Kotlin+%2F+C%2B%2B+%2F+Smali;No+rigid+structure.+Just+config.;Any+method+from+any+.py+%E2%80%94+a+pipeline+step." alt="ApkForge typing animation showing workflow steps"/>

</div>

<br/>

---

## 🧩 What is ApkForge?

**ApkForge** is a Python toolkit for the full Android APK lifecycle: from decompilation to a signed, installation-ready
file.

> **Core principle:** ApkForge does not dictate how your project should be structured. Everything is controlled via
`build_config.json` — you specify the paths, choose the steps, and run. The tool integrates seamlessly into any existing
> project with any directory layout.

<br/>

<div style="text-align: center;">

```
  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
  │  Your APK   │────▶│   build_config   │────▶│  ApkForge   │
  │  + Code     │     │      .json       │     │  Pipeline   │
  └──────────────┘     └──────────────────┘     └──────┬───────┘
                                                        │
               ┌────────────────────────────────────────┘
               ▼
  ┌────────────────────────────────────────────────────────────┐
  │  Decompile  →  Compile  →  Modify  →  Sign               │
  └────────────────────────────────────────────────────────────┘
               │
               ▼
  ┌──────────────────────┐
  │  Ready-to-use APK ✅ │
  └──────────────────────┘
```

</div>

<br/>

---

## ✨ Features

ApkForge ships with a wide set of ready-made modules — but that's just the starting point. Any developer can write their
own method in **any `.py` file** and instantly add it to the `pipeline`. **The only limit is your imagination.**

<br/>

<div style="text-align: center;">

| &nbsp;&nbsp;Module&nbsp;&nbsp; | Description                                                       |
|:------------------------------:|:------------------------------------------------------------------|
|       🔓 **Decompiler**        | Unpacks APK via apktool, extracts smali, resources and manifest   |
|       🔬 **ApkAnalyzer**       | Analyzes DEX structure, package name, main activity, multidex     |
|       ☕ **JavaCompiler**       | Compiles `.java` sources via `javac`                              |
|     🎯 **KotlinCompiler**      | Compiles `.kt` sources via `kotlinc`                              |
|       📦 **JarBuilder**        | Packages classes into a JAR and merges with libraries             |
|       ⚡ **DexConverter**       | Converts JAR → DEX via `d8`                                       |
|     📝 **SmaliDecompiler**     | Decompiles DEX → smali via `baksmali`                             |
|      ⚙️ **NativeBuilder**      | Builds C++ libraries via CMake + Ninja for target ABIs            |
|       🏗️ **ApkBuilder**       | Reassembles APK from decompiled files via apktool                 |
|        🔐 **ApkSigner**        | Signs APK (v1/v2/v3/v4) and performs zipalign                     |
|    🛡️ **ManifestUpdater**     | Intelligently merges your AndroidManifest.xml with the original   |
|     🎨 **ResourceManager**     | Copies and updates Android resources                              |
|        📐 **ABIFilter**        | Removes unwanted ABI directories to reduce APK size               |
|      ✏️ **SmaliUpdater**       | Updates `VERSION_CODE`, `VERSION_NAME`, `APPLICATION_ID` in smali |
|     🔤 **StringsUpdater**      | Updates the app name in `strings.xml`                             |
|      🗂️ **YamlUpdater**       | Updates version and APK filename in `apktool.yml`                 |
|     🔧 **PipelineManager**     | Executes any method or function from **any `.py` file** as a step |

</div>

<br/>

---

## 📋 Dependencies

The only **required** dependency is **Python 3.8+**.

Everything else is only needed if the corresponding steps are included in your `pipeline`:

<br/>

<div style="text-align: center;">

| Dependency           | When needed                    |
|:---------------------|:-------------------------------|
| **Java JDK 8+**      | apktool, baksmali, smali, d8   |
| **Android SDK**      | d8, apksigner, zipalign        |
| **apktool**          | APK decompilation / reassembly |
| **baksmali / smali** | DEX ↔ smali conversion         |
| **CMake + Ninja**    | Building native C++ libraries  |
| **kotlinc**          | Compiling Kotlin sources       |

</div>

> Paths to apktool, baksmali, smali and other tools are set in `build_config.json` — they can be located anywhere on
> your machine.

<br/>

---

## 🚀 Quick Start

<br/>

**1. Clone the repository**

```bash
git clone https://github.com/All1eexx/ApkForge.git
```

<br/>

**2. Create `build_config.json` in the root of your project**

> ⚠️ `build_config.json` is the only file with a strict placement requirement. It **must** be located in the root of
> your project. ApkForge finds it by walking up the directory tree from the location of `main.py`.

```json
{
  "version": { "code": 2, "name": "2.0" },
  "app": { "name": "MyApp", "package_id": "com.my.app" },
  "build": { "type": "Release", "target_dex_index": 2 },
  "paths": {
    "tools": {
      "apktool":     "path/to/apktool.jar",
      "baksmali":    "path/to/baksmali.jar",
      "smali":       "path/to/smali.jar",
      "android_sdk": null
    },
    "directories": {
      "original_game": "path/to/folder/with/apk",
      "modded":        "path/to/output/folder",
      "src":           "path/to/your/sources"
    }
  },
  "pipeline": [
    "_load_project_config",
    "_load_keystore_config",
    "_find_files",
    "_run_apktool_decompile",
    "_build_unsigned_apk",
    "_zipalign_apk",
    "_sign_apk",
    "_verify_signature",
    "_print_final_summary"
  ]
}
```

> 💡 All paths can be specified **relative to the folder where `build_config.json` lives** (e.g. `"tools/apktool.jar"`),
> or as **absolute paths** (e.g. `"C:/Android/apktool.jar"` or `"/home/user/tools/apktool.jar"`). Both formats work on
> all platforms.

<br/>

**3. Create `keystore.json`** *(required only if the signing step is in your pipeline)*

```json
{
  "keystore_path":     "path/to/your.keystore",
  "keystore_alias":    "mykey",
  "keystore_password": "password",
  "key_password":      "password"
}
```

<br/>

**4. Run `main.py`** from anywhere — ApkForge will locate `build_config.json` automatically

```bash
python path/to/ApkForge/main.py
```

<br/>

---

## 🔬 How It Works

### How ApkForge finds `build_config.json`

On startup, `PathManager` walks up the directory tree from the location of `main.py` and looks for the first
`build_config.json` it encounters. This allows you to keep the ApkForge modules in a subdirectory while the config stays
in your project root:

```
MyProject/                    ← build_config.json lives here
├── build_config.json
├── keystore.json
│
└── tools/
    └── ApkForge/             ← main.py and all modules live here
        ├── main.py
        ├── pipeline_manager.py
        └── ...
```

<br/>

### How PipelineManager works

`PipelineManager` resolves and executes each step string from the `pipeline` list. A step can be a method from
`main.py`, a standalone function from any module, or a class method from any module — with or without arguments:

```
build_config.json                     Resolution
┌───────────────────────────────┐     ┌──────────────────────────────────────────┐
│ "pipeline": [                 │     │  "_print_header"                         │
│   "_print_header",            │──▶  │    → ApkForge._print_header()            │
│   "_find_files",              │     │                                          │
│   "decompiler.Decompiler      │     │  "decompiler.Decompiler.decompile"       │
│     .decompile",              │──▶  │    → Decompiler(...).decompile()         │
│   "platform_utils             │     │                                          │
│     .setup_utf8_environment", │──▶  │  "platform_utils.setup_utf8_environment" │
│   "abi_filter.ABIFilter       │     │    → setup_utf8_environment()            │
│     .filter('arm64-v8a')"     │     │                                          │
│ ]                             │──▶  │  "abi_filter.ABIFilter.filter('arm64')"  │
└───────────────────────────────┘     │    → ABIFilter(...).filter('arm64')      │
                                      └──────────────────────────────────────────┘
```

<br/>

### Pipeline step formats

There are three ways to write a step — all supported simultaneously in the same pipeline:

**1. Method from `main.py` (ApkForge class):**

```json
"_print_header"
"_find_files"
"_load_project_config"
```

**2. Function from any `.py` file:**

```json
"platform_utils.setup_utf8_environment"
"sdk_detector.SDKDetector.find_sdk"
```

**3. Class method from any `.py` file — with optional arguments:**

```json
"decompiler.Decompiler.decompile"
"abi_filter.ABIFilter.filter('arm64-v8a')"
"strings_updater.StringsUpdater.update_app_name('My App')"
"smali_updater.SmaliUpdater.update_build_config(2, '2.0', 'com.example', 'release')"
"dex_converter.DexConverter.convert_to_dex"
```

> 💡 Arguments support all Python literal types: strings `'hello'`, numbers `42`, booleans `True`, `None`, lists
`[1, 2]`, and dicts `{'key': 'val'}`.

<br/>

**Full example pipeline:**

```json
"pipeline": [
  "_print_header",
  "_print_platform_info",
  "_load_project_config",
  "_load_keystore_config",
  "_find_files",
  "_cleanup_all",
  "_prepare_decompile_directory",
  "_run_apktool_decompile",
  "_count_decompiled_files",
  "_verify_decompile_success",
  "_analyze_apk_structure",
  "abi_filter.ABIFilter.filter",
  "_copy_resources",
  "_update_apktool_yml",
  "_update_build_config",
  "strings_updater.StringsUpdater.update_app_name('My App')",
  "_update_manifest",
  "_build_unsigned_apk",
  "_zipalign_apk",
  "_sign_apk",
  "_verify_signature",
  "_print_final_summary"
]
```

<br/>

### Instance auto-creation

When calling a class method (e.g. `"abi_filter.ABIFilter.filter"`), `PipelineManager` automatically instantiates the
class by mapping common constructor parameter names to build state:

| Constructor parameter | Resolved from                            |
|:----------------------|:-----------------------------------------|
| `modded_dir`          | `build_tool.paths["modded_dir"]`         |
| `android_sdk`         | `build_tool.paths["android_sdk"]`        |
| `paths`               | `build_tool.paths`                       |
| `config`              | `build_tool.config`                      |
| `apktool_jar`         | `build_tool.found_files["apktool_jar"]`  |
| `baksmali_jar`        | `build_tool.found_files["baksmali_jar"]` |
| `source_apk`          | `build_tool.found_files["source_apk"]`   |
| `logger`              | `None` (uses module logger)              |

If a constructor requires a parameter not in this list, pass the arguments directly in the step string:

```json
"my_module.MyClass.my_method('arg1', 'arg2')"
```

Class instances are **cached** — each class is instantiated only once per pipeline run.

<br/>

### Adding your own step

You can extend the pipeline in two ways:

**Option A — method in `main.py`** (classic, has access to full `self` state):

```python
def _my_custom_step(self):
    print("My custom logic!")
    # full access to self.paths, self.config, self.found_files, etc.
```

```json
"pipeline": ["...", "_my_custom_step", "..."]
```

**Option B — standalone module** (reusable, testable independently):

```python
# my_tool.py
class MyTool:
    def __init__(self, modded_dir):  # auto-resolved
        self.modded_dir = modded_dir

    def process(self, mode='fast'):
        print(f"Processing in {mode} mode: {self.modded_dir}")
```

```json
"pipeline": ["...", "my_tool.MyTool.process('thorough')", "..."]
```

<br/>

### Data flow: APK to APK

```
  Source APK
      │
      ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  DECOMPILATION                                               │
  │  apktool d app.apk → smali/ + res/ + AndroidManifest.xml   │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
       ┌─────────────────────────┤
       ▼                         ▼
  ┌─────────────┐         ┌─────────────────────────────────────┐
  │ COMPILATION │         │  MODIFICATION                       │
  │ .java/.kt   │         │  • ManifestUpdater → AndroidManifest│
  │     ↓       │         │  • SmaliUpdater   → BuildConfig     │
  │   javac/    │         │  • StringsUpdater → strings.xml     │
  │   kotlinc   │         │  • YamlUpdater    → apktool.yml     │
  │     ↓       │         │  • ResourceManager→ res/            │
  │   .class    │         │  • ABIFilter      → lib/            │
  │     ↓       │         └─────────────────────────────────────┘
  │    d8/dx    │
  │     ↓       │
  │    .dex     │
  │     ↓       │
  │  baksmali   │
  │     ↓       │
  │   .smali    │
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  BUILD                                                       │
  │  apktool b path/to/output/folder → unsigned.apk             │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  SIGNING                                                     │
  │  zipalign -f -p 4 → aligned.apk                            │
  │  apksigner sign --v1/v2/v3/v4 → MyApp (2.0).apk ✅        │
  └──────────────────────────────────────────────────────────────┘
```

<br/>

### Android SDK auto-detection

If `android_sdk` is `null` in the config, `SDKDetector` searches in the following order:

```
1. Environment variables  →  ANDROID_SDK_ROOT / ANDROID_HOME
2. Standard paths         →  ~/Android/Sdk  (Linux/macOS)
                              %LOCALAPPDATA%\Android\Sdk  (Windows)
3. sdkmanager in PATH     →  resolves SDK location automatically
```

<br/>

### Manifest merging

`ManifestUpdater` performs an intelligent merge of two AndroidManifest.xml files:

```
Original manifest (from APK)       Your manifest (src/)
          │                                 │
          └──────────────┬──────────────────┘
                         ▼
               ┌─────────────────┐
               │ ManifestUpdater │
               └────────┬────────┘
                        │
          ┌─────────────┼──────────────────┐
          ▼             ▼                  ▼
   Replace package  Add permissions   Merge activity /
   throughout the   and features      service / receiver /
   manifest                           provider / meta-data
          │             │                  │
          └─────────────┴──────────────────┘
                        │
                        ▼
              Final manifest ✅
```

<br/>

---

## ⚙️ `build_config.json` Reference

<br/>

### `version` — app version

```json
"version": {
  "code": 2,
  "name": "2.0"
}
```

| Field  | Type  | Description                                                             |
|:-------|:-----:|:------------------------------------------------------------------------|
| `code` | `int` | Numeric version code — updated in `apktool.yml` and `BuildConfig.smali` |
| `name` | `str` | Version string — updated in `apktool.yml` and `BuildConfig.smali`       |

<br/>

### `app` — application info

```json
"app": {
  "name": "My Application",
  "package_id": "com.my.application"
}
```

| Field        | Type  | Description                                                          |
|:-------------|:-----:|:---------------------------------------------------------------------|
| `name`       | `str` | App name — written to `strings.xml`, used as the output APK filename |
| `package_id` | `str` | Package name — replaces the original package throughout the manifest |

<br/>

### `build` — build parameters

```json
"build": {
  "type": "Release",
  "target_dex_index": 2,
  "auto_multidex": false
}
```

| Field              |  Type  | Description                                                                         |
|:-------------------|:------:|:------------------------------------------------------------------------------------|
| `type`             | `str`  | Build type: `Debug` or `Release`                                                    |
| `target_dex_index` | `int`  | Which DEX receives the compiled code (`1` = `smali/`, `2` = `smali_classes2/`, ...) |
| `auto_multidex`    | `bool` | Automatically add `multiDexEnabled=true` when multiple DEX files are present        |

<br/>

### `abi` — architecture filtering

```json
"abi": {
  "keep_only": ["arm64-v8a"],
  "remove_others": true,
  "warn_if_missing": true
}
```

| Field             |  Type  | Description                                     |
|:------------------|:------:|:------------------------------------------------|
| `keep_only`       | `list` | List of ABIs to keep                            |
| `remove_others`   | `bool` | Delete directories of other ABIs                |
| `warn_if_missing` | `bool` | Warn if a requested ABI is not found in the APK |

Supported ABIs: `armeabi` · `armeabi-v7a` · `arm64-v8a` · `x86` · `x86_64` · `mips` · `mips64`

<br/>

### `dex_placement` — DEX placement

```json
"dex_placement": {
  "prefer_existing": true,
  "create_new_if_full": true,
  "max_files_per_dex": 15000,
  "space_threshold": 10000
}
```

| Field                |  Type  | Description                                       |
|:---------------------|:------:|:--------------------------------------------------|
| `prefer_existing`    | `bool` | Prefer existing DEX directories                   |
| `create_new_if_full` | `bool` | Create a new DEX if the current one is full       |
| `max_files_per_dex`  | `int`  | Maximum number of smali files per DEX             |
| `space_threshold`    | `int`  | Free-space threshold for selecting the target DEX |

<br/>

### `paths` — paths

```json
"paths": {
  "tools": {
    "apktool":     "relative/or/absolute/path/to/apktool.jar",
    "baksmali":    "relative/or/absolute/path/to/baksmali.jar",
    "smali":       "relative/or/absolute/path/to/smali.jar",
    "android_sdk": null
  },
  "directories": {
    "original_game": "folder/containing/source/apk",
    "modded":        "folder/for/decompiled/apk",
    "src":           "folder/with/your/source/code"
  },
  "source_structure": {
    "java":       "path/to/java/sources",
    "kotlin":     "path/to/kotlin/sources",
    "res":        "path/to/res",
    "cpp":        "path/to/cpp",
    "manifest":   "path/to/AndroidManifest.xml",
    "cmakelists": "path/to/CMakeLists.txt",
    "assets":     "path/to/assets"
  },
  "output": {
    "build": "path/for/output/files",
    "logs":  "path/for/logs",
    "temp":  "path/for/temp/files"
  },
  "additional_smali_dirs": [],
  "keystore": "keystore.json"
}
```

> **About paths:** every path can be specified **relative to the folder where `build_config.json` is located** (e.g.
`"tools/apktool.jar"`), or as an **absolute path** (e.g. `"C:/Android/apktool.jar"` or
`"/home/user/tools/apktool.jar"`). Both formats work on all platforms.

> If `android_sdk` is `null`, ApkForge will locate the SDK automatically via environment variables and standard
> installation paths.

<br/>

### `pipeline` — step pipeline

```json
"pipeline": [
  "_print_header",
  "_load_project_config",
  "_load_keystore_config",
  "_find_files",
  "_cleanup_all",
  "_run_apktool_decompile",
  "_analyze_apk_structure",
  "abi_filter.ABIFilter.filter",
  "_copy_resources",
  "_update_apktool_yml",
  "_update_build_config",
  "_update_strings",
  "_update_manifest",
  "_build_unsigned_apk",
  "_zipalign_apk",
  "_sign_apk",
  "_verify_signature",
  "_cleanup_temp_files",
  "_print_final_summary"
]
```

Each entry is a step string. Three formats are supported:

| Format                        | Example                                      | Resolves to                          |
|:------------------------------|:---------------------------------------------|:-------------------------------------|
| `"_method"`                   | `"_find_files"`                              | `ApkForge._find_files()`             |
| `"module.function"`           | `"platform_utils.setup_utf8_environment"`    | `setup_utf8_environment()`           |
| `"module.Class.method"`       | `"abi_filter.ABIFilter.filter"`              | `ABIFilter(...).filter()`            |
| `"module.Class.method(args)"` | `"abi_filter.ABIFilter.filter('arm64-v8a')"` | `ABIFilter(...).filter('arm64-v8a')` |

<br/>

### `pipeline_behavior` — error handling

```json
"pipeline_behavior": {
  "stop_on_error":   true,
  "stop_on_warning": false,
  "timeout_seconds": 30
}
```

| Field             |  Type  | Description                                             |
|:------------------|:------:|:--------------------------------------------------------|
| `stop_on_error`   | `bool` | Pause the pipeline on error and ask whether to continue |
| `stop_on_warning` | `bool` | Pause on warning                                        |
| `timeout_seconds` | `int`  | Wait timeout before auto-continuing the pipeline        |

<br/>

---

## 🗺️ Module Map

```
main.py (ApkForge)
│
├── pipeline_manager.py      — resolves & executes any method/function from any .py
├── project_config.py        — load & validate build_config.json
├── path_manager.py          — path resolution, build_config.json lookup
├── sdk_detector.py          — Android SDK auto-detection
│
├── decompiler.py            — APK decompilation (apktool)
├── apk_analyzer.py          — APK DEX structure analysis
│
├── compiler.py              — compilation orchestrator
│   ├── java_compiler.py     — Java compilation (javac)
│   ├── kotlin_compiler.py   — Kotlin compilation (kotlinc)
│   ├── jar_builder.py       — JAR creation and merging
│   ├── dex_converter.py     — JAR → DEX conversion (d8)
│   └── smali_decompiler.py  — DEX → smali decompilation (baksmali)
│
├── cpp_builder.py           — native library build
│   ├── cmake_builder.py     — CMake configure & build
│   ├── native_build_config.py — CMake build parameters
│   ├── library_deployer.py  — deploy .so files to correct ABI dirs
│   └── tool_finder.py       — locate CMake, Ninja, NDK
│
├── abi_filter.py            — ABI directory filtering
├── resource_manager.py      — resource copying and updating
│
├── manifest_manager.py      — AndroidManifest.xml reading
├── manifest_updater.py      — intelligent manifest merging
├── smali_updater.py         — BuildConfig.smali patching
├── strings_updater.py       — strings.xml update
├── yaml_updater.py          — apktool.yml update
│
├── apk_builder.py           — APK reassembly (apktool)
├── apk_signer.py            — signing (v1/v2/v3/v4) and zipalign
│
├── file_finder.py           — locate tools and source APK
├── file_cleaner.py          — temp file cleanup
├── config.py                — keystore.json loading
└── platform_utils.py        — cross-platform utilities
```

> All of the above modules — and any `.py` file you create — can be called directly from the pipeline without touching
`main.py`.

<br/>

---

## 🌍 Environment Variables

Useful for CI/CD — environment variables override values from `build_config.json`:

| Variable                            | Description                     |
|:------------------------------------|:--------------------------------|
| `ANDROID_HOME` / `ANDROID_SDK_ROOT` | Path to Android SDK             |
| `BUILD_VERSION_CODE`                | Override version code           |
| `BUILD_VERSION_NAME`                | Override version name           |
| `BUILD_APP_NAME`                    | Override app name               |
| `BUILD_PACKAGE_ID`                  | Override package name           |
| `BUILD_TYPE`                        | Build type: `Debug` / `Release` |
| `BUILD_TARGET_DEX`                  | Target DEX index                |

<br/>

---

## ❓ FAQ

<details>
<summary><b>APK won't install after rebuilding?</b></summary>

Make sure your `pipeline` contains the steps in the correct order: `_zipalign_apk` → `_sign_apk` → `_verify_signature`.
If you're updating an already-installed app, the signing key must match the one used for the previous version.

</details>

<details>
<summary><b>"No platforms found" error during compilation?</b></summary>

Specify the Android SDK path explicitly in `build_config.json`:

```json
"tools": { "android_sdk": "/path/to/your/android/sdk" }
```

Or set the `ANDROID_HOME` environment variable.

</details>

<details>
<summary><b>How do I keep only 64-bit libraries?</b></summary>

```json
"abi": { "keep_only": ["arm64-v8a"], "remove_others": true }
```

</details>

<details>
<summary><b>How do I inject pre-built smali files without compiling?</b></summary>

Point to the folders containing your `.smali` files in the config:

```json
"paths": { "additional_smali_dirs": ["path/to/my/smali"] }
```

The `_merge_custom_smali` step will copy them into the correct DEX.

</details>

<details>
<summary><b>How do I call a method from another .py file in the pipeline?</b></summary>

Use the `"module.ClassName.method"` format — no registration needed:

```json
"pipeline": [
  "abi_filter.ABIFilter.filter('arm64-v8a')",
  "strings_updater.StringsUpdater.update_app_name('My App')",
  "dex_converter.DexConverter.find_d8",
  "platform_utils.setup_utf8_environment"
]
```

The file just needs to exist on the Python path (same directory as `main.py` is fine). Class instances are created
automatically and cached for the duration of the pipeline run.

</details>

<details>
<summary><b>How do I extend ApkForge with custom logic?</b></summary>

**Option A — add to `main.py`** (full access to build state via `self`):

```python
def _my_step(self):
    print(f"Working in: {self.paths['modded_dir']}")
```

```json
"pipeline": ["...", "_my_step", "..."]
```

**Option B — create a new `.py` file** (reusable, testable):

```python
# my_module.py
class MyTool:
    def __init__(self, modded_dir):
        self.modded_dir = modded_dir

    def run(self, mode='fast'):
        print(f"Running in {mode} mode")
```

```json
"pipeline": ["...", "my_module.MyTool.run('thorough')", "..."]
```

No registration, no imports needed in `main.py`.

</details>

<details>
<summary><b>Where must build_config.json be placed?</b></summary>

Strictly in the root of your project. ApkForge finds it by walking up the directory tree from the location of `main.py`.
The `main.py` file itself can live anywhere — in a subdirectory, alongside the other modules, etc.

</details>

<br/>

---

## 📄 License

Distributed under the **MIT** License. See [LICENSE](LICENSE) for details.

<br/>

---

<div style="text-align: center;">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0a,50:00ff88,100:0a0a0a&height=120&section=footer&animation=fadeIn" width="100%" alt="ApkForge footer wave"/>

Made with ❤️ by [All1eexx](https://github.com/All1eexx)

[![GitHub](https://img.shields.io/badge/GitHub-All1eexx-00ff88?style=for-the-badge&logo=github&logoColor=white&labelColor=0d0d0d)](https://github.com/All1eexx)

⭐ If you find this project useful — drop a star on GitHub!

</div>