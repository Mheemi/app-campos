from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import pyqtSignal

class BarcodeScannerInput(QLineEdit):
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Escanee un código de barras...")
        self.returnPressed.connect(self.on_barcode_scanned)

    def on_barcode_scanned(self):
        barcode = self.text()
        self.barcode_scanned.emit(barcode)
        self.clear()