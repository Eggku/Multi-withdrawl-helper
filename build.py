#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for MultiWithdrawalHelper using PyInstaller.
Generates a single executable file for Windows.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# --- Configuration ---
APP_NAME = "MultiWithdrawalHelper"
APP_VERSION = "1.1.0"  # 2024.06 新版：多交易所、自动识别地址类型、N/N进度、OKX特殊格式、UI优化
MAIN_SCRIPT_NAME = "main_qt.py"
ICON_FILE_NAME = "app.ico"
REQUIREMENTS_FILE_NAME = "requirements.txt"
README_FILE_NAME = f"README_使用说明_{APP_VERSION}.txt"

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT_PATH = SCRIPT_DIR / MAIN_SCRIPT_NAME
ICON_FILE_PATH = SCRIPT_DIR / ICON_FILE_NAME
REQUIREMENTS_FILE_PATH = SCRIPT_DIR / REQUIREMENTS_FILE_NAME

# Output directories
DIST_ROOT_DIR = SCRIPT_DIR / "dist_packages"  # Root for all packaged versions
DIST_APP_DIR = DIST_ROOT_DIR / f"{APP_NAME}_v{APP_VERSION}" # Versioned output directory
BUILD_TEMP_DIR = SCRIPT_DIR / "build_temp"  # PyInstaller temporary work directory
SPEC_FILE_NAME = f"{APP_NAME}.spec"

