from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .database import Base

class Conversation(Base):
    """Modelo para almacenar conversaciones del chatbot"""
    __tablename__ = "conversaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    mensaje_usuario = Column(Text, nullable=False)
    respuesta_bot = Column(Text, nullable=False)
    intencion = Column(String(100), nullable=True)
    marca_tiempo = Column(DateTime(timezone=True), server_default=func.now())
    
class Order(Base):
    """Modelo para pedidos"""
    __tablename__ = "pedidos"
    
    id_pedido = Column(String(50), primary_key=True, index=True)
    nombre_cliente = Column(String(100), nullable=False)
    estado = Column(String(50), nullable=False)
    
class Product(Base):
    """Modelo para productos"""
    __tablename__ = "productos"
    
    id_producto = Column(String(50), primary_key=True, index=True)
    nombre_producto = Column(String(200), nullable=False)
    disponibilidad = Column(Boolean, default=True)
    precio = Column(String(20), nullable=True)
    categoria = Column(String(100), nullable=True)
    
class CompanyInfo(Base):
    """Modelo para información de la empresa"""
    __tablename__ = "info_empresa"
    
    id = Column(Integer, primary_key=True, index=True)
    tema = Column(String(100), nullable=False)
    informacion = Column(Text, nullable=False)
