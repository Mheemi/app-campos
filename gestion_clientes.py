from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt
from db import Cliente

class GestionClientesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Clientes")
        self.setMinimumWidth(600)
        self.setup_ui()
        self.load_clientes()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Formulario para agregar/editar clientes
        form_layout = QHBoxLayout()
        self.nombre_edit = QLineEdit()
        self.rut_edit = QLineEdit()
        self.direccion_edit = QLineEdit()
        self.telefono_edit = QLineEdit()
        

        form_layout.addWidget(QLabel("Nombre:"))
        form_layout.addWidget(self.nombre_edit)
        form_layout.addWidget(QLabel("RUT:"))
        form_layout.addWidget(self.rut_edit)
        form_layout.addWidget(QLabel("Dirección:"))
        form_layout.addWidget(self.direccion_edit)
        form_layout.addWidget(QLabel("Teléfono:"))
        form_layout.addWidget(self.telefono_edit)
        
        layout.addLayout(form_layout)

        # Botones para agregar y editar
        button_layout = QHBoxLayout()
        self.agregar_btn = QPushButton("Agregar Cliente")
        self.editar_btn = QPushButton("Editar Cliente")
        button_layout.addWidget(self.agregar_btn)
        button_layout.addWidget(self.editar_btn)
        layout.addLayout(button_layout)

        # Lista de clientes
        self.cliente_tree = QTreeWidget()
        self.cliente_tree.setHeaderLabels(["Nombre", "RUT", "Dirección", "Teléfono"])
        layout.addWidget(self.cliente_tree)

        # Conexiones
        self.agregar_btn.clicked.connect(self.agregar_cliente)
        self.editar_btn.clicked.connect(self.editar_cliente)
        self.cliente_tree.itemClicked.connect(self.seleccionar_cliente)

    def load_clientes(self):
        self.cliente_tree.clear()
        for cliente in Cliente.select():
            QTreeWidgetItem(self.cliente_tree, [
                cliente.nombre,
                cliente.rut,
                cliente.direccion or "",
                cliente.telefono or ""
            ])

    def agregar_cliente(self):
        nombre = self.nombre_edit.text()
        rut = self.rut_edit.text()
        direccion = self.direccion_edit.text()
        telefono = self.telefono_edit.text()


        if not nombre or not rut:
            QMessageBox.warning(self, "Error", "Nombre y RUT son obligatorios.")
            return

        try:
            Cliente.create(
                nombre=nombre,
                rut=rut,
                direccion=direccion,
                telefono=telefono,
            
            )
            self.load_clientes()
            self.limpiar_campos()
            QMessageBox.information(self, "Éxito", "Cliente agregado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar el cliente: {str(e)}")

    def editar_cliente(self):
        selected_items = self.cliente_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Por favor, seleccione un cliente para editar.")
            return

        item = selected_items[0]
        rut_original = item.text(1)

        try:
            cliente = Cliente.get(Cliente.rut == rut_original)
            cliente.nombre = self.nombre_edit.text()
            cliente.rut = self.rut_edit.text()
            cliente.direccion = self.direccion_edit.text()
            cliente.telefono = self.telefono_edit.text()
            cliente.save()

            self.load_clientes()
            self.limpiar_campos()
            QMessageBox.information(self, "Éxito", "Cliente actualizado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el cliente: {str(e)}")

    def seleccionar_cliente(self, item):
        self.nombre_edit.setText(item.text(0))
        self.rut_edit.setText(item.text(1))
        self.direccion_edit.setText(item.text(2))
        self.telefono_edit.setText(item.text(3))

    def limpiar_campos(self):
        self.nombre_edit.clear()
        self.rut_edit.clear()
        self.direccion_edit.clear()
        self.telefono_edit.clear()