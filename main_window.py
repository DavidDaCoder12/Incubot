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
import threading
import sys

def print_all_threads():
    """Print all active threads for debugging"""
    print("\n" + "="*60)
    print("ACTIVE THREADS:")
    print("="*60)
    for thread in threading.enumerate():
        print(f"  Thread: {thread.name}")
        print(f"    Alive: {thread.is_alive()}")
        print(f"    Daemon: {thread.daemon}")
        print(f"    Ident: {thread.ident}")
        print()
    print("="*60 + "\n")

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    # ─── Initialization ───────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # IMMEDIATELY disable checkable on ALL well buttons before anything else
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for row in rows:
            for col in range(1, 13):
                button_name = f"button{row}{col}_2"
                button = getattr(self, button_name, None)
                if button is not None:
                    button.setCheckable(False)
                    button.setChecked(False)
                    button.setDown(False)
                    button.setAutoExclusive(False)
        
        if hasattr(self, 'wellgridwidget'):
            self.wellgridwidget.enable_checking = False
        
        self.stackedWidget.setCurrentIndex(0)

        # Hardware components - START with camera disconnected for safety
        self.camera_preview = CameraPreview(self.cameraView)
        
        # Temporarily disconnect during initialization
        if hasattr(self.camera_preview, 'camera_thread'):
            try:
                self.camera_preview.camera_thread.frame_ready.disconnect()
            except:
                pass
        
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

        # Calibration - UPDATED for manual focus
        self.tilt_calibration = TiltCalibration()
        self.calibration_z_values = {}  # Changed to dict
        self.calibration_in_progress = False
        
        # Manual focus wells (9 strategic points)
        self.focus_wells = [
            0,   # A1 (top-left)
            5,   # A6 (top-center)
            11,  # A12 (top-right)
            42,  # D7 (center-left)
            47,  # D8 (true center)
            53,  # D12 (center-right)
            84,  # H1 (bottom-left)
            89,  # H6 (bottom-center)
            95   # H12 (bottom-right)
        ]
        self.current_focus_index = 0

        self.setup_calibration_buttons()
        self.initUI()
        
        # Reconnect camera after everything is set up
        if hasattr(self.camera_preview, 'camera_thread'):
            try:
                self.camera_preview.camera_thread.frame_ready.connect(
                    self.camera_preview.update_preview
                )
            except:
                pass

    def initUI(self):
        self._connect_navigation()
        self._connect_camera()
        self._connect_movement()
        self._connect_leds()
        self._connect_sliders()

        # Well grid setup
        self.create_button_map()
        self.connect_buttons()

        if hasattr(self, 'wellgridwidget'):
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
        self.buttonBegin.clicked.connect(self.begin_button_clicked)
        self.buttonCancelImaging.clicked.connect(self.cancel_imaging)
        self.back1.clicked.connect(lambda: self.switch_page(0))
        self.back2.clicked.connect(lambda: self.switch_page(1))
        self.back3.clicked.connect(lambda: self.switch_page(2))
        self.back4.clicked.connect(lambda: self.switch_page(3))

    def _connect_camera(self):
        self.buttonZoomPos.clicked.connect(self.camera_actions.zoom_in)
        self.buttonZoomNeg.clicked.connect(self.camera_actions.zoom_out)
        self.buttonCaptureImg.clicked.connect(self.capture_and_save_image)

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
        # Main page sliders
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
        
        # Calibration page sliders - connect to SAME functions AND sync values
        if hasattr(self, 'sliderExposure_5'):
            self.sliderExposure_5.setRange(0, 100000)
            self.sliderExposure_5.valueChanged.connect(self.camera_actions.set_exposure)
            # Sync both sliders
            self.sliderExposure.valueChanged.connect(self.sliderExposure_5.setValue)
            self.sliderExposure_5.valueChanged.connect(self.sliderExposure.setValue)
        
        if hasattr(self, 'sliderBrightness_5'):
            self.sliderBrightness_5.setRange(0, 10)
            self.sliderBrightness_5.valueChanged.connect(
                lambda v: self.camera_actions.apply_settings(brightness=v / 10)
            )
            self.sliderBrightness.valueChanged.connect(self.sliderBrightness_5.setValue)
            self.sliderBrightness_5.valueChanged.connect(self.sliderBrightness.setValue)
        
        if hasattr(self, 'sliderContrast_5'):
            self.sliderContrast_5.setRange(0, 50)
            self.sliderContrast_5.valueChanged.connect(
                lambda v: self.camera_actions.apply_settings(contrast=v / 10)
            )
            self.sliderContrast.valueChanged.connect(self.sliderContrast_5.setValue)
            self.sliderContrast_5.valueChanged.connect(self.sliderContrast.setValue)
        
        # LED slider (add to page_4 in Qt Designer first)
        if hasattr(self, 'sliderLED_5'):
            self.sliderLED_5.setRange(0, 255)
            self.sliderLED_5.setValue(255)
            self.sliderLED_5.valueChanged.connect(self.on_led_brightness_changed)
            self.sliderLED.valueChanged.connect(self.sliderLED_5.setValue)
            self.sliderLED_5.valueChanged.connect(self.sliderLED.setValue)

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
                # Prevent highlighting
                button.setCheckable(False)
                button.setAutoExclusive(False)
                button.setDown(False)
                
                # Connect and immediately clear any pressed state
                def make_click_handler(idx):
                    def handler():
                        self.movement_control.move_to_well(idx)
                        # Reset button appearance after click
                        for btn_name in self.button_map.keys():
                            btn = getattr(self, btn_name, None)
                            if btn:
                                btn.setDown(False)
                    return handler
                
                button.clicked.connect(make_click_handler(index))

    # ─── Calibration ──────────────────────────────────────────────────────────
        
    def setup_calibration_buttons(self):
        """Set up calibration button connections."""
        # confirmZ1 stores Z and moves to next well
        self.confirmZ1.clicked.connect(self.store_z_value_manual)
    
    def begin_button_clicked(self):
        """Start manual focus calibration at 9 strategic wells."""
        from PyQt5.QtWidgets import QApplication
        
        print("\n" + "="*60)
        print("BEGINNING MANUAL FOCUS CALIBRATION")
        print("="*60)
        
        try:
            # Reset calibration
            self.calibration_z_values = {}
            self.calibration_in_progress = True
            self.current_focus_index = 0
            
            print("Calibration variables reset")
            
            # SAFELY switch to calibration page
            # Disconnect camera signal
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.disconnect()
                except:
                    pass
            
            QApplication.processEvents()
            time.sleep(0.1)
            
            # Switch to calibration page
            self.stackedWidget.setCurrentIndex(1)
            
            QApplication.processEvents()
            
            # Reconnect camera signal
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.connect(
                        self.camera_preview.update_preview
                    )
                except:
                    pass
            
            QApplication.processEvents()
            
            # Now move to first focus well
            self.move_to_next_focus_well()
            
        except Exception as e:
            print(f"Error in begin_button_clicked: {e}")
            import traceback
            traceback.print_exc()
            
            # Make sure camera reconnects even on error
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.connect(
                        self.camera_preview.update_preview
                    )
                except:
                    pass

    def move_to_next_focus_well(self):
        """Move to the next well that needs manual focus."""
        from PyQt5.QtWidgets import QApplication
        
        if self.current_focus_index >= len(self.focus_wells):
            self.complete_manual_calibration()
            return
        
        well_idx = self.focus_wells[self.current_focus_index]
        row = well_idx // 12
        col = well_idx % 12
        well_name = f"{chr(65 + row)}{col + 1}"
        
        print(f"\nMoving to focus well {self.current_focus_index + 1}/{len(self.focus_wells)}: {well_name}")
        
        try:
            # Move to well
            self.movement_control.move_to_well(well_idx)
            print(f"Moving to {well_name}, waiting for stage...")
            time.sleep(2.0)
            
            QApplication.processEvents()
            
            # Update label
            if hasattr(self, 'label'):
                self.label.setText(f"Calibration Step {self.current_focus_index + 1}/9 (Well {well_name})")
            
            print(f"Ready for manual focus at {well_name}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


    def store_z_value_manual(self):
        """Store Z value for current focus well and move to next."""
        if not self.calibration_in_progress:
            print("Calibration not in progress")
            return
        
        well_idx = self.focus_wells[self.current_focus_index]
        self.calibration_z_values[well_idx] = params.zPos
        
        row = well_idx // 12
        col = well_idx % 12
        well_name = f"{chr(65 + row)}{col + 1}"
        
        print(f"✓ Well {well_name} (index {well_idx}) Z confirmed: {params.zPos:.4f} mm")
        
        # Move to next well
        self.current_focus_index += 1
        self.move_to_next_focus_well()


    def complete_manual_calibration(self):
        """Complete calibration and return to main page."""
        from PyQt5.QtWidgets import QApplication
        
        print("\n" + "="*60)
        print("COMPLETING MANUAL CALIBRATION")
        print("="*60)
        
        try:
            measured_wells = list(self.calibration_z_values.keys())
            measured_x = [params.x_positions[i] for i in measured_wells]
            measured_y = [params.y_positions[i] for i in measured_wells]
            measured_z = [self.calibration_z_values[i] for i in measured_wells]
            
            print(f"Calibration points: {len(measured_wells)}")
            
            # Fit plane
            z_corrected = TiltCalibration.calibrate_z(measured_x, measured_y, measured_z)
            TiltCalibration.apply_calibration(z_corrected)
            TiltCalibration.save_calibration()
            
            self.calibration_in_progress = False
            
            print("="*60)
            print("✓ MANUAL CALIBRATION COMPLETE")
            print("="*60 + "\n")
            
            # SAFELY return to main page
            print("Returning to main page...")
            
            # Disconnect camera signal
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.disconnect()
                except:
                    pass
            
            QApplication.processEvents()
            time.sleep(0.1)
            
            # Switch page
            self.stackedWidget.setCurrentIndex(0)
            
            QApplication.processEvents()
            
            # Reconnect camera signal
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.connect(
                        self.camera_preview.update_preview
                    )
                except:
                    pass
            
            QApplication.processEvents()
            
            QtWidgets.QMessageBox.information(
                self,
                "Calibration Complete",
                f"Manual focus calibration successful!\n\n"
                f"Focused wells: {len(measured_wells)}\n"
                f"Z plane fitted to all {len(params.z_positions)} wells\n\n"
                f"Ready to begin imaging."
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Calibration Error",
                f"Failed to complete calibration:\n{str(e)}"
            )
            
            # Make sure camera reconnects even on error
            if hasattr(self.camera_preview, 'camera_thread'):
                try:
                    self.camera_preview.camera_thread.frame_ready.connect(
                        self.camera_preview.update_preview
                    )
                except:
                    pass

    def update_calibration_status(self):
        """Print current calibration status."""
        print("\nManual Calibration Status:")
        print(f"  Completed: {len(self.calibration_z_values)}/{len(self.focus_wells)} wells")
        
        for i, well_idx in enumerate(self.focus_wells):
            row = well_idx // 12
            col = well_idx % 12
            well_name = f"{chr(65 + row)}{col + 1}"
            
            if well_idx in self.calibration_z_values:
                z = self.calibration_z_values[well_idx]
                print(f"  ✓ {well_name}: {z:.4f} mm")
            else:
                print(f"  ○ {well_name}: Not measured")
        print()

    def switch_page(self, page_index):
        """Switch to the given page and move stage to the appropriate corner."""
        from PyQt5.QtWidgets import QApplication
    
        self.stackedWidget.setCurrentIndex(page_index)
        QApplication.processEvents()  # Let GUI update
    
        corner_indices = self.tilt_calibration.get_corner_indices()
        corner_names = ["A1", "A12", "H1", "H12"]

        if 1 <= page_index <= 4:
            corner = page_index - 1
        
            # Give a moment for page transition
            time.sleep(0.2)
            QApplication.processEvents()
        
            # Move to corner
            self.movement_control.move_to_well(corner_indices[corner])
            print(f"Move to Corner {corner + 1}: Well {corner_names[corner]} (index {corner_indices[corner]})")
        
            QApplication.processEvents()

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
    
    def capture_and_save_image(self):
        """Capture image with timestamp filename"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        self.camera_actions.capture_image(filename)

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