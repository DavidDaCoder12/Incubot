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

    def beginButtonClicked(self):
        # if not self.imaging_worker.isRunning():

        z_arr = [None,None,None,None]
        self.switch_page(1)  # Go to Page 1

        self.confirmZ1.clicked.connect(lambda: self.store_z_value(0, params.zPos, z_arr))
        self.confirmZ2.clicked.connect(lambda: self.store_z_value(1, params.zPos, z_arr))
        self.confirmZ3.clicked.connect(lambda: self.store_z_value(2, params.zPos, z_arr))
        self.confirmZ4.clicked.connect(lambda: self.store_z_value(3, params.zPos, z_arr))
            
        print("Begin Imaging button clicked") 
        # Wait for finish signal


        # else:
        #     print("Imaging process is already running.")

        #     # Reset the worker if necessary
        #     # self.initialize_imaging_worker()
        #     # self.imaging_worker.start()
    
    def open_experiment_dialog(self):
        dialog = ExperimentDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            data = dialog.get_experiment_data()
            self.preset_manager.save_preset(data["name"], data)
    
    def store_z_value(self, index, value, z_arr):
        z_arr[index] = value
        print(f"Z{index+1} confirmed:", value)

        if all(z is not None for z in z_arr):
            x_arr = [params.x_positions[0], params.x_positions[11], params.x_positions[84], params.x_positions[95]]
            y_arr = [params.y_positions[0], params.y_positions[11], params.y_positions[84], params.y_positions[95]]
            z_corrected = TiltCalibration.calibrate_z(self, x_arr, y_arr, z_arr)
            print("Z plane calibrated")
            print(z_corrected)


    def switch_page(self, page_index):
        """Switches to the given page, updates button states, and moves the CNC head."""
        self.stackedWidget.setCurrentIndex(page_index)

        if page_index == 1:  # Calibration Page 1
            self.movement_control.move_to_well(0)
        elif page_index == 2:  # Calibration Page 2
            self.movement_control.move_to_well(11)
        elif page_index == 3:  # Calibration Page 3
            self.movement_control.move_to_well(84)
        elif page_index == 4:
            self.movement_control.move_to_well(95)


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
