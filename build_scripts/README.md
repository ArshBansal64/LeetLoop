# Building LeetLoop Executables

This directory contains scripts for building LeetLoop into standalone executables for distribution.

## Prerequisites

Install build dependencies:

```bash
pip install -r ../requirements-build.txt
```

This installs PyInstaller, which bundles your Python application into a single executable file.

## Building

### Basic Build

```bash
python build.py
```

This creates a standalone executable in `dist/`

- **Windows**: `dist/LeetLoop.exe`
- **macOS**: `dist/LeetLoop`
- **Linux**: `dist/LeetLoop`

### Custom Output Directory

```bash
python build.py --output-dir /path/to/output
```

## What Gets Bundled

The build script automatically includes:

- All Python dependencies from `requirements.txt`
- Configuration templates (`config/`)
- Example files (`examples/`)
- Timezone data (`tzdata`)
- All necessary system libraries

The executable is self-contained and requires no Python installation on the target machine.

## Creating Platform-Specific Installers

Once you have the executable, you can create native installers:

### Windows (.exe installer)

Use NSIS (Nullsoft Scriptable Install System):

1. Install NSIS: https://nsis.sourceforge.io/
2. Create an `.nsi` script (see example below)
3. Run NSIS to generate the installer

Example NSIS script:

```nsis
!include "MUI2.nsh"

Name "LeetLoop"
OutFile "LeetLoop-Installer.exe"
InstallDir "$PROGRAMFILES\LeetLoop"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "dist\LeetLoop.exe"
  CreateDirectory "$SMPROGRAMS\LeetLoop"
  CreateShortcut "$SMPROGRAMS\LeetLoop\LeetLoop.lnk" "$INSTDIR\LeetLoop.exe"
  CreateShortcut "$DESKTOP\LeetLoop.lnk" "$INSTDIR\LeetLoop.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\LeetLoop\LeetLoop.lnk"
  Delete "$DESKTOP\LeetLoop.lnk"
  RMDir "$SMPROGRAMS\LeetLoop"
  Delete "$INSTDIR\LeetLoop.exe"
  RMDir "$INSTDIR"
SectionEnd
```

### macOS (.dmg)

Use macOS native tools:

```bash
# Create the .app bundle
python build.py

# Create a .dmg file
mkdir -p dist/LeetLoop.dmg
hdiutil create -volname "LeetLoop" -srcfolder dist/LeetLoop.app -ov -format UDZO dist/LeetLoop.dmg
```

### Linux (.AppImage or .deb)

Use AppImage or create a .deb package:

```bash
# For AppImage, use appimagetool:
appimagetool dist/LeetLoop.AppDir LeetLoop.AppImage

# For .deb, create the package structure and use dpkg
```

## Troubleshooting

### Build fails with "PyInstaller not found"

```bash
pip install -r requirements-build.txt
```

### Executable is too large

PyInstaller bundles everything needed, including Python. ~80-100MB is typical for a complete application.

### Executable won't start on target machine

- Ensure the machine has compatible architecture (x86_64, Apple Silicon, etc.)
- Check that all dependencies are included in the bundle
- Run `python build.py` on a machine matching your target OS/architecture

### Hidden imports not found

If the executable crashes with missing module errors, add to `build.py`:

```python
pyinstaller_args.extend([
    "--hidden-import=module_name",
])
```

## Distribution

Once you have built executables and installers:

1. Test thoroughly on target machines
2. Upload to GitHub Releases
3. Create installation instructions for users
4. Consider code signing for macOS/Windows for security

## More Information

- PyInstaller documentation: https://pyinstaller.org/
- NSIS documentation: https://nsis.sourceforge.io/
- AppImage documentation: https://appimage.org/
