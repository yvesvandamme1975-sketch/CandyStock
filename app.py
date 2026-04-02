import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from ui.main_window import MainWindow
from src.print_server import start_print_server

if __name__ == "__main__":
    # Start embedded print server for the web app (runs in background)
    start_print_server()

    app = MainWindow(base_dir=BASE_DIR)
    app.run()
