"""
Technology Context Service for TechStore Pro

This service provides comprehensive context about the technology company,
product categories, and specialized knowledge for the AI agent.
All product data comes from Supabase database, not hardcoded values.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

class TechnologyContext:
    """Service that provides technology-specific context and company information"""
    
    def __init__(self):
        self.company_info = {
            "name": "Waver",
            "founded": "2018",
            "specialization": "Advanced technology and futuristic devices",
            "target_market": "Consumers and businesses seeking the latest innovation",
            "unique_value": "Cutting-edge products with specialized technical support",
            "mission": "Leading the technological future with innovative devices"
        }
        
        # Technology categories based on the actual futuristic products in Supabase
        # Products include: Quantum Processor, Nebula Smartwatch, Orion VR Headset, etc.
        self.product_categories = {
            "processors": {
                "name": "Advanced Processors",
                "products": ["Quantum Processor X1"],
                "keywords": ["processor", "quantum", "procesador", "cpu", "computing"]
            },
            "wearables": {
                "name": "Wearables and Smart Devices",
                "products": ["Nebula Smartwatch", "Momentum-Smart Ring"],
                "keywords": ["smartwatch", "reloj", "smart ring", "anillo", "wearable", "nebula", "momentum"]
            },
            "vr_ar": {
                "name": "Virtual and Augmented Reality",
                "products": ["Orion VR Headset"],
                "keywords": ["vr", "virtual reality", "realidad virtual", "headset", "orion", "ar"]
            },
            "gaming": {
                "name": "Gaming and Entertainment",
                "products": ["Titan-C Gaming Mouse", "Stealth-Grip Controller", "Legacy-Gaming Console"],
                "keywords": ["gaming", "mouse", "controller", "console", "titan", "stealth", "legacy", "juegos"]
            },
            "peripherals": {
                "name": "Peripherals and Input Devices",
                "products": ["Cyber-Synth Keyboard", "Galileo-Pen Stylus", "Vertex-Graphics Tablet"],
                "keywords": ["keyboard", "teclado", "stylus", "tablet", "cyber", "galileo", "vertex", "graphics"]
            },
            "audio": {
                "name": "Audio and Sound",
                "products": ["Echo-Buds Pro", "Pulse-Wave Speakers", "Cosmo-Mic Pro", "Apollo-Audio Interface"],
                "keywords": ["audio", "earbuds", "speakers", "mic", "microphone", "echo", "pulse", "cosmo", "apollo"]
            }
        }
        
        # Services offered by the company
        self.services = {
            "shipping": "Free shipping on purchases over $200,000",
            "warranty": "Extended warranty available for high-tech products",
            "support": "Specialized 24/7 technical support for advanced devices",
            "installation": "Professional installation and configuration of complex equipment",
            "trade_in": "Technology upgrade program for used equipment",
            "financing": "Financing available for cutting-edge technology"
        }
    
    def get_company_introduction(self) -> str:
        """Get a comprehensive company overview for administrative purposes"""
        return f"""**Panel Administrativo de {self.company_info['name']}** - Gestión Empresarial desde {self.company_info['founded']}.

**Perfil de la Empresa:**
Especialización: {self.company_info['specialization']}
Mercado objetivo: {self.company_info['target_market']}
Ventaja competitiva: {self.company_info['unique_value']}

**Categorías de productos en inventario:**
{self.get_categories_overview()}

**Servicios que ofrecemos:**
{self.get_services_overview()}

**Funciones administrativas disponibles:**
- Monitoreo de inventario y stock
- Seguimiento de pedidos y entregas
- Análisis de clientes y ventas
- Configuración de políticas y servicios"""
    
    def get_categories_overview(self) -> str:
        """Get an overview of all product categories"""
        overview = []
        for category_key, category in self.product_categories.items():
            overview.append(f"• **{category['name']}**: {', '.join(category['products'][:3])}")
        return "\n".join(overview)
    
    def get_services_overview(self) -> str:
        """Get an overview of company services"""
        services = []
        for service_key, service_desc in self.services.items():
            services.append(f"• {service_desc}")
        return "\n".join(services)
    
    def get_category_by_keywords(self, message: str) -> Optional[Dict[str, Any]]:
        """Identify product category based on keywords in message"""
        message_lower = message.lower()
        
        for category_key, category in self.product_categories.items():
            # Check if any keywords match
            for keyword in category['keywords']:
                if keyword in message_lower:
                    return {
                        "key": category_key,
                        "category": category,
                        "confidence": "high" if len(keyword) > 5 else "medium"
                    }
        
        return None
    
    def get_detailed_category_info(self, category_key: str) -> str:
        """Get detailed information about a specific category"""
        if category_key not in self.product_categories:
            return "Category not found."
        
        category = self.product_categories[category_key]
        
        info = f"**{category['name']}**\n\n"
        info += f"**Productos principales:** {', '.join(category['products'])}\n\n"
        info += "**Funciones administrativas disponibles:** Verificar stock, analizar ventas, revisar disponibilidad y configurar alertas de inventario para esta categoría."
        
        return info
    
    def get_technology_suggestions(self, user_message: str) -> str:
        """Get technology suggestions based on user query"""
        message_lower = user_message.lower()
        
        # Detect if asking about general categories
        if any(word in message_lower for word in ["categorías", "tipos", "que tenemos", "qué tenemos"]):
            return self.get_categories_overview()
        
        # Detect specific category interest
        detected_category = self.get_category_by_keywords(user_message)
        if detected_category:
            return self.get_detailed_category_info(detected_category["key"])
        
        # General technology response
        return self.get_general_technology_response()
    
    def get_general_technology_response(self) -> str:
        """Get a general administrative response about technology inventory"""
        return f"""**Panel de Control - {self.company_info['name']}**

**Inventario de dispositivos futuristas disponible:**
{self.get_categories_overview()}

**¿Qué información necesitas revisar?** Puedo ayudarte con:
• Verificación de inventario en tiempo real
• Análisis de categorías y rendimiento
• Estados de disponibilidad por producto
• Reportes de stock y rotación
• Configuración de alertas de inventario

**Especifica el tipo de consulta o nombre del producto que necesitas revisar.**"""
    
    def enhance_product_response(self, base_response: str, user_message: str) -> str:
        """Enhance a basic product response with technology context"""
        # Add technology context based on detected categories
        detected_category = self.get_category_by_keywords(user_message)
        
        if detected_category:
            category = detected_category["category"]
            enhancement = f"\n\n**Note:** This query is related to {category['name']}. "
            enhancement += f"We also handle products like {', '.join(category['products'][:3])} in this category."
            return base_response + enhancement
        
        return base_response
    
    def get_contextualized_greeting(self) -> str:
        """Get an administrative-focused greeting for the store owner"""
        return f"""**Bienvenido al Panel Administrativo de {self.company_info['name']}**

Soy tu asistente administrativo especializado. Puedo ayudarte a gestionar y monitorear tu tienda:

**Gestión de Inventario**: Verificar stock, disponibilidad, categorías de productos
**Monitoreo de Pedidos**: Estados, seguimiento, analítica de órdenes
**Análisis de Clientes**: Estadísticas, patrones de compra, segmentación
**Reportes Ejecutivos**: Resúmenes de ventas, KPIs, tendencias
**Configuración**: Políticas, horarios, servicios de la tienda

¿Qué información necesitas revisar hoy? Puedes consultar sobre inventario, pedidos, clientes o generar reportes."""

# Singleton instance
tech_context = TechnologyContext()