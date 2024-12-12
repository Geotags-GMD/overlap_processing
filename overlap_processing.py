
from qgis.PyQt.QtCore import *
from qgis.utils import iface
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
#from .overlap_processing_dialog import OptionSelectionDialog
#import os.path

from .main_script import run_main_script

class OptionSelection:

    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        if not self.action:
            self.action = QAction("Process Building Points in the Overlap", self.iface.mainWindow())
            self.action.triggered.connect(self.run_script)
            self.iface.addPluginToMenu("Processing Overlaps", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("Processing Overlaps", self.action)
            self.action = None

    def run_script(self):
        run_main_script()
