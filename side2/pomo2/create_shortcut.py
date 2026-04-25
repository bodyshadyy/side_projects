"""
Run once to place a Pomodoro Timer shortcut on your Desktop.

    python create_shortcut.py

What this does:
  • Generates a custom tomato-clock icon  (data/pomo.ico)
  • Creates a .lnk that launches via pythonw.exe  (no console window)
"""
import os
import sys
import struct
from pathlib import Path


# ── Icon generation ────────────────────────────────────────────────────────────

def _render_frame(size: int):
    """Draw the app icon at `size` × `size` pixels using PyQt6."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPainter, QColor, QPixmap, QBrush, QPen
    from PyQt6.QtCore import Qt, QRectF, QLineF

    _app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841 — must stay alive

    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))           # transparent background
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s  = float(size)
    cx, cy = s / 2, s / 2

    # Tomato-red outer circle
    p.setBrush(QBrush(QColor("#e53e3e")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(0, 0, s, s))

    # White clock face
    m = s * 0.18
    p.setBrush(QBrush(QColor("#ffffff")))
    p.drawEllipse(QRectF(m, m, s - m * 2, s - m * 2))

    # Clock hands
    pen = QPen(QColor("#2d3748"))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setWidthF(max(1.2, s / 10))
    p.setPen(pen)
    p.drawLine(QLineF(cx, cy, cx, cy - s * 0.27))      # minute -> 12
    pen.setWidthF(max(1.0, s / 13))
    p.setPen(pen)
    p.drawLine(QLineF(cx, cy, cx + s * 0.20, cy))       # hour -> 3

    # Green leaf on top
    p.setBrush(QBrush(QColor("#48bb78")))
    p.setPen(Qt.PenStyle.NoPen)
    lw = s * 0.16
    p.drawEllipse(QRectF(cx - lw / 2, -lw * 0.25, lw, lw * 1.1))

    p.end()
    return pix


def _pixmap_to_ico_chunk(pix, size: int) -> bytes:
    """Convert a QPixmap to raw ICO image data (DIB header + pixels + AND mask)."""
    from PyQt6.QtGui import QImage

    img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)

    # Raw bytes: Qt ARGB32 on little-endian = BGRA in memory (what BMP/ICO expects)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    raw = bytes(ptr)

    # Flip rows top->bottom to bottom->top as required by ICO
    stride = size * 4
    rows_btot = b"".join(raw[r * stride: (r + 1) * stride] for r in range(size - 1, -1, -1))

    # BITMAPINFOHEADER (biHeight doubled: XOR bitmap + AND mask)
    bmi = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2,     # biSize, biWidth, biHeight (×2 for ICO)
        1, 32,                  # biPlanes, biBitCount
        0, 0, 0, 0, 0, 0,       # biCompression…biClrImportant
    )

    # AND mask — all zeros means "fully use the XOR/color bitmap"
    mask_stride = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (mask_stride * size)

    return bmi + rows_btot + and_mask


def build_ico(out_path: Path) -> bool:
    """Generate a multi-size ICO file and write it to `out_path`."""
    try:
        sizes  = [16, 32, 48]
        chunks = [_pixmap_to_ico_chunk(_render_frame(s), s) for s in sizes]

        # ICO file header
        ico = struct.pack("<HHH", 0, 1, len(sizes))

        # Directory entries
        offset = 6 + len(sizes) * 16
        for s, chunk in zip(sizes, chunks):
            ico += struct.pack(
                "<BBBBHHII",
                s, s,           # width, height
                0, 0,           # colorCount, reserved
                1, 32,          # planes, bitCount
                len(chunk),     # sizeInBytes
                offset,         # offsetInBytes
            )
            offset += len(chunk)

        out_path.write_bytes(ico + b"".join(chunks))
        print(f"  Icon  -> {out_path}")
        return True
    except Exception as exc:
        print(f"  Warning: icon generation failed ({exc}); using default Python icon.")
        return False


# ── Launcher detection ─────────────────────────────────────────────────────────

def _find_pythonw() -> str:
    """Return the path to pythonw.exe (no console window) alongside sys.executable."""
    py = Path(sys.executable)
    for directory in [py.parent, *py.parents]:
        pw = directory / "pythonw.exe"
        if pw.exists():
            return str(pw)
    return str(py)   # fallback: regular python.exe (console will appear)


# ── Shortcut creation ──────────────────────────────────────────────────────────

def create_shortcut() -> None:
    script_dir  = Path(__file__).parent.absolute()
    main_script = script_dir / "main.py"
    icon_file   = script_dir / "data" / "pomo.ico"
    pythonw     = _find_pythonw()

    # Locate Desktop
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    shortcut_path = desktop / "Pomodoro Timer.lnk"

    print("Pomodoro Timer - Desktop Shortcut Creator")
    print("-" * 42)

    # Generate icon
    icon_file.parent.mkdir(exist_ok=True)
    has_icon = build_ico(icon_file)
    icon_location = f"{icon_file},0" if has_icon else pythonw

    # Create shortcut
    _write_shortcut(shortcut_path, pythonw, main_script, script_dir, icon_location)

    print(f"  Shortcut -> {shortcut_path}")
    print(f"  Launcher -> {pythonw}")
    print()
    print("Done! Double-click 'Pomodoro Timer' on your Desktop to launch.")


def _write_shortcut(lnk_path, target, args_script, work_dir, icon_location) -> None:
    """Write the .lnk file via win32com or PowerShell fallback."""
    try:
        import win32com.client
        sh  = win32com.client.Dispatch("WScript.Shell")
        lnk = sh.CreateShortCut(str(lnk_path))
        lnk.Targetpath       = target
        lnk.Arguments        = f'"{args_script}"'
        lnk.WorkingDirectory = str(work_dir)
        lnk.IconLocation     = icon_location
        lnk.Description      = "Pomodoro Timer — Productivity App"
        lnk.save()
    except ImportError:
        # Fallback: PowerShell (no extra dependencies needed)
        import subprocess
        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk_path}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.Arguments = \'"{args_script}"\'; '
            f'$s.WorkingDirectory = "{work_dir}"; '
            f'$s.IconLocation = "{icon_location}"; '
            f'$s.Description = "Pomodoro Timer"; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-Command", ps], check=True)


if __name__ == "__main__":
    create_shortcut()
