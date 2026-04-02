import os
import subprocess
import sys


class DymoPrinter:
    @staticmethod
    def list_dymo_printers():
        """Return printer names available via CUPS (macOS/Linux) or Windows."""
        if sys.platform == "win32":
            return DymoPrinter._list_windows_printers()
        # macOS / Linux — use CUPS via lpstat -e (locale-independent)
        try:
            result = subprocess.run(
                ["lpstat", "-e"], capture_output=True, text=True, timeout=3)
            names = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return names or ["(aucune)"]
        except Exception:
            return ["(aucune)"]

    @staticmethod
    def _list_windows_printers():
        """Return all printer names via win32print (Windows only)."""
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            names = [p[2] for p in printers]
            return names or ["(aucune)"]
        except Exception:
            return ["(aucune)"]

    @staticmethod
    def print_label_pdf(pdf_path: str, printer_name: str) -> None:
        """Send a label PDF directly to the printer."""
        if sys.platform == "win32":
            DymoPrinter._win_print(pdf_path, printer_name)
        else:
            # macOS / Linux — CUPS
            # Specify label dimensions and landscape so CUPS does not rotate.
            subprocess.run([
                "lp", "-d", printer_name,
                "-o", "media=Custom.36x89mm",      # portrait feed: 36 mm wide × 89 mm long
                "-o", "orientation-requested=4",   # 4 = landscape → CUPS rotates PDF 90° to fit
                "-o", "fit-to-page",
                pdf_path,
            ], check=True)

    @staticmethod
    def _win_print(pdf_path: str, printer_name: str) -> None:
        """Print a PDF on Windows to a specific printer."""
        # Strategy 1: SumatraPDF (best — silent, respects printer choice)
        sumatra = _find_sumatra()
        if sumatra:
            # Hide the process window completely on Windows
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            subprocess.run(
                [sumatra, "-print-to", printer_name, "-silent",
                 "-print-settings", "fit",
                 pdf_path],
                check=True,
                startupinfo=si,
                creationflags=0x08000000)  # CREATE_NO_WINDOW
            return
        # Strategy 2: win32api ShellExecute "printto" — sends to specific printer
        try:
            import win32api
            win32api.ShellExecute(
                0, "printto", os.path.abspath(pdf_path),
                f'"{printer_name}"', ".", 0)
            return
        except Exception:
            pass
        # Strategy 3: PowerShell — sends to specific printer
        try:
            ps_cmd = (
                f'Start-Process -FilePath "{os.path.abspath(pdf_path)}" '
                f'-Verb PrintTo '
                f'-ArgumentList \\"{printer_name}\\" '
                f'-WindowStyle Hidden -Wait'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=True, timeout=15)
            return
        except Exception:
            pass
        # Last resort: default printer (may not be Dymo)
        os.startfile(os.path.abspath(pdf_path), "print")

    @staticmethod
    def open_pdf_and_print(pdf_path: str) -> None:
        """Open a PDF with the system print dialog (A4)."""
        if sys.platform == "darwin":
            subprocess.run(["open", pdf_path], check=True)
        elif sys.platform == "win32":
            # Open in the default PDF viewer so the user sees the print dialog
            # and can select the correct A4 printer (not the Dymo default).
            os.startfile(os.path.abspath(pdf_path))
        else:
            subprocess.run(["xdg-open", pdf_path], check=True)


def _find_sumatra() -> str | None:
    """Return the path to SumatraPDF.exe: bundled first, then system install."""
    # 1. Bundled inside PyInstaller _MEIPASS temp dir
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        bundled = os.path.join(meipass, 'SumatraPDF.exe')
        if os.path.exists(bundled):
            return bundled
    # 2. Next to the running .exe (dev or portable deploy)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    local = os.path.join(exe_dir, 'SumatraPDF.exe')
    if os.path.exists(local):
        return local
    # 3. Standard system install paths
    for path in [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    ]:
        if os.path.exists(path):
            return path
    return None