def run_command(command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Runs a subprocess command and returns exit code, stdout, and stderr."""
    print(f"\nExecuting command: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            cwd=cwd if cwd else SCRIPT_DIR,
            shell=False # Safer, relies on command being in PATH or absolute
        )
        stdout, stderr = process.communicate()
        if stdout:
            print("--- stdout ---")
            print(stdout)
        if stderr and process.returncode != 0 : # Only print stderr if there was an error
            print("--- stderr ---")
            print(stderr)
        return process.returncode, stdout, stderr
    except FileNotFoundError:
        print(f"Error: Command '{command[0]}' not found. Is it in your PATH?")
        return -1, "", f"Command '{command[0]}' not found."
    except Exception as e:
        print(f"An unexpected error occurred while running command: {e}")
        return -1, "", str(e)

def check_and_install_pyinstaller():
    """Checks if PyInstaller is installed, and installs it if not."""
    print("\n--- Checking PyInstaller ---")
    try:
        import PyInstaller
        print(f"PyInstaller found (Version: {PyInstaller.__version__}).")
        return True
    except ImportError:
        print("PyInstaller not found. Attempting to install...")
        ret_code, _, err_msg = run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
        if ret_code == 0:
            print("PyInstaller installed successfully.")
            return True
        else:
            print(f"Failed to install PyInstaller. Error: {err_msg}")
            return False

def install_requirements():
    """Installs dependencies from requirements.txt."""
    print(f"\n--- Checking and Installing Dependencies from {REQUIREMENTS_FILE_NAME} ---")
    if not REQUIREMENTS_FILE_PATH.exists():
        print(f"Warning: {REQUIREMENTS_FILE_NAME} not found. Skipping dependency installation.")
        print("Please ensure all necessary packages (PyQt6, pandas, python-binance, okx, etc.) are installed.")
        return True # Continue build, assuming user managed dependencies

    ret_code, _, err_msg = run_command([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE_PATH)])
    if ret_code == 0:
        print("Dependencies installed/updated successfully.")
        return True
    else:
        print(f"Failed to install dependencies. Error: {err_msg}")
        # Decide if this should be a fatal error
        # return False
        print("Continuing build, but it may fail or the EXE might not work correctly.")
        return True


def clean_previous_build():
    """Removes previous build and distribution directories."""
    print("\n--- Cleaning Previous Build Artifacts ---")
    if BUILD_TEMP_DIR.exists():
        print(f"Removing temporary build directory: {BUILD_TEMP_DIR}")
        shutil.rmtree(BUILD_TEMP_DIR)
    if DIST_APP_DIR.exists(): # Remove specific versioned dist_app_dir
        print(f"Removing previous distribution directory: {DIST_APP_DIR}")
        shutil.rmtree(DIST_APP_DIR)
    # Optionally, clean the .spec file
    spec_file_path = SCRIPT_DIR / SPEC_FILE_NAME
    if spec_file_path.exists():
        print(f"Removing previous spec file: {spec_file_path}")
        os.remove(spec_file_path)

    DIST_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    DIST_APP_DIR.mkdir(parents=True, exist_ok=True)


def create_readme_file():
    """Creates the README.txt file in the distribution directory."""
    print(f"\n--- Creating README File: {README_FILE_NAME} ---")
    readme_path = DIST_APP_DIR / README_FILE_NAME
    content = f"""# {APP_NAME} v{APP_VERSION} - 使用说明

感谢您使用 {APP_NAME}！本工具旨在帮助您更高效地管理和执行在多个交易所的提币操作。

## 主要功能

*   支持多家主流交易所 (Binance, OKX)
*   自动识别地址类型，无需手动选择
*   OKX特殊地址格式（如SOL、SUI等）自动处理
*   进度条与进度标签采用N/N格式显示（如5/100）
*   实时显示提币金额的美元估值（蓝色高亮）
*   支持Excel/CSV格式地址列表导入，支持多列（EVM/SOL/SUI等）
*   自动验证地址格式
*   支持批量提币，可设置提币间隔和大额阈值
*   实时显示等待时间
*   保存多交易所提币历史记录
*   支持大额提币二次确认
*   自动保存上次使用的地址文件
*   "支持开发者"按钮采用蓝色字体，风格统一

## 配置文件与数据存储

*   **配置文件 (`config.ini`)**: 首次运行时，程序会在您的用户文档目录下创建一个名为 `{APP_NAME}` 的文件夹，并在其中生成 `config.ini`。
    *   Windows: `%USERPROFILE%\\Documents\\{APP_NAME}\\config.ini`
    *   macOS/Linux: `~/Documents/{APP_NAME}/config.ini`
*   **日志文件 (`app.log`)**: 操作日志同样存储在上述 `{APP_NAME}` 文件夹内。
*   **设计原因**: 将这些文件存储在用户文档目录是为了避免程序目录的写入权限问题，并确保配置在程序更新或移动后得以保留。

## 首次运行与设置

1.  **启动程序**: 运行 `{APP_NAME}.exe`。
2.  **API密钥配置**:
    *   点击主界面顶部的 **「设置」** 按钮。
    *   为每个计划使用的交易所填入有效的 **API Key**, **API Secret** (OKX还需 **Passphrase**)。
    *   **重要**: 确保API密钥具有"允许提现"的权限。建议配置IP白名单。
    *   保存设置后，程序将尝试连接交易所。状态指示灯会显示连接结果。

## 使用流程简要

1.  **选择交易所**: 从顶部工具栏选择要操作的交易所。
2.  **导入地址**: 点击「导入地址」，选择包含提币地址的 Excel (`.xlsx`) 或 CSV (`.csv`) 文件。
    *   文件可为单列 `address`，也可为多列（EVM/SOL/SUI等），系统自动识别类型。
3.  **参数配置**: 在左侧面板设置提币币种、网络、数量范围和地址处理范围。
4.  **(推荐)** **验证地址**: 点击「验证地址」检查导入地址的格式。
5.  **开始提币**: 点击「开始提币」。请在操作日志区监控进度和结果。
6.  **提币历史**: 点击「历史记录」查看选定币种在交易所的近期提币记录。

## 注意事项

*   **API密钥安全**: 请妥善保管您的API密钥和配置文件。建议为此工具生成专用的、权限严格控制的API密钥。
*   **风险提示**: 自动化提币操作具有风险。请务必先用小额资金进行充分测试。开发者不对因使用本软件直接或间接造成的任何资金损失负责。
*   **OKX特殊格式**: OKX部分币种（如SOL、SUI）需使用"地址:标签"格式，系统已自动处理。

## 更新说明 (v{APP_VERSION})

*   支持多交易所（Binance、OKX）
*   自动识别地址类型，移除手动选择
*   进度条与标签N/N显示
*   OKX特殊地址格式自动处理
*   UI细节优化与风格统一

---
祝您使用愉快！
如有任何问题或建议，请联系开发者。
"""
    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"README 文件已创建: {readme_path}")
    except IOError as e:
        print(f"错误: 创建 README 文件失败: {e}")
        # Non-fatal, build can continue

def build_executable():
    """Builds the executable using PyInstaller."""
    print("\n--- Building Executable with PyInstaller ---")

    if not MAIN_SCRIPT_PATH.exists():
        print(f"Error: Main script '{MAIN_SCRIPT_PATH}' not found. Aborting.")
        return False

    pyinstaller_command = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",  # Use --console for debugging if needed
        "--distpath", str(DIST_APP_DIR),
        "--workpath", str(BUILD_TEMP_DIR),
        "--specpath", str(SCRIPT_DIR), # Place .spec file in script directory
        "--collect-data=PyQt6",      # Let PyInstaller handle PyQt6 files
        "--exclude-module=PyQt5",    # Avoid potential PyQt5 conflicts
        "--log-level=INFO"           # Set a default log level
    ]

    if ICON_FILE_PATH.exists():
        pyinstaller_command.extend(["--icon", str(ICON_FILE_PATH)])
        # Also add as data if QIcon('app.ico') is used directly and --icon is not enough for embedding
        # For --onefile, --icon should embed it. This --add-data might be redundant but often kept.
        pyinstaller_command.extend(["--add-data", f"{str(ICON_FILE_PATH)}{os.pathsep}."])
    else:
        print(f"Warning: Icon file '{ICON_FILE_PATH}' (expected: {ICON_FILE_NAME}) not found. Using default icon.")

    # --- Hidden Imports (Simplified) ---
    # Most hidden imports should be automatically detected by PyInstaller or handled by --collect-data=PyQt6.
    # We will start with a minimal set. If runtime errors occur (e.g., ModuleNotFoundError),
    # specific hidden imports can be added back.
    # Common ones that might still be needed if not picked up:
    hidden_imports = [
        # "pandas._libs.tslibs.np_datetime", # Example if pandas sub-modules are missed
        # "pandas._libs.tslibs.nattype",
        # "pkg_resources.py2_warn" # Sometimes needed for older setuptools/pkg_resources
    ]
    # For now, we try without any explicit hidden imports beyond what --collect-data provides.
    # If your application directly imports modules that PyInstaller misses, add them here.
    # For example, if 'eth_utils' or 'base58' are direct imports and cause issues:
    # hidden_imports.extend(["eth_utils", "base58"])


    for hi in hidden_imports:
        pyinstaller_command.extend(["--hidden-import", hi])

    # --- Add data files for candlelite ---
    try:
        import candlelite 
        import inspect
        candlelite_pkg_dir = Path(inspect.getfile(candlelite)).parent
        candlelite_settings_config_src = candlelite_pkg_dir / "SETTINGS.config"
        if candlelite_settings_config_src.exists():
            pyinstaller_command.extend(["--add-data", f"{str(candlelite_settings_config_src)}{os.pathsep}candlelite"])
            print(f"Found and added to PyInstaller command: {candlelite_settings_config_src} -> candlelite/SETTINGS.config")
        else:
            print(f"Warning: {candlelite_settings_config_src} not found. The application might fail if this file is required by 'candlelite'.")
    except ImportError:
        print("Warning: 'candlelite' package not found by build script. Cannot automatically add its SETTINGS.config.")
    except Exception as e_cl_settings:
        print(f"Warning: Error determining path for candlelite/SETTINGS.config: {e_cl_settings}")
        
    pyinstaller_command.append(str(MAIN_SCRIPT_PATH)) # Main script at the end

    ret_code, out_msg, err_msg = run_command(pyinstaller_command) # Ensure 3 values are unpacked

    if ret_code == 0:
        print(f"PyInstaller build successful. Executable at: {DIST_APP_DIR / (APP_NAME + '.exe')}")
        return True
    else:
        print(f"PyInstaller build failed. Exit code: {ret_code}")
        if "UPX is not available." in err_msg or "UPX is not available." in out_msg: # stdout might also contain it
             print("Note: UPX (executable packer) was not found. The EXE is larger but should still work.")
             print("If you want smaller EXEs, install UPX and ensure it's in your system PATH.")
             # If UPX not found is the *only* error, we might consider it a soft fail or success.
             # For now, any non-zero exit code is a failure.
        return False

def main_build_process():
    """Main function to orchestrate the build process."""
    print(f"========== Starting Build for {APP_NAME} v{APP_VERSION} ==========")
    
    if not check_and_install_pyinstaller():
        sys.exit("PyInstaller is required. Please install it and try again.")

    if not install_requirements():
        # Depending on strictness, you might exit here
        print("Dependency installation issues encountered. Build might be unstable.")
        # sys.exit("Failed to install dependencies.")

    clean_previous_build()

    if build_executable():
        create_readme_file() # Create README only on successful build
        print(f"\n========== Build process completed successfully for {APP_NAME} v{APP_VERSION} ==========")
        print(f"Find your packaged application in: {DIST_APP_DIR.resolve()}")
    else:
        print(f"\n========== Build process failed for {APP_NAME} v{APP_VERSION} ==========")
        sys.exit("Build failed.")

if __name__ == "__main__":
    # Ensure the script's current working directory is its own directory
    # This helps with relative paths for icon, main_script etc.
    os.chdir(SCRIPT_DIR)
    main_build_process() 