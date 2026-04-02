import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from ui.main_window import MainWindow

if __name__ == "__main__":
    app = MainWindow(base_dir=BASE_DIR)
    app.run()
