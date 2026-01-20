"""
Script to create a desktop shortcut for the Pomodoro app.
"""
import os
import sys
from pathlib import Path

try:
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

def create_shortcut():
    """Create a desktop shortcut for the Pomodoro app."""
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    main_script = script_dir / "main.py"
    python_exe = sys.executable
    
    # Get desktop path
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        # Try common desktop locations
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if not desktop.exists():
            desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    
    shortcut_path = desktop / "Pomodoro Timer.lnk"
    
    if HAS_WIN32:
        # Use Windows COM to create proper shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = python_exe
        shortcut.Arguments = f'"{main_script}"'
        shortcut.WorkingDirectory = str(script_dir)
        shortcut.IconLocation = python_exe
        shortcut.Description = "Pomodoro Timer - Productivity App"
        shortcut.save()
        print(f"Shortcut created successfully at: {shortcut_path}")
    else:
        # Fallback: Create a batch file
        batch_path = desktop / "Pomodoro Timer.bat"
        batch_content = f'''@echo off
cd /d "{script_dir}"
"{python_exe}" "{main_script}"
pause
'''
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        print(f"Batch file created at: {batch_path}")
        print("Note: Install pywin32 for a proper shortcut: pip install pywin32")

if __name__ == "__main__":
    create_shortcut()

