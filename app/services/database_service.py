from app.models.supabase_client import get_supabase_client
from app.models.pydantic_models import ConversationCreate
from typing import List, Optional, Dict, Any, cast
from supabase import Client
from datetime import datetime, timedelta
import os
import uuid
import json

class DatabaseService:
    """Servicio simplificado para operaciones con Supabase"""

    def __init__(self):
        client = get_supabase_client()
        if client is None:
            raise RuntimeError("Supabase no está configurado. Configura SUPABASE_URL y SUPABASE_KEY.")
        # Garantizar a los análisis de tipos que self.supabase no es None
        self.supabase: Client = cast(Client, client)

    def save_conversation(self, conversation_data: ConversationCreate) -> Dict[str, Any]:
        """Guardar conversación en Supabase"""
        conversation_dict = conversation_data.dict()
        conversation_dict['id'] = str(uuid.uuid4())
        conversation_dict['marca_tiempo'] = datetime.now().isoformat()
        try:
            response = self.supabase.table('Conversaciones').insert(conversation_dict).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            if os.getenv('DEBUG_LOG', '0') in ('1','true','TRUE'):
                print(f"Error guardando conversación: {e} -> {conversation_dict}")
        return conversation_dict

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtener pedido por ID desde Supabase"""
        response = self.supabase.table('Pedidos').select('*').eq('order_id', order_id.upper()).execute()
        if response.data:
            return response.data[0]
        return None

    def get_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Obtener pedidos por estado"""
        response = self.supabase.table('Pedidos').select('*').ilike('status', f'%{status}%').execute()
        return response.data if response.data else []

    def get_all_orders(self) -> List[Dict[str, Any]]:
        """Obtener todos los pedidos"""
        response = self.supabase.table('Pedidos').select('*').execute()
        return response.data if response.data else []

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Obtener todos los productos"""
        response = self.supabase.table('Productos').select('*').execute()
        return response.data if response.data else []

    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Obtener productos por categoría"""
        response = self.supabase.table('Productos').select('*').ilike('category', f'%{category}%').execute()
        return response.data if response.data else []

    def get_products_by_price_range(self, min_price: float, max_price: float) -> List[Dict[str, Any]]:
        """Obtener productos en rango de precio"""
        response = self.supabase.table('Productos').select('*').gte('price', min_price).lte('price', max_price).execute()
        return response.data if response.data else []

    def search_orders_by_customer(self, customer_name: str) -> List[Dict[str, Any]]:
        """Buscar pedidos por nombre de cliente"""
        response = self.supabase.table('Pedidos').select('*').ilike(
            'customer_name', f'%{customer_name}%'
        ).execute()
        return response.data if response.data else []

    def search_products(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Buscar productos por palabras clave"""
        if not keywords:
            return []
        name_cols = ['product_name', 'nombre_producto', 'nombre']
        results: list = []
        for kw in keywords:
            like = f"%{kw}%"
            # Construir OR dinámico para columnas de nombre
            or_filters = []
            for col in name_cols:
                or_filters.append(f"{col}.ilike.{like}")
            try:
                resp = self.supabase.table('Productos').select('*').or_(",".join(or_filters)).limit(10).execute()
                if resp.data:
                    results.extend(resp.data)
            except Exception:
                # Si 'or_' no está disponible en versión del cliente, hacer consultas por columna
                for col in name_cols:
                    try:
                        r = self.supabase.table('Productos').select('*').ilike(col, like).limit(10).execute()
                        if r.data:
                            results.extend(r.data)
                    except Exception:
                        continue
        # dedup por product_id/nombre
        dedup: list = []
        seen = set()
        for p in results:
            key = p.get('product_id') or p.get('id_producto') or p.get('codigo') or p.get('id') or p.get('product_name')
            key = str(key)
            if key not in seen:
                seen.add(key)
                dedup.append(p)
        return dedup[:5]

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Obtener producto por ID"""
        # Probar varias columnas de código
        code_cols = ['product_id', 'id_producto', 'codigo', 'code', 'id']
        for col in code_cols:
            resp = self.supabase.table('Productos').select('*').eq(col, product_id).limit(1).execute()
            if resp.data:
                return resp.data[0]
            if '-' in product_id:
                resp = self.supabase.table('Productos').select('*').eq(col, product_id.replace('-', '')).limit(1).execute()
                if resp.data:
                    return resp.data[0]
        return None

    def get_company_info_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Obtener información de la empresa por tema"""
        response = self.supabase.table('Info_empresa').select('*').ilike(
            'topic', f'%{topic}%'
        ).execute()
        if response.data:
            return response.data[0]
        return None

    def get_all_company_info(self) -> List[Dict[str, Any]]:
        """Obtener toda la información de la empresa"""
        response = self.supabase.table('Info_empresa').select('*').execute()
        return response.data if response.data else []

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener conversaciones recientes"""
        response = self.supabase.table('Conversaciones').select('*').order(
            'marca_tiempo', desc=True
        ).limit(limit).execute()
        return response.data if response.data else []
    
    # CONSULTAS COMPLEJAS PARA ANÁLISIS
    
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Obtener lista de todos los clientes únicos"""
        response = self.supabase.table('Pedidos').select('customer_name').execute()
        if response.data:
            # Obtener clientes únicos
            unique_customers = list(set(item['customer_name'] for item in response.data if item.get('customer_name')))
            return [{'customer_name': name} for name in sorted(unique_customers)]
        return []
    
    def get_customer_orders(self, customer_name: str) -> List[Dict[str, Any]]:
        """Obtener todos los pedidos de un cliente específico"""
        response = self.supabase.table('Pedidos').select('*').eq(
            'customer_name', customer_name
        ).execute()
        return response.data if response.data else []
    
    def get_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Obtener pedidos por estado"""
        response = self.supabase.table('Pedidos').select('*').eq('status', status).execute()
        return response.data if response.data else []

    def get_total_orders(self) -> int:
        """Obtener total de pedidos"""
        try:
            resp = self.supabase.table('Pedidos').select('order_id').execute()
            return len(resp.data) if resp.data else 0
        except Exception:
            return 0

    def get_total_orders_by_status(self, status: str) -> int:
        """Obtener total de pedidos por estado"""
        try:
            resp = self.supabase.table('Pedidos').select('order_id').eq('status', status).execute()
            return len(resp.data) if resp.data else 0
        except Exception:
            return 0

    @staticmethod
    def normalize_order_status_query(message_lower: str) -> str | None:
        """Normaliza sinónimos de estado de pedidos a valores del sistema.
        Estados oficiales: Entregado, Cancelado, Pendiente de pago, En tránsito
        """
        # Mapear frases comunes a estados
        mapping = {
            'entregado': 'Entregado',
            'entregados': 'Entregado',
            'cancelado': 'Cancelado',
            'cancelados': 'Cancelado',
            'pendiente de pago': 'Pendiente de pago',
            'pendiente pago': 'Pendiente de pago',
            'pendiente': 'Pendiente de pago',
            'en transito': 'En tránsito',
            'en tránsito': 'En tránsito',
            'transito': 'En tránsito',
            'tránsito': 'En tránsito',
            'reparto': 'En tránsito',
            'entrega': 'En tránsito',
            'en entrega': 'En tránsito',
            'envio': 'En tránsito',
            'envío': 'En tránsito'
        }
        for key, val in mapping.items():
            if key in message_lower:
                return val
        return None
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de pedidos"""
        response = self.supabase.table('Pedidos').select('*').execute()
        if response.data:
            total = len(response.data)
            status_count = {}
            customer_count = {}
            
            for order in response.data:
                # Contar por estado
                status = order.get('status', 'Desconocido')
                status_count[status] = status_count.get(status, 0) + 1
                
                # Contar por cliente
                customer = order.get('customer_name', 'Desconocido')
                customer_count[customer] = customer_count.get(customer, 0) + 1
            
            return {
                'total_orders': total,
                'by_status': status_count,
                'unique_customers': len(customer_count),
                'top_customers': sorted(customer_count.items(), key=lambda x: x[1], reverse=True)[:5]
            }
        return {'total_orders': 0, 'by_status': {}, 'unique_customers': 0, 'top_customers': []}
    
    def get_all_products_detailed(self) -> List[Dict[str, Any]]:
        """Obtener todos los productos con información detallada"""
        response = self.supabase.table('Productos').select('*').execute()
        return response.data if response.data else []
    
    def get_products_by_availability(self, availability: str) -> List[Dict[str, Any]]:
        """Obtener productos por disponibilidad"""
        response = self.supabase.table('Productos').select('*').eq(
            'availability', availability
        ).execute()
        return response.data if response.data else []
    
    def get_product_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de productos"""
        response = self.supabase.table('Productos').select('*').execute()
        if response.data:
            total = len(response.data)
            availability_count = {}
            
            for product in response.data:
                avail = product.get('availability', 'Desconocido')
                availability_count[avail] = availability_count.get(avail, 0) + 1
            
            return {
                'total_products': total,
                'by_availability': availability_count,
                'in_stock': availability_count.get('En stock', 0),
                'out_of_stock': availability_count.get('Sin stock', 0)
            }
        return {'total_products': 0, 'by_availability': {}, 'in_stock': 0, 'out_of_stock': 0}
    
    def search_orders_advanced(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Búsqueda avanzada de pedidos con múltiples filtros"""
        query = self.supabase.table('Pedidos').select('*')
        
        if filters.get('customer_name'):
            query = query.ilike('customer_name', f"%{filters['customer_name']}%")
        if filters.get('status'):
            query = query.eq('status', filters['status'])
        if filters.get('order_id'):
            query = query.ilike('order_id', f"%{filters['order_id']}%")
        
        response = query.execute()
        return response.data if response.data else []
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Obtener resumen completo del negocio"""
        return {
            'orders': self.get_order_statistics(),
            'products': self.get_product_statistics(),
            'total_customers': len(self.get_all_customers()),
            'policies': len(self.get_all_company_info())
        }

class ResponseGenerator:
    """Generador de respuestas basado en plantillas y datos de BD"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    # ==== Utilidades de formato ====
    def _wants_table(self, message_lower: str) -> bool:
        triggers = ["tabla", "table", "formato tabla", "en tabla"]
        return any(t in message_lower for t in triggers)
    
    def _format_table(self, rows: List[Dict[str, Any]], columns: List[tuple]) -> str:
        # columns: list of tuples (header, key)
        # Calcular anchos
        widths = []
        for header, key in columns:
            max_len = len(header)
            for r in rows:
                val = str(r.get(key, ""))
                if len(val) > max_len:
                    max_len = len(val)
            widths.append(max_len)
        
        # Construir líneas
        def fmt_row(values: List[str]) -> str:
            parts = []
            for i, v in enumerate(values):
                parts.append(" "+str(v).ljust(widths[i])+" ")
            return "|"+"|".join(parts)+"|"
        
        sep = "+"+"+".join(["-"*(w+2) for w in widths])+"+"
        header_vals = [h for h,_ in columns]
        table_lines = [sep, fmt_row(header_vals), sep]
        for r in rows:
            row_vals = [str(r.get(key, "")) for _, key in columns]
            table_lines.append(fmt_row(row_vals))
        table_lines.append(sep)
        return "\n".join(table_lines)
    
    def generate_order_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para consultas de pedidos"""
        numero_pedido = entities.get("numero_pedido")
        
        if numero_pedido:
            order = self.db_service.get_order_by_id(numero_pedido)
            if order:
                # Datos reales de la base de datos
                order_id = order.get('order_id', '')
                status = order.get('status', '')
                customer = order.get('customer_name', '')
                return f"**Pedido {order_id}**\n\n• Estado: {status}\n• Cliente: {customer}"
            else:
                # Verificar si existe algún pedido con formato similar
                all_orders = self.db_service.get_all_orders()
                existing_ids = [o.get('order_id', '') for o in all_orders]
                
                return f"**Pedido no encontrado**\n\nEl pedido {numero_pedido} no existe en el sistema.\n\n• Total de pedidos registrados: {len(existing_ids)}\n• Últimos IDs: {', '.join(existing_ids[-5:]) if existing_ids else 'ninguno'}"
        else:
            return "Proporciona el número de pedido para consultar (ej: ORD-001)."
    
    def generate_product_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para consultas de productos"""
        message_lower = user_message.lower()
        
        # Soporte explícito: productos "bajo demanda" (on demand)
        if any(t in message_lower for t in ["bajo demanda", "on demand", "a demanda", "demanda"]):
            products = self.db_service.get_all_products_detailed()
            on_demand = [p for p in products if "bajo demanda" in str(p.get('availability', '')).lower()]
            total = len(on_demand)
            if total == 0:
                return "**Productos Bajo Demanda**\n\nNo hay productos bajo demanda actualmente."
            
            # Formato en tabla si el usuario lo pide
            if self._wants_table(message_lower):
                cols = [("Producto", "product_name"), ("Categoría", "category"), ("Precio", "price"), ("Disponibilidad", "availability")]
                rows = on_demand[:10]
                table = self._format_table(rows, cols)
                return f"**Productos Bajo Demanda** ({total})\n\n{table}"
            
            # Formato en lista (por defecto)
            sample = on_demand[:8]
            bullets = []
            for p in sample:
                name = p.get('product_name', 'Producto sin nombre')
                cat = p.get('category', 'Categoría N/D')
                price = p.get('price', 'N/D')
                bullets.append(f"• {name} — {cat} — ${price}")
            more = f"\n\n*Y {total - len(sample)} más...*" if total > len(sample) else ""
            return f"**Productos Bajo Demanda** ({total})\n\n" + "\n".join(bullets) + more
        
        keywords = entities.get("producto_keywords", [])
        
        if keywords:
            products = self.db_service.search_products(keywords)
            if products:
                if len(products) == 1:
                    product = products[0]
                    # Datos reales de la BD
                    avail_str = str(product.get('availability', '')).lower()
                    availability = "disponible" if ("sin" not in avail_str) else "agotado"
                    product_name = product.get('product_name', '')
                    price = product.get('price', 'No especificado')
                    return f"**{product_name}**\n\n• Estado: {availability}\n• Precio: {price}"
                else:
                    product_list = "\n".join([f"• {p.get('product_name', 'Producto')} ({str(p.get('availability', '')).lower()})" for p in products[:10]])
                    more_info = f"\n\n*Mostrando {min(len(products), 10)} de {len(products)} resultados*" if len(products) > 10 else ""
                    return f"**Productos encontrados** ({len(products)})\n\n{product_list}{more_info}"
            else:
                return f"**Sin resultados**\n\nNo se encontraron productos con: {', '.join(keywords)}"
        else:
            return "¿Qué producto buscas? Especifica nombre o características."
    
    def generate_policy_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para consultas de políticas - maneja múltiples preguntas"""
        message_lower = user_message.lower()
        responses = []
        
        # Detectar múltiples políticas consultadas
        policies_found = []
        
        if "devolución" in message_lower or "cambio" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("devoluciones")
            if policy_info:
                info = policy_info.get('info', '')
                policies_found.append(("**Política de Devoluciones**", info))
        
        if "horario" in message_lower or "atención" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("horarios")
            if policy_info:
                info = policy_info.get('info', '')
                policies_found.append(("**Horarios de Atención**", info))
        
        if "envío" in message_lower or "entrega" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("envios")
            if policy_info:
                info = policy_info.get('info', '')
                policies_found.append(("**Política de Envíos**", info))
        
        if policies_found:
            # Formatear respuestas múltiples
            formatted_responses = []
            for title, info in policies_found:
                # Dividir info en puntos si es largo
                if len(info) > 100:
                    formatted_responses.append(f"{title}\n\n• {info[:100]}...")
                else:
                    formatted_responses.append(f"{title}\n\n• {info}")
            
            return "\n\n".join(formatted_responses)
        else:
            # Si no se encontró nada específico, mostrar opciones disponibles
            all_policies = self.db_service.get_all_company_info()
            if all_policies:
                topics = [p.get('topic', '') for p in all_policies]
                topic_list = "\n".join([f"• {topic.title()}" for topic in topics])
                return f"**Políticas Disponibles**\n\n{topic_list}"
            else:
                return "**Sin políticas**\n\nNo hay información de políticas registrada."
    
    def generate_general_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para información general"""
        message_lower = user_message.lower()
        
        if any(greeting in message_lower for greeting in ["hola", "hi", "hello", "buenos días", "buenas tardes"]):
            return "**Panel Administrativo Waver**\n\nPuedo ayudarte a revisar:\n\n• Pedidos y estados\n• Inventario y productos\n• Políticas de la tienda"
        
        elif any(help_word in message_lower for help_word in ["ayuda", "help", "asistencia"]):
            return "**Asistencia Disponible**\n\n• Consulta de pedidos (proporciona el número)\n• Revisión de inventario\n• Análisis y estadísticas\n• Políticas de empresa"
        
        elif any(thanks in message_lower for thanks in ["gracias", "thank you"]):
            return "**De nada**\n\n¿Necesitas consultar algo más?"
        
        elif any(bye in message_lower for bye in ["adiós", "bye", "hasta luego"]):
            return "**Hasta luego**\n\nQue tengas un buen día."
        
        else:
            return "**¿En qué puedo ayudarte?**\n\nEspecifica qué información necesitas:\n\n• Pedidos\n• Inventario\n• Políticas"
    
    def generate_escalation_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para escalación a humanos"""
        return "Transfiriendo consulta a soporte técnico especializado. Por favor espera."
    
    def generate_analytics_response(self, analytics_type: str, user_message: str) -> str:
        """Generar respuesta para consultas analíticas y complejas"""
        message_lower = user_message.lower()
        
        # Análisis de clientes
        if any(word in message_lower for word in ["clientes", "customers", "compradores"]):
            if "todos" in message_lower or "lista" in message_lower or "cuáles" in message_lower:
                customers = self.db_service.get_all_customers()
                if customers:
                    customer_names = [c['customer_name'] for c in customers[:8]]  # Primeros 8
                    total = len(customers)
                    customer_list = "\n".join([f"• {name}" for name in customer_names])
                    more_info = f"\n\n*Y {total-8} clientes más...* " if total > 8 else ""
                    return f"**Clientes Registrados** ({total})\n\n{customer_list}{more_info}"
                else:
                    return "**Sin clientes**\n\nNo hay clientes registrados en el sistema."
            
            elif "estadísticas" in message_lower or "resumen" in message_lower:
                stats = self.db_service.get_order_statistics()
                top_customers = [f"• {c[0]}: {c[1]} pedidos" for c in stats.get('top_customers', [])[:3]]
                top_list = "\n".join(top_customers) if top_customers else "• No hay datos"
                return f"**Estadísticas de Clientes**\n\n• Total: {stats.get('unique_customers', 0)}\n\n**Top Clientes:**\n{top_list}"
        
        # Análisis de pedidos
        elif any(word in message_lower for word in ["pedidos", "orders", "órdenes"]):
            # Por estado (incluye sinónimos) — PRIORIDAD sobre conteo total
            normalized = self.db_service.normalize_order_status_query(message_lower)
            if normalized:
                count = self.db_service.get_total_orders_by_status(normalized)
                if count > 0:
                    some = self.db_service.get_orders_by_status(normalized)[:3]
                    ids_list = "\n".join([f"• {o.get('order_id','')}" for o in some]) if some else ""
                    return f"**Pedidos '{normalized}'** ({count})\n\n**Ejemplos:**\n{ids_list}"
                else:
                    return f"**Pedidos '{normalized}'**\n\nNo hay pedidos con este estado."
            
            # Conteo total
            if any(x in message_lower for x in ["cuantos", "cuántos", "total"]):
                total = self.db_service.get_total_orders()
                return f"**Total de Pedidos**\n\n• {total} pedidos registrados"
            
            # Estadísticas/resumen
            if any(x in message_lower for x in ["estadísticas", "resumen", "análisis"]):
                stats = self.db_service.get_order_statistics()
                status_list = "\n".join([f"• {k}: {v}" for k, v in stats.get('by_status', {}).items()])
                return f"**Resumen de Pedidos**\n\n• Total: {stats.get('total_orders', 0)}\n\n**Por Estado:**\n{status_list}"
        
        # Análisis de productos
        elif any(word in message_lower for word in ["productos", "products", "inventario"]):
            
            # PRIMERO: Consultas específicas de stock/disponibilidad
            if any(phrase in message_lower for phrase in ["en stock", "stock", "disponibles", "tenemos"]):
                products = self.db_service.get_all_products_detailed()
                in_stock = [p for p in products if p.get('availability') == 'En stock']
                
                if not in_stock:
                    return "**Productos en Stock**\n\nNo hay productos disponibles en stock actualmente."
                
                # Mostrar productos reales en stock
                total = len(in_stock)
                sample = in_stock[:10]  # Primeros 10
                product_list = []
                for p in sample:
                    name = p.get('product_name', 'Producto sin nombre')
                    price = p.get('price', 'N/D')
                    category = p.get('category', 'N/D')
                    product_list.append(f"• **{name}** — {category} — ${price}")
                
                more_info = f"\n\n*Mostrando {len(sample)} de {total} productos en stock*" if total > len(sample) else ""
                
                return f"**Productos en Stock** ({total})\n\n" + "\n".join(product_list) + more_info
            
            # Consulta de todos los productos
            elif any(phrase in message_lower for phrase in ["todos los productos", "todo el inventario", "catálogo completo", "todos"]):
                products = self.db_service.get_all_products_detailed()
                
                if not products:
                    return "**Catálogo de Productos**\n\nNo hay productos registrados."
                
                total = len(products)
                sample = products[:12]  # Primeros 12
                product_list = []
                for p in sample:
                    name = p.get('product_name', 'Producto sin nombre')
                    price = p.get('price', 'N/D')
                    availability = p.get('availability', 'N/D')
                    # Usar emoji para disponibilidad
                    status_emoji = "✅" if availability == "En stock" else ("⚠️" if "bajo demanda" in availability.lower() else "❌")
                    product_list.append(f"• **{name}** — ${price} {status_emoji} {availability}")
                
                more_info = f"\n\n*Mostrando {len(sample)} de {total} productos*" if total > len(sample) else ""
                
                return f"**Catálogo Completo** ({total} productos)\n\n" + "\n".join(product_list) + more_info
            
            # Productos bajo demanda (on demand)
            if any(t in message_lower for t in ["bajo demanda", "on demand", "a demanda", "demanda"]):
                products = self.db_service.get_all_products_detailed()
                on_demand = [p for p in products if "bajo demanda" in str(p.get('availability', '')).lower()]
                total = len(on_demand)
                if total == 0:
                    return "**Productos Bajo Demanda**\n\nNo hay productos bajo demanda actualmente."
                
                # Si el usuario pide tabla, mostrar tabla
                if self._wants_table(message_lower):
                    cols = [("Producto", "product_name"), ("Categoría", "category"), ("Precio", "price"), ("Disponibilidad", "availability")]
                    # Limitar filas para no ser demasiado extenso
                    rows = on_demand[:10]
                    table = self._format_table(rows, cols)
                    return f"**Productos Bajo Demanda** ({total})\n\n{table}"
                
                # Respuesta en lista breve
                sample = on_demand[:8]
                bullets = []
                for p in sample:
                    name = p.get('product_name', 'Producto sin nombre')
                    cat = p.get('category', 'Categoría N/D')
                    price = p.get('price', 'N/D')
                    bullets.append(f"• {name} — {cat} — ${price}")
                more = f"\n\n*Y {total - len(sample)} más...*" if total > len(sample) else ""
                return f"**Productos Bajo Demanda** ({total})\n\n" + "\n".join(bullets) + more
            
            # Resumen/estadísticas de inventario
            if "estadísticas" in message_lower or "resumen" in message_lower:
                stats = self.db_service.get_product_statistics()
                avail_list = "\n".join([f"• {k}: {v}" for k, v in stats.get('by_availability', {}).items()])
                return f"**Resumen de Inventario**\n\n• Total: {stats.get('total_products', 0)}\n\n**Disponibilidad:**\n{avail_list}"
        
        # Resumen general del negocio
        elif "resumen" in message_lower and ("negocio" in message_lower or "tienda" in message_lower or "general" in message_lower):
            summary = self.db_service.get_business_summary()
            return f"**Resumen del Negocio**\n\n• Pedidos: {summary.get('orders', {}).get('total_orders', 0)}\n• Clientes: {summary.get('total_customers', 0)}\n• Productos: {summary.get('products', {}).get('total_products', 0)}\n• Políticas: {summary.get('policies', 0)}"
        
        # Fallback dinámico basado en datos (evita respuesta genérica)
        business = self.db_service.get_business_summary()
        orders_total = business.get('orders', {}).get('total_orders', 0)
        customers_total = business.get('total_customers', 0)
        products_total = business.get('products', {}).get('total_products', 0)
        inventory_breakdown = business.get('products', {}).get('by_availability', {})
        inv_lines = "\n".join([f"• {k}: {v}" for k, v in inventory_breakdown.items()]) if inventory_breakdown else "• Sin datos"
        return (
            "**Opciones basadas en tus datos**\n\n"
            f"• Pedidos registrados: {orders_total}\n"
            f"• Clientes registrados: {customers_total}\n"
            f"• Productos en catálogo: {products_total}\n\n"
            "Puedes pedirme, por ejemplo:\n"
            "• Pedidos por estado (ej. 'pendiente', 'en proceso', 'entregado')\n"
            "• Productos bajo demanda (lista o en tabla)\n"
            "• Resumen de inventario por disponibilidad\n\n"
            "**Disponibilidad actual:**\n" + inv_lines
        )

    def save_simple_conversation(self, mensaje_usuario: str, respuesta_bot: str, intencion: Optional[str] = None, entidades: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Guardar conversación simple en la tabla conversaciones_simple"""
        try:
            conversation_data = {
                'mensaje_usuario': mensaje_usuario,
                'respuesta_bot': respuesta_bot,
                'intencion': intencion,
                'entidades': entidades or {},
                'created_at': datetime.now().isoformat()
            }
            
            response = self.supabase.table('conversaciones_simple').insert(conversation_data).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            if os.getenv('DEBUG_LOG', '0') in ('1','true','TRUE'):
                print(f"Error guardando conversación simple: {e}")
        return None
