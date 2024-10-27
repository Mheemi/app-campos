
import random
from barcode import EAN8
from barcode.writer import ImageWriter
from peewee import DoesNotExist
from db import Producto
import os
import matplotlib.pyplot as plt

def generar_codigo_ean8(prefijo="881"):
    numero_producto = f"{random.randint(0, 9999):04}"
    codigo_parcial = prefijo + numero_producto
    digito_control = calcular_digito_control(codigo_parcial)
    return codigo_parcial + str(digito_control)

def calcular_digito_control(codigo_barras):
    """Calcula el dígito de control para un código EAN-8."""
    suma = 0
    for i in range(7):
        num = int(codigo_barras[i])
        suma += num * 3 if i % 2 == 0 else num
    return (10 - (suma % 10)) % 10

def guardar_codigo_ean8_imagen(codigo_barras, carpeta='barcodes'):
    
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    # Ruta completa del archivo
    filename = os.path.join(carpeta, f'{codigo_barras}.png')
    
    # Crear y guardar el código de barras
    ean = EAN8(codigo_barras, writer=ImageWriter())
    ean.save(filename)
    
    # Mostrar la imagen del código de barras
    img = plt.imread(filename)
    plt.imshow(img)
    plt.axis('off')  # No mostrar los ejes
    plt.show()

    return filename

def buscar_producto_por_codigo(codigo_barras):
    
    #Busca un producto en la base de datos utilizando su código de barras
    try:
        producto = Producto.get(Producto.codigo_barras == codigo_barras)
        return producto
    except DoesNotExist:
        return None

"""for i in range(20): #CREAR COD DE BARRAS NUEVOS!
    try:
        nuevo_codigo = generar_codigo_ean8()
        ruta_imagen = guardar_codigo_ean8_imagen(nuevo_codigo, carpeta='barcodes')
        print(f'Código EAN-8 guardado en {ruta_imagen}')
    except Exception as e:
        print(f'Ocurrió un error al generar o guardar el código: {e}')"""

def procesar_codigo_barras(codigo_barras):
    producto = buscar_producto_por_codigo(codigo_barras)
    if producto:
        return producto
    return None

