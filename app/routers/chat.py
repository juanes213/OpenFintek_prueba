from fastapi import APIRouter, HTTPException
from app.models.pydantic_models import ChatMessage, ChatResponse
from app.services.chatbot_service import ChatbotService
from datetime import datetime

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage, session_id: str = None):
    """
    Endpoint principal del chat con soporte de sesiones
    
    Recibe un mensaje del usuario y devuelve la respuesta del chatbot
    Mantiene contexto de conversación por sesión
    """
    try:
        # Validar que el mensaje no esté vacío
        if not message.mensaje or not message.mensaje.strip():
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
        
        # Inicializar servicio del chatbot con session_id si se proporciona
        chatbot = ChatbotService(session_id=session_id)
        
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
async def get_chat_history(limit: int = 10, session_id: str = None):
    """
    Obtener historial de conversaciones
    """
    try:
        chatbot = ChatbotService(session_id=session_id)
        history = chatbot.get_conversation_history(limit)
        return {"history": history}
        
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
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "service": "ecommerce-chatbot"
    }
