import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.environment_check import main as check_environment

def main():
    app = QApplication(sys.argv)
    check_environment()  # 检查环境
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()