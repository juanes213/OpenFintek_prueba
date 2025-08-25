from app.services.ai_service import IntentClassifier, LLMService
from app.services.database_service import DatabaseService, ResponseGenerator
from app.services.conversation_context import ConversationContext, SentimentAnalyzer, ConversationMemory
from app.models.pydantic_models import ConversationCreate
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
    """Servicio principal del chatbot con capacidades agenticas avanzadas"""
    
    def __init__(self, session_id: str | None = None):
        self.db_service = DatabaseService()  # Ya no necesita db_session
        self.intent_classifier = IntentClassifier()
        self.llm_service = LLMService()
        self.response_generator = ResponseGenerator(self.db_service)
        
        # Inicializar componentes de contexto avanzado
        self.sentiment_analyzer = SentimentAnalyzer()
        self.conversation_memory = ConversationMemory()
        self.session_id = session_id or str(uuid.uuid4())
        self.conversation_context = self.conversation_memory.get_or_create_session(self.session_id)
        
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
        """Procesar mensaje del usuario con capacidades agenticas avanzadas"""
        try:
            # 1. Analizar sentimiento del mensaje
            sentiment = self.sentiment_analyzer.analyze(user_message)
            sentiment_label = self.sentiment_analyzer.get_sentiment_label(sentiment)
            
            # 2. Clasificar intención y determinar complejidad
            intent = self.intent_classifier.classify_intent(user_message)
            complexity = self.intent_classifier.determine_query_complexity(user_message, intent)
            
            # 3. Extraer entidades del mensaje
            entities = self.intent_classifier.extract_entities(user_message, intent)
            
            # 4. Decidir el modo de procesamiento basado en complejidad
            should_use_agentic = await self._should_use_agentic_processing(
                user_message, intent, complexity
            )
            
            response_data = {}
            
            if should_use_agentic and self.agentic_enabled:
                # 5a. Procesamiento agentico para consultas complejas
                logger.info(f"Using agentic processing for complex query: {user_message[:50]}...")
                response_data = await self._process_with_agentic_system(
                    user_message, intent, entities, complexity
                )
            else:
                # 5b. Procesamiento tradicional para consultas simples
                logger.info(f"Using traditional processing for simple query: {user_message[:50]}...")
                response_data = await self._process_with_traditional_system(
                    user_message, intent, entities, complexity
                )
            
            # 6. Limpiar y formatear respuesta
            response = self._clean_output(response_data.get("respuesta", ""))
            
            # 7. Actualizar contexto de conversación
            self.conversation_context.add_turn(
                user_message, response, intent, entities, sentiment
            )
            
            # 8. Guardar conversación en base de datos
            conversation_data = ConversationCreate(
                mensaje_usuario=user_message,
                respuesta_bot=response,
                intencion=intent
            )
            self.db_service.save_conversation(conversation_data)
            
            # 9. Retornar respuesta estructurada completa
            final_response = {
                "respuesta": response,
                "intencion": intent,
                "timestamp": datetime.now(),
                "entities": entities,
                "sentiment": sentiment_label,
                "session_id": self.session_id,
                "processing_mode": "agentic" if should_use_agentic else "traditional",
                "complexity": complexity
            }
            
            # Agregar metadatos adicionales del procesamiento agentico
            if "agentic_metadata" in response_data:
                final_response["agentic_metadata"] = response_data["agentic_metadata"]
            
            if "context_data" in response_data:
                final_response["context_data"] = response_data["context_data"]
            
            return final_response
            
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
        
        # Usar agentico para consultas comparativas
        comparative_indicators = ["compare", "comparison", "versus", "vs", "difference between", 
                                "mejor que", "comparar", "diferencia entre"]
        if any(indicator in user_message.lower() for indicator in comparative_indicators):
            return True
        
        # Usar agentico para consultas multi-entidad
        multi_entity_indicators = ["and", "y", "both", "ambos", "multiple", "varios", "all", "todos"]
        if any(indicator in user_message.lower() for indicator in multi_entity_indicators):
            return True
        
        # Usar agentico para consultas que requieren cálculos
        calculation_indicators = ["total", "count", "cuantos", "cuántos", "sum", "average", "percentage"]
        if any(indicator in user_message.lower() for indicator in calculation_indicators):
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
                    "entities": entities,
                    "session_id": self.session_id
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
                    "entities": entities,
                    "session_id": self.session_id
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
                Mejora esta respuesta para que sea más natural y conversacional:
                
                Pregunta original: {user_message}
                Datos encontrados: {response_data}
                
                Genera una respuesta natural, amigable y completa en español.
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
        """Generar respuesta básica cuando Gemini no está disponible"""
        if intent == "consulta_pedido":
            if "numero_pedido" in entities:
                return f"Permíteme verificar el pedido {entities['numero_pedido']}. Un momento por favor."
            else:
                return "Por favor proporciona tu número de pedido para consultarlo."
        
        elif intent == "consulta_analitica":
            # Usar ResponseGenerator para consultas analíticas
            return self.response_generator.generate_analytics_response(intent, user_message)
        
        elif intent == "consulta_producto":
            return "¿Qué producto te interesa? Puedo ayudarte a verificar disponibilidad y precios."
        
        elif intent == "politicas_empresa":
            return "Puedo ayudarte con información sobre nuestras políticas. ¿Qué necesitas saber?"
        
        elif intent == "escalacion_humana":
            return "Te conecto con un agente humano. Por favor espera un momento."
        
        else:  # informacion_general
            message_lower = user_message.lower()
            if any(greeting in message_lower for greeting in ["hola", "hi", "hello", "buenos días"]):
                return "¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
            elif "gracias" in message_lower:
                return "¡De nada! ¿Hay algo más en lo que pueda ayudarte?"
            else:
                return "¿En qué puedo ayudarte? Puedo consultar pedidos, productos o políticas de la empresa."
    
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
                if "producto_keywords" in entities:
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
        """Elimina marcadores internos como [DATOS BD] antes de mostrar al usuario"""
        if not isinstance(text, str):
            return text
        cleaned = text.replace("[DATOS BD]", "").strip()
        # Normalizar dobles espacios y saltos
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        return cleaned

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
