from app.services.ai_service import IntentClassifier, LLMService
from app.services.database_service import DatabaseService, ResponseGenerator
from app.services.technology_context import tech_context
from app.models.pydantic_models import ConversationCreate
from typing import List
from datetime import datetime
import uuid
from app.services.nlp_utils import extract_keywords

# Agentic System Imports
from app.services.agent_tools import ToolRegistry, DatabaseQueryTool, CalculationTool, TextProcessingTool
from app.services.query_decomposition import QueryDecomposer, QueryType
from app.services.agent_orchestrator import AgentOrchestrator
import logging

logger = logging.getLogger(__name__)

class ChatbotService:
    """Servicio principal del chatbot con memoria simple y capacidades agenticas"""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.intent_classifier = IntentClassifier()
        self.llm_service = LLMService()
        self.response_generator = ResponseGenerator(self.db_service)
        
        # Simple conversation memory (in-memory for current session)
        self.conversation_history = []
        self.max_history = 20  # Máximo 20 conversaciones en memoria
        
        # Inicializar sistema agentico
        self._initialize_agentic_system()
        
        # Control de modo: 'simple' para consultas básicas, 'agentic' para complejas
        self.processing_mode = "adaptive"  # adaptive, simple, agentic
    
    def _initialize_agentic_system(self):
        """Inicializar el sistema agentico con herramientas y orquestador"""
        try:
            # Crear registro de herramientas
            self.tool_registry = ToolRegistry()
            
            # Registrar herramientas disponibles
            self.tool_registry.register_tool(DatabaseQueryTool(self.db_service))
            self.tool_registry.register_tool(CalculationTool())
            self.tool_registry.register_tool(TextProcessingTool())
            
            # Crear descomponedor de consultas
            self.query_decomposer = QueryDecomposer(self.llm_service)
            
            # Crear orquestador de agentes
            self.agent_orchestrator = AgentOrchestrator(
                tool_registry=self.tool_registry,
                max_concurrent_tasks=3
            )
            
            self.agentic_enabled = True
            logger.info("Agentic system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agentic system: {str(e)}")
            self.agentic_enabled = False
    
    async def process_message(self, user_message: str) -> dict:
        """Procesar mensaje del usuario con memoria simple y capacidades agenticas"""
        try:
            # 1. Detectar si hay múltiples preguntas
            questions = self._detect_multiple_questions(user_message)
            
            if len(questions) > 1:
                # Procesar múltiples preguntas
                responses = []
                combined_intents = []
                combined_entities = {}
                
                for i, question in enumerate(questions[:3]):  # Máximo 3 preguntas
                    # Procesar cada pregunta individualmente con AI
                    intent = self.intent_classifier.classify_intent(question)
                    entities = self.intent_classifier.extract_entities(question, intent)
                    
                    # Obtener datos de contexto
                    context_data = self._get_context_data(intent, entities, question)
                    
                    # Generar respuesta con AI (Gemini) con mejor formato
                    if self.llm_service.gemini_service.is_available():
                        ai_response = await self._generate_ai_response_with_format(
                            question, intent, entities, context_data
                        )
                        response = ai_response
                    else:
                        # Fallback to ResponseGenerator
                        response = self._get_fallback_response(intent, entities, question)
                    
                    responses.append(f"**{i+1}.** {response}")
                    combined_intents.append(intent)
                    combined_entities.update(entities)
                
                # Combinar respuestas
                final_response = "\n\n".join(responses)
                main_intent = combined_intents[0] if combined_intents else "multiple_questions"
                
            else:
                # Procesar pregunta única con AI mejorada
                intent = self.intent_classifier.classify_intent(user_message)
                complexity = self.intent_classifier.determine_query_complexity(user_message, intent)
                entities = self.intent_classifier.extract_entities(user_message, intent)
                
                # Obtener datos de contexto
                context_data = self._get_context_data(intent, entities, user_message)
                
                # SIEMPRE obtener datos reales de la base de datos primero
                db_context = self._get_comprehensive_context(user_message, intent, entities)
                
                # Generar respuesta con AI (Gemini) usando contexto real de BD
                if self.llm_service.gemini_service.is_available():
                    final_response = await self._generate_ai_response_with_db_context(
                        user_message, intent, entities, db_context
                    )
                else:
                    # Si Gemini no está disponible, usar datos de BD directamente
                    final_response = self._generate_direct_db_response(user_message, intent, entities, db_context)
                
                main_intent = intent
                combined_entities = entities
            
            # 5. Limpiar y formatear respuesta
            response = self._clean_output(final_response)
            
            # 6. Usar contexto de conversaciones anteriores para mejorar respuesta
            context_from_history = self._get_conversation_context(user_message)
            if context_from_history:
                # Si hay contexto relevante, agregarlo a la respuesta
                if "pedido" in user_message.lower() and any("pedido" in prev.lower() for prev in context_from_history):
                    response = f"{response}\n\n*Nota: He detectado que has preguntado sobre pedidos antes.*"
            
            # 7. Guardar en memoria simple (mantener solo las últimas conversaciones)
            self.conversation_history.append({
                "timestamp": datetime.now(),
                "user_message": user_message,
                "bot_response": response,
                "intent": main_intent,
                "entities": combined_entities
            })
            
            # Mantener solo las últimas conversaciones en memoria
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history:]
            
            logger.info(f"Conversación #{len(self.conversation_history)} guardada en memoria")
            
            # 8. Retornar respuesta estructurada
            return {
                "respuesta": response,
                "intencion": main_intent,
                "timestamp": datetime.now(),
                "entities": combined_entities,
                "processing_mode": "ai_enhanced",
                "complexity": "simple",
                "conversation_length": len(self.conversation_history),
                "multiple_questions": len(questions) > 1
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_response = "Lo siento, ocurrió un error. Por favor intenta nuevamente."
            
            return {
                "respuesta": error_response,
                "intencion": "error",
                "timestamp": datetime.now(),
                "entities": {},
                "error": str(e),
                "processing_mode": "error"
            }
    
    def get_conversation_history(self, limit: int = 10) -> list:
        """Obtener historial de conversación simple de la sesión actual"""
        return self.conversation_history[-limit:] if limit > 0 else self.conversation_history
    
    def _get_conversation_context(self, current_message: str) -> list:
        """Obtener contexto relevante de conversaciones anteriores"""
        if not self.conversation_history:
            return []
        
        # Buscar conversaciones similares en los últimos 5 mensajes
        recent_history = self.conversation_history[-5:]
        relevant_messages = []
        
        current_lower = current_message.lower()
        keywords = ["pedido", "producto", "cliente", "orden"]
        
        for conv in recent_history:
            prev_message = conv["user_message"].lower()
            # Si comparten palabras clave, es contexto relevante
            if any(keyword in current_lower and keyword in prev_message for keyword in keywords):
                relevant_messages.append(conv["user_message"])
        
        return relevant_messages
    
    def get_memory_summary(self) -> str:
        """Obtener resumen de la memoria de conversaciones para debugging"""
        if not self.conversation_history:
            return "**Memoria vacía** - No hay conversaciones previas."
        
        total = len(self.conversation_history)
        recent = self.conversation_history[-3:]  # Últimas 3
        
        summary = f"**Memoria del chat** ({total} conversaciones)\n\n"
        summary += "**Últimas conversaciones:**\n"
        
        for i, conv in enumerate(recent, 1):
            timestamp = conv["timestamp"].strftime("%H:%M:%S")
            user_msg = conv["user_message"][:40] + "..." if len(conv["user_message"]) > 40 else conv["user_message"]
            summary += f"{i}. [{timestamp}] Usuario: {user_msg}\n"
        
        return summary
    
    def _get_comprehensive_context(self, user_message: str, intent: str, entities: dict) -> dict:
        """Obtener contexto completo y real de la base de datos para cualquier consulta"""
        context = {
            "pedidos": {"data": [], "total": 0, "por_estado": {}},
            "productos": {"data": [], "total": 0, "por_disponibilidad": {}}, 
            "politicas": {"data": [], "topics": []},
            "query_specific": {}
        }
        
        try:
            # SIEMPRE obtener datos de las 3 tablas principales
            
            # 1. PEDIDOS - obtener todos y estadísticas
            all_orders = self.db_service.get_all_orders()
            context["pedidos"]["data"] = all_orders
            context["pedidos"]["total"] = len(all_orders)
            
            # Agrupar pedidos por estado
            estados = {}
            for order in all_orders:
                estado = order.get('status', 'Sin estado')
                estados[estado] = estados.get(estado, 0) + 1
            context["pedidos"]["por_estado"] = estados
            
            # 2. PRODUCTOS - obtener todos y estadísticas  
            all_products = self.db_service.get_all_products_detailed()
            context["productos"]["data"] = all_products
            context["productos"]["total"] = len(all_products)
            
            # Agrupar productos por disponibilidad
            disponibilidad = {}
            for product in all_products:
                disp = product.get('availability', 'Sin información')
                disponibilidad[disp] = disponibilidad.get(disp, 0) + 1
            context["productos"]["por_disponibilidad"] = disponibilidad
            
            # 3. INFO EMPRESA - obtener todas las políticas
            all_policies = self.db_service.get_all_company_info()
            context["politicas"]["data"] = all_policies
            context["politicas"]["topics"] = [p.get('topic', '') for p in all_policies]
            
            # 4. ANÁLISIS ESPECÍFICO según el mensaje del usuario
            message_lower = user_message.lower()
            
            # MEJORADO: Búsqueda avanzada de PEDIDOS
            if any(word in message_lower for word in ["pedido", "orden", "ped-", "entrega", "envío", "compra"]):
                # Buscar por ID específico
                if entities.get("numero_pedido"):
                    specific_order = self.db_service.get_order_by_id(entities["numero_pedido"])
                    context["query_specific"]["pedido_buscado"] = specific_order
                
                # Buscar por estado específico - MEJORADO
                estado_keywords = {
                    "entregado": ["entregado", "entregados", "completado", "completados", "finalizado"],
                    "en tránsito": ["transito", "tránsito", "enviado", "enviados", "camino", "proceso"],
                    "cancelado": ["cancelado", "cancelados", "anulado", "anulados"],
                    "pendiente": ["pendiente", "pendientes", "espera", "procesando"],
                    "devuelto": ["devuelto", "devueltos", "devolución", "retornado"]
                }
                
                estado_encontrado = None
                for estado, keywords in estado_keywords.items():
                    if any(kw in message_lower for kw in keywords):
                        estado_encontrado = estado
                        break
                
                if estado_encontrado:
                    # Filtrar pedidos por estado encontrado
                    pedidos_filtrados = [o for o in all_orders if o.get('status', '').lower() == estado_encontrado.lower()]
                    context["query_specific"]["pedidos_por_estado"] = pedidos_filtrados
                    context["query_specific"]["estado_buscado"] = estado_encontrado
                
                # Si pregunta por "todos los pedidos" o lista general
                elif any(phrase in message_lower for phrase in ["todos los pedidos", "lista de pedidos", "mostrar pedidos", "ver pedidos"]):
                    context["query_specific"]["todos_los_pedidos"] = all_orders
                
                # Buscar por cliente específico
                if "cliente" in message_lower:
                    # Extraer nombre del cliente si se menciona
                    for order in all_orders:
                        customer = order.get('customer_name', '').lower()
                        if customer and customer in message_lower:
                            pedidos_cliente = [o for o in all_orders if o.get('customer_name', '').lower() == customer]
                            context["query_specific"]["pedidos_cliente"] = pedidos_cliente
                            context["query_specific"]["cliente_buscado"] = customer
                            break
            
            # Si pregunta por productos específicos
            if any(word in message_lower for word in ["producto", "inventario", "stock", "catálogo"]):
                # Productos en stock
                if any(phrase in message_lower for phrase in ["en stock", "disponibles", "stock"]):
                    productos_stock = [p for p in all_products if p.get('availability') == 'En stock']
                    context["query_specific"]["productos_en_stock"] = productos_stock
                
                # Productos bajo demanda
                if any(phrase in message_lower for phrase in ["bajo demanda", "demanda"]):
                    productos_demanda = [p for p in all_products if 'bajo demanda' in str(p.get('availability', '')).lower()]
                    context["query_specific"]["productos_bajo_demanda"] = productos_demanda
                
                # Búsqueda por keywords
                if entities.get("producto_keywords"):
                    productos_encontrados = self.db_service.search_products(entities["producto_keywords"])
                    context["query_specific"]["productos_buscados"] = productos_encontrados
            
            # MEJORADO: Búsqueda inteligente de POLÍTICAS basada en los 40 temas reales
            # Detectar si el usuario pregunta sobre políticas, normas, procedimientos, etc.
            policy_triggers = ["política", "políticas", "norma", "regla", "procedimiento", "término", "condición",
                             "horario", "devolución", "garantía", "reembolso", "envío", "entrega", "pago",
                             "privacidad", "datos", "cookie", "denuncia", "ética", "lealtad", "regalo",
                             "sostenibilidad", "igualdad", "discriminación", "inflación", "responsabilidad"]
            
            if any(word in message_lower for word in policy_triggers):
                politicas_relevantes = []
                
                # Mapa completo de categorías de políticas basado en los 40 registros reales
                policy_categories = {
                    "horarios": {
                        "keywords": ["horario", "hora", "abierto", "cerrado", "atención", "soporte", "tienda", 
                                    "festivo", "domingo", "sábado", "lunes", "viernes", "entrega", "franja"],
                        "topics": ["Horario de Atención al Cliente", "Horario de Soporte Técnico", 
                                  "Horario de Tiendas Físicas", "Horario de Días Festivos", "Horarios de Entrega a Domicilio"]
                    },
                    "devoluciones": {
                        "keywords": ["devolución", "devolver", "retorno", "reembolso", "garantía", "defecto", 
                                    "cambio", "truque", "reclamar", "días", "30 días", "15 días"],
                        "topics": ["Política de Devoluciones", "Proceso para Devoluciones", "Política de Reembolsos",
                                  "Política de Garantía de Productos", "Cómo Reclamar una Garantía", 
                                  "Política de Cambios y Trueques"]
                    },
                    "privacidad": {
                        "keywords": ["privacidad", "datos", "información personal", "cookie", "confidencial",
                                    "eliminar", "acceso", "GDPR", "protección", "terceros"],
                        "topics": ["Política de Privacidad de Datos", "Uso de Información Personal", "Política de Cookies",
                                  "Acceso a la Información del Cliente", "Derecho a la Eliminación de Datos"]
                    },
                    "envios": {
                        "keywords": ["envío", "entrega", "shipping", "domicilio", "costo", "gratis", "express",
                                    "estándar", "nacional", "tarifa", "200.000", "15.000"],
                        "topics": ["Política de Envíos Nacionales", "Costos de Envío", "Horarios de Entrega a Domicilio"]
                    },
                    "pagos": {
                        "keywords": ["pago", "tarjeta", "crédito", "débito", "PSE", "efectivo", "visa", "mastercard",
                                    "transacción", "segura", "encriptada", "método"],
                        "topics": ["Métodos de Pago Aceptados", "Política de Seguridad en Pagos"]
                    },
                    "terminos": {
                        "keywords": ["términos", "condiciones", "servicio", "uso", "aceptable", "propiedad intelectual",
                                    "contraseña", "responsabilidad", "usuario"],
                        "topics": ["Términos y Condiciones del Servicio", "Política de Uso Aceptable", "Propiedad Intelectual",
                                  "Política de Contraseña Segura", "Responsabilidad del Usuario"]
                    },
                    "pedidos": {
                        "keywords": ["cancelar", "cancelación", "pedido", "error", "inventario", "precio", "promoción"],
                        "topics": ["Política de Cancelación de Pedidos", "Política de Errores de Inventario", 
                                  "Política de Precios y Promociones"]
                    },
                    "cliente": {
                        "keywords": ["conducta", "comportamiento", "respeto", "trato", "cliente", "notificación", "cambios"],
                        "topics": ["Código de Conducta del Cliente", "Notificaciones de Cambios en Políticas"]
                    },
                    "programas": {
                        "keywords": ["lealtad", "puntos", "regalo", "tarjeta", "descuento", "canjear", "vencimiento"],
                        "topics": ["Programa de Lealtad", "Condiciones del Programa de Lealtad", 
                                  "Política de Tarjetas de Regalo", "Restricciones de Tarjetas de Regalo"]
                    },
                    "empresa": {
                        "keywords": ["sostenibilidad", "reciclable", "carbono", "reseña", "opinión", "contacto", "legal",
                                    "denuncia", "ética", "igualdad", "discriminación", "inclusivo", "inflación", "ajuste"],
                        "topics": ["Política de Sostenibilidad", "Política de Reseñas de Productos", 
                                  "Contacto para Asuntos de Políticas", "Canal de Denuncias Éticas",
                                  "Política de Igualdad y no Discriminación", "Ajustes por Inflación de Precios"]
                    }
                }
                
                # Buscar políticas relevantes usando búsqueda inteligente
                for policy in all_policies:
                    topic = policy.get('topic', '')
                    topic_lower = topic.lower()
                    info_lower = policy.get('info', '').lower()
                    
                    # Puntuación de relevancia
                    relevance_score = 0
                    
                    # Verificar cada categoría
                    for category, details in policy_categories.items():
                        # Verificar si alguna keyword de la categoría está en el mensaje
                        for keyword in details["keywords"]:
                            if keyword in message_lower:
                                # Si el topic está en la lista de topics de esta categoría
                                if topic in details["topics"]:
                                    relevance_score += 3  # Alta relevancia
                                # Si la keyword está en el topic o info
                                elif keyword in topic_lower or keyword in info_lower:
                                    relevance_score += 2  # Media relevancia
                    
                    # Búsqueda directa: si palabras del mensaje están en el topic
                    words_in_message = [w for w in message_lower.split() if len(w) > 3]
                    for word in words_in_message:
                        if word in topic_lower:
                            relevance_score += 1
                    
                    # Si tiene alguna relevancia, agregar a la lista
                    if relevance_score > 0:
                        politicas_relevantes.append((policy, relevance_score))
                
                # Ordenar por relevancia y tomar las más relevantes
                if politicas_relevantes:
                    politicas_relevantes.sort(key=lambda x: x[1], reverse=True)
                    # Tomar solo las políticas (sin el score) y limitar a las 10 más relevantes
                    politicas_finales = [p[0] for p in politicas_relevantes[:10]]
                    context["query_specific"]["politicas_relevantes"] = politicas_finales
                    context["query_specific"]["num_politicas_encontradas"] = len(politicas_finales)
                
                # Si no se encontraron políticas específicas pero pidió todas
                elif any(phrase in message_lower for phrase in ["todas las políticas", "lista de políticas", "todas las normas", "todos los procedimientos"]):
                    context["query_specific"]["todas_las_politicas"] = all_policies
        
        except Exception as e:
            logger.error(f"Error obteniendo contexto comprehensivo: {e}")
        
        return context
    
    async def _generate_ai_response_with_db_context(self, user_message: str, intent: str, entities: dict, db_context: dict) -> str:
        """Generar respuesta AI usando contexto real completo de la base de datos"""
        try:
            # Construir prompt con datos reales específicos para la consulta
            context_info = self._build_rich_context_prompt(user_message, db_context)
            
            enhanced_prompt = f"""
CONTEXTO DE LA BASE DE DATOS WAVER:
{context_info}

PREGUNTA DEL ADMINISTRADOR: {user_message}

INSTRUCCIONES CRÍTICAS:
- Eres un asistente administrativo experto de Waver (tienda de tecnología)
- OBLIGATORIO: Usa TODOS los datos reales proporcionados arriba
- Si encuentras información de POLÍTICAS, muestra el TÍTULO completo y la INFORMACIÓN completa
- Para PEDIDOS: muestra ID, cliente y estado
- Para PRODUCTOS: muestra nombre e ID
- Formato estricto: **títulos en negrita**, • para listas, números para enumeraciones
- Si hay múltiples resultados, MUESTRA TODOS (no solo ejemplos)
- PROHIBIDO decir "no se encuentra información" si los datos están en el contexto
- PROHIBIDO inventar o suponer datos
- Responde SIEMPRE en español profesional
- Si preguntan por políticas, horarios, devoluciones, etc., busca en las POLÍTICAS RELEVANTES del contexto
- Cuando des información de políticas, cita el nombre exacto de la política

Genera una respuesta completa y precisa basada ÚNICAMENTE en los datos proporcionados.
"""

            ai_response = self.llm_service.gemini_service.generate_response(
                enhanced_prompt, "", max_tokens=300
            )
            
            # Validar que la respuesta AI use los datos reales
            if ai_response and len(ai_response.strip()) > 10:
                # Verificar que no sea una respuesta genérica
                generic_phrases = ["no tengo información", "no puedo acceder", "no tengo acceso", 
                                 "no dispongo de", "no hay información disponible"]
                response_lower = ai_response.lower()
                
                # Si detectamos respuesta genérica cuando sí hay datos, usar respuesta directa
                if any(phrase in response_lower for phrase in generic_phrases) and self._has_relevant_data(db_context):
                    logger.warning("AI gave generic response despite having data, using direct DB response")
                    return self._generate_direct_db_response(user_message, intent, entities, db_context)
                
                return ai_response
            else:
                # Si Gemini falla, usar respuesta directa con datos
                return self._generate_direct_db_response(user_message, intent, entities, db_context)
                
        except Exception as e:
            logger.error(f"Error generating AI response with DB context: {e}")
            return self._generate_direct_db_response(user_message, intent, entities, db_context)
    
    def _build_rich_context_prompt(self, user_message: str, db_context: dict) -> str:
        """Construir prompt rico con datos específicos de la consulta"""
        context_parts = []
        
        # Información general de las tablas
        context_parts.append(f"RESUMEN GENERAL:")
        context_parts.append(f"- Pedidos registrados: {db_context['pedidos']['total']} (IDs como PED-001, PED-002...)")
        context_parts.append(f"- Productos en catálogo: {db_context['productos']['total']} (IDs como PRD-001, PRD-002...)")
        context_parts.append(f"- Políticas configuradas: {len(db_context['politicas']['data'])}")
        
        # Estados de pedidos
        if db_context['pedidos']['por_estado']:
            context_parts.append(f"\nESTADOS DE PEDIDOS:")
            for estado, cantidad in db_context['pedidos']['por_estado'].items():
                context_parts.append(f"- {estado}: {cantidad} pedidos")
        
        # Disponibilidad de productos
        if db_context['productos']['por_disponibilidad']:
            context_parts.append(f"\nDISPONIBILIDAD DE PRODUCTOS:")
            for disp, cantidad in db_context['productos']['por_disponibilidad'].items():
                context_parts.append(f"- {disp}: {cantidad} productos")
        
        # Datos específicos según la consulta
        query_specific = db_context.get('query_specific', {})
        
        # PEDIDOS ESPECÍFICOS
        if query_specific.get('pedido_buscado'):
            pedido = query_specific['pedido_buscado']
            context_parts.append(f"\nPEDIDO ESPECÍFICO ENCONTRADO:")
            context_parts.append(f"- ID: {pedido.get('order_id', 'N/A')}")
            context_parts.append(f"- Cliente: {pedido.get('customer_name', 'N/A')}")
            context_parts.append(f"- Estado: {pedido.get('status', 'N/A')}")
        
        if query_specific.get('pedidos_por_estado'):
            pedidos = query_specific['pedidos_por_estado']
            estado_buscado = query_specific.get('estado_buscado', 'consultado')
            context_parts.append(f"\nPEDIDOS CON ESTADO '{estado_buscado.upper()}' ({len(pedidos)} encontrados):")
            # Mostrar TODOS los pedidos encontrados, no limitarse a 5
            for i, pedido in enumerate(pedidos, 1):
                context_parts.append(f"{i}. ID: {pedido.get('order_id', '')} - Cliente: {pedido.get('customer_name', '')} - Estado: {pedido.get('status', '')}")
        
        if query_specific.get('todos_los_pedidos'):
            pedidos = query_specific['todos_los_pedidos']
            context_parts.append(f"\nTODOS LOS PEDIDOS ({len(pedidos)}):")
            for i, pedido in enumerate(pedidos, 1):
                context_parts.append(f"{i}. ID: {pedido.get('order_id', '')} - Cliente: {pedido.get('customer_name', '')} - Estado: {pedido.get('status', '')}")
        
        if query_specific.get('pedidos_cliente'):
            pedidos = query_specific['pedidos_cliente']
            cliente = query_specific.get('cliente_buscado', '')
            context_parts.append(f"\nPEDIDOS DEL CLIENTE '{cliente.upper()}' ({len(pedidos)}):")
            for i, pedido in enumerate(pedidos, 1):
                context_parts.append(f"{i}. ID: {pedido.get('order_id', '')} - Estado: {pedido.get('status', '')}")
        
        # PRODUCTOS
        if query_specific.get('productos_en_stock'):
            productos = query_specific['productos_en_stock']
            context_parts.append(f"\nPRODUCTOS EN STOCK COMPLETOS ({len(productos)}):")
            for i, producto in enumerate(productos, 1):
                name = producto.get('product_name', 'Sin nombre')
                prod_id = producto.get('product_id', '')
                context_parts.append(f"{i}. {name} (ID: {prod_id})")
        
        if query_specific.get('productos_bajo_demanda'):
            productos = query_specific['productos_bajo_demanda']
            context_parts.append(f"\nPRODUCTOS BAJO DEMANDA ({len(productos)}):")
            for i, producto in enumerate(productos, 1):
                name = producto.get('product_name', 'Sin nombre')
                prod_id = producto.get('product_id', '')
                context_parts.append(f"{i}. {name} (ID: {prod_id})")
        
        if query_specific.get('productos_buscados'):
            productos = query_specific['productos_buscados']
            context_parts.append(f"\nPRODUCTOS ENCONTRADOS EN BÚSQUEDA ({len(productos)}):")
            for i, producto in enumerate(productos, 1):
                name = producto.get('product_name', 'Sin nombre')
                disp = producto.get('availability', 'N/A')
                prod_id = producto.get('product_id', '')
                context_parts.append(f"{i}. {name} - {disp} (ID: {prod_id})")
        
        # POLÍTICAS MEJORADO - Mostrar información COMPLETA
        if query_specific.get('politicas_relevantes'):
            politicas = query_specific['politicas_relevantes']
            context_parts.append(f"\nPOLÍTICAS RELEVANTES ENCONTRADAS ({len(politicas)}):")
            for i, politica in enumerate(politicas, 1):
                topic = politica.get('topic', 'Sin tema')
                info = politica.get('info', 'Sin información')
                # Mostrar información COMPLETA de cada política (sin truncar)
                context_parts.append(f"\n{i}. POLÍTICA: {topic}")
                context_parts.append(f"   INFORMACIÓN COMPLETA: {info}")
        
        if query_specific.get('todas_las_politicas'):
            politicas = query_specific['todas_las_politicas']
            context_parts.append(f"\nTODAS LAS POLÍTICAS DISPONIBLES ({len(politicas)}):")
            for i, politica in enumerate(politicas, 1):
                topic = politica.get('topic', 'Sin tema')
                context_parts.append(f"{i}. {topic}")
        
        # Si no hay datos específicos, dar información general
        if not any(query_specific.values()):
            # Información general de pedidos
            if db_context['pedidos']['data']:
                context_parts.append(f"\nINFORMACIÓN GENERAL DE PEDIDOS:")
                context_parts.append(f"Total de pedidos: {len(db_context['pedidos']['data'])}")
                if db_context['pedidos']['por_estado']:
                    for estado, cantidad in db_context['pedidos']['por_estado'].items():
                        context_parts.append(f"- {estado}: {cantidad}")
            
            # Información general de productos
            if db_context['productos']['data']:
                context_parts.append(f"\nINFORMACIÓN GENERAL DE PRODUCTOS:")
                context_parts.append(f"Total en catálogo: {len(db_context['productos']['data'])}")
                if db_context['productos']['por_disponibilidad']:
                    for disp, cantidad in db_context['productos']['por_disponibilidad'].items():
                        context_parts.append(f"- {disp}: {cantidad}")
            
            # Lista de temas de políticas disponibles
            if db_context['politicas']['topics']:
                context_parts.append(f"\nTEMAS DE POLÍTICAS DISPONIBLES:")
                for i, topic in enumerate(db_context['politicas']['topics'][:10], 1):
                    context_parts.append(f"{i}. {topic}")
        
        return "\n".join(context_parts)
    
    def _has_relevant_data(self, db_context: dict) -> bool:
        """Verificar si el contexto tiene datos relevantes"""
        # Verificar si hay datos en las tablas principales
        has_orders = db_context.get('pedidos', {}).get('total', 0) > 0
        has_products = db_context.get('productos', {}).get('total', 0) > 0
        has_policies = len(db_context.get('politicas', {}).get('data', [])) > 0
        
        # Verificar si hay datos específicos de la consulta
        query_specific = db_context.get('query_specific', {})
        has_specific_data = any(query_specific.values())
        
        return has_orders or has_products or has_policies or has_specific_data
    
    def _generate_direct_db_response(self, user_message: str, intent: str, entities: dict, db_context: dict) -> str:
        """Generar respuesta directa usando solo datos de BD cuando Gemini no está disponible"""
        message_lower = user_message.lower()
        query_specific = db_context.get('query_specific', {})
        
        # PEDIDOS - Respuestas mejoradas
        if query_specific.get('pedido_buscado'):
            pedido = query_specific['pedido_buscado']
            return f"**Pedido {pedido.get('order_id', '')}**\n\n• Cliente: {pedido.get('customer_name', '')}\n• Estado: {pedido.get('status', '')}"
        
        if query_specific.get('pedidos_por_estado'):
            pedidos = query_specific['pedidos_por_estado']
            estado = query_specific.get('estado_buscado', 'consultado')
            if pedidos:
                pedido_list = "\n".join([f"{i}. **{p.get('order_id', '')}** - Cliente: {p.get('customer_name', '')} - Estado: {p.get('status', '')}" 
                                         for i, p in enumerate(pedidos, 1)])
                return f"**Pedidos con estado '{estado.upper()}'** ({len(pedidos)} encontrados)\n\n{pedido_list}"
            else:
                return f"**No se encontraron pedidos con estado '{estado}'**\n\nEstados disponibles: {', '.join(db_context['pedidos']['por_estado'].keys())}"
        
        if query_specific.get('todos_los_pedidos'):
            pedidos = query_specific['todos_los_pedidos']
            if pedidos:
                pedido_list = "\n".join([f"{i}. **{p.get('order_id', '')}** - {p.get('customer_name', '')} ({p.get('status', '')})" 
                                         for i, p in enumerate(pedidos, 1)])
                return f"**Lista completa de pedidos** ({len(pedidos)} pedidos)\n\n{pedido_list}"
        
        if query_specific.get('pedidos_cliente'):
            pedidos = query_specific['pedidos_cliente']
            cliente = query_specific.get('cliente_buscado', '')
            pedido_list = "\n".join([f"{i}. **{p.get('order_id', '')}** - Estado: {p.get('status', '')}" 
                                     for i, p in enumerate(pedidos, 1)])
            return f"**Pedidos del cliente '{cliente.title()}'** ({len(pedidos)} pedidos)\n\n{pedido_list}"
        
        # PRODUCTOS
        if query_specific.get('productos_en_stock'):
            productos = query_specific['productos_en_stock']
            product_list = "\n".join([f"{i}. {p.get('product_name', '')} (ID: {p.get('product_id', '')})" 
                                      for i, p in enumerate(productos, 1)])
            return f"**Productos en Stock** ({len(productos)})\n\n{product_list}"
        
        if query_specific.get('productos_bajo_demanda'):
            productos = query_specific['productos_bajo_demanda']
            product_list = "\n".join([f"{i}. {p.get('product_name', '')} (ID: {p.get('product_id', '')})" 
                                      for i, p in enumerate(productos, 1)])
            return f"**Productos Bajo Demanda** ({len(productos)})\n\n{product_list}"
        
        # POLÍTICAS - Mostrar información COMPLETA
        if query_specific.get('politicas_relevantes'):
            politicas = query_specific['politicas_relevantes']
            response = f"**Políticas relevantes encontradas** ({len(politicas)})\n\n"
            for i, politica in enumerate(politicas, 1):
                topic = politica.get('topic', 'Sin tema')
                info = politica.get('info', 'Sin información')
                # Mostrar la información COMPLETA sin truncar
                response += f"**{i}. {topic}**\n\n{info}\n\n"
                response += "-" * 60 + "\n\n"  # Separador entre políticas
            return response
        
        if query_specific.get('todas_las_politicas'):
            politicas = query_specific['todas_las_politicas']
            topics_list = "\n".join([f"{i}. {p.get('topic', '')}" for i, p in enumerate(politicas, 1)])
            return f"**Todas las políticas disponibles** ({len(politicas)} políticas)\n\n{topics_list}\n\n*Para ver detalles de una política específica, pregunta por su nombre*"
        
        # Respuesta general mejorada con información de las 3 tablas
        pedidos_total = db_context['pedidos']['total']
        productos_total = db_context['productos']['total']
        politicas_total = len(db_context['politicas']['data'])
        
        response = f"**Panel Administrativo Waver**\n\n"
        response += f"**Resumen del sistema:**\n"
        response += f"• Pedidos registrados: {pedidos_total}\n"
        response += f"• Productos en catálogo: {productos_total}\n"
        response += f"• Políticas configuradas: {politicas_total}\n\n"
        
        if db_context['pedidos']['por_estado']:
            response += "**Estados de pedidos:**\n"
            for estado, cant in db_context['pedidos']['por_estado'].items():
                response += f"• {estado}: {cant}\n"
        
        response += "\n*Puedes consultar pedidos por estado, productos en stock, o políticas específicas*"
        
        return response
    
    def _detect_multiple_questions(self, user_message: str) -> List[str]:
        """Detectar si hay múltiples preguntas en el mensaje"""
        # Separadores comunes para múltiples preguntas
        separators = [' y ', ' y también ', ', ', '?', ' además ', ' por otro lado ', ' otra cosa ']
        
        # Dividir por separadores
        questions = [user_message]
        for sep in separators:
            new_questions = []
            for q in questions:
                parts = q.split(sep)
                new_questions.extend([p.strip() for p in parts if p.strip()])
            questions = new_questions
        
        # Filtrar preguntas válidas (mínimo 5 caracteres)
        valid_questions = [q for q in questions if len(q) >= 5]
        
        return valid_questions if len(valid_questions) > 1 else [user_message]
    
    async def _generate_ai_response_with_format(self, user_message: str, intent: str, entities: dict, context_data: dict) -> str:
        """Generar respuesta AI con formato mejorado y datos precisos de BD"""
        try:
            # Primero verificar si tenemos datos reales para respuestas precisas
            precise_data = None
            
            if intent == "consulta_pedido":
                numero_pedido = entities.get("numero_pedido")
                if numero_pedido:
                    order = self.db_service.get_order_by_id(numero_pedido)
                    if order:
                        precise_data = f"**Pedido {order.get('order_id', '')}**\n\n• Estado: {order.get('status', '')}\n• Cliente: {order.get('customer_name', '')}"
                    else:
                        # Datos reales de cuántos pedidos existen
                        all_orders = self.db_service.get_all_orders()
                        existing_ids = [o.get('order_id', '') for o in all_orders]
                        precise_data = f"**Pedido no encontrado**\n\nEl pedido {numero_pedido} no existe en el sistema.\n\n• Total de pedidos registrados: {len(existing_ids)}\n• Últimos IDs: {', '.join(existing_ids[-5:]) if existing_ids else 'ninguno'}"
            
            elif intent == "consulta_analitica":
                # Para consultas analíticas, usar datos directos de BD
                precise_data = self.response_generator.generate_analytics_response(intent, user_message)
            
            # NUEVO: consultas de productos "bajo demanda"
            elif intent == "consulta_producto":
                msg = user_message.lower()
                if any(t in msg for t in ["bajo demanda", "on demand", "a demanda", "demanda"]):
                    precise_data = self.response_generator.generate_product_response(entities, user_message)
            
            # Si tenemos datos precisos de BD, usarlos directamente
            if precise_data:
                return precise_data
            
            # Si no, usar AI con contexto de BD pero formato mejorado
            context_info = ""
            if context_data.get("pedido_info"):
                context_info += f"Información de pedido: {context_data['pedido_info']}\n"
            if context_data.get("productos"):
                context_info += f"Productos encontrados: {context_data['productos']}\n"
            if context_data.get("productos_bajo_demanda"):
                names = ", ".join([p.get('product_name', 'Producto') for p in context_data["productos_bajo_demanda"][:5]])
                context_info += f"Productos bajo demanda (ejemplos): {names}\n"
            if context_data.get("politica_info"):
                context_info += f"Políticas: {context_data['politica_info']}\n"
            if context_data.get("analytics_data"):
                context_info += f"Datos analíticos: {context_data['analytics_data']}\n"
            
            # Usar prompt mejorado para formato profesional
            enhanced_prompt = f"""
Usuario (Panel Admin): {user_message}

Información de base de datos:
{context_info}

Instrucciones de formato:
- Usa **títulos en negrita** para secciones importantes
- Usa • para bullet points (NO asteriscos)
- Respuesta concisa pero completa para administrador
- Información precisa y útil
- NO uses emojis, tono profesional
- Estructura clara con espaciado apropiado
- SIEMPRE en español

Genera una respuesta profesional y bien formateada.
"""
            
            ai_response = self.llm_service.gemini_service.generate_response(
                enhanced_prompt, context_info, max_tokens=200
            )
            
            # Verificar calidad de respuesta AI
            if (ai_response and 
                "no está disponible" not in ai_response.lower() and 
                "ocurrió un error" not in ai_response.lower() and
                len(ai_response.strip()) > 20):
                
                # Aplicar mejoras de formato si es necesario
                formatted_response = self._improve_response_format(ai_response)
                return formatted_response
            else:
                # Fallback a ResponseGenerator con formato
                return self._get_fallback_response(intent, entities, user_message)
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_response(intent, entities, user_message)
    
    def _improve_response_format(self, response: str) -> str:
        """Mejorar formato de respuesta AI"""
        # Reemplazar asteriscos con bullets circulares
        response = response.replace('* ', '• ')
        response = response.replace('- ', '• ')
        
        # Asegurar que los títulos estén en negrita
        lines = response.split('\n')
        improved_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('•') and not line.startswith('**') and ':' in line:
                # Posible título, ponerlo en negrita
                if not line.startswith('**'):
                    line = f"**{line.split(':')[0]}**{':' + ':'.join(line.split(':')[1:]) if ':' in line else ''}"
            improved_lines.append(line)
        
        return '\n'.join(improved_lines)
    
    def _get_fallback_response(self, intent: str, entities: dict, user_message: str) -> str:
        """Generar respuesta de fallback con formato mejorado"""
        if intent == "consulta_pedido":
            return self.response_generator.generate_order_response(entities, user_message)
        elif intent == "consulta_producto":
            return self.response_generator.generate_product_response(entities, user_message)
        elif intent == "informacion_politicas":
            return self.response_generator.generate_policy_response(entities, user_message)
        elif intent == "consulta_analitica":
            return self.response_generator.generate_analytics_response(intent, user_message)
        else:
            return self.response_generator.generate_general_response(entities, user_message)
    
    
    async def _should_use_agentic_processing(self, user_message: str, intent: str, complexity: str) -> bool:
        """Determinar si se debe usar procesamiento agentico basado en la complejidad"""
        
        if not self.agentic_enabled:
            return False
        
        # Modo de procesamiento
        if self.processing_mode == "simple":
            return False
        elif self.processing_mode == "agentic":
            return True
        
        # Modo adaptativo: decidir basado en complejidad y patrones
        
        # Siempre usar agentico para consultas complejas
        if complexity == "complex":
            return True
        
        # Usar agentico para consultas analíticas
        if intent == "consulta_analitica":
            return True
        
        # Verificar si la consulta requiere análisis aunque el intent sea otro
        message_lower = user_message.lower()
        
        # Palabras clave que indican necesidad de procesamiento agentico
        agentic_keywords = [
            "estadísticas", "completas", "completo", "comparativas", "comparar",
            "análisis", "resumen", "todos", "cuales", "cuáles", "lista",
            "cuántos", "cuantos", "total", "inventario", "catálogo",
            "disponibles", "tenemos", "general",
            # Keywords específicos de tecnología para análisis
            "smartphones disponibles", "laptops disponibles", "tablets disponibles",
            "productos apple", "productos samsung", "gaming disponible",
            "cámaras disponibles", "audio disponible", "monitores disponibles",
            "categorías de productos", "marcas disponibles", "tipos de productos"
        ]
        
        if any(keyword in message_lower for keyword in agentic_keywords):
            return True
        
        # Usar agentico para consultas comparativas
        comparative_indicators = ["compare", "comparison", "versus", "vs", "difference between", 
                                "mejor que", "comparar", "diferencia entre"]
        if any(indicator in message_lower for indicator in comparative_indicators):
            return True
        
        # Usar agentico para consultas multi-entidad
        multi_entity_indicators = ["and", "y", "both", "ambos", "multiple", "varios", "all", "todos"]
        if any(indicator in message_lower for indicator in multi_entity_indicators):
            return True
        
        # Usar agentico para consultas que requieren cálculos
        calculation_indicators = ["total", "count", "cuantos", "cuántos", "sum", "average", "percentage"]
        if any(indicator in message_lower for indicator in calculation_indicators):
            return True
        
        # Por defecto, usar tradicional para consultas simples
        return False
    
    async def _process_with_agentic_system(self, user_message: str, intent: str, 
                                         entities: dict, complexity: str) -> dict:
        """Procesar consulta usando el sistema agentico completo"""
        
        try:
            # 1. Descomponer la consulta en sub-tareas
            decomposition = await self.query_decomposer.decompose_query(
                user_message, 
                context={
                    "intent": intent,
                    "entities": entities
                }
            )
            
            logger.info(f"Query decomposed into {len(decomposition.sub_tasks)} tasks, "
                       f"type: {decomposition.query_type.value}, "
                       f"complexity: {decomposition.complexity_score}")
            
            # 2. Ejecutar el plan de tareas usando el orquestador
            execution_result = await self.agent_orchestrator.execute_query_plan(
                decomposition,
                context={
                    "user_message": user_message,
                    "intent": intent,
                    "entities": entities
                }
            )
            
            if execution_result.get("success"):
                # 3. Formatear la respuesta final usando Gemini si está disponible
                final_response = await self._enhance_agentic_response(
                    execution_result["result"], user_message, decomposition
                )
                
                return {
                    "respuesta": final_response,
                    "agentic_metadata": {
                        "execution_id": execution_result["execution_id"],
                        "execution_time": execution_result["execution_time"],
                        "tasks_executed": execution_result["tasks_executed"],
                        "query_type": execution_result["query_type"],
                        "complexity_score": execution_result["complexity_score"]
                    },
                    "context_data": execution_result["result"]
                }
            else:
                # Fallback si falla la ejecución agentica
                logger.warning(f"Agentic execution failed: {execution_result.get('error')}")
                return await self._process_with_traditional_system(
                    user_message, intent, entities, complexity
                )
                
        except Exception as e:
            logger.error(f"Agentic processing failed: {str(e)}")
            # Fallback al sistema tradicional
            return await self._process_with_traditional_system(
                user_message, intent, entities, complexity
            )
    
    async def _process_with_traditional_system(self, user_message: str, intent: str, 
                                             entities: dict, complexity: str) -> dict:
        """Procesar consulta usando el sistema tradicional (original)"""
        
        # Obtener datos relevantes de la base de datos si es necesario
        context_data = self._get_context_data(intent, entities, user_message)
        
        # Mejorar manejo de consultas generales de productos
        if intent == "consulta_producto":
            message_lower = user_message.lower()
            if any(word in message_lower for word in ["cuales", "cuáles", "que", "qué", "tenemos", "disponibles", "stock", "inventario"]):
                # Para consultas generales, proporcionar datos útiles directamente
                try:
                    products = self.db_service.get_all_products_detailed()
                    if products:
                        # Crear una respuesta informativa con ejemplos
                        sample_products = products[:5]  # Mostrar 5 ejemplos
                        examples = []
                        for p in sample_products:
                            name = p.get('product_name', 'Producto')
                            availability = p.get('availability', 'Desconocido')
                            examples.append(f"{name} ({availability})")
                        
                        response = f"**Panel Administrativo Waver** - Inventario total: {len(products)} productos. Muestra del inventario:\n\n"
                        response += "\n".join([f"• {ex}" for ex in examples])
                        
                        if len(products) > 5:
                            response += f"\n\n... y {len(products) - 5} productos más."
                        
                        response += "\n\n**¿Quieres información más detallada?** Puedo proporcionarte análisis de:\n"
                        response += "• Smartphones y tablets - Stock, rotación, tendencias\n"
                        response += "• Laptops y computadoras - Disponibilidad por categoría\n"
                        response += "• Monitores - Inventario 4K, gaming, ultrawide\n"
                        response += "• Audio - Stock de auriculares y sistemas de sonido\n"
                        response += "• Gaming - Consolas y accesorios gaming\n"
                        response += "• Cámaras - Inventario DSLR, mirrorless, acción\n"
                        response += "• Accesorios - Stock de cables, cargadores, fundas\n"
                        response += "\n**Solo especifica qué categoría o producto necesitas analizar.**"
                        
                        return {
                            "respuesta": response,
                            "context_data": {"products_shown": len(examples), "total_products": len(products)}
                        }
                except Exception as e:
                    logger.error(f"Error getting products for general query: {str(e)}")
        
        # Usar Gemini directamente para generar la respuesta
        if self.llm_service.gemini_service.is_available():
            try:
                # Construir contexto simple para Gemini
                context_info = ""
                if context_data.get("pedido_info"):
                    context_info += f"Información de pedido específico: {context_data['pedido_info']}\n"
                if context_data.get("productos"):
                    context_info += f"Productos encontrados: {context_data['productos']}\n"
                if context_data.get("politica_info"):
                    context_info += f"Información de políticas: {context_data['politica_info']}\n"
                if context_data.get("analytics_data"):
                    context_info += f"Datos para análisis: {context_data['analytics_data']}\n"
                
                # Generar respuesta con modelo apropiado según complejidad
                response = self.llm_service.gemini_service.generate_response(
                    user_message, context_info, max_tokens=150, complexity=complexity
                )
                
                if (not response 
                    or "no está disponible" in response.lower() 
                    or "ocurrió un error" in response.lower() 
                    or "error" in response.lower()):
                    # Fallback a respuesta basada en BD si Gemini falla o está en cuota
                    response = self._generate_fallback_response(intent, entities, user_message)
                else:
                    # Heurística: si es consulta analítica de conteo y la respuesta no tiene números, usar BD
                    if intent == "consulta_analitica":
                        ml = user_message.lower()
                        has_count_intent = any(x in ml for x in ["cuantos", "cuántos", "total"]) or \
                            (self.db_service.normalize_order_status_query(ml) is not None)
                        has_number = any(ch.isdigit() for ch in response)
                        if has_count_intent and not has_number:
                            response = self._generate_fallback_response(intent, entities, user_message)
                    
            except Exception as e:
                print(f"Error con Gemini: {e}")
                response = self._generate_fallback_response(intent, entities, user_message)
        else:
            # Si Gemini no está disponible, usar respuesta base
            response = self._generate_fallback_response(intent, entities, user_message)
        
        return {
            "respuesta": response,
            "context_data": context_data
        }
    
    async def _enhance_agentic_response(self, agentic_result: dict, user_message: str, 
                                      decomposition) -> str:
        """Mejorar la respuesta agentica usando Gemini para mayor naturalidad"""
        
        try:
            # Extraer la información principal del resultado agentico
            response_data = ""
            
            if isinstance(agentic_result, dict):
                if "response" in agentic_result:
                    response_data = str(agentic_result["response"])
                elif "data" in agentic_result:
                    response_data = self._format_data_for_response(agentic_result["data"])
                elif "items" in agentic_result:
                    response_data = self._format_items_for_response(agentic_result["items"])
                elif "analytics" in agentic_result:
                    response_data = self._format_analytics_for_response(agentic_result["analytics"])
                elif "report" in agentic_result:
                    response_data = self._format_report_for_response(agentic_result["report"])
                else:
                    response_data = str(agentic_result)
            else:
                response_data = str(agentic_result)
            
            # Si tenemos datos y Gemini está disponible, mejorar la respuesta
            if response_data and self.llm_service.gemini_service.is_available():
                enhancement_prompt = f"""
Mejora esta respuesta para que sea más natural y conversacional.

Pregunta original: {user_message}
Datos encontrados: {response_data}

Reglas:
- Mantén los datos exactos
- Solo mejora la redacción y el orden
- No uses emojis
- Responde en español

Respuesta mejorada:
"""
                
                enhanced_response = self.llm_service.gemini_service.generate_response(
                    enhancement_prompt, "", max_tokens=200
                )
                
                if enhanced_response and "error" not in enhanced_response.lower():
                    return enhanced_response
            
            # Fallback: formatear los datos de manera legible
            return self._format_agentic_data_fallback(response_data, user_message)
            
        except Exception as e:
            logger.error(f"Error enhancing agentic response: {str(e)}")
            return str(agentic_result)
    
    def _format_data_for_response(self, data: any) -> str:
        """Formatear datos estructurados para respuesta"""
        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    parts.append(f"{key}: {len(value) if isinstance(value, list) else 'datos disponibles'}")
                else:
                    parts.append(f"{key}: {value}")
            return "; ".join(parts)
        elif isinstance(data, list):
            return f"Se encontraron {len(data)} elementos"
        else:
            return str(data)
    
    def _format_items_for_response(self, items: list) -> str:
        """Formatear lista de elementos para respuesta"""
        if not items:
            return "No se encontraron elementos"
        
        if len(items) <= 5:
            return "; ".join([str(item) for item in items])
        else:
            first_few = "; ".join([str(item) for item in items[:3]])
            return f"{first_few} y {len(items) - 3} más"
    
    def _format_analytics_for_response(self, analytics: dict) -> str:
        """Formatear datos analíticos para respuesta"""
        parts = []
        
        if "summary" in analytics:
            parts.append(f"Resumen: {analytics['summary']}")
        
        if "metrics" in analytics:
            metrics = analytics["metrics"]
            if isinstance(metrics, dict):
                metric_parts = [f"{k}: {v}" for k, v in metrics.items() if isinstance(v, (int, float))]
                if metric_parts:
                    parts.append(f"Métricas: {'; '.join(metric_parts)}")
        
        return "; ".join(parts) if parts else "Análisis completado"
    
    def _format_report_for_response(self, report: dict) -> str:
        """Formatear reporte para respuesta"""
        parts = []
        
        if "executive_summary" in report:
            summary = report["executive_summary"]
            if isinstance(summary, dict) and summary:
                summary_parts = [f"{k}: {v}" for k, v in summary.items()]
                parts.append(f"Resumen ejecutivo: {'; '.join(summary_parts)}")
        
        if "detailed_findings" in report:
            findings = report["detailed_findings"]
            if isinstance(findings, list):
                parts.append(f"Hallazgos detallados: {len(findings)} elementos analizados")
        
        return "; ".join(parts) if parts else "Reporte generado"
    
    def _format_agentic_data_fallback(self, data: str, user_message: str) -> str:
        """Formateo de emergencia para datos agenticos"""
        if not data:
            return "He procesado tu consulta pero no encontré información específica."
        
        # Limpiar y estructurar la respuesta
        clean_data = data.replace("{", "").replace("}", "").replace("[", "").replace("]", "")
        
        if "cuantos" in user_message.lower() or "cuántos" in user_message.lower():
            # Buscar números en la respuesta
            import re
            numbers = re.findall(r'\d+', clean_data)
            if numbers:
                return f"Según los datos disponibles, el total es {numbers[-1]}."
        
        # Respuesta genérica mejorada
        return f"He analizado tu consulta y encontré: {clean_data[:200]}{'...' if len(clean_data) > 200 else ''}"
    
    # Métodos para gestión del sistema agentico
    
    def get_agentic_performance_metrics(self) -> dict:
        """Obtener métricas de rendimiento del sistema agentico"""
        if not self.agentic_enabled:
            return {"agentic_enabled": False}
        
        return {
            "agentic_enabled": True,
            "orchestrator_metrics": self.agent_orchestrator.get_performance_metrics(),
            "tool_registry_info": {
                "total_tools": len(self.tool_registry.get_all_tools()),
                "tool_names": self.tool_registry.get_tool_names(),
                "usage_stats": self.tool_registry.get_usage_stats()
            }
        }
    
    def set_processing_mode(self, mode: str) -> bool:
        """Cambiar el modo de procesamiento (simple, agentic, adaptive)"""
        valid_modes = ["simple", "agentic", "adaptive"]
        if mode in valid_modes:
            self.processing_mode = mode
            logger.info(f"Processing mode changed to: {mode}")
            return True
        return False
    
    def _generate_fallback_response(self, intent: str, entities: dict, user_message: str) -> str:
        """Usar SIEMPRE los datos de la BD para responder"""
        # SIEMPRE obtener contexto completo de BD
        db_context = self._get_comprehensive_context(user_message, intent, entities)
        
        if intent == "consulta_pedido":
            # Usar datos reales de BD
            return self._generate_direct_db_response(user_message, intent, entities, db_context)
        
        elif intent == "consulta_analitica":
            # Usar ResponseGenerator para consultas analíticas
            return self.response_generator.generate_analytics_response(intent, user_message)
        
        elif intent == "consulta_producto":
            # Mejorar respuesta para consultas de productos generales
            message_lower = user_message.lower()
            
            # Si es una consulta general sobre productos, proporcionar información útil del inventario real desde Supabase
            if any(word in message_lower for word in ["cuales", "cuáles", "que", "qué", "tenemos", "disponibles", "stock", "inventario", "catálogo", "productos", "todos", "mostrar", "ver", "listar"]):
                try:
                    # Obtener datos reales desde la base de datos Supabase
                    products = self.db_service.get_all_products_detailed()
                    
                    if products and len(products) > 0:
                        # Detectar si quiere ver productos específicos en stock
                        if any(phrase in message_lower for phrase in ["en stock", "disponibles", "stock"]):
                            in_stock_products = [p for p in products if p.get('availability') == 'En stock']
                            if in_stock_products:
                                total = len(in_stock_products)
                                sample = in_stock_products[:10]  # Primeros 10
                                product_list = []
                                for i, p in enumerate(in_stock_products, 1):  # TODOS los productos, no solo sample
                                    name = p.get('product_name', 'Producto sin nombre')
                                    prod_id = p.get('product_id', 'N/A')
                                    product_list.append(f"{i}. {name} (ID: {prod_id})")
                                
                                response = f"**Productos en Stock** ({total})\n\n" + "\n".join(product_list)
                                
                                return {
                                    "respuesta": response,
                                    "context_data": {"products": in_stock_products, "total_shown": len(sample)}
                                }
                        
                        # Si quiere todos los productos o catálogo completo
                        elif any(phrase in message_lower for phrase in ["todos", "catálogo", "completo", "inventario"]):
                            total = len(products)
                            sample = products[:12]  # Primeros 12
                            product_list = []
                            for i, p in enumerate(products, 1):  # TODOS los productos
                                name = p.get('product_name', 'Producto sin nombre')
                                prod_id = p.get('product_id', 'N/A')
                                availability = p.get('availability', 'N/D')
                                product_list.append(f"{i}. {name} ({availability}) - ID: {prod_id}")
                            
                            response = f"**Catálogo Completo** ({total} productos)\n\n" + "\n".join(product_list)
                            
                            return {
                                "respuesta": response,
                                "context_data": {"products": products, "total_shown": len(sample)}
                            }
                        
                        # Respuesta por defecto con resumen
                        in_stock = sum(1 for p in products if p.get('availability') == 'En stock')
                        out_of_stock = sum(1 for p in products if p.get('availability') == 'Sin stock')
                        on_demand = sum(1 for p in products if 'bajo demanda' in p.get('availability', '').lower())
                        total_products = len(products)
                        
                        # Mostrar algunos productos de ejemplo
                        sample_products = []
                        for i, product in enumerate(products[:10], 1):  # Primeros 10 productos como muestra
                            name = product.get('product_name', 'Producto sin nombre')
                            availability = product.get('availability', 'Desconocido')
                            prod_id = product.get('product_id', 'N/A')
                            sample_products.append(f"{i}. {name} ({availability})")
                        
                        response = f"**Inventario Waver** ({total_products} productos)\n\n"
                        response += f"**Resumen:**\n"
                        response += f"• En stock: {in_stock} productos\n"
                        response += f"• Bajo demanda: {on_demand} productos\n"
                        response += f"• Sin stock: {out_of_stock} productos\n\n"
                        
                        response += f"**Muestra del catálogo:**\n"
                        response += "\n".join(sample_products)
                        response += f"\n\n*Para ver más detalles, pregunta por \"productos en stock\" o \"catálogo completo\"*"
                        
                        return {
                            "respuesta": response,
                            "context_data": {"products": products, "inventory_summary": {"total": total_products, "in_stock": in_stock, "out_of_stock": out_of_stock, "on_demand": on_demand}}
                        }
                    else:
                        return {
                            "respuesta": "Actualmente estamos actualizando nuestro inventario. Por favor díme qué producto específico buscas y te ayudaré a encontrarlo.",
                            "context_data": {"products": []}
                        }
                except Exception as e:
                    logger.error(f"Error fetching real inventory for general query: {str(e)}")
                    return {
                        "respuesta": tech_context.get_general_technology_response(),
                        "context_data": {"fallback": True}
                    }
            
            # Respuesta estándar para consultas específicas
            return "¿Qué producto tecnológico necesitas revisar? Puedo verificar disponibilidad, inventario, estado de stock y especificaciones de smartphones, laptops, tablets, cámaras, auriculares y más. Solo especifica la marca o modelo."
        
        elif intent == "politicas_empresa":
            return "Puedo ayudarte a revisar la configuración de políticas empresariales. ¿Qué política necesitas consultar o modificar?"
        
        elif intent == "escalacion_humana":
            return "Escalando consulta a administrador o soporte técnico especializado. Por favor espera un momento."
        
        else:  # informacion_general
            message_lower = user_message.lower()
            if any(greeting in message_lower for greeting in ["hola", "hi", "hello", "buenos días", "buenas tardes"]):
                return tech_context.get_contextualized_greeting()
            elif "gracias" in message_lower:
                return "¡De nada! Es un placer asistirte en la gestión de tu tienda. ¿Hay alguna otra consulta administrativa que pueda ayudarte a resolver?"
            elif any(word in message_lower for word in ["categorias", "categorías", "tipos", "que tenemos", "qué tenemos"]):
                return tech_context.get_general_technology_response()
            else:
                return "**Panel Administrativo Waver** - ¿Qué información necesitas revisar? Puedo consultar estados de pedidos, inventario de productos tecnológicos, verificar stock de smartphones, laptops, tablets y más, o revisar políticas de envío y garantía."
    
    def _get_context_data(self, intent: str, entities: dict, user_message: str = "") -> dict:
        """Obtener datos de contexto relevantes según la intención"""
        context_data = {}
        
        try:
            if intent == "consulta_analitica":
                # Para consultas analíticas, obtener datos masivos
                message_lower = user_message.lower()
                
                if any(word in message_lower for word in ["clientes", "customers"]):
                    customers = self.db_service.get_all_customers()
                    if "estadísticas" in message_lower:
                        stats = self.db_service.get_order_statistics()
                        context_data["analytics_data"] = f"Estadísticas clientes: {stats}"
                    else:
                        context_data["analytics_data"] = f"Lista clientes: {customers}"
                    context_data["tiene_datos"] = len(customers) > 0
                
                elif any(word in message_lower for word in ["pedidos", "orders"]):
                    if "estadísticas" in message_lower or "resumen" in message_lower:
                        stats = self.db_service.get_order_statistics()
                        context_data["analytics_data"] = f"Estadísticas pedidos: {stats}"
                    else:
                        orders = self.db_service.get_all_orders()
                        context_data["analytics_data"] = f"Todos los pedidos: {orders}"
                    context_data["tiene_datos"] = True
                
                elif any(word in message_lower for word in ["productos", "inventario"]):
                    if "estadísticas" in message_lower:
                        stats = self.db_service.get_product_statistics()
                        context_data["analytics_data"] = f"Estadísticas productos: {stats}"
                    else:
                        products = self.db_service.get_all_products_detailed()
                        context_data["analytics_data"] = f"Inventario completo: {products}"
                    context_data["tiene_datos"] = True
                
                else:
                    summary = self.db_service.get_business_summary()
                    context_data["analytics_data"] = f"Resumen del negocio: {summary}"
                    context_data["tiene_datos"] = True
            
            elif intent == "consulta_pedido":
                if "numero_pedido" in entities:
                    # Consulta específica por número de pedido
                    pedido = self.db_service.get_order_by_id(entities["numero_pedido"])
                    if pedido:
                        order_id = pedido.get('order_id', '')
                        status = pedido.get('status', '')
                        customer = pedido.get('customer_name', '')
                        context_data["pedido_info"] = f"Pedido {order_id}: {status} - Cliente: {customer}"
                        context_data["tiene_datos"] = True
                    else:
                        context_data["pedido_info"] = f"No se encontró el pedido {entities['numero_pedido']}"
                        context_data["tiene_datos"] = False
            
            elif intent == "consulta_producto":
                message_lower = user_message.lower()
                # Rama nueva: productos bajo demanda
                if any(t in message_lower for t in ["bajo demanda", "on demand", "a demanda", "demanda"]):
                    products = self.db_service.get_all_products_detailed()
                    on_demand = [p for p in products if "bajo demanda" in str(p.get('availability', '')).lower()]
                    context_data["productos_bajo_demanda"] = on_demand[:10]
                    context_data["tiene_datos"] = len(on_demand) > 0
                elif "producto_keywords" in entities:
                    productos = self.db_service.search_products(entities["producto_keywords"])
                    if productos:
                        productos_info = []
                        for p in productos[:5]:
                            name = p.get('product_name', '')
                            disponible = p.get('availability', 'En stock')
                            productos_info.append(f"{name} ({disponible})")
                        context_data["productos"] = "; ".join(productos_info)
                        context_data["tiene_datos"] = True
                    else:
                        context_data["productos"] = f"No se encontraron productos para: {', '.join(entities['producto_keywords'])}"
                        context_data["tiene_datos"] = False
            
            elif intent == "politicas_empresa":
                politicas = self.db_service.get_all_company_info()
                if politicas:
                    info_list = []
                    for p in politicas:
                        topic = p.get('topic', '')
                        info = p.get('info', '')
                        info_list.append(f"{topic}: {info}")
                    context_data["politica_info"] = "; ".join(info_list)
                    context_data["tiene_datos"] = True
                else:
                    context_data["politica_info"] = "No hay información de políticas disponible"
                    context_data["tiene_datos"] = False
        
        except Exception as e:
            print(f"Error obteniendo contexto: {e}")
        
        return context_data
    
    def _clean_output(self, text: str) -> str:
        """Limpia y formatea la salida para seguir los patrones modernos de LLM"""
        if not isinstance(text, str):
            return text
        
        # Eliminar marcadores internos
        cleaned = text.replace("[DATOS BD]", "").strip()
        
        # Convertir listas con asteriscos (*) a guiones (-) para cumplir con patrones modernos
        import re
        
        # Reemplazar listas con asteriscos por guiones
        # Patrón: líneas que empiezan con * seguido de espacio
        cleaned = re.sub(r'^\* ', '- ', cleaned, flags=re.MULTILINE)
        
        # También reemplazar asteriscos en medio del texto que actúan como viñetas
        cleaned = re.sub(r'\n\* ', '\n- ', cleaned)
        
        # Mejorar espaciado para listas
        # Asegurar que las listas tengan espaciado apropiado
        lines = cleaned.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Si es una línea de lista (empieza con -), asegurar espaciado
            if line.strip().startswith('- '):
                # Si la línea anterior no era una lista y no está vacía, agregar espacio
                if i > 0 and formatted_lines and not formatted_lines[-1].strip().startswith('- ') and formatted_lines[-1].strip():
                    formatted_lines.append('')  # Línea vacía antes de la lista
            
            formatted_lines.append(line)
        
        cleaned = '\n'.join(formatted_lines)
        
        # Normalizar espacios múltiples
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        
        # Normalizar múltiples saltos de línea (máximo 2 consecutivos)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()

    def get_conversation_history(self, limit: int = 10) -> list:
        """Obtener historial de conversaciones"""
        try:
            conversations = self.db_service.get_recent_conversations(limit)
            return [
                {
                    "id": conv.get('id', ''),
                    "mensaje_usuario": conv.get('mensaje_usuario', ''),
                    "respuesta_bot": conv.get('respuesta_bot', ''),
                    "intencion": conv.get('intencion', ''),
                    "timestamp": conv.get('marca_tiempo', '')
                }
                for conv in conversations
            ]
        except Exception as e:
            print(f"Error obteniendo historial: {e}")
            return []
