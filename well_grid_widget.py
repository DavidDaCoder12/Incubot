from PyQt5.QtWidgets import QWidget, QToolButton
from PyQt5.QtCore import QTimer

class WellGridWidget(QWidget):
    def __init__(self, parent=None, read_only=False, enable_checking=True, highlight_selection=True):
        super().__init__(parent)
        self.read_only = read_only
        self.enable_checking = enable_checking
        self.highlight_selection = highlight_selection  # NEW: controls whether selection is green
        self.selected_buttons = set()

        QTimer.singleShot(0, self.setup_buttons)

    def setup_buttons(self):
        print(f"Setting up buttons in {self.__class__.__name__}... highlight_selection={self.highlight_selection}")
        for btn in self.findChildren(QToolButton):
            btn.setCheckable(self.enable_checking)
            btn.setEnabled(not self.read_only)

            if self.highlight_selection:
                # Used in Experiment window
                btn.setStyleSheet("""
                    QToolButton {
                        background-color: white !important;
                        border: 1px solid #ccc;
                        color: black;
                        cursor: pointer;
                    }
                    QToolButton:hover {
                        background-color: lightblue !important;
                    }
                    QToolButton:checked {
                        background-color: lightgreen !important;
                    }
                """)
            else:
                # Used in Main window — no green highlight
                btn.setStyleSheet("""
                    QToolButton {
                        background-color: white !important;
                        border: 1px solid #ccc;
                        color: black;
                        cursor: pointer;
                    }
                    QToolButton:hover {
                        background-color: lightblue !important;
                    }
                    QToolButton:checked {
                        background-color: lightblue !important;  /* Or same as hover */
                    }
                """)

    def get_selected_wells(self):
        if not self.enable_checking:
            return []
        return [
            btn.objectName()
            for btn in self.findChildren(QToolButton)
            if btn.isCheckable() and btn.isChecked()
        ]

    def set_selected_wells(self, well_names):
        if not self.enable_checking:
            return
        for btn in self.findChildren(QToolButton):
            btn.setChecked(btn.objectName() in well_names)
