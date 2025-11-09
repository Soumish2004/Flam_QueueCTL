# Building QueueCTL as an Executable

## Prerequisites

Install PyInstaller:
```powershell
pip install pyinstaller
```

---

## Method 1: Simple One-File Executable

Create a single executable file:

```powershell
pyinstaller --onefile --name queuectl queuectl.py
```

**Output:** `dist\queuectl.exe`

**Pros:** Single portable file  
**Cons:** Slower startup (unpacks to temp folder each time)

---

## Method 2: One-Folder Distribution (Recommended)

Create executable with dependencies in a folder:

```powershell
pyinstaller --name queuectl --add-data "queuectl\schema.sql;queuectl" queuectl.py
```

**Output:** `dist\queuectl\` folder with `queuectl.exe` inside

**Pros:** Faster startup  
**Cons:** Multiple files to distribute

---

## Method 3: Advanced Configuration (Best for QueueCTL)

Create a `queuectl.spec` file for better control:

```powershell
# Generate initial spec file
pyi-makespec --name queuectl --add-data "queuectl\schema.sql;queuectl" queuectl.py

# Then build
pyinstaller queuectl.spec
```

### Custom queuectl.spec

Create `queuectl.spec` file:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['queuectl.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('queuectl/schema.sql', 'queuectl'),
        ('queuectl/__init__.py', 'queuectl'),
        ('queuectl/storage.py', 'queuectl'),
        ('queuectl/worker.py', 'queuectl'),
        ('queuectl/worker_manager.py', 'queuectl'),
    ],
    hiddenimports=['click', 'tabulate'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='queuectl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

Build with:
```powershell
pyinstaller queuectl.spec
```

---

## Complete Build Script

Create `build.ps1`:

```powershell
# QueueCTL Build Script

Write-Host "Building QueueCTL executable..." -ForegroundColor Cyan

# Clean previous builds
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "queuectl.spec") { Remove-Item -Force "queuectl.spec" }

# Install PyInstaller if not present
pip install pyinstaller --quiet

# Build executable
Write-Host "`nBuilding..." -ForegroundColor Yellow
pyinstaller --onefile `
    --name queuectl `
    --add-data "queuectl\schema.sql;queuectl" `
    --hidden-import click `
    --hidden-import tabulate `
    queuectl.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Build complete!" -ForegroundColor Green
    Write-Host "Executable: dist\queuectl.exe" -ForegroundColor Green
    
    # Test the executable
    Write-Host "`nTesting executable..." -ForegroundColor Yellow
    .\dist\queuectl.exe --version
    
    Write-Host "`nYou can now distribute dist\queuectl.exe" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}
```

Run:
```powershell
.\build.ps1
```

---

## Testing the Executable

```powershell
# Test basic commands
.\dist\queuectl.exe --help
.\dist\queuectl.exe --version

# Test enqueue
.\dist\queuectl.exe enqueue --id test --command "echo Test"

# Test list
.\dist\queuectl.exe list

# Test worker
.\dist\queuectl.exe worker start --foreground
```

---

## Common Issues & Solutions

### Issue 1: "schema.sql not found"

**Solution:** Use `--add-data` flag:
```powershell
pyinstaller --onefile --add-data "queuectl\schema.sql;queuectl" queuectl.py
```

### Issue 2: Module import errors

**Solution:** Add hidden imports:
```powershell
pyinstaller --onefile --hidden-import click --hidden-import tabulate queuectl.py
```

### Issue 3: Worker subprocess not working

**Solution:** The executable handles this automatically, but ensure workers are spawned correctly.

### Issue 4: Large executable size (~10-15 MB)

**Solution:** This is normal. PyInstaller bundles Python interpreter + dependencies.

To reduce size:
```powershell
# Use UPX compression
pip install pyinstaller[compression]
pyinstaller --onefile --upx-dir C:\upx queuectl.py
```

---

## Distribution

After building, distribute:

### Option 1: Single EXE
```
queuectl.exe  (just this one file)
```

Users can run it directly:
```powershell
.\queuectl.exe --help
```

### Option 2: With Setup Instructions

Create a `INSTALL.txt`:
```
QueueCTL Installation

1. Copy queuectl.exe to any folder (e.g., C:\Tools\)
2. Add to PATH (optional):
   - Windows Settings > System > About > Advanced System Settings
   - Environment Variables > System Variables > Path > Edit > New
   - Add: C:\Tools\

3. Usage:
   queuectl.exe enqueue --id job1 --command "echo Hello"
   queuectl.exe worker start --foreground

Data is stored in: %USERPROFILE%\.queuectl\data\
```

---

## Optional: Create Installer

For professional distribution, use **Inno Setup**:

1. Download: https://jrsoftware.org/isdl.php
2. Create `queuectl-installer.iss`:

```iss
[Setup]
AppName=QueueCTL
AppVersion=1.0.0
DefaultDirName={pf}\QueueCTL
DefaultGroupName=QueueCTL
OutputDir=installer
OutputBaseFilename=QueueCTL-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\queuectl.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\QueueCTL"; Filename: "{app}\queuectl.exe"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Add to PATH
    RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', 
      GetEnv('Path') + ';' + ExpandConstant('{app}'));
  end;
end;
```

3. Compile with Inno Setup Compiler
4. Output: `installer\QueueCTL-Setup.exe`

---

## Summary

**Quickest method:**
```powershell
pip install pyinstaller
pyinstaller --onefile --add-data "queuectl\schema.sql;queuectl" --name queuectl queuectl.py
```

**Output:** `dist\queuectl.exe` - Ready to distribute!

**File size:** ~10-15 MB (includes Python + dependencies)

**Works on:** Any Windows machine (no Python installation needed)
