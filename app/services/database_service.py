from app.models.supabase_client import get_supabase_client
from app.models.pydantic_models import ConversationCreate
from typing import List, Optional, Dict, Any, cast
from supabase import Client
from datetime import datetime
import os
import uuid

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
                return f"[DATOS BD] Pedido {order_id}: Estado {status}. Cliente: {customer}."
            else:
                return f"[SIN DATOS] No hay información del pedido {numero_pedido} en el sistema."
        else:
            return "Necesito el número de pedido (ej: ORD123)."
    
    def generate_product_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para consultas de productos"""
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
                    return f"[DATOS BD] {product_name}: {availability}."
                else:
                    product_names = [p.get('product_name', '') for p in products]
                    return f"[DATOS BD] Encontré {len(products)} productos: {', '.join(product_names[:10])}{'...' if len(product_names)>10 else ''}."
            else:
                return f"[SIN DATOS] No hay productos con '{', '.join(keywords)}' en el sistema."
        else:
            return "¿Qué producto buscas?"
    
    def generate_policy_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para consultas de políticas"""
        message_lower = user_message.lower()
        
        if "devolución" in message_lower or "cambio" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("devoluciones")
        elif "envío" in message_lower or "entrega" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("envios")
        elif "horario" in message_lower or "atención" in message_lower:
            policy_info = self.db_service.get_company_info_by_topic("horarios")
        else:
            policy_info = None
        
        if policy_info:
            # Datos reales de la BD
            info = policy_info.get('info', '')
            return f"[DATOS BD] {info[:100]}" if len(info) > 100 else f"[DATOS BD] {info}"
        else:
            all_policies = self.db_service.get_all_company_info()
            if all_policies:
                topics = [p.get('topic', '') for p in all_policies]
                return f"[DATOS BD] Temas disponibles: {', '.join(topics)}."
            else:
                return "[SIN DATOS] No hay información de políticas en el sistema."
    
    def generate_general_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para información general"""
        message_lower = user_message.lower()
        
        if any(greeting in message_lower for greeting in ["hola", "hi", "hello", "buenos días", "buenas tardes"]):
            return "¡Hola! Puedo ayudarte con pedidos, productos y políticas."
        
        elif any(help_word in message_lower for help_word in ["ayuda", "help", "asistencia"]):
            return "Puedo ayudarte con: pedidos (dame el número), productos, políticas."
        
        elif any(thanks in message_lower for thanks in ["gracias", "thank you"]):
            return "¡De nada!"
        
        elif any(bye in message_lower for bye in ["adiós", "bye", "hasta luego"]):
            return "¡Hasta luego!"
        
        else:
            return "¿En qué puedo ayudarte? Pedidos, productos o políticas."
    
    def generate_escalation_response(self, entities: dict, user_message: str) -> str:
        """Generar respuesta para escalación a humanos"""
        return "Te conecto con un agente humano. Por favor espera."
    
    def generate_analytics_response(self, analytics_type: str, user_message: str) -> str:
        """Generar respuesta para consultas analíticas y complejas"""
        message_lower = user_message.lower()
        
        # Análisis de clientes
        if any(word in message_lower for word in ["clientes", "customers", "compradores"]):
            if "todos" in message_lower or "lista" in message_lower or "cuáles" in message_lower:
                customers = self.db_service.get_all_customers()
                if customers:
                    customer_names = [c['customer_name'] for c in customers[:10]]  # Primeros 10
                    total = len(customers)
                    return f"[DATOS BD] Tenemos {total} clientes. Algunos: {', '.join(customer_names)}..."
                else:
                    return "[SIN DATOS] No hay clientes registrados."
            
            elif "estadísticas" in message_lower or "resumen" in message_lower:
                stats = self.db_service.get_order_statistics()
                return f"[DATOS BD] Total clientes: {stats['unique_customers']}. Top clientes: {', '.join([f'{c[0]} ({c[1]} pedidos)' for c in stats['top_customers'][:3]])}"
        
        # Análisis de pedidos
        elif any(word in message_lower for word in ["pedidos", "orders", "órdenes"]):
            # Por estado (incluye sinónimos) — PRIORIDAD sobre conteo total
            normalized = self.db_service.normalize_order_status_query(message_lower)
            if normalized:
                count = self.db_service.get_total_orders_by_status(normalized)
                if count > 0:
                    # Opcionalmente listar algunos IDs
                    some = self.db_service.get_orders_by_status(normalized)[:5]
                    ids = ', '.join([o.get('order_id','') for o in some])
                    suffix = f" IDs: {ids}" if ids.strip() else ""
                    return f"[DATOS BD] Pedidos en '{normalized}': {count}.{suffix}"
                else:
                    return f"[DATOS BD] Pedidos en '{normalized}': 0."
            
            # Conteo total
            if any(x in message_lower for x in ["cuantos", "cuántos", "total"]):
                total = self.db_service.get_total_orders()
                return f"[DATOS BD] Total de pedidos: {total}."
            
            # Estadísticas/resumen
            if any(x in message_lower for x in ["estadísticas", "resumen", "análisis"]):
                stats = self.db_service.get_order_statistics()
                status_info = ', '.join([f"{k}: {v}" for k, v in stats['by_status'].items()])
                return f"[DATOS BD] Total pedidos: {stats['total_orders']}. Por estado: {status_info}"
        
        # Análisis de productos
        elif any(word in message_lower for word in ["productos", "products", "inventario"]):
            if "estadísticas" in message_lower or "resumen" in message_lower:
                stats = self.db_service.get_product_statistics()
                avail_info = ', '.join([f"{k}: {v}" for k, v in stats['by_availability'].items()])
                return f"[DATOS BD] Total productos: {stats['total_products']}. Disponibilidad: {avail_info}"
            
            elif "stock" in message_lower or "disponible" in message_lower:
                target = "Sin stock" if ("sin stock" in message_lower or "agotado" in message_lower) else "En stock"
                products = self.db_service.get_products_by_availability(target)
                
                if products:
                    # Mostrar tabla si el usuario la pide o si hay muchos registros
                    if self._wants_table(message_lower) or len(products) > 10:
                        cols = [("ID", "product_id"), ("Producto", "product_name"), ("Disponibilidad", "availability")]
                        table = self._format_table(products, cols)
                        return f"[DATOS BD] Productos {target} ({len(products)}):\n{table}"
                    else:
                        # Lista completa en texto si son pocos
                        names = [p.get('product_name','') for p in products]
                        return f"[DATOS BD] Productos {target} ({len(products)}): {', '.join(names)}."
                else:
                    return "[SIN DATOS] No hay productos con ese criterio."
        
        # Resumen general del negocio
        elif "resumen" in message_lower and ("negocio" in message_lower or "tienda" in message_lower or "general" in message_lower):
            summary = self.db_service.get_business_summary()
            return f"""[DATOS BD] RESUMEN TIENDA:
- Pedidos totales: {summary['orders']['total_orders']}
- Clientes únicos: {summary['total_customers']}
- Productos totales: {summary['products']['total_products']}
- Políticas definidas: {summary['policies']}"""
        
        # Consulta de cliente específico
        elif "cliente" in message_lower and any(word in message_lower for word in ["pedidos de", "compras de", "historial de"]):
            # Extraer nombre del cliente de la consulta
            parts = message_lower.split()
            for i, part in enumerate(parts):
                if part in ["cliente", "de"] and i + 1 < len(parts):
                    customer_name = parts[i + 1].capitalize()
                    if customer_name.startswith("cliente"):
                        customer_name = f"Cliente {parts[i + 2]}" if i + 2 < len(parts) else customer_name
                    
                    orders = self.db_service.get_customer_orders(customer_name)
                    if orders:
                        order_info = ', '.join([f"{o['order_id']} ({o['status']})" for o in orders])
                        return f"[DATOS BD] {customer_name} tiene {len(orders)} pedidos: {order_info}"
                    else:
                        return f"[SIN DATOS] No hay pedidos de {customer_name}."
        
        return "[DATOS BD] Puedo ayudarte con: lista de clientes, estadísticas de pedidos/productos, resumen del negocio."
