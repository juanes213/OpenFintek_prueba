from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
from app.models.pydantic_models import ChatMessage, ChatResponse
from app.services.chatbot_service import ChatbotService
from app.services.database_service import DatabaseService
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage, request: Request):
    """
    Endpoint principal del chat con memoria simple
    
    Recibe un mensaje del usuario y devuelve la respuesta del chatbot
    Mantiene memoria de la conversación en la sesión actual
    """
    try:
        # Validar que el mensaje no esté vacío
        if not message.mensaje or not message.mensaje.strip():
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
        
        # Inicializar servicio del chatbot (sin session_id complejo)
        chatbot = ChatbotService()
        
        # Procesar mensaje
        result = await chatbot.process_message(message.mensaje.strip())
        
        # Devolver respuesta
        return ChatResponse(
            respuesta=result["respuesta"],
            intencion=result["intencion"],
            timestamp=result["timestamp"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/chat/history")
async def get_chat_history(
    limit: int = Query(10, ge=1, le=50, description="Número de mensajes a retornar")
):
    """
    Obtener historial de conversación simple
    """
    try:
        db_service = DatabaseService()
        
        # Obtener historial simple de la base de datos
        simple_history = db_service.get_simple_conversation_history(limit)
        
        # También obtener historial de la sesión actual en memoria
        chatbot = ChatbotService()
        session_history = chatbot.get_conversation_history(limit)
        
        return {
            "history": simple_history,
            "session_history": session_history,
            "total_db_messages": len(simple_history)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial: {str(e)}"
        )

@router.get("/chat/health")
async def health_check():
    """
    Endpoint de verificación de salud del servicio
    """
    try:
        db_service = DatabaseService()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "service": "waver-admin-panel",
            "features": {
                "basic_chat": True,
                "memory": True,
                "database_connection": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "service": "waver-admin-panel",
            "error": str(e),
            "features": {
                "basic_chat": False,
                "memory": False,
                "database_connection": False
            }
        }
