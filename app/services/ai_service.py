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
                r"(?i).*(todos.*productos|todo.*inventario|cat[aá]logo.*completo).*",
                r"(?i).*(productos.*en.*stock|productos.*disponibles|qu[eé].*tenemos).*",
                r"(?i).*(mostrar.*productos|ver.*productos|listar.*productos).*",
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
            "historial de", "reporte de", "métricas", "indicadores",
            # Nuevos keywords para consultas de productos generales
            "cuales productos", "cuáles productos", "que productos", "qué productos", 
            "todos los productos", "lista de productos", "productos disponibles",
            "productos tenemos", "tenemos en stock", "inventario", "catálogo",
            "comparativas", "comparar", "completas", "completo", "general",
            # Keywords específicos de tecnología
            "smartphones", "laptops", "tablets", "teléfonos", "computadoras",
            "monitores", "cámaras", "auriculares", "accesorios", "gaming",
            "apple", "samsung", "iphone", "ipad", "macbook", "android",
            "productos tecnológicos", "dispositivos", "electrónicos", "gadgets",
            "equipos", "tecnología", "tech", "hardware", "software",
            # Keywords de productos reales del inventario
            "quantum", "processor", "nebula", "smartwatch", "orion", "vr", "headset",
            "cyber", "synth", "keyboard", "titan", "mouse", "gaming", "helios", "solar",
            "echo", "buds", "spectra", "monitor", "aura", "light", "stealth", "drone",
            "nova", "pad", "vortex", "cooling", "chroma", "key", "matrix", "router",
            "zenith", "power", "bank", "pulse", "wave", "speakers", "core", "connect",
            "fusion", "cam", "4k", "equinox", "projector", "galileo", "pen", "stylus",
            "cosmo", "mic", "hyper", "drive", "ssd", "atlas", "mount", "stand",
            "infinity", "webcam", "elysium", "chair", "terra", "scanner", "3d",
            "apollo", "audio", "interface", "rift", "cables", "vertex", "graphics",
            "pioneer", "robotic", "arm", "guardian", "smart", "lock", "odyssey",
            "backpack", "nomad", "portable", "momentum", "ring", "catalyst",
            "converter", "element", "air", "purifier", "synapse", "adapter",
            "horizon", "docking", "station", "legacy", "console"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in analytical_keywords)
    
    def _should_be_analytical(self, message: str, detected_intent: str) -> bool:
        """Verifica si una intención debería ser reclasificada como analítica"""
        # Si detecta pedido/producto pero es consulta masiva
        if detected_intent in ["consulta_pedido", "consulta_producto"]:
            analytical_modifiers = [
                "todos", "lista", "cuántos", "cuantos", "total", "estadísticas", "resumen",
                "cuales", "cuáles", "que", "qué", "disponibles", "tenemos", "inventario",
                "catálogo", "completas", "completo", "comparativas", "comparar",
                "general", "en stock",
                # Modificadores específicos de tecnología
                "smartphones", "laptops", "tablets", "teléfonos", "computadoras",
                "monitores", "cámaras", "auriculares", "gaming", "tecnológicos",
                "dispositivos", "electrónicos", "equipos", "accesorios",
                "marcas", "modelos", "categorías", "tipos", "gama", "precios"
            ]
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
    """Service for interacting with language models - Gemini only"""
    
    def __init__(self):
        # Use Gemini as the primary and only service
        self.gemini_service = GeminiService()
    
    def generate_response_with_gemini(self, prompt: str, context: str = "") -> str:
        """Generate response using Gemini (primary option)"""
        if self.gemini_service.is_available():
            return self.gemini_service.generate_response(prompt, context)
        else:
            return self._get_fallback_response(prompt)
    
    def generate_enhanced_response(self, base_response: str, user_message: str, context: str = "") -> str:
        """Enhance response using Gemini"""
        if self.gemini_service.is_available():
            return self.gemini_service.enhance_response(base_response, user_message, context)
        else:
            return base_response
    
    def generate_personalized_response(self, intent: str, entities: dict, context_data: dict, user_message: str) -> str:
        """Generate personalized response using Gemini"""
        if self.gemini_service.is_available():
            return self.gemini_service.generate_personalized_response(intent, entities, context_data, user_message)
        else:
            return self._get_fallback_response(user_message)
    
    def generate_response_with_fallback(self, prompt: str, context: str = "") -> str:
        """Generate response with Gemini or fallback"""
        # Try Gemini first
        if self.gemini_service.is_available():
            try:
                response = self.generate_response_with_gemini(prompt, context)
                if response and "not available" not in response.lower():
                    return response
            except Exception as e:
                print(f"Error with Gemini: {e}")
        
        # Use predefined response as fallback
        return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Predefined administrative responses as fallback in Spanish"""
        # Simple prompt analysis to generate appropriate administrative response
        prompt_lower = prompt.lower()
        
        if "pedido" in prompt_lower or "orden" in prompt_lower or "order" in prompt_lower:
            return "Para revisar el estado de un pedido específico, proporciona el número de pedido. Puedo acceder al sistema y verificar la información de estado, cliente y tracking."
        
        elif "producto" in prompt_lower or "disponible" in prompt_lower or "product" in prompt_lower:
            return "Puedo ayudarte a verificar el inventario y disponibilidad de productos. Especifica el nombre del producto o categoría para consultar el stock actual."
        
        elif "política" in prompt_lower or "devolución" in prompt_lower or "policy" in prompt_lower:
            return "Puedo consultar las políticas configuradas en el sistema. ¿Qué política específica necesitas revisar? (devoluciones, envíos, horarios, garantías)"
        
        elif "hola" in prompt_lower or "ayuda" in prompt_lower or "hello" in prompt_lower or "help" in prompt_lower:
            return "¡Hola! Soy tu asistente administrativo para la gestión de Waver. Puedo ayudarte con monitoreo de pedidos, inventario, análisis de clientes, reportes y configuración de políticas. ¿Qué información necesitas revisar?"
        
        else:
            return "Consulta recibida. Para una respuesta más específica, proporciona más detalles sobre qué información de la tienda necesitas revisar (pedidos, inventario, clientes, reportes)."
