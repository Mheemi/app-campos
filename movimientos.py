from peewee import *
from db import db, Producto
from datetime import datetime
import calendar
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class Movimiento(Model):
    fecha = DateTimeField(default=datetime.now)
    tipo = CharField()
    producto = ForeignKeyField(Producto, backref='movimientos')
    cantidad = IntegerField(null=True)
    detalles = TextField(null=True)

    class Meta:
        database = db

def registrar_movimiento(tipo, producto, cantidad=None, detalles=None):
    Movimiento.create(
        tipo=tipo,
        producto=producto,
        cantidad=cantidad,
        detalles=detalles)

def obtener_movimientos(fecha_inicio=None, fecha_fin=None):

    if fecha_inicio is None:
        fecha_inicio = datetime(2024, 9, 1)
    
    
    if fecha_fin is None:
        fecha_fin = datetime.now()

    
    query = (Movimiento
            .select(Movimiento, Producto)
            .join(Producto)
            .where((Movimiento.fecha >= fecha_inicio) & (Movimiento.fecha <= fecha_fin))
            .order_by(Movimiento.fecha.desc()))
    
    return query

def exportar_movimientos_pdf(movimientos, nombre_archivo):
    doc = SimpleDocTemplate(nombre_archivo, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Reporte de Movimientos", styles['Title']))
    elements.append(Spacer(1, 12))
    
    data = [['Fecha', 'Tipo', 'Producto', 'Cantidad', 'Detalles']]
    for m in movimientos:
        data.append([
            m.fecha.strftime('%Y-%m-%d %H:%M:%S'),
            m.tipo,
            m.producto.nombre,
            str(m.cantidad) if m.cantidad is not None else '',
            m.detalles or ''
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    

def obtener_ventas_por_mes(año):
    return (Movimiento
            .select(
                fn.strftime('%m', Movimiento.fecha).alias('mes'),
                fn.SUM(Movimiento.cantidad).alias('total_vendido'),
                fn.SUM(Movimiento.cantidad * Producto.precio).alias('total_ingresos')
            )
            .join(Producto)
            .where(
                (Movimiento.tipo == 'venta') & 
                (fn.strftime('%Y', Movimiento.fecha) == str(año))
            )
            .group_by(fn.strftime('%m', Movimiento.fecha))
            .order_by(fn.strftime('%m', Movimiento.fecha)))

def obtener_ingresos_por_mes(año):
    return (Movimiento
            .select(
                fn.strftime('%m', Movimiento.fecha).alias('mes'),
                fn.SUM(Movimiento.cantidad).alias('total_ingresado')
            )
            .where(
                (Movimiento.tipo == 'ingreso') & 
                (fn.strftime('%Y', Movimiento.fecha) == str(año))
            )
            .group_by(fn.strftime('%m', Movimiento.fecha))
            .order_by(fn.strftime('%m', Movimiento.fecha)))


def obtener_resumen_anual(año):
    ventas = {int(venta.mes): (venta.total_vendido or 0, venta.total_ingresos or 0) 
            for venta in obtener_ventas_por_mes(año)}
    ingresos = {int(ingreso.mes): ingreso.total_ingresado or 0 
                for ingreso in obtener_ingresos_por_mes(año)}
    
    resumen = []
    for mes in range(1, 13):
        nombre_mes = calendar.month_name[mes]
        total_vendido, total_ingresos = ventas.get(mes, (0, 0))
        total_ingresado = ingresos.get(mes, 0)
        resumen.append({
            'mes': nombre_mes,
            'total_vendido': total_vendido,
            'total_ingresos': total_ingresos,
            'total_ingresado': total_ingresado
        })
    
    return resumen
db.create_tables([Movimiento])