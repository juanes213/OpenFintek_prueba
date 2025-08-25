"""
Servicio de Contexto de Conversación Avanzado
Maneja memoria multi-turno, análisis de sentimiento y estado del cliente
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import json
import re

class ConversationContext:
    """Maneja el contexto completo de la conversación con memoria multi-turno"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversation_history = deque(maxlen=max_history)
        self.user_profile = {}
        self.current_intent_chain = []
        self.sentiment_history = []
        self.entities_mentioned = {}
        self.pending_actions = []
        self.conversation_state = "active"
        self.frustration_level = 0
        self.satisfaction_score = 5  # 1-10 scale
        
    def add_turn(self, user_message: str, bot_response: str, intent: str, entities: Dict, sentiment: float = 0.0):
        """Agregar un turno de conversación al contexto"""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "intent": intent,
            "entities": entities,
            "sentiment": sentiment
        }
        
        self.conversation_history.append(turn)
        self.current_intent_chain.append(intent)
        self.sentiment_history.append(sentiment)
        
        # Actualizar entidades mencionadas
        for key, value in entities.items():
            if key not in self.entities_mentioned:
                self.entities_mentioned[key] = []
            self.entities_mentioned[key].append(value)
        
        # Actualizar nivel de frustración basado en sentimiento
        self._update_frustration_level(sentiment, user_message)
        
    def _update_frustration_level(self, sentiment: float, message: str):
        """Actualizar nivel de frustración basado en señales"""
        frustration_keywords = [
            "no funciona", "problema", "mal", "terrible", "horrible",
            "no entiendes", "no sirve", "perdiendo tiempo", "frustrado",
            "enojado", "molesto", "cansado de", "harto"
        ]
        
        # Detectar palabras de frustración
        message_lower = message.lower()
        frustration_detected = any(keyword in message_lower for keyword in frustration_keywords)
        
        if frustration_detected or sentiment < -0.3:
            self.frustration_level = min(10, self.frustration_level + 2)
        elif sentiment > 0.3:
            self.frustration_level = max(0, self.frustration_level - 1)
        
        # Ajustar satisfaction score
        if self.frustration_level > 7:
            self.satisfaction_score = max(1, self.satisfaction_score - 2)
        elif self.frustration_level < 3:
            self.satisfaction_score = min(10, self.satisfaction_score + 1)
    
    def get_conversation_summary(self) -> str:
        """Obtener resumen de la conversación actual"""
        if not self.conversation_history:
            return "Nueva conversación"
        
        recent_intents = list(set(self.current_intent_chain[-3:]))
        mentioned_products = self.entities_mentioned.get("producto_keywords", [])
        mentioned_orders = self.entities_mentioned.get("numero_pedido", [])
        
        summary_parts = []
        
        if mentioned_orders:
            summary_parts.append(f"Pedidos consultados: {', '.join(set(mentioned_orders))}")
        
        if mentioned_products:
            products_flat = [p for sublist in mentioned_products for p in (sublist if isinstance(sublist, list) else [sublist])]
            summary_parts.append(f"Productos de interés: {', '.join(set(products_flat[:3]))}")
        
        if recent_intents:
            summary_parts.append(f"Temas recientes: {', '.join(recent_intents)}")
        
        return " | ".join(summary_parts) if summary_parts else "Conversación general"
    
    def get_context_for_response(self) -> Dict[str, Any]:
        """Obtener contexto relevante para generar respuesta"""
        recent_turns = list(self.conversation_history)[-3:]
        
        return {
            "conversation_summary": self.get_conversation_summary(),
            "frustration_level": self.frustration_level,
            "satisfaction_score": self.satisfaction_score,
            "recent_turns": recent_turns,
            "entities_mentioned": self.entities_mentioned,
            "pending_actions": self.pending_actions,
            "conversation_length": len(self.conversation_history),
            "average_sentiment": sum(self.sentiment_history) / len(self.sentiment_history) if self.sentiment_history else 0
        }
    
    def should_escalate(self) -> bool:
        """Determinar si se debe escalar a un agente humano"""
        return (
            self.frustration_level >= 8 or
            len([i for i in self.current_intent_chain[-3:] if i == "escalacion_humana"]) >= 2 or
            self.satisfaction_score <= 3
        )
    
    def needs_empathy(self) -> bool:
        """Determinar si se necesita una respuesta más empática"""
        return self.frustration_level >= 5 or self.satisfaction_score <= 5
    
    def get_personalization_hints(self) -> Dict[str, Any]:
        """Obtener hints para personalizar la respuesta"""
        hints = {
            "tone": "empathetic" if self.needs_empathy() else "professional",
            "urgency": "high" if self.frustration_level >= 7 else "normal",
            "should_apologize": self.frustration_level >= 6,
            "should_offer_alternatives": len(self.conversation_history) > 3 and self.satisfaction_score < 7,
            "conversation_stage": self._determine_conversation_stage()
        }
        return hints
    
    def _determine_conversation_stage(self) -> str:
        """Determinar en qué etapa está la conversación"""
        turn_count = len(self.conversation_history)
        
        if turn_count == 0:
            return "greeting"
        elif turn_count <= 2:
            return "exploration"
        elif turn_count <= 5:
            return "assistance"
        elif turn_count <= 8:
            return "resolution"
        else:
            return "extended_support"
    
    def add_pending_action(self, action: str, data: Dict = None):
        """Agregar una acción pendiente para seguimiento"""
        self.pending_actions.append({
            "action": action,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def clear_pending_action(self, action: str):
        """Limpiar una acción pendiente completada"""
        self.pending_actions = [a for a in self.pending_actions if a["action"] != action]
    
    def get_follow_up_suggestions(self) -> List[str]:
        """Sugerir acciones de seguimiento basadas en el contexto"""
        suggestions = []
        
        # Si hay productos mencionados sin compra
        if "producto_keywords" in self.entities_mentioned and "purchase" not in self.current_intent_chain:
            suggestions.append("offer_purchase_assistance")
        
        # Si hay consulta de pedido reciente
        if "numero_pedido" in self.entities_mentioned:
            suggestions.append("offer_tracking_updates")
        
        # Si la satisfacción es baja
        if self.satisfaction_score < 5:
            suggestions.append("offer_human_assistance")
        
        # Si es una conversación larga
        if len(self.conversation_history) > 7:
            suggestions.append("summarize_and_confirm")
        
        return suggestions


class SentimentAnalyzer:
    """Analizador de sentimiento simple basado en reglas y palabras clave"""
    
    def __init__(self):
        self.positive_words = [
            "gracias", "excelente", "perfecto", "genial", "bueno", "bien",
            "feliz", "contento", "satisfecho", "maravilloso", "increíble",
            "ayuda", "útil", "claro", "entiendo", "super", "fantástico"
        ]
        
        self.negative_words = [
            "mal", "problema", "error", "no funciona", "terrible", "horrible",
            "molesto", "frustrado", "enojado", "decepcionado", "lento",
            "no sirve", "pesimo", "inaceptable", "no entiendo", "confundido"
        ]
        
        self.intensifiers = ["muy", "demasiado", "extremadamente", "super", "bastante"]
        
    def analyze(self, text: str) -> float:
        """
        Analizar sentimiento del texto
        Retorna un valor entre -1 (muy negativo) y 1 (muy positivo)
        """
        text_lower = text.lower()
        
        # Contar palabras positivas y negativas
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)
        
        # Verificar intensificadores
        has_intensifier = any(intensifier in text_lower for intensifier in self.intensifiers)
        multiplier = 1.5 if has_intensifier else 1.0
        
        # Calcular score
        if positive_count + negative_count == 0:
            return 0.0
        
        sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
        sentiment_score *= multiplier
        
        # Limitar entre -1 y 1
        return max(-1.0, min(1.0, sentiment_score))
    
    def get_sentiment_label(self, score: float) -> str:
        """Obtener etiqueta de sentimiento basada en el score"""
        if score > 0.5:
            return "muy_positivo"
        elif score > 0.1:
            return "positivo"
        elif score < -0.5:
            return "muy_negativo"
        elif score < -0.1:
            return "negativo"
        else:
            return "neutral"


class ConversationMemory:
    """Memoria persistente de conversaciones por usuario (sesión)"""
    
    def __init__(self):
        self.sessions = {}
        self.global_insights = {
            "common_intents": {},
            "common_products": {},
            "peak_hours": {},
            "average_satisfaction": []
        }
    
    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """Obtener o crear una sesión de conversación"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext()
        return self.sessions[session_id]
    
    def update_global_insights(self, intent: str, products: List[str] = None, satisfaction: float = None):
        """Actualizar insights globales de todas las conversaciones"""
        # Actualizar intenciones comunes
        self.global_insights["common_intents"][intent] = \
            self.global_insights["common_intents"].get(intent, 0) + 1
        
        # Actualizar productos comunes
        if products:
            for product in products:
                self.global_insights["common_products"][product] = \
                    self.global_insights["common_products"].get(product, 0) + 1
        
        # Actualizar satisfacción promedio
        if satisfaction is not None:
            self.global_insights["average_satisfaction"].append(satisfaction)
            # Mantener solo las últimas 100
            if len(self.global_insights["average_satisfaction"]) > 100:
                self.global_insights["average_satisfaction"] = \
                    self.global_insights["average_satisfaction"][-100:]
    
    def get_trending_products(self, top_n: int = 3) -> List[str]:
        """Obtener productos más consultados"""
        sorted_products = sorted(
            self.global_insights["common_products"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [product for product, _ in sorted_products[:top_n]]
    
    def clean_old_sessions(self, hours: int = 24):
        """Limpiar sesiones antiguas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for session_id in list(self.sessions.keys()):
            session = self.sessions[session_id]
            if session.conversation_history:
                last_turn = session.conversation_history[-1]
                last_time = datetime.fromisoformat(last_turn["timestamp"])
                if last_time < cutoff_time:
                    del self.sessions[session_id]
