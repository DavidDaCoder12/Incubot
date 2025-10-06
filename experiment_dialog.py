from PyQt5 import QtWidgets
from PyQt5 import uic
from ui_experiment_dialog import Ui_ExperimentDialog
from presets import PresetManager

class ExperimentDialog(QtWidgets.QDialog, Ui_ExperimentDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.experimentPresetManager = PresetManager(
            self.presetDropDown,
            self.parameterListView,
        )

        self.well_grid = self.wellgridwidget  # promoted in Qt Designer
        
        self.experimentPresetManager.get_selected_buttons = self.well_grid.get_selected_wells
        self.experimentPresetManager.set_selected_buttons = self.well_grid.set_selected_wells

        # Connect save and cancel
        self.buttonSaveExperiment.clicked.connect(self.accept)
        self.buttonCancelExperiment.clicked.connect(self.reject)

    def get_experiment_data(self):
        selected_buttons = []

        # Iterate through all children, filter toggleable buttons
        for button in self.findChildren(QtWidgets.QToolButton):
            if button.isCheckable() and button.isChecked():
                selected_buttons.append(button.objectName())

        return {
            "name": self.lineEditPresetName.text(),
            "selected_buttons": selected_buttons,
            # You can also include brightness/contrast/etc here
        }
    
