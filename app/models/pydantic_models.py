from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List, Any
import uuid

class ChatMessage(BaseModel):
    """Esquema para mensajes del chat"""
    mensaje: str
    
class ChatResponse(BaseModel):
    """Esquema para respuestas del chat"""
    respuesta: str
    intencion: str
    timestamp: datetime
    
class ConversationCreate(BaseModel):
    """Esquema para crear conversación simple"""
    mensaje_usuario: str
    respuesta_bot: str
    intencion: Optional[str] = None
    
class SimpleConversationHistory(BaseModel):
    """Esquema para historial de conversación simple"""
    id: int
    mensaje_usuario: str
    respuesta_bot: str
    intencion: Optional[str] = None
    entidades: Optional[Dict[str, Any]] = None
    created_at: datetime
    
class OrderInfo(BaseModel):
    """Esquema para información de pedidos"""
    id_pedido: str
    nombre_cliente: str
    estado: str
    
class ProductInfo(BaseModel):
    """Esquema para información de productos"""
    id_producto: str
    nombre_producto: str
    disponibilidad: bool
    precio: Optional[str] = None
    categoria: Optional[str] = None
