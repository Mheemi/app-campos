from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QDialog, QSpinBox, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import pyqtSignal, Qt
from db import Producto
from barcode_reader import BarcodeScannerInput
from codigo_barras import procesar_codigo_barras
from movimientos import registrar_movimiento
from peewee import *

class StockTab(QWidget):
    stock_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.producto_actual = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        
        search_layout = QHBoxLayout()
        self.stock_search_entry = QLineEdit()
        self.stock_search_entry.setPlaceholderText("Ingrese código de barras o nombre del producto")
        search_layout.addWidget(self.stock_search_entry)
        self.buscar_stock_btn = QPushButton("Buscar")
        search_layout.addWidget(self.buscar_stock_btn)
        layout.addLayout(search_layout)

        self.stock_tree = QTreeWidget()
        self.stock_tree.setHeaderLabels(['Código de Barras', 'Nombre', 'Precio', 'Stock'])
        layout.addWidget(self.stock_tree)

        self.producto_info = QLabel()
        layout.addWidget(self.producto_info)
        
        button_layout = QHBoxLayout()
        self.sumar_stock_btn = QPushButton("Sumar Stock")
        self.restar_stock_btn = QPushButton("Restar Stock")
        button_layout.addWidget(self.sumar_stock_btn)
        button_layout.addWidget(self.restar_stock_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        
        self.buscar_stock_btn.clicked.connect(self.buscar_producto)
        self.sumar_stock_btn.clicked.connect(lambda: self.ajustar_stock("sumar"))
        self.restar_stock_btn.clicked.connect(lambda: self.ajustar_stock("restar"))
        self.stock_tree.itemClicked.connect(self.on_item_clicked)
    
    def handle_barcode_scan(self, barcode):
        producto = procesar_codigo_barras(barcode)
        if producto:
            self.mostrar_info_producto(producto)
        else:
            QMessageBox.warning(self, "No encontrado", f"No se encontró ningún producto con el código de barras {barcode}")

    def mostrar_info_producto(self, producto):
        if producto is None:
            return  
        
        self.stock_tree.clear()
        item = QTreeWidgetItem(self.stock_tree)
        item.setText(0, producto.codigo_barras)
        item.setText(1, producto.nombre)
        item.setText(2, str(producto.precio))
        item.setText(3, str(producto.stock))
        item.setText(4, producto.id_int or "")
        item.setText(5, producto.id_cr or "")
        item.setText(6, producto.id_t or "")
        self.producto_actual = producto
        
        # Actualizar la información del producto incluyendo los IDs
        info_text = f"Código de Barras: {producto.codigo_barras}\n" \
                    f"Nombre: {producto.nombre}\n" \
                    f"Stock: {producto.stock}\n" \
                    f"Precio: ${producto.precio:.2f}\n" \
                    f"Interior: {producto.id_int or ' '}\n" \
                    f"Casa Repuesto: {producto.id_cr or ' '}\n" \
                    f"Tallerista: {producto.id_t or ' '}"
        self.producto_info.setText(info_text)

    def buscar_producto(self):
        busqueda = self.stock_search_entry.text().strip()
        self.stock_tree.clear()
        
        productos = Producto.select().where(
            (Producto.codigo_barras == busqueda) |
            (fn.LOWER(Producto.nombre).contains(busqueda.lower())) |
            (Producto.id_int == busqueda) |
            (Producto.id_cr == busqueda) |
            (Producto.id_t == busqueda)
        )
        
        if productos.count() > 0:
            for producto in productos:
                item = QTreeWidgetItem(self.stock_tree)
                item.setText(0, producto.codigo_barras)
                item.setText(1, producto.nombre)
                item.setText(2, str(producto.precio))
                item.setText(3, str(producto.stock))
                item.setText(4, producto.id_int or "")
                item.setText(5, producto.id_cr or "")
                item.setText(6, producto.id_t or "")
                item.setData(0, 256, producto)  
            
            self.producto_actual = None
            self.producto_info.clear()
        else:
            QMessageBox.warning(self, "No encontrado", "No se encontraron productos que coincidan con la búsqueda.")
        
    def on_item_clicked(self, item, column):
        producto_seleccionado = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Verificar si el producto seleccionado es diferente al actual
        if producto_seleccionado != self.producto_actual:
            self.producto_actual = producto_seleccionado
            self.mostrar_info_producto(self.producto_actual)
    
    def ajustar_stock(self, operacion):
        if not self.producto_actual:
            QMessageBox.warning(self, "Error", "Por favor, busque un producto primero.")
            return
        
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Ajustar Stock")
            dialog.resize(150,120)
            layout = QVBoxLayout()

            cantidad_spin = QSpinBox()
            cantidad_spin.setRange(1, 1000)
            layout.addWidget(QLabel("Cantidad:"))
            layout.addWidget(cantidad_spin)

            confirmar_btn = QPushButton("Confirmar")
            layout.addWidget(confirmar_btn)

            dialog.setLayout(layout)

            def on_confirmar():
                cantidad = cantidad_spin.value()
                if operacion == "sumar":
                    self.producto_actual.stock += cantidad
                    accion = "sumado"
                else:
                    if self.producto_actual.stock - cantidad < 0:
                        QMessageBox.warning(dialog, "Error", "No hay suficiente stock.")
                        return
                    self.producto_actual.stock -= cantidad
                    accion = "restado"
                
                self.producto_actual.save()
                registrar_movimiento(f'ajuste_stock_{operacion}', self.producto_actual, cantidad, f"Se han {accion} {cantidad} unidades al stock")
                self.mostrar_info_producto(self.producto_actual)  
                self.stock_updated.emit()
                dialog.accept()

            confirmar_btn.clicked.connect(on_confirmar)
            dialog.exec()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Ocurrió un error: {str(e)}")