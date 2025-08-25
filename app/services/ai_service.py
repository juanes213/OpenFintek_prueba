import re
from typing import Dict, List, Tuple
import requests
import json
import os
from dotenv import load_dotenv
from .gemini_service import GeminiService

load_dotenv()

class IntentClassifier:
    """Clasificador de intenciones para el chatbot"""
    
    def __init__(self):
        # Inicializar Gemini como opción principal
        self.gemini_service = GeminiService()
        
        # Patrones regex como fallback
        self.intent_patterns = {
            "consulta_analitica": [
                r"(?i).*(todos.*clientes|lista.*clientes|cu[aá]les.*clientes).*",
                r"(?i).*(cu[aá]ntos.*clientes|total.*clientes).*",
                r"(?i).*(estad[ií]sticas|an[aá]lisis|resumen|reporte).*",
                r"(?i).*(cu[aá]ntos.*pedidos|total.*pedidos).*",
                r"(?i).*(pedidos.*por.*estado|pedidos.*entregados|pedidos.*cancelados).*",
                r"(?i).*(productos.*sin.*stock|productos.*agotados).*",
                r"(?i).*(resumen.*negocio|resumen.*tienda|resumen.*general).*",
                r"(?i).*(top.*clientes|mejores.*clientes|principales.*clientes).*",
                r"(?i).*(inventario|productos.*disponibles).*",
                r"(?i).*(historial.*cliente|pedidos.*cliente|compras.*cliente).*"
            ],
            "consulta_pedido": [
                r"(?i).*(pedido|orden|compra|estado|seguimiento|track|rastreo).*",
                r"(?i).*(d[oó]nde est[aá]|cuando llega|entrega).*",
                r"(?i).*(n[uú]mero.*pedido|id.*pedido).*"
            ],
            "consulta_producto": [
                r"(?i).*(producto|art[ií]culo|disponible|stock|precio|costo).*",
                r"(?i).*(hay|tienen|venden|existe).*",
                r"(?i).*(cu[aá]nto cuesta|precio de|valor de).*"
            ],
            "politicas_empresa": [
                r"(?i).*(pol[ií]tica|horario|devoluci[oó]n|cambio|garant[ií]a).*",
                r"(?i).*(env[ií]o|delivery|domicilio|entrega).*",
                r"(?i).*(atenci[oó]n|servicio|contacto|tel[eé]fono).*"
            ],
            "informacion_general": [
                r"(?i).*(hola|hi|hello|buenos d[ií]as|buenas tardes).*",
                r"(?i).*(ayuda|help|asistencia|soporte).*",
                r"(?i).*(gracias|thank you|bye|adi[oó]s).*"
            ],
            "escalacion_humana": [
                r"(?i).*(hablar.*persona|agente humano|representante).*",
                r"(?i).*(no entiendo|problema|queja|reclamo).*",
                r"(?i).*(urgente|emergencia|prioridad).*"
            ]
        }
    
    def classify_intent(self, message: str) -> str:
        """Clasifica la intención del mensaje del usuario"""
        message = message.strip()
        
        # Primero verificar si es consulta analítica (prioridad alta)
        if self._is_analytical_query(message):
            return "consulta_analitica"
        
        # Intentar usar Gemini primero si está disponible
        if self.gemini_service.is_available():
            try:
                intent = self.gemini_service.classify_intent_with_ai(message)
                # Si Gemini detecta consulta compleja, mapearla a analítica
                if self._should_be_analytical(message, intent):
                    return "consulta_analitica"
                return intent
            except Exception as e:
                print(f"Error con Gemini, usando regex fallback: {e}")
        
        # Fallback a clasificación por regex
        return self._classify_with_regex(message.lower())
    
    def _classify_with_regex(self, message: str) -> str:
        """Clasificación usando patrones regex (fallback)"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    return intent
        
        return "informacion_general"
    
    def _is_analytical_query(self, message: str) -> bool:
        """Detecta si es una consulta analítica que requiere procesamiento complejo"""
        analytical_keywords = [
            "todos los clientes", "lista de clientes", "cuáles son los clientes",
            "cuántos clientes", "cuantos clientes", "estadísticas", "análisis", "resumen",
            "total de pedidos", "cuántos pedidos", "cuantos pedidos", "pedidos por estado", "productos sin stock",
            "productos en stock", "en stock",
            "resumen del negocio", "top clientes", "inventario completo",
            "historial de", "reporte de", "métricas", "indicadores"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in analytical_keywords)
    
    def _should_be_analytical(self, message: str, detected_intent: str) -> bool:
        """Verifica si una intención debería ser reclasificada como analítica"""
        # Si detecta pedido/producto pero es consulta masiva
        if detected_intent in ["consulta_pedido", "consulta_producto"]:
            analytical_modifiers = ["todos", "lista", "cuántos", "total", "estadísticas", "resumen"]
            message_lower = message.lower()
            return any(modifier in message_lower for modifier in analytical_modifiers)
        return False
    
    def determine_query_complexity(self, message: str, intent: str) -> str:
        """Determina si la consulta es simple o compleja para elegir el modelo"""
        # Consultas simples
        if intent in ["informacion_general", "escalacion_humana"]:
            return "simple"
        
        # Consultas analíticas siempre son complejas
        if intent == "consulta_analitica":
            return "complex"
        
        # Verificar complejidad por palabras clave
        complex_keywords = [
            "análisis", "estadísticas", "resumen", "todos", "cuántos",
            "comparar", "tendencia", "historial", "completo", "detallado"
        ]
        
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in complex_keywords):
            return "complex"
        
        # Verificar longitud del mensaje
        if len(message.split()) > 15:
            return "complex"
        
        return "simple"
    
    def extract_entities(self, message: str, intent: str) -> Dict:
        """Extrae entidades relevantes del mensaje según la intención"""
        entities = {}
        
        if intent == "consulta_pedido":
            # Buscar número de pedido (acepta guiones y prefijos tipo ORD, PED, PRD, etc.)
            # Ejemplos soportados: ORD001, ORD-001, PED1234, PRD-001
            pedido_match = re.search(r'(?i)(?:pedido|orden|order)[\s#:*-]*([A-Z0-9-]{3,})', message)
            if pedido_match:
                entities["numero_pedido"] = pedido_match.group(1).upper().strip('-')
            else:
                # Segundo intento: patrón aislado (palabra en mayúsculas con dígitos y posible guion)
                alt_match = re.search(r'\b([A-Z]{2,}[A-Z0-9-]{2,})\b', message)
                if alt_match and any(prefix in alt_match.group(1).upper() for prefix in ["ORD", "PED", "PRD"]):
                    entities["numero_pedido"] = alt_match.group(1).upper().strip('-')
        
        elif intent == "consulta_producto":
            # Buscar nombre de producto
            # Esto se puede mejorar con NER más sofisticado
            words = message.split()
            # Filtrar palabras comunes
            stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'y', 'o', 'en', 'con'}
            entities["producto_keywords"] = [w for w in words if w not in stop_words and len(w) > 2]
        
        return entities

class LLMService:
    """Servicio para interactuar con modelos de lenguaje"""
    
    def __init__(self):
        # Priorizar Gemini como servicio principal
        self.gemini_service = GeminiService()
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    def generate_response_with_gemini(self, prompt: str, context: str = "") -> str:
        """Generar respuesta usando Gemini (opción principal)"""
        if self.gemini_service.is_available():
            return self.gemini_service.generate_response(prompt, context)
        else:
            return self._get_fallback_response(prompt)
    
    def generate_enhanced_response(self, base_response: str, user_message: str, context: str = "") -> str:
        """Mejorar respuesta usando Gemini"""
        if self.gemini_service.is_available():
            return self.gemini_service.enhance_response(base_response, user_message, context)
        else:
            return base_response
    
    def generate_personalized_response(self, intent: str, entities: dict, context_data: dict, user_message: str) -> str:
        """Generar respuesta personalizada usando Gemini"""
        if self.gemini_service.is_available():
            return self.gemini_service.generate_personalized_response(intent, entities, context_data, user_message)
        else:
            return self._get_fallback_response(user_message)
    
    def generate_response_with_huggingface(self, prompt: str) -> str:
        """Generar respuesta usando HuggingFace (fallback)"""
        try:
            # Usar el modelo gratuito de HuggingFace
            API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
            headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 150,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
            
            return "Lo siento, no puedo procesar tu consulta en este momento."
            
        except Exception as e:
            print(f"Error with HuggingFace API: {e}")
            return "Lo siento, hay un problema técnico. Por favor intenta más tarde."
    
    def generate_response_with_fallback(self, prompt: str, context: str = "") -> str:
        """Generar respuesta con jerarquía: Gemini -> HuggingFace -> Fallback"""
        # 1. Intentar con Gemini primero
        if self.gemini_service.is_available():
            try:
                response = self.generate_response_with_gemini(prompt, context)
                if response and "no está disponible" not in response.lower():
                    return response
            except Exception as e:
                print(f"Error con Gemini: {e}")
        
        # 2. Intentar con HuggingFace si Gemini no funciona
        if self.huggingface_api_key:
            try:
                response = self.generate_response_with_huggingface(prompt)
                if response and "no puedo procesar" not in response.lower():
                    return response
            except Exception as e:
                print(f"Error con HuggingFace: {e}")
        
        # 3. Usar respuesta predefinida como último recurso
        return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Respuestas predefinidas como fallback"""
        # Análisis simple del prompt para generar respuesta apropiada
        prompt_lower = prompt.lower()
        
        if "pedido" in prompt_lower or "orden" in prompt_lower:
            return "Para consultar el estado de tu pedido, por favor proporciona tu número de pedido. Nuestro equipo verificará la información y te proporcionará una actualización."
        
        elif "producto" in prompt_lower or "disponible" in prompt_lower:
            return "Te ayudo a consultar la disponibilidad de productos. Por favor especifica el nombre del producto que te interesa."
        
        elif "política" in prompt_lower or "devolución" in prompt_lower:
            return "Puedes consultar nuestras políticas de devolución y garantía. ¿Hay algún aspecto específico sobre el que te gustaría saber más?"
        
        elif "hola" in prompt_lower or "ayuda" in prompt_lower:
            return "¡Hola! Soy tu asistente virtual. Puedo ayudarte con consultas sobre pedidos, productos, políticas de la empresa y más. ¿En qué puedo asistirte hoy?"
        
        else:
            return "Entiendo tu consulta. Para brindarte la mejor asistencia, podrías proporcionar más detalles o contactar con nuestro equipo de atención al cliente."
