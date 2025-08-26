# Waver - Chatbot Administrativo de E-commerce

Asistente administrativo que responde con datos reales de Supabase y apoya el entendimiento semántico con Gemini. Sin catálogos predefinidos ni respuestas genéricas inventadas.

## Características Clave (actualizado)

- Respuestas basadas exclusivamente en datos reales de la base de datos
- Integración con Google Gemini para entender mejor la intención del usuario y generar respuestas claras (prompt neutral, sin sesgos de catálogo)
- Soporte a consultas sobre:
  - Productos: lista completa y por disponibilidad (sin campo de precio)
  - Pedidos: filtrado por estado, pedidos de un cliente, pedido específico
  - Políticas de la empresa (Info_empresa): 40 temas con información completa (topic + info)
- Fallback robusto: si el modelo no está disponible, responde directamente con datos de la BD
- Formato profesional: títulos en negrita, bullets, enumeraciones; sin emojis

## Flujo funcional actualizado

1) Recepción del mensaje (ChatbotService)
- Extrae intención y entidades con IntentClassifier (Gemini + regex fallback)
- Determina complejidad (simple/complex)

2) Obtención de datos reales (DatabaseService)
- Carga SIEMPRE las tres tablas principales: Productos, Pedidos e Info_empresa
- Construye “query_specific” según la consulta:
  - Productos: en stock, bajo demanda, búsqueda por keywords
  - Pedidos: por estado, por cliente, por ID específico
  - Políticas: mapeo por categorías y palabras clave, búsqueda en topic e info

3) Generación de respuesta (GeminiService con prompt neutral)
- Se construye un prompt con el contexto real, sin catálogo ni servicios predefinidos
- Reglas: no inventar datos; si no está en el contexto, indicarlo; políticas con topic + info
- Si Gemini falla o responde genérico cuando hay datos, se usa respuesta directa de BD

4) Formateo y entrega
- Limpieza de salida (negritas, bullets “•”, enumeraciones)
- Se guarda un resumen en memoria de la sesión

Consulta el diagrama de flujo completo en docs/flow-diagram.md.

## Cambios destacados por dominio

Productos
- Lista completa del catálogo y/o productos en stock, con formato: “1. Nombre (ID: PRD-XXX)”
- No se muestra el precio (no existe columna de precio)
- Respuestas siempre con la lista completa cuando el usuario pida “todos” o “en stock”

Pedidos
- Filtrado por estado (entregado, en tránsito, cancelado, pendiente, devuelto, etc.)
- Búsqueda por ID de pedido o por cliente
- Formato: “1. PED-001 - Cliente: Nombre - Estado: X”

Políticas (Info_empresa)
- 40 políticas reales (topic + info)
- Búsqueda inteligente: categorías, palabras clave, topic e info
- Se devuelven políticas relevantes con su información completa (sin truncar)

## Stack Tecnológico

Backend
- FastAPI (Python 3.8+)
- Supabase (PostgreSQL)
- Google Gemini (2.0 Flash y 2.5 Pro)
- Pydantic

Frontend
- HTML + CSS + JS (sin frameworks)
- Templates Jinja2

## Estructura del proyecto (resumen)

```
ecommerce-chatbot/
├── app/
│   ├── services/
│   │   ├── chatbot_service.py        # Lógica principal del chatbot
│   │   ├── gemini_service.py         # Prompt neutral y generación con Gemini
│   │   ├── database_service.py       # Acceso a Supabase (Productos, Pedidos, Info_empresa)
│   │   ├── ai_service.py             # IntentClassifier y LLMService
│   │   ├── agent_orchestrator.py     # Orquestación agentica
│   │   ├── query_decomposition.py    # Descomposición de consultas
│   │   └── agent_tools.py            # Herramientas del agente
├── docs/
│   └── flow-diagram.md               # Diagrama de flujo del sistema (Mermaid)
├── templates/, static/               # Interfaz web
├── main.py                           # App FastAPI
└── requirements.txt                  # Dependencias
```

## Instalación y configuración

Prerrequisitos
- Python 3.8+
- Cuenta Supabase
- API key de Gemini

Instalación

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Variables de entorno (.env)

```env
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_clave_de_supabase
GEMINI_API_KEY=tu_api_key_de_gemini
PORT=8001
HOST=127.0.0.1
DEBUG=True
```

Ejecución

```bash
# Opción uvicorn
uvicorn main:app --reload --port 8001
# http://localhost:8001
```

## Uso: ejemplos de consultas

Productos
- “Lista todos los productos del catálogo”
- “Muestra los productos en stock”
- “Busca productos con ‘monitor’”

Pedidos
- “Muéstrame los pedidos cancelados”
- “Pedidos en tránsito”
- “Detalle del pedido PED-001”

Políticas
- “¿Cuál es la política de devoluciones?”
- “¿Cuánto cuestan los envíos?”
- “Horarios de atención y días festivos”

## Diagrama de flujo

El diagrama Mermaid está en docs/flow-diagram.md para visualizar todo el flujo desde la entrada del usuario hasta la respuesta final.

## Notas técnicas importantes

- El prompt de Gemini es neutral y no incluye catálogos/servicios predefinidos. El modelo se guía solo por datos reales del contexto.
- Si Gemini no está disponible o responde de forma genérica con datos presentes, el sistema responde directamente usando los datos consultados en Supabase.
- La tabla Productos no tiene columna de precio. Se evita cualquier referencia a “price”.
- En Info_empresa se devuelven topic + info completos, sin truncar.

## Troubleshooting

Conexión a Supabase
- Verifica SUPABASE_URL y SUPABASE_KEY

Gemini API
- Asegura GEMINI_API_KEY válida

PowerShell (Windows)
- Evita usar ‘&&’ en comandos encadenados; ejecuta los comandos por separado.

## Contribución

- Código en español con type hints cuando aplique
- PRs con descripción técnica clara
- Mantener consistencia de formato en respuestas (negritas, bullets, sin emojis)

---

Desarrollado para Waver usando FastAPI, Supabase y Gemini.
