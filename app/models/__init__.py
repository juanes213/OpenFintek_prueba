# Modelos de la aplicación - Solo Supabase (sin datos de ejemplo)
from .supabase_client import get_supabase_client
from .pydantic_models import ChatMessage, ChatResponse, ConversationCreate, OrderInfo, ProductInfo

__all__ = [
    "get_supabase_client",
    "ChatMessage",
    "ChatResponse",
    "ConversationCreate",
    "OrderInfo",
    "ProductInfo"
]
