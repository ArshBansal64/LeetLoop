#!/usr/bin/env python3
"""
Build LeetLoop as a standalone PyInstaller executable.
Usage: python build_scripts/build.py [--output-dir <path>]
"""

import os
import sys
import subprocess
import platform
import argparse
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.parent


def build_executable(output_dir=None):
    """Build the LeetLoop executable using PyInstaller."""
    
    project_root = get_project_root()
    if output_dir is None:
        output_dir = project_root / "dist"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    system = platform.system()
    
    # PyInstaller spec file path
    spec_dir = project_root / "build_scripts"
    
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--distpath", str(output_dir),
        "--workpath", str(project_root / "build"),
        "--specpath", str(spec_dir),
        "--name", "LeetLoop",
        "--onefile",  # Single executable file
        "--icon", str(project_root / "assets" / "icon.ico") if (project_root / "assets" / "icon.ico").exists() else None,
        "--add-data", f"{str(project_root / 'config')}:config",
        "--add-data", f"{str(project_root / 'examples')}:examples",
        "--hidden-import=pytz",
        "--hidden-import=urllib3",
        "--hidden-import=chardet",
        "--hidden-import=idna",
        "--hidden-import=certifi",
        str(project_root / "src" / "app_launcher.py"),
    ]
    
    # Filter out None values
    pyinstaller_args = [arg for arg in pyinstaller_args if arg is not None]
    
    # Platform-specific options
    if system == "Windows":
        pyinstaller_args.extend([
            "--console",  # Console window for Windows
            "--collect-all=tzdata",
        ])
    elif system == "Darwin":  # macOS
        pyinstaller_args.extend([
            "--osx-bundle-identifier=com.leetloop.app",
        ])
    
    print(f"Building LeetLoop for {system}...")
    print(f"Output directory: {output_dir}")
    print()
    
    result = subprocess.run(pyinstaller_args, cwd=str(project_root))
    
    if result.returncode == 0:
        exe_path = output_dir / ("LeetLoop.exe" if system == "Windows" else "LeetLoop")
        print()
        print("=" * 60)
        print("✓ Build successful!")
        print(f"✓ Executable: {exe_path}")
        print("=" * 60)
        return exe_path
    else:
        print()
        print("✗ Build failed!")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build LeetLoop executable")
    parser.add_argument("--output-dir", help="Output directory for executable")
    args = parser.parse_args()
    
    exe = build_executable(args.output_dir)
    sys.exit(0 if exe else 1)
