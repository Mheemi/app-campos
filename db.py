from peewee import *
from datetime import datetime

db = SqliteDatabase('inventario.db')

class CaseInsensitiveField(CharField):
    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        return value.lower() if value else None

    def python_value(self, value):
        return value

class Producto(Model):
    codigo_barras = CharField(unique=True, primary_key=True)
    nombre = CaseInsensitiveField()
    precio = FloatField()
    stock = IntegerField(default=0)
    id_int = CharField(null=True)  
    id_cr = CharField(null=True)   
    id_t = CharField(null=True)    
    fecha_creacion = DateTimeField(default=datetime.now)
    fecha_modificacion = DateTimeField(default=datetime.now)

    class Meta:
        database = db

    @classmethod
    def buscar_por_codigo_barras(cls, codigo_barras):
        return cls.get_or_none(cls.codigo_barras == codigo_barras)

    @classmethod
    def buscar_por_nombre(cls, nombre):
        return cls.select().where(fn.LOWER(cls.nombre).contains(nombre.lower()))

class Cliente(Model):
    nombre = CharField()
    rut = CharField(null=True)
    direccion = CharField(null=True)
    telefono = CharField(null=True)
    fecha_creacion = DateTimeField(default=datetime.now)

    class Meta:
        database = db

db.connect()
db.create_tables([Producto, Cliente], safe=True)
