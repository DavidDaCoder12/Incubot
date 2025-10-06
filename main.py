from PyQt5 import QtWidgets
from main_window import MainWindow 
import sys
import os

module_path = '/home/ziqiu/Desktop/Incubot Files and Scripts/qtGUI'
if module_path not in sys.path:
    sys.path.append(module_path)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
