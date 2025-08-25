import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class GeminiService:
    """Servicio avanzado para interactuar con Google Gemini AI como agente comercial"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Modelos duales: Flash para consultas simples, Pro para complejas
            self.flash_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.pro_model = genai.GenerativeModel('gemini-2.5-pro')
            self.model = self.flash_model  # Por defecto usar flash
        else:
            self.flash_model = None
            self.pro_model = None
            self.model = None
    
    def is_available(self) -> bool:
        """Verificar si Gemini está disponible"""
        return self.flash_model is not None and self.api_key is not None
    
    def _select_model(self, complexity: str) -> Optional[object]:
        """Seleccionar modelo según complejidad"""
        if complexity == "complex" and self.pro_model:
            return self.pro_model
        return self.flash_model
    
    def generate_response(self, prompt: str, context: str = "", max_tokens: int = 2000, complexity: str = "simple") -> str:
        """
        Generar respuesta usando Gemini
        
        Args:
            prompt: El prompt del usuario
            context: Contexto adicional (datos de productos, pedidos, etc.)
            max_tokens: Máximo número de tokens en la respuesta (ahora más generoso)
        
        Returns:
            Respuesta generada por Gemini o mensaje de error
        """
        if not self.is_available():
            return "Lo siento, el servicio de IA no está disponible en este momento."
        
        try:
            # Seleccionar modelo según complejidad
            selected_model = self._select_model(complexity)
            if not selected_model:
                return "Lo siento, el servicio de IA no está disponible."
            
            # Construir el prompt completo
            full_prompt = self._build_prompt(prompt, context)
            
            # Configurar parámetros sin limitaciones restrictivas
            if complexity == "complex":
                generation_config = {
                    'max_output_tokens': 2000,  # Sin limitaciones restrictivas
                    'temperature': 0.3,  # Menos creativo, más preciso
                    'top_p': 0.8
                }
            else:
                generation_config = {
                    'max_output_tokens': 1500,  # Generoso para respuestas completas
                    'temperature': 0.7,
                    'top_p': 0.9
                }
            
            # Generar respuesta
            response = selected_model.generate_content(full_prompt, generation_config=generation_config)
            
            # Verificar si hay contenido válido
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    if candidate.finish_reason == 2:  # SAFETY
                        return "Lo siento, no puedo procesar esa consulta por políticas de seguridad."
                    elif candidate.finish_reason == 3:  # RECITATION
                        return "Lo siento, no puedo proporcionar esa información específica."
            
            if response.text:
                return response.text.strip()
            else:
                return "Lo siento, no pude generar una respuesta apropiada."
                
        except Exception as e:
            print(f"Error con Gemini API: {e}")
            return "Lo siento, ocurrió un error al procesar tu consulta."
    
    def classify_intent_with_ai(self, message: str, complexity: str = "simple") -> str:
        """
        Usar Gemini para clasificar intenciones de manera más sofisticada
        """
        if not self.is_available():
            return "informacion_general"
        
        try:
            prompt = f"""
            Clasifica la siguiente consulta de un cliente de e-commerce en una de estas categorías:
            
            1. consulta_analitica - Análisis, estadísticas, listas completas (ej: "todos los clientes", "resumen de pedidos")
            2. consulta_pedido - Pregunta sobre UN pedido específico
            3. consulta_producto - Pregunta sobre UN producto específico
            4. politicas_empresa - Preguntas sobre horarios, devoluciones, envíos
            5. informacion_general - Saludos, despedidas, ayuda general
            6. escalacion_humana - Solicita hablar con una persona
            
            Consulta del cliente: "{message}"
            
            SOLO responde con el nombre de la categoría:
            """
            
            # Usar modelo apropiado para clasificación
            selected_model = self._select_model(complexity)
            response = selected_model.generate_content(prompt)
            
            # Verificar si hay contenido válido
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    if candidate.finish_reason == 2:  # SAFETY
                        return "informacion_general"
            
            if response.text:
                intent = response.text.strip().lower()
            else:
                intent = "informacion_general"
            
            # Validar que la respuesta sea una intención válida
            valid_intents = [
                "consulta_analitica", "consulta_pedido", "consulta_producto", 
                "politicas_empresa", "informacion_general", "escalacion_humana"
            ]
            
            if intent in valid_intents:
                return intent
            else:
                return "informacion_general"
                
        except Exception as e:
            print(f"Error clasificando intención con Gemini: {e}")
            return "informacion_general"
    
    def enhance_response(self, base_response: str, user_message: str, context: str = "") -> str:
        """
        Mejorar una respuesta base usando Gemini para hacerla más natural
        """
        if not self.is_available():
            return base_response
        
        try:
            prompt = f"""
            Eres un agente de servicio al cliente.
            
            Consulta: "{user_message}"
            Respuesta base: "{base_response}"
            Contexto: {context}
            
            REGLAS:
            - MANTÉN los datos exactos de la respuesta base
            - Solo mejora la redacción (más natural)
            - Máximo 250 palabras
            - Directo y conciso
            - NO inventes información nueva
            
            Respuesta mejorada:
            """
            
            response = self.model.generate_content(prompt)
            
            # Verificar si hay contenido válido
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    if candidate.finish_reason == 2:  # SAFETY
                        return base_response
            
            if response.text and len(response.text.strip()) > 10:
                return response.text.strip()
            else:
                return base_response
                
        except Exception as e:
            print(f"Error mejorando respuesta con Gemini: {e}")
            return base_response
    
    def _build_prompt(self, user_message: str, context: str) -> str:
        """Construir prompt simple para Gemini"""
        system_prompt = """
        Eres un agente de servicio al cliente amigable y útil para una tienda de e-commerce.
        
        Puedes ayudar con:
        - Consultas sobre pedidos específicos o generales
        - Búsquedas de productos y catálogo completo
        - Información sobre políticas de la empresa
        - Análisis de datos cuando te proporcionen información de la base de datos
        
        FORMATO DE RESPUESTA:
        - Usa **texto** para resaltar información importante (nombres, números, estados)
        - Sé claro, completo y preciso
        - Si te proporcionan información de la base de datos, analízala y responde de manera útil
        - Si el usuario hace preguntas generales, usa toda la información disponible para responder
        - Mantén las respuestas naturales, completas y útiles
        """
        
        if context and context.strip():
            full_prompt = f"{system_prompt}\n\nInformación de la base de datos:\n{context}\n\nUsuario: {user_message}\n\nAsistente:"
        else:
            full_prompt = f"{system_prompt}\n\nUsuario: {user_message}\n\nAsistente:"
        
        return full_prompt
    
    def generate_personalized_response(self, intent: str, entities: dict, context_data: dict, user_message: str, 
                                      conversation_context: Optional[dict] = None, complexity: str = "simple") -> str:
        """
        Generar respuesta personalizada con capacidades comerciales avanzadas
        """
        if not self.is_available():
            return "Lo siento, no puedo procesar tu consulta en este momento."
        
        # Construir contexto específico según la intención
        context = self._build_context_for_intent(intent, entities, context_data)
        
        # Agregar contexto de conversación si está disponible
        if conversation_context:
            personalization_hints = conversation_context.get('personalization_hints', {})
            tone = personalization_hints.get('tone', 'professional')
            urgency = personalization_hints.get('urgency', 'normal')
            should_apologize = personalization_hints.get('should_apologize', False)
            frustration_level = conversation_context.get('frustration_level', 0)
            satisfaction_score = conversation_context.get('satisfaction_score', 5)
        else:
            tone = 'professional'
            urgency = 'normal'
            should_apologize = False
            frustration_level = 0
            satisfaction_score = 5
        
        # Prompt mejorado con estrategias comerciales
        prompt = f"""
        Eres un agente de servicio al cliente para una tienda de e-commerce.
        
        REGLAS CRÍTICAS:
        1. SOLO usa la información proporcionada en "DATOS DISPONIBLES"
        2. NO inventes datos, precios, estados o información
        3. Si no hay datos, di "No tengo esa información en el sistema"
        4. Sé PRECISO y COMPLETO - incluye toda la información relevante
        5. Usa formato claro con **negritas** para datos importantes
        
        CONTEXTO:
        - Tipo de consulta: {intent}
        - Frustración del cliente: {frustration_level}/10
        {"- El cliente está frustrado, sé empático" if should_apologize else ""}
        
        MENSAJE DEL CLIENTE:
        "{user_message}"
        
        DATOS DISPONIBLES:
        {context}
        
        RESPONDE:
        - Si hay datos: úsalos exactamente como están y proporciona información completa
        - Si NO hay datos: "No encuentro esa información en el sistema"
        - Sé claro, informativo y completo en tu respuesta
        
        RESPUESTA:
        """
        
        try:
            # Seleccionar modelo según complejidad
            selected_model = self._select_model(complexity)
            if not selected_model:
                return "No puedo procesar tu consulta."
            
            # Configurar parámetros según complejidad
            if complexity == "complex":
                config = {
                    'max_output_tokens': 1500,  # Más generoso para consultas complejas
                    'temperature': 0.3,
                    'top_p': 0.8
                }
            else:
                config = {
                    'max_output_tokens': 1000,  # Suficiente para respuestas completas
                    'temperature': 0.7,
                    'top_p': 0.9
                }
            
            response = selected_model.generate_content(prompt, generation_config=config)
            
            # Verificar si hay contenido válido
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    if candidate.finish_reason == 2:  # SAFETY
                        return "No puedo procesar esa consulta específica."
            
            return response.text.strip() if response.text else "¿En qué más puedo ayudarte?"
        except Exception as e:
            print(f"Error generando respuesta personalizada: {e}")
            return "¿En qué más puedo ayudarte?"
    
    def _build_context_for_intent(self, intent: str, entities: dict, context_data: dict) -> str:
        """Construir contexto específico para cada tipo de intención"""
        context_parts = []
        
        if intent == "consulta_pedido" and "pedido_info" in context_data:
            pedido = context_data["pedido_info"]
            context_parts.append(f"Información del pedido: {pedido}")
        
        elif intent == "consulta_producto" and "productos" in context_data:
            productos = context_data["productos"]
            context_parts.append(f"Productos encontrados: {productos}")
        
        elif intent == "politicas_empresa" and "politica_info" in context_data:
            politica = context_data["politica_info"]
            context_parts.append(f"Información de políticas: {politica}")
        
        # Agregar entidades extraídas
        if entities:
            context_parts.append(f"Datos extraídos: {entities}")
        
        return "\n".join(context_parts) if context_parts else "No hay contexto específico disponible."
