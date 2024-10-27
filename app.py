import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
QHBoxLayout, QLabel, QPushButton, QLineEdit, QTreeWidget,
QTreeWidgetItem, QFormLayout, QMessageBox, QComboBox, QMenuBar, QDialog, QInputDialog)
from PyQt6.QtGui import QIcon, QAction, QFont,QPalette,QColor
from PyQt6.QtCore import Qt
from peewee import *
from datetime import datetime
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from db import Producto,Cliente
from movimientos import registrar_movimiento, obtener_movimientos, Movimiento, obtener_resumen_anual
from codigo_barras import generar_codigo_ean8, guardar_codigo_ean8_imagen, buscar_producto_por_codigo,procesar_codigo_barras
from stock_tab import StockTab
from barcode_reader import BarcodeScannerInput
from PyQt6.QtWidgets import QFileDialog, QDateEdit
from movimientos import obtener_movimientos, exportar_movimientos_pdf,obtener_ventas_por_mes
from gestion_clientes import GestionClientesDialog



class InventarioApp(QMainWindow):
    def resource_path(self, relative_path):
        
        try:
            
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(os.path.dirname(__file__))
        
        return os.path.join(base_path, relative_path)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TS Inventario")
        self.setGeometry(100, 100, 1000, 600)

        
        try:
            icon_path = self.resource_path("icono.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Error al cargar el icono: {e}")
        
        self.apply_dark_theme()
        self.notebook = QTabWidget()
        self.productos_widget = QWidget() 
        self.productos_layout = QVBoxLayout()  
        self.productos_widget.setLayout(self.productos_layout) 
        self.boleta_widget = QWidget()
        self.movimientos_widget = QWidget()
        self.stock_widget = StockTab()
        self.resumen_anual_widget = QWidget()
        
        self.font_size = 10 
        self.create_widgets()
        self.create_menu_bar()
        self.apply_font()
        self.barcode_input = BarcodeScannerInput()
        self.barcode_input.barcode_scanned.connect(self.handle_barcode_scan)
        self.productos_layout.addWidget(self.barcode_input)
        
    def apply_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))  
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(210, 210, 210))  
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))  
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))  
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(210, 210, 210))  
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(210, 210, 210))  
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))  
        dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(210, 210, 210))  
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))  
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))  
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))  

        self.setPalette(dark_palette)


    def create_menu_bar(self):
        menubar = self.menuBar()
        
        self.menuBar().setStyleSheet("""
            QMenuBar {
                background-color: #2a2a2a;
                color: white;
            }
            QMenuBar::item:selected {
                background-color: #3a3a3a;
            }
        """)
        
        # Menú Archivo
        archivo_menu = menubar.addMenu('Archivo')
        
        boletas_action = QAction('Boletas', self)
        boletas_action.triggered.connect(self.abrir_carpeta_boletas)
        archivo_menu.addAction(boletas_action)
        
        clientes_action = QAction('Gestionar Clientes', self)
        clientes_action.triggered.connect(self.abrir_gestion_clientes)
        archivo_menu.addAction(clientes_action)
        
        barcodes_action = QAction('Códigos de Barras', self)
        barcodes_action.triggered.connect(self.abrir_carpeta_barcodes)
        archivo_menu.addAction(barcodes_action)
        
        # Menú Precios
        precio_menu = menubar.addMenu('Precios')
        
        aumentar_action = QAction('Aumentar Precios', self)
        aumentar_action.triggered.connect(lambda: self.ajustar_precios('aumentar'))
        precio_menu.addAction(aumentar_action)
        
        disminuir_action = QAction('Disminuir Precios', self)
        disminuir_action.triggered.connect(lambda: self.ajustar_precios('disminuir'))
        precio_menu.addAction(disminuir_action)
        
        # Menú Ajustes
        ajustes_menu = menubar.addMenu('Ajustes')
        
        aumentar_fuente_action = QAction('Aumentar Tamaño de Fuente', self)
        aumentar_fuente_action.triggered.connect(lambda: self.ajustar_fuente(1))
        ajustes_menu.addAction(aumentar_fuente_action)
        
        disminuir_fuente_action = QAction('Disminuir Tamaño de Fuente', self)
        disminuir_fuente_action.triggered.connect(lambda: self.ajustar_fuente(-1))
        ajustes_menu.addAction(disminuir_fuente_action)
        
        # Acción Salir
        salir_action = QAction('Salir', self)
        salir_action.triggered.connect(self.close)
        menubar.addAction(salir_action)
    
    def abrir_gestion_clientes(self):
        dialog = GestionClientesDialog(self)
        dialog.exec()

    def handle_barcode_scan(self, barcode):
        producto = procesar_codigo_barras(barcode)
        if producto:
            self.mostrar_info_producto(producto)
        else:
            self.mostrar_mensaje_no_encontrado(barcode)

    def mostrar_info_producto(self, producto):
        self.stock_tree.clear()
        item = QTreeWidgetItem(self.stock_tree)
        item.setText(0, producto.codigo_barras_barras)
        item.setText(1, producto.nombre)
        item.setText(2, str(producto.precio))
        item.setText(3, str(producto.stock))
        item.setText(4, producto.id_int or "")
        item.setText(5, producto.id_cr or "")
        item.setText(6, producto.id_t or "")
        self.producto_actual = producto
        
        self.producto_info.setText(
            f"Código: {producto.codigo_barras_barras}\n"
            f"Nombre: {producto.nombre}\n"
            f"Stock: {producto.stock}\n"
            f"INT: {producto.id_int or 'No asignado'}\n"
            f"CR: {producto.id_cr or 'No asignado'}\n"
            f"T: {producto.id_t or 'No asignado'}"
        )

    def mostrar_mensaje_no_encontrado(self, codigo):
        QMessageBox.warning(self, "Producto no encontrado", f"No se encontró ningún producto con el código {codigo}")

    def abrir_carpeta_boletas(self):
        self.abrir_carpeta('boletas')

    def abrir_carpeta_barcodes(self):
        self.abrir_carpeta('barcodes')

    def abrir_carpeta(self, nombre_carpeta):
        ruta_carpeta = os.path.join(os.getcwd(), nombre_carpeta)
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)
        
        if sys.platform == 'win32':
            os.startfile(ruta_carpeta)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', ruta_carpeta])
        else:  # Linux
            subprocess.call(['xdg-open', ruta_carpeta])

    def ajustar_precios(self, operacion):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{'Aumentar' if operacion == 'aumentar' else 'Disminuir'} Precios")
        layout = QVBoxLayout()

        # Campo para el porcentaje
        porcentaje_layout = QHBoxLayout()
        porcentaje_layout.addWidget(QLabel("Porcentaje:"))
        porcentaje_input = QLineEdit()
        porcentaje_layout.addWidget(porcentaje_input)
        layout.addLayout(porcentaje_layout)

        # Selector de tipo de ID
        tipo_id_layout = QHBoxLayout()
        tipo_id_layout.addWidget(QLabel("Tipo de ID:"))
        tipo_id_combo = QComboBox()
        tipo_id_combo.addItems(["TODOS", "TALLERISTA", "CASA REPUESTO", "INTERIOR"])
        tipo_id_layout.addWidget(tipo_id_combo)
        layout.addLayout(tipo_id_layout)

        # Botones
        button_layout = QHBoxLayout()
        aceptar_btn = QPushButton("Aceptar")
        cancelar_btn = QPushButton("Cancelar")
        button_layout.addWidget(aceptar_btn)
        button_layout.addWidget(cancelar_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        def on_aceptar():
            try:
                porcentaje = float(porcentaje_input.text())
                tipo_id = tipo_id_combo.currentText()
                
                if porcentaje <= 0:
                    raise ValueError("El porcentaje debe ser un número positivo.")
                
                self.aplicar_ajuste_precios(operacion, porcentaje, tipo_id)
                dialog.accept()
            except ValueError as e:
                QMessageBox.critical(dialog, "Error", str(e))

        aceptar_btn.clicked.connect(on_aceptar)
        cancelar_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def actualizar_vistas(self):
        self.cargar_productos()
        if self.notebook.currentWidget() == self.movimientos_widget:
            self.cargar_movimientos()

    def aplicar_ajuste_precios(self, operacion, porcentaje, tipo_id):
        factor = 1 + (porcentaje / 100) if operacion == 'aumentar' else 1 - (porcentaje / 100)
        
        query = Producto.select()
        if tipo_id != "TODOS":
            if tipo_id == "TALLERISTA":
                query = query.where(Producto.id_t == "SI")
            elif tipo_id == "CASA REPUESTO":
                query = query.where(Producto.id_cr == "SI")
            elif tipo_id == "INTERIOR":
                query = query.where(Producto.id_int == "SI")
        
        count = 0
        for producto in query:
            producto.precio = round(producto.precio * factor, 2)
            producto.save()
            registrar_movimiento('ajuste_precio', producto, None,f"Precio {'aumentado' if operacion == 'aumentar' else 'disminuido'} en {porcentaje}% - Tipo ID: {tipo_id}")
            count += 1
        
        self.cargar_productos()  # Actualizar la vista de productos
        QMessageBox.information(self, "Éxito", f"Se han actualizado {count} productos correctamente.")

    def ajustar_fuente(self, delta):
        self.font_size += delta
        self.font_size = max(12, min(self.font_size, 22))  # Limitar el tamaño entre 6 y 20
        self.apply_font()

    def apply_font(self):
        font = QFont()
        font.setPointSize(self.font_size)
        QApplication.setFont(font)
        self.update()
        for widget in self.findChildren(QWidget):
            widget.setFont(font)
            widget.update()

    def create_widgets(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        title_label = QLabel("Taller Sosa")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addWidget(self.notebook)
        
        self.notebook.addTab(self.productos_widget, "Productos")
        self.notebook.addTab(self.stock_widget, "Stock")
        self.notebook.addTab(self.boleta_widget, "Boleta")
        self.notebook.addTab(self.movimientos_widget, "Movimientos")
        self.notebook.addTab(self.resumen_anual_widget, "Resumen Anual")
        
        self.crear_widgets_productos()
        self.crear_widgets_boleta()
        self.crear_widgets_movimientos()
        self.crear_widgets_resumen_anual()
        
        self.stock_widget.stock_updated.connect(self.actualizar_vistas)
        
        # Ajustar el estilo de los QLineEdit
        for entry in self.entries.values():
            entry.setStyleSheet("""
                QLineEdit {
                    background-color: #2a2a2a;
                    color: white;
                    border: 1px solid #3a3a3a;
                    padding: 5px;
                }
            """)

        # Ajustar el estilo de los QPushButton
        for button in [self.agregar_btn, self.editar_btn, self.eliminar_btn, self.limpiar_btn]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)

        # Ajustar el estilo del QTreeWidget
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2a2a2a;
                color: white;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #3a3a3a;
            }
        """)

    def crear_widgets_productos(self):
        self.productos_layout

        form_layout = QFormLayout()
        self.entries = {}
        campos = [ 
            ("Cód de Barras", "codigo_barras"), 
            ("Nombre", "nombre"), 
            ("Precio", "precio"),
            ("INTERIOR", "id_int"),
            ("CASA REPUESTO", "id_cr"),
            ("TALLERISTA", "id_t")
        ]

        for label_text, field_name in campos:
            label = QLabel(label_text)
            entry = QLineEdit()
            entry.setFixedWidth(220)  
            self.entries[field_name] = entry
            form_layout.addRow(label, entry)
        self.productos_layout.addLayout(form_layout)

        # Botones
        button_layout = QHBoxLayout()
        self.agregar_btn = QPushButton("Agregar")
        self.editar_btn = QPushButton("Editar")
        self.eliminar_btn = QPushButton("Eliminar")
        self.limpiar_btn = QPushButton("Limpiar")
        
        button_layout.addWidget(self.agregar_btn)
        button_layout.addWidget(self.editar_btn)
        button_layout.addWidget(self.eliminar_btn)
        button_layout.addWidget(self.limpiar_btn)
        self.productos_layout.addLayout(button_layout)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Cód de barras', 'Nombre', 'Precio', 'Stock', 'INTERIOR', 'CASA REPUESTO', 'TALLERISTA'])
        self.productos_layout.addWidget(self.tree)

        # Campo de búsqueda
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar:"))
        self.search_entry = QLineEdit()
        search_layout.addWidget(self.search_entry)
        self.productos_layout.addLayout(search_layout)

        # Conexiones de señales y slots
        self.agregar_btn.clicked.connect(self.agregar_producto)
        self.editar_btn.clicked.connect(self.editar_producto)
        self.eliminar_btn.clicked.connect(self.eliminar_producto)
        self.limpiar_btn.clicked.connect(self.limpiar_formulario)
        self.tree.itemSelectionChanged.connect(self.item_seleccionado)
        self.search_entry.textChanged.connect(self.buscar_producto_en_lista)
        self.cargar_productos()
    
    def buscar_producto_en_lista(self):
        busqueda = self.search_entry.text().strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if busqueda in item.text(1).lower() or busqueda in item.text(0).lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def crear_widgets_boleta(self):
        boleta_layout = QVBoxLayout()
        self.boleta_widget.setLayout(boleta_layout)
        
        # Selector de cliente
        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        self.cliente_combo = QComboBox()
        cliente_layout.addWidget(self.cliente_combo)
        self.actualizar_cliente_btn = QPushButton("Actualizar Clientes")
        cliente_layout.addWidget(self.actualizar_cliente_btn)
        boleta_layout.addLayout(cliente_layout)
        
        # Campo de búsqueda unificado para la boleta
        self.boleta_search_entry = QLineEdit()
        self.boleta_search_entry.setPlaceholderText("Buscar por código, nombre o escanear cod de barras")
        boleta_layout.addWidget(self.boleta_search_entry)

        # Campo para la cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_layout.addWidget(QLabel("Cantidad:"))
        self.boleta_cantidad_entry = QLineEdit()
        self.boleta_cantidad_entry.setFixedWidth(100)
        cantidad_layout.addWidget(self.boleta_cantidad_entry)
        self.agregar_a_boleta_btn = QPushButton("Agregar")
        self.agregar_a_boleta_btn.setFixedWidth(80)
        cantidad_layout.addWidget(self.agregar_a_boleta_btn)
        boleta_layout.addLayout(cantidad_layout)

        # TreeWidget para la boleta
        self.boleta_tree = QTreeWidget()
        self.boleta_tree.setHeaderLabels(['Código', 'Nombre', 'Precio', 'Cantidad', 'Subtotal'])
        boleta_layout.addWidget(self.boleta_tree)

        # Widgets para acciones de la boleta
        action_layout = QHBoxLayout()
        self.total_label = QLabel("Total: $0.00")
        action_layout.addWidget(self.total_label)
        self.generar_boleta_btn = QPushButton("Generar Boleta")
        action_layout.addWidget(self.generar_boleta_btn)
        self.limpiar_boleta_btn = QPushButton("Limpiar Boleta")
        action_layout.addWidget(self.limpiar_boleta_btn)
        boleta_layout.addLayout(action_layout)

        # Conexiones
        self.boleta_search_entry.returnPressed.connect(self.buscar_producto_boleta)
        self.actualizar_cliente_btn.clicked.connect(self.actualizar_clientes_combo)
        self.agregar_a_boleta_btn.clicked.connect(self.agregar_a_boleta)
        self.generar_boleta_btn.clicked.connect(self.generar_boleta)
        self.limpiar_boleta_btn.clicked.connect(self.limpiar_boleta)
        
        self.actualizar_clientes_combo()

    def actualizar_clientes_combo(self):
        self.cliente_combo.clear()
        for cliente in Cliente.select():
            self.cliente_combo.addItem(f"{cliente.nombre} - {cliente.rut}", cliente.id)

    def handle_boleta_barcode_scan(self, barcode):
        producto = procesar_codigo_barras(barcode)
        if producto:
            # Autocompletar el código del producto
            self.boleta_codigo_entry.setText(producto.codigo_barras)
            # Enfocar en el campo de cantidad
            self.boleta_cantidad_entry.setFocus()
            self.boleta_cantidad_entry.selectAll()
        else:
            QMessageBox.warning(self, "No encontrado", f"No se encontró ningún producto con el código {barcode}")

    def crear_widgets_movimientos(self):
        movimientos_layout = QVBoxLayout()
        self.movimientos_widget.setLayout(movimientos_layout)

        # Widgets para el filtro de fechas
        filtro_layout = QHBoxLayout()
        self.fecha_inicio = QDateEdit()
        self.fecha_fin = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_fin.setCalendarPopup(True)
        filtro_layout.addWidget(QLabel("Fecha inicio:"))
        filtro_layout.addWidget(self.fecha_inicio)
        filtro_layout.addWidget(QLabel("Fecha fin:"))
        filtro_layout.addWidget(self.fecha_fin)
        self.filtrar_btn = QPushButton("Filtrar")
        filtro_layout.addWidget(self.filtrar_btn)
        movimientos_layout.addLayout(filtro_layout)

        # TreeWidget para los movimientos
        self.movimientos_tree = QTreeWidget()
        self.movimientos_tree.setHeaderLabels(['Fecha', 'Tipo', 'Producto', 'Cantidad', 'Detalles'])
        movimientos_layout.addWidget(self.movimientos_tree)

        # Botones para actualizar y exportar
        botones_layout = QHBoxLayout()
        self.actualizar_movimientos_btn = QPushButton("Actualizar Movimientos")
        self.exportar_pdf_btn = QPushButton("Exportar a PDF")
        botones_layout.addWidget(self.actualizar_movimientos_btn)
        botones_layout.addWidget(self.exportar_pdf_btn)
        movimientos_layout.addLayout(botones_layout)

        # Conexiones
        self.filtrar_btn.clicked.connect(self.filtrar_movimientos)
        self.actualizar_movimientos_btn.clicked.connect(self.cargar_movimientos)
        self.exportar_pdf_btn.clicked.connect(self.exportar_movimientos_pdf)

        # Cargar movimientos iniciales
        self.cargar_movimientos()

    def crear_widgets_resumen_anual(self):
        layout = QVBoxLayout()
        self.resumen_anual_widget.setLayout(layout)

        # Selector de año
        año_actual = datetime.now().year
        self.año_selector = QComboBox()
        self.año_selector.addItems([str(año) for año in range(año_actual - 5, año_actual + 1)])
        self.año_selector.setCurrentText(str(año_actual))
        layout.addWidget(self.año_selector)

        # Botón para actualizar
        self.actualizar_resumen_btn = QPushButton("Actualizar Resumen")
        layout.addWidget(self.actualizar_resumen_btn)

        # TreeWidget para el resumen
        self.resumen_tree = QTreeWidget()
        self.resumen_tree.setHeaderLabels(['Mes', 'Total Vendido', 'Total Ingresos ($)', 'Total Ingresado'])
        layout.addWidget(self.resumen_tree)

        # Conexiones
        self.actualizar_resumen_btn.clicked.connect(self.cargar_resumen_anual)
        self.año_selector.currentTextChanged.connect(self.cargar_resumen_anual)
        self.cargar_resumen_anual()

    def filtrar_movimientos(self):
        fecha_inicio = self.fecha_inicio.date().toPyDate()
        fecha_fin = self.fecha_fin.date().toPyDate()
        self.cargar_movimientos(fecha_inicio, fecha_fin)   

    def cargar_movimientos(self, fecha_inicio=None, fecha_fin=None):
        self.movimientos_tree.clear()
        for movimiento in obtener_movimientos(fecha_inicio, fecha_fin):
            self.movimientos_tree.addTopLevelItem(QTreeWidgetItem([
                movimiento.fecha.strftime("%Y-%m-%d %H:%M:%S"),
                movimiento.tipo,
                movimiento.producto.nombre,
                str(movimiento.cantidad) if movimiento.cantidad else "",
                movimiento.detalles or ""
            ]))

    def exportar_movimientos_pdf(self):
        fecha_inicio = self.fecha_inicio.date().toPyDate()
        fecha_fin = self.fecha_fin.date().toPyDate()
        movimientos = obtener_movimientos(fecha_inicio, fecha_fin)
        
        nombre_archivo, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "", "PDF Files (*.pdf)")
        
        if nombre_archivo:
            if not nombre_archivo.endswith('.pdf'):
                nombre_archivo += '.pdf'
            exportar_movimientos_pdf(movimientos, nombre_archivo)
            QMessageBox.information(self, "Éxito", f"El reporte ha sido guardado como {nombre_archivo}")

    def cargar_resumen_anual(self):
        año_seleccionado = int(self.año_selector.currentText())
        resumen = obtener_resumen_anual(año_seleccionado)
        self.resumen_tree.clear()
        for dato in resumen:
            self.resumen_tree.addTopLevelItem(QTreeWidgetItem([
                dato['mes'],
                str(dato['total_vendido']),
                f"${dato['total_ingresos']:.2f}",
                str(dato['total_ingresado'])
            ]))        

    def agregar_producto(self):
        if self.validar_entrada():
            try:
                codigo_barras = self.entries['codigo_barras'].text()
                nombre = self.entries['nombre'].text()
                precio = float(self.entries['precio'].text())
                id_int = self.entries['id_int'].text()
                id_cr = self.entries['id_cr'].text()
                id_t = self.entries['id_t'].text()
                
                producto = Producto.create(
                    codigo_barras=codigo_barras, 
                    nombre=nombre, 
                    precio=precio,
                    id_int=id_int,
                    id_cr=id_cr,
                    id_t=id_t,
                    stock=0  # Agregamos el stock inicial
                )
                registrar_movimiento('ingreso', producto, 0, f"Producto agregado con stock inicial de 0")
                
                self.tree.addTopLevelItem(QTreeWidgetItem([
                    producto.codigo_barras, 
                    producto.nombre, 
                    str(producto.precio), 
                    str(producto.stock),
                    producto.id_int or "",
                    producto.id_cr or "",
                    producto.id_t or ""
                ]))
                self.limpiar_formulario()
                QMessageBox.information(self, "Éxito", "Producto agregado correctamente con stock inicial de 0.")
            
                if self.notebook.currentWidget() == self.movimientos_widget:
                    self.cargar_movimientos()
            except IntegrityError:
                QMessageBox.critical(self, "Error", "Error de integridad en la base de datos. El código de barras ya existe.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ha ocurrido un error inesperado: {str(e)}")

    def validar_entrada(self):
        try:
            codigo_barras = self.entries['codigo_barras'].text()
            nombre = self.entries['nombre'].text()
            precio = self.entries['precio'].text()
            
            if not codigo_barras:
                raise ValueError("El código de barras del producto no puede estar vacío.")

            if not nombre:
                raise ValueError("El nombre del producto no puede estar vacío.")

            if not precio:
                raise ValueError("El precio no puede estar vacío.")

            # Validar que el precio sea un número positivo
            precio_float = float(precio)
            if precio_float <= 0:
                raise ValueError("El precio debe ser un número positivo.")

            return True
        except ValueError as e:
            QMessageBox.critical(self, "Error de validación", str(e))
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ha ocurrido un error inesperado: {str(e)}")
            return False

    def editar_producto(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un producto para editar.")
            return

        if self.validar_entrada():
            try:
                codigo_barras = self.entries['codigo_barras'].text()
                nombre = self.entries['nombre'].text()
                precio = float(self.entries['precio'].text())
                id_int = self.entries['id_int'].text()
                id_cr = self.entries['id_cr'].text()
                id_t = self.entries['id_t'].text()
                
                producto = Producto.get(Producto.codigo_barras == codigo_barras)
                detalles = f"Editado - Anterior: Nombre={producto.nombre}, Precio={producto.precio}, Código de Barras={producto.codigo_barras}"
                
                producto.nombre = nombre
                producto.precio = precio
                producto.id_int = id_int
                producto.id_cr = id_cr
                producto.id_t = id_t
                producto.fecha_modificacion = datetime.now()
                producto.save()
                
                registrar_movimiento('edicion', producto, None, detalles)

                item = selected_items[0]
                item.setText(0, codigo_barras)
                item.setText(1, nombre)
                item.setText(2, str(precio))
                item.setText(3, str(producto.stock))
                item.setText(4, id_int)
                item.setText(5, id_cr)
                item.setText(6, id_t)

                self.limpiar_formulario()
                QMessageBox.information(self, "Éxito", "Producto actualizado correctamente.")
            except Producto.DoesNotExist:
                QMessageBox.critical(self, "Error", "El producto no existe.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ha ocurrido un error inesperado: {str(e)}")

    def eliminar_producto(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un producto para eliminar.")
            return

        if QMessageBox.question(self, "Confirmar", "¿Está seguro de que desea eliminar este producto?", 
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                codigo_barras = selected_items[0].text(0)
                producto = Producto.get(Producto.codigo_barras == codigo_barras)
                registrar_movimiento('eliminacion', producto, producto.stock, f"Eliminado - Stock={producto.stock}")
                producto.delete_instance()
                
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(selected_items[0]))
                self.limpiar_formulario()
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente.")
                
            except Producto.DoesNotExist:
                QMessageBox.critical(self, "Error", "El producto no existe.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ha ocurrido un error inesperado: {str(e)}")

    def limpiar_formulario(self):
        for entry in self.entries.values():
            entry.clear()
        self.tree.clearSelection()

    def item_seleccionado(self):
        selected_items = self.tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            for i, campo in enumerate(self.entries.keys()):
                self.entries[campo].setText(item.text(i))

    def cargar_productos(self):
        self.tree.clear()
        for producto in Producto.select():
            self.tree.addTopLevelItem(QTreeWidgetItem([
                producto.codigo_barras, 
                producto.nombre, 
                str(producto.precio),
                str(producto.stock),  # Movemos el stock a su posición correcta
                producto.id_int or "",
                producto.id_cr or "",
                producto.id_t or ""
            ]))

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
                item.setData(0, 256, producto)  # Guardar el objeto producto en el item
            
            self.producto_actual = None
            self.stock_widget.buscar_producto()
            self.producto_info.clear()
        else:
            QMessageBox.warning(self, "No encontrado", "No se encontraron productos que coincidan con la búsqueda.")

    def buscar_producto_boleta(self):
        busqueda = self.boleta_search_entry.text().strip()
        try:
            producto = Producto.get(
                (Producto.codigo_barras == busqueda) | 
                (fn.LOWER(Producto.nombre) == busqueda.lower())
            )
            self.boleta_search_entry.setText(producto.nombre)
            self.boleta_cantidad_entry.setFocus()
        except Producto.DoesNotExist:
            QMessageBox.warning(self, "No encontrado", "No se encontró ningún producto con la búsqueda proporcionada.")

    def agregar_a_boleta(self):
        nombre_producto = self.boleta_search_entry.text()
        cantidad = self.boleta_cantidad_entry.text()

        try:
            producto = Producto.get(Producto.nombre == nombre_producto)
            
            if not cantidad:
                raise ValueError("Por favor, ingrese la cantidad")
            
            cantidad = int(cantidad)
            
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor que cero")
            
            if cantidad > producto.stock:
                raise ValueError(f"Stock insuficiente. Stock actual: {producto.stock}")
            
            subtotal = producto.precio * cantidad
            
            self.boleta_tree.addTopLevelItem(QTreeWidgetItem([producto.codigo_barras, producto.nombre, str(producto.precio), str(cantidad), str(subtotal)]))
            
            self.actualizar_total_boleta()
            self.boleta_search_entry.clear()
            self.boleta_cantidad_entry.clear()
            self.boleta_search_entry.setFocus()
        except Producto.DoesNotExist:
            QMessageBox.critical(self, "Error", "Producto no encontrado")
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    def actualizar_total_boleta(self):
        total = sum(float(self.boleta_tree.topLevelItem(i).text(4)) for i in range(self.boleta_tree.topLevelItemCount()))
        self.total_label.setText(f"Total: ${total:.2f}")

    def generar_boleta(self):
        try:
            items = [[self.boleta_tree.topLevelItem(i).text(j) for j in range(5)] 
                    for i in range(self.boleta_tree.topLevelItemCount())]
            total = self.total_label.text().split(":")[1].strip()
            
            if not os.path.exists('boletas'):
                os.makedirs('boletas')
            
            fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f'boletas/boleta_{fecha_actual}.pdf'

            doc = SimpleDocTemplate(nombre_archivo, pagesize=letter, 
                                topMargin=50, bottomMargin=50, 
                                leftMargin=50, rightMargin=50)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            
            try:
                # Usar resource_path para el logo
                logo_path = self.resource_path("logo-pdf.png")
                if os.path.exists(logo_path):
                    logo = Image(logo_path, width=80, height=80)
                    logo_legend_style = ParagraphStyle(
                        'LogoLegend',
                        parent=styles['Normal'],
                        fontSize=8,
                        alignment=TA_CENTER,
                        fontName="Helvetica-Bold",
                        textColor=colors.black
                    )
                    logo_legend = Paragraph("Taller Sosa", logo_legend_style)
                    
                    logo_table = Table([
                        [logo],
                        [logo_legend]
                    ], colWidths=[100])
                    
                    logo_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    
                    elements.append(logo_table)
            except Exception as e:
                print(f"Error al cargar el logo: {e}")
                # Continuar sin el logo si hay error
            
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Boleta de Venta", title_style))
            elements.append(Spacer(1, 12))
            
            elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 
                                    ParagraphStyle('Date', alignment=2)))
            elements.append(Spacer(1, 20))

            # Información del cliente
            cliente_index = self.cliente_combo.currentIndex()
            if cliente_index != -1:
                cliente_id = self.cliente_combo.itemData(cliente_index)
                cliente = Cliente.get_by_id(cliente_id)
                elements.append(Paragraph(f"Cliente: {cliente.nombre}", styles['Normal']))
                elements.append(Paragraph(f"Dirección: {cliente.direccion}", styles['Normal']))
            else:
                elements.append(Paragraph("Cliente: Consumidor Final", styles['Normal']))
            
            elements.append(Spacer(1, 12))

            data = [['Código', 'Nombre', 'Precio', 'Cantidad', 'Subtotal']] + items
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Total: {total}", styles['Heading2']))
            
            doc.build(elements)
            
            self.actualizar_inventario(items)
            
            QMessageBox.information(self, "Boleta Generada", f"Boleta generada y guardada como {nombre_archivo}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar la boleta: {str(e)}")
            # También podemos guardar el error en un archivo de log
            with open('error_log.txt', 'a') as f:
                f.write(f"\n[{datetime.now()}] Error al generar boleta: {str(e)}")

    def limpiar_boleta(self):
        self.boleta_tree.clear()
        self.total_label.setText("Total: $0.00")

    def actualizar_inventario(self, items):
        for item in items:
            codigo, _, _, cantidad, _ = item
            try:
                producto = Producto.get(Producto.codigo_barras == codigo)
                cantidad_vendida = int(cantidad)
                producto.stock -= cantidad_vendida
                producto.save()
                registrar_movimiento('venta', producto, cantidad_vendida, f"Venta de {cantidad_vendida} unidades")
            except Producto.DoesNotExist:
                QMessageBox.warning(self, "Error", f"No se encontró el producto con código de barras {codigo}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InventarioApp()
    window.show()
    sys.exit(app.exec())