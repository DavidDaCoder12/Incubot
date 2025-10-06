import os
import json
from PyQt5.QtCore import QStringListModel
import parameters as params

class PresetManager:
    def __init__(self, presetDropDown, parameterListView, camera_actions=None):
        self.presetDropDown = presetDropDown
        self.parameterListView = parameterListView
        self.camera_actions = camera_actions

        self.parameterListModel = QStringListModel()
        self.parameterListView.setModel(self.parameterListModel)

        # Get absolute path to 'presets' directory based on this file's location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.preset_dir = os.path.join(base_dir, "presets")
        os.makedirs(self.preset_dir, exist_ok=True)

        self.presetDropDown.currentIndexChanged.connect(self.load_selected_preset)

        self.refresh_presets()


    def get_preset_path(self, name):
        return os.path.join(self.preset_dir, f"preset_{name}.json")

    def get_preset_files(self):
        return [
            f for f in os.listdir(self.preset_dir)
            if f.startswith('preset_') and f.endswith('.json')
        ]

    def refresh_presets(self):
        files = self.get_preset_files()
        preset_names = [f[7:-5] for f in files]  # Strip 'preset_' and '.json'
        self.presetDropDown.clear()
        self.presetDropDown.addItems(preset_names)

    def load_selected_preset(self):
        name = self.presetDropDown.currentText()
        if not name:
            return

        data = self.load_preset_from_file(name)
        if data is None:
            return

        # Load parameters
        params.brightness = data.get('brightness', params.brightness)
        params.contrast = data.get('contrast', params.contrast)
        params.exposure_time = data.get('exposure_time', params.exposure_time)
        if self.camera_actions:
            self.camera_actions.set_brightness(params.brightness)
            self.camera_actions.set_contrast(params.contrast)
            self.camera_actions.set_exposure(params.exposure_time)

        self.update_parameter_list()
        print(f"Loaded preset: {name}")

    def load_preset_from_file(self, name):
        filepath = self.get_preset_path(name)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading preset {name}: {e}")
            return None

    def save_preset_to_file(self, name, data):
        filepath = self.get_preset_path(name)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Preset '{name}' saved successfully.")
            self.refresh_presets()
        except Exception as e:
            print(f"Failed to save preset {name}: {e}")

    def update_parameter_list(self, data=None):
        if not data:
            return

        param_display = []
        if 'brightness' in data:
            param_display.append(f"Brightness: {data['brightness']}")
        if 'contrast' in data:
            param_display.append(f"Contrast: {data['contrast']}")
        if 'exposure_time' in data:
            param_display.append(f"Exposure Time: {data['exposure_time']}")
        if 'selected_buttons' in data:
            param_display.append(f"Selected Buttons: {', '.join(data['selected_buttons'])}")

        self.parameterListModel.setStringList(param_display)
