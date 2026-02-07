
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import os

# Check for --no-cuda argument early to configure backend before imports
if "--no-cuda" in sys.argv:
    os.environ["TERRANO_NO_CUDA"] = "1"
    sys.argv.remove("--no-cuda")
    print("Launching with CUDA disabled (CPU only mode).")

from src.ui.editor_window import EditorWindow

def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
