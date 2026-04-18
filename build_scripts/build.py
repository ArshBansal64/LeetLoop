#!/usr/bin/env python3
"""
Build LeetLoop as a standalone PyInstaller executable.
Usage: python build_scripts/build.py [--output-dir <path>]
"""

import sys
import subprocess
import platform
import argparse
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.parent


def pyinstaller_data_arg(source: Path, dest: str) -> str:
    separator = ";" if platform.system() == "Windows" else ":"
    return f"{source}{separator}{dest}"


def build_executable(output_dir=None):
    """Build the LeetLoop executable using PyInstaller."""

    project_root = get_project_root()
    if output_dir is None:
        output_dir = project_root / "dist"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    system = platform.system()
    spec_dir = project_root / "build_scripts"
    icon_path = project_root / "assets" / "icon.ico"

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(project_root / "build"),
        "--specpath",
        str(spec_dir),
        "--name",
        "LeetLoop",
        "--add-data",
        pyinstaller_data_arg(project_root / "config", "config"),
        "--add-data",
        pyinstaller_data_arg(project_root / "examples", "examples"),
        "--hidden-import=urllib3",
        "--hidden-import=chardet",
        "--hidden-import=idna",
        "--hidden-import=certifi",
        str(project_root / "src" / "app_launcher.py"),
    ]

    if icon_path.exists():
        pyinstaller_args.extend(["--icon", str(icon_path)])

    if system == "Windows":
        pyinstaller_args.extend([
            "--console",
            "--collect-all=tzdata",
        ])
    elif system == "Darwin":
        pyinstaller_args.extend([
            "--osx-bundle-identifier=com.leetloop.app",
        ])

    print(f"Building LeetLoop for {system}...")
    print(f"Output directory: {output_dir}")
    print()

    result = subprocess.run(pyinstaller_args, cwd=str(project_root))

    if result.returncode == 0:
        exe_path = output_dir / "LeetLoop" / ("LeetLoop.exe" if system == "Windows" else "LeetLoop")
        print()
        print("=" * 60)
        print("Build successful!")
        print(f"Executable: {exe_path}")
        print("=" * 60)
        return exe_path

    print()
    print("Build failed!")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build LeetLoop executable")
    parser.add_argument("--output-dir", help="Output directory for executable")
    args = parser.parse_args()

    exe = build_executable(args.output_dir)
    sys.exit(0 if exe else 1)
