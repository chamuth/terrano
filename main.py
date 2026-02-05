
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.editor_window import EditorWindow

def main():
    app = QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
