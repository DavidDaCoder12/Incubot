from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
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
from well_grid_widget import WellGridWidget
import time


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)
        self.wellgridwidget.enable_checking = False
        self.stackedWidget.setCurrentIndex(0)
        
        # Initialize components before calling initUI
        self.camera_preview = CameraPreview(self.cameraView)
        self.camera_actions = CameraActions(self.camera_preview)

        self.preset_manager = PresetManager(
            presetDropDown=self.presetDropDown, 
            parameterListView=self.parameterListView, 
            camera_actions=self.camera_actions
            )
        
        self.camera_actions.set_preset_manager(self.preset_manager)
        
        self.led_control = LedControl()
        self.movement_control = MovementControl(port='/dev/ttyACM0', baudrate=115200)

        # Initialize the ImagingScript object
        self.imaging_script = ImagingScript(
            self.movement_control, 
            self.camera_actions
        )

        self.imaging_worker = None
        # Initialize tilt calibration
        self.tilt_calibration = TiltCalibration()
        self.calibration_z_values = [None, None, None, None]  # Store Z values for 4 corners
        self.calibration_in_progress = False
    
        # Connect calibration buttons once during initialization
        self.setup_calibration_buttons()
        self.initUI()
        

    def initUI(self):
        # Button connections
        self.buttonExperiments.clicked.connect(self.open_experiment_dialog)
        self.buttonBegin.clicked.connect(self.beginButtonClicked)
        self.buttonCancelImaging.clicked.connect(self.cancel_imaging)

        self.next1.clicked.connect(lambda: self.switch_page(2))  # Go to Page 2
        self.back1.clicked.connect(lambda: self.switch_page(0))  # Return to Main Page
        self.next2.clicked.connect(lambda: self.switch_page(3))  # Go to Page 3
        self.back2.clicked.connect(lambda: self.switch_page(1))  # Return to Page 1
        self.next3.clicked.connect(lambda: self.switch_page(4))
        self.back3.clicked.connect(lambda: self.switch_page(2))
        # self.finish.clicked.connect(beginImaging)
        self.back4.clicked.connect(lambda: self.switch_page(3))


        # # Start imaging experiment
        # self.finish.clicked.connect(lambda: )

        self.buttonZoomPos.clicked.connect(lambda: self.camera_actions.zoom_in())
        self.buttonZoomNeg.clicked.connect(lambda: self.camera_actions.zoom_out())
        self.buttonCaptureImg.clicked.connect(lambda: self.camera_actions.capture_image("captured_image.jpg"))
        self.buttonHome.clicked.connect(lambda: self.movement_control.goHome())
        # self.buttonHome.clicked.connect(self.on_home_button_clicked)

        # Movement control
        self.buttonLeft.pressed.connect(lambda: self.movement_control.XNegFine())
        self.buttonRight.pressed.connect(lambda: self.movement_control.XPosFine())
        self.buttonUp.pressed.connect(lambda: self.movement_control.YNegFine())
        self.buttonDown.pressed.connect(lambda: self.movement_control.YPosFine())
        self.buttonZPos.pressed.connect(lambda: self.movement_control.ZPosFine())
        self.buttonZNeg.pressed.connect(lambda: self.movement_control.ZNegFine())

        self.buttonZNegRough.pressed.connect(lambda: self.movement_control.ZNegRough())
        self.buttonZPosRough.pressed.connect(lambda: self.movement_control.ZPosRough())

        self.create_button_map()
        self.connect_buttons()

        # LED controls
        self.buttonRed.clicked.connect(lambda: self.led_control.toggle('red'))
        self.buttonGreen.clicked.connect(lambda: self.led_control.toggle('green'))
        self.buttonBlue.clicked.connect(lambda: self.led_control.toggle('blue'))
        self.buttonWhite.clicked.connect(lambda: self.led_control.toggle('white'))

        # Slider ranges
        self.sliderExposure.setRange(0, 100000)
        self.sliderBrightness.setRange(0, 10) 
        self.sliderContrast.setRange(0, 50) 

        # Connect sliders to camera actions
        self.sliderExposure.valueChanged.connect(lambda value: self.camera_actions.set_exposure(value))
        self.sliderBrightness.valueChanged.connect(lambda value: self.camera_actions.apply_settings(brightness=value / 10))
        self.sliderContrast.valueChanged.connect(lambda value: self.camera_actions.apply_settings(contrast=value / 10))

        # Preset save button
        self.buttonSavePreset.clicked.connect(self.save_current_preset)

        self.wellgridwidget.setup_buttons()
        self.wellgridwidget.set_selected_wells([])
        for btn in self.wellgridwidget.findChildren(QToolButton):
            btn.setCheckable(False)

    def on_home_button_clicked(self):
        """Handle the Home button click: move stage home, then autofocus."""
        print("Returning home and running autofocus...")

        # Move to home position
        self.movement_control.goHome()

        # Give hardware a short pause to finish homing
        time.sleep(1.5)

        # Run autofocus using the camera actions
        try:
            self.camera_actions.auto_focus(
                movement_control=self.movement_control,
                start_z=params.zPos,
                step=0.05,       # step size for Z scanning
                n_steps=8        # number of steps to scan up and down
            )
            print("Autofocus completed.")
        except Exception as e:
            print(f"Autofocus failed: {e}")
    
    def create_button_map(self):
        """
        Creates a dictionary mapping button object names to their index in the coordinate arrays.
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))
        self.button_map = {}

        index = 0
        for row in rows:
            for col in cols:
                button_name = f"button{row}{col}_2"
                self.button_map[button_name] = index
                index += 1

    def connect_buttons(self):
        """
        Connects each well button's clicked signal to the move_to_well method.
        """
        print("Connecting buttons in main window...")
        for button_name, index in self.button_map.items():
            # Get the button object from the UI by its name
            button = getattr(self, button_name, None)
            print(button)
            if button is not None and isinstance(button, QToolButton):
                # print(f"button connected")
                # Connect the button click signal to move_to_well with the corresponding index
                button.clicked.connect(lambda _, i=index: self.movement_control.move_to_well(i))
                print(f"Connected {button_name} to well index {index}")
            else:
                print(f"Warning: {button_name} not found in UI")

    def save_current_preset(self):
        self.preset_manager.save_preset()

    def setup_calibration_buttons(self):
        """
        Set up calibration button connections once during initialization.
        This prevents duplicate connections.
        """
        self.confirmZ1.clicked.connect(lambda: self.store_z_value(0))
        self.confirmZ2.clicked.connect(lambda: self.store_z_value(1))
        self.confirmZ3.clicked.connect(lambda: self.store_z_value(2))
        self.confirmZ4.clicked.connect(lambda: self.store_z_value(3))

    def beginButtonClicked(self):
        """
        Start the calibration process by moving to the first corner.
        """
        print("Begin calibration button clicked")
    
        # Reset calibration values
        self.calibration_z_values = [None, None, None, None]
        self.calibration_in_progress = True
    
        # Switch to first calibration page and move to first corner
        self.switch_page(1)
    
        # Update UI to show which corners need calibration
        self.update_calibration_status()
    
    def open_experiment_dialog(self):
        dialog = ExperimentDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_experiment_data()
            self.preset_manager.save_preset(data["name"], data)
    
    def store_z_value(self, index):
        """
        Store the current Z position for the specified corner.
    
        Parameters:
        -----------
        index : int
            Corner index (0-3)
        """
        if not self.calibration_in_progress:
            print("Calibration not in progress")
            return
    
        # Store current Z position
        self.calibration_z_values[index] = params.zPos
        print(f"✓ Corner {index + 1} Z confirmed: {params.zPos:.4f} mm")
    
        # Update UI to show this corner is confirmed
        self.update_calibration_status()
    
        # Check if all corners are measured
        if all(z is not None for z in self.calibration_z_values):
            self.complete_calibration()

    def update_calibration_status(self):
        """
        Update UI to show which corners have been measured.
        Optional: Add visual indicators on your UI.
        """
        status = []
        corner_names = ["A1 (Top-Left)", "A12 (Top-Right)", "H1 (Bottom-Left)", "H12 (Bottom-Right)"]
    
        for i, z_val in enumerate(self.calibration_z_values):
            if z_val is not None:
                status.append(f"✓ {corner_names[i]}: {z_val:.4f} mm")
            else:
                status.append(f"○ {corner_names[i]}: Not measured")
    
        print("\nCalibration Status:")
        print("\n".join(status))
        print()


    def complete_calibration(self):
        """
        Complete the calibration process by calculating and applying Z corrections.
        """
        print("\n" + "="*50)
        print("COMPLETING CALIBRATION")
        print("="*50)
    
        try:
            # Get corner coordinates
            corner_indices = self.tilt_calibration.get_corner_indices()
            x_arr = [params.x_positions[i] for i in corner_indices]
            y_arr = [params.y_positions[i] for i in corner_indices]
            z_arr = self.calibration_z_values

            # Validate measurements
            is_valid, message = TiltCalibration.validate_corner_measurements(z_arr)
            if not is_valid:
                print(f"✗ Calibration validation failed: {message}")
                # Optionally show error dialog to user
                QtWidgets.QMessageBox.warning(
                    self,
                    "Calibration Validation Failed",
                    f"{message}\n\nPlease restart calibration and check your measurements."
                )
                return

            print(f"✓ Validation passed: {message}")

            # Calculate corrected Z positions
            z_corrected = TiltCalibration.calibrate_z(x_arr, y_arr, z_arr)

            # Apply to parameters
            TiltCalibration.apply_calibration(z_corrected)

            # Optionally save calibration
            TiltCalibration.save_calibration()

            print("="*50)
            print("✓ CALIBRATION COMPLETE")
            print("="*50 + "\n")

            self.calibration_in_progress = False

            # Show success message to user
            QtWidgets.QMessageBox.information(
                self, 
                "Calibration Complete", 
                f"Z-axis calibration successful!\n{message}\n\nReturning to main window."
            )

            # Return to main window (page 0)
            self.switch_page(0)

        except Exception as e:
            print(f"✗ Calibration failed: {e}")
            import traceback
            traceback.print_exc()

            # Show error dialog to user
            QtWidgets.QMessageBox.critical(
                self, 
                "Calibration Error", 
                f"Failed to complete calibration:\n{str(e)}"
            )

    def switch_page(self, page_index):
        """
        Switches to the given page and moves to the appropriate corner well.
        """
        self.stackedWidget.setCurrentIndex(page_index)
    
        corner_indices = self.tilt_calibration.get_corner_indices()
    
        if page_index == 1:  # Corner 1: A1 (top-left)
            self.movement_control.move_to_well(corner_indices[0])
            print(f"Move to Corner 1: Well A1 (index {corner_indices[0]})")

        elif page_index == 2:  # Corner 2: A12 (top-right)
            self.movement_control.move_to_well(corner_indices[1])
            print(f"Move to Corner 2: Well A12 (index {corner_indices[1]})")

        elif page_index == 3:  # Corner 3: H1 (bottom-left)
            self.movement_control.move_to_well(corner_indices[2])
            print(f"Move to Corner 3: Well H1 (index {corner_indices[2]})")

        elif page_index == 4:  # Corner 4: H12 (bottom-right)
            self.movement_control.move_to_well(corner_indices[3])
            print(f"Move to Corner 4: Well H12 (index {corner_indices[3]})")

    def load_previous_calibration(self):
        """
        Attempt to load a previously saved calibration.
        Call this during initialization if you want to restore calibration between sessions.
        """
        if TiltCalibration.load_calibration():
            print("Previous calibration loaded successfully")
            return True
        else:
            print("No previous calibration found or load failed")
            return False
    
    def initialize_imaging_worker(self):
        if self.imaging_worker is not None:
            self.imaging_worker.deleteLater()  # Clean up the old worker
        # Create a new worker instance
        self.imaging_worker = ImagingWorker(self.imaging_script)
        self.imaging_worker.finished.connect(self.on_imaging_finished)
        # self.imaging_worker.errorOccurred.connect(self.on_imaging_error)

    def cancel_imaging(self):
        if self.imaging_worker and self.imaging_worker.isRunning():
            self.imaging_worker.cancel()
            print("Cancel request sent to imaging script.")
        else:
            print("No imaging process to cancel.")

        # if self.autofocus_worker and self.autofocus_worker.isRunning():
        #     self.autofocus_worker.cancel()
        #     print("Cancel request sent to autofocus.")


    def on_imaging_finished(self):
        print("Imaging process completed.")
        self.imaging_worker = None  # Reset the worker

    def on_imaging_error(self, error_message):
        print(f"Imaging error: {error_message}")
        self.imaging_worker = None  # Reset on error

    def update_preview(self):
        print("Begin button clicked")
        self.camera_preview.update_frame()
        

    def closeEvent(self, event):
        # Check if the worker thread is running
        if self.imaging_worker is not None and self.imaging_worker.isRunning():
            print("Stopping worker thread before closing...")
            self.imaging_worker.stop()  # Stop the worker thread
            self.imaging_worker.wait(5000)  # Wait up to 5 seconds for the worker to finish

            # Check if the worker is still running and force terminate if necessary
            if self.imaging_worker.isRunning():
                print("Force terminating the worker thread")
                self.imaging_worker.terminate()
                self.imaging_worker.wait()

        # Safely close other components
        self.movement_control.close()
        self.camera_preview.close()
        self.led_control.cleanup()

        event.accept()
