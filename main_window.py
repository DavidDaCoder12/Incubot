from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QToolButton
from ui_mainwindow import Ui_MainWindow
from camera_preview import CameraPreview
from led_control import LedControl
from movement_control import MovementControl
from camera_actions import CameraActions
import parameters as params
from presets import PresetManager
from imaging_script import ImagingScript
from imaging_worker import ImagingWorker
from tilt_calibration import TiltCalibration
from experiment_dialog import ExperimentDialog
import time


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    # ─── Initialization ───────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.wellgridwidget.enable_checking = False
        self.stackedWidget.setCurrentIndex(0)

        # Hardware components
        self.camera_preview = CameraPreview(self.cameraView)
        self.camera_actions = CameraActions(self.camera_preview)
        self.led_control = LedControl()
        self.movement_control = MovementControl(port='/dev/ttyACM0', baudrate=115200)

        # Preset manager
        self.preset_manager = PresetManager(
            presetDropDown=self.presetDropDown,
            parameterListView=self.parameterListView,
            camera_actions=self.camera_actions,
            main_window=self
        )
        self.camera_actions.set_preset_manager(self.preset_manager)

        # Imaging
        self.imaging_script = ImagingScript(self.movement_control, self.camera_actions)
        self.imaging_worker = None

        # Calibration
        self.tilt_calibration = TiltCalibration()
        self.calibration_z_values = [None, None, None, None]
        self.calibration_in_progress = False

        self.setup_calibration_buttons()
        self.initUI()

    def initUI(self):
        self._connect_navigation()
        self._connect_camera()
        self._connect_movement()
        self._connect_leds()
        self._connect_sliders()

        # Well grid setup
        self.create_button_map()
        self.connect_buttons()
        self.wellgridwidget.setup_buttons()
        self.wellgridwidget.set_selected_wells([])
        for btn in self.wellgridwidget.findChildren(QToolButton):
            btn.setCheckable(False)

        # Preset save button
        self.buttonSavePreset.clicked.connect(self.save_current_preset)
        self.buttonExperiments.clicked.connect(self.open_experiment_dialog)

        # Initialize parameter list on boot
        self.preset_manager.update_parameter_list({
            'brightness': params.brightness,
            'contrast': params.contrast,
            'exposure_time': params.exposure_time,
            'led_brightness': self.sliderLED.value()
        })

    # ─── UI Connection Helpers ─────────────────────────────────────────────────

    def _connect_navigation(self):
        self.buttonBegin.clicked.connect(self.beginButtonClicked)
        self.buttonCancelImaging.clicked.connect(self.cancel_imaging)
        self.next1.clicked.connect(lambda: self.switch_page(2))
        self.back1.clicked.connect(lambda: self.switch_page(0))
        self.next2.clicked.connect(lambda: self.switch_page(3))
        self.back2.clicked.connect(lambda: self.switch_page(1))
        self.next3.clicked.connect(lambda: self.switch_page(4))
        self.back3.clicked.connect(lambda: self.switch_page(2))
        self.back4.clicked.connect(lambda: self.switch_page(3))

    def _connect_camera(self):
        self.buttonZoomPos.clicked.connect(self.camera_actions.zoom_in)
        self.buttonZoomNeg.clicked.connect(self.camera_actions.zoom_out)
        self.buttonCaptureImg.clicked.connect(
            lambda: self.camera_actions.capture_image("captured_image.jpg")
        )

    def _connect_movement(self):
        self.buttonHome.clicked.connect(self.movement_control.goHome)
        self.buttonLeft.pressed.connect(self.movement_control.XNegFine)
        self.buttonRight.pressed.connect(self.movement_control.XPosFine)
        self.buttonUp.pressed.connect(self.movement_control.YNegFine)
        self.buttonDown.pressed.connect(self.movement_control.YPosFine)
        self.buttonZPos.pressed.connect(self.movement_control.ZPosFine)
        self.buttonZNeg.pressed.connect(self.movement_control.ZNegFine)
        self.buttonZNegRough.pressed.connect(self.movement_control.ZNegRough)
        self.buttonZPosRough.pressed.connect(self.movement_control.ZPosRough)

    def _connect_leds(self):
        self.led_buttons = {
            'red': self.buttonRed,
            'green': self.buttonGreen,
            'blue': self.buttonBlue,
            'white': self.buttonWhite
        }
        for color, button in self.led_buttons.items():
            button.clicked.connect(lambda _, c=color: self.toggle_led(c))

    def _connect_sliders(self):
        self.sliderExposure.setRange(0, 100000)
        self.sliderBrightness.setRange(0, 10)
        self.sliderContrast.setRange(0, 50)
        self.sliderLED.setRange(0, 255)
        self.sliderLED.setValue(255)

        self.sliderExposure.valueChanged.connect(self.camera_actions.set_exposure)
        self.sliderBrightness.valueChanged.connect(
            lambda v: self.camera_actions.apply_settings(brightness=v / 10)
        )
        self.sliderContrast.valueChanged.connect(
            lambda v: self.camera_actions.apply_settings(contrast=v / 10)
        )
        self.sliderLED.valueChanged.connect(self.on_led_brightness_changed)

    # ─── LED ──────────────────────────────────────────────────────────────────

    def toggle_led(self, color):
        self.led_control.toggle(color)
        for color_name, button in self.led_buttons.items():
            if self.led_control.color_states[color_name]:
                button.setStyleSheet('background-color: lightgreen; border: 1px solid #ccc; color: black;')
            else:
                button.setStyleSheet('')

    def on_led_brightness_changed(self, value):
        self.led_control.set_brightness(value)
        self.preset_manager.update_parameter_list({
            'brightness': params.brightness,
            'contrast': params.contrast,
            'exposure_time': params.exposure_time,
            'led_brightness': value
        })

    # ─── Presets ──────────────────────────────────────────────────────────────

    def save_current_preset(self):
        self.preset_manager.save_preset()

    def open_experiment_dialog(self):
        dialog = ExperimentDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_experiment_data()
            self.preset_manager.save_preset(data["name"], data)

    def update_sliders_from_preset(self, preset_data):
        """Update slider positions to match preset values without triggering camera updates."""
        sliders = {
            'exposure_time': (self.sliderExposure, 1),
            'brightness': (self.sliderBrightness, 10),
            'contrast': (self.sliderContrast, 10),
        }
        for key, (slider, multiplier) in sliders.items():
            if key in preset_data:
                slider.blockSignals(True)
                slider.setValue(int(preset_data[key] * multiplier))
                slider.blockSignals(False)

    # ─── Well Grid ────────────────────────────────────────────────────────────

    def create_button_map(self):
        """Map button names to well coordinate indices."""
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        self.button_map = {
            f"button{row}{col}_2": (row_i * 12) + (col - 1)
            for row_i, row in enumerate(rows)
            for col in range(1, 13)
        }

    def connect_buttons(self):
        """Connect each well button to move_to_well."""
        for button_name, index in self.button_map.items():
            button = getattr(self, button_name, None)
            if button is not None and isinstance(button, QToolButton):
                button.clicked.connect(lambda _, i=index: self.movement_control.move_to_well(i))
            else:
                print(f"Warning: {button_name} not found in UI")

    # ─── Calibration ──────────────────────────────────────────────────────────

    def setup_calibration_buttons(self):
        """Connect calibration buttons once during initialization."""
        for i, btn in enumerate([self.confirmZ1, self.confirmZ2, self.confirmZ3, self.confirmZ4]):
            btn.clicked.connect(lambda _, idx=i: self.store_z_value(idx))

    def beginButtonClicked(self):
        """Start the calibration process."""
        self.calibration_z_values = [None, None, None, None]
        self.calibration_in_progress = True
        self.switch_page(1)
        self.update_calibration_status()

    def store_z_value(self, index):
        """Store the current Z position for the specified corner."""
        if not self.calibration_in_progress:
            print("Calibration not in progress")
            return

        self.calibration_z_values[index] = params.zPos
        print(f"✓ Corner {index + 1} Z confirmed: {params.zPos:.4f} mm")
        self.update_calibration_status()

        if all(z is not None for z in self.calibration_z_values):
            self.complete_calibration()

    def update_calibration_status(self):
        """Print current calibration status."""
        corner_names = ["A1 (Top-Left)", "A12 (Top-Right)", "H1 (Bottom-Left)", "H12 (Bottom-Right)"]
        status = [
            f"{'✓' if z is not None else '○'} {name}: {f'{z:.4f} mm' if z is not None else 'Not measured'}"
            for name, z in zip(corner_names, self.calibration_z_values)
        ]
        print("\nCalibration Status:\n" + "\n".join(status) + "\n")

    def complete_calibration(self):
        """Calculate and apply Z corrections from corner measurements."""
        print("\n" + "="*50 + "\nCOMPLETING CALIBRATION\n" + "="*50)
        try:
            corner_indices = self.tilt_calibration.get_corner_indices()
            x_arr = [params.x_positions[i] for i in corner_indices]
            y_arr = [params.y_positions[i] for i in corner_indices]

            is_valid, message = TiltCalibration.validate_corner_measurements(self.calibration_z_values)
            if not is_valid:
                QtWidgets.QMessageBox.warning(
                    self, "Calibration Validation Failed",
                    f"{message}\n\nPlease restart calibration and check your measurements."
                )
                return

            z_corrected = TiltCalibration.calibrate_z(x_arr, y_arr, self.calibration_z_values)
            TiltCalibration.apply_calibration(z_corrected)
            TiltCalibration.save_calibration()

            self.calibration_in_progress = False
            print("="*50 + "\n✓ CALIBRATION COMPLETE\n" + "="*50)

            QtWidgets.QMessageBox.information(
                self, "Calibration Complete",
                f"Z-axis calibration successful!\n{message}\n\nReturning to main window."
            )
            self.switch_page(0)

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "Calibration Error",
                f"Failed to complete calibration:\n{str(e)}"
            )

    def switch_page(self, page_index):
        """Switch to the given page and move stage to the appropriate corner."""
        self.stackedWidget.setCurrentIndex(page_index)
        corner_indices = self.tilt_calibration.get_corner_indices()
        corner_names = ["A1", "A12", "H1", "H12"]

        if 1 <= page_index <= 4:
            corner = page_index - 1
            self.movement_control.move_to_well(corner_indices[corner])
            print(f"Move to Corner {corner + 1}: Well {corner_names[corner]} (index {corner_indices[corner]})")

    # ─── Imaging ──────────────────────────────────────────────────────────────

    def initialize_imaging_worker(self):
        if self.imaging_worker is not None:
            self.imaging_worker.deleteLater()
        self.imaging_worker = ImagingWorker(self.imaging_script)
        self.imaging_worker.finished.connect(self.on_imaging_finished)

    def cancel_imaging(self):
        if self.imaging_worker and self.imaging_worker.isRunning():
            self.imaging_worker.cancel()
            print("Cancel request sent to imaging script.")
        else:
            print("No imaging process to cancel.")

    def on_imaging_finished(self):
        print("Imaging process completed.")
        self.imaging_worker = None

    def on_imaging_error(self, error_message):
        print(f"Imaging error: {error_message}")
        self.imaging_worker = None

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.imaging_worker is not None and self.imaging_worker.isRunning():
            self.imaging_worker.stop()
            self.imaging_worker.wait(5000)
            if self.imaging_worker.isRunning():
                self.imaging_worker.terminate()
                self.imaging_worker.wait()

        self.movement_control.close()
        self.camera_preview.close()
        self.led_control.cleanup()
        event.accept()