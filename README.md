# Chatbot de E-commerce - Asistente Virtual de Atención al Cliente

Este es un chatbot simple pero funcional para comercio electrónico desarrollado con FastAPI, SQLite y tecnologías web nativas.

## 🚀 Características Principales

- **Clasificación de Intenciones**: Identifica automáticamente el tipo de consulta del usuario
- **Consultas de Pedidos**: Permite consultar el estado de pedidos por número
- **Información de Productos**: Búsqueda de productos y verificación de disponibilidad
- **Políticas de Empresa**: Responde preguntas sobre horarios, devoluciones, envíos, etc.
- **Escalación Humana**: Identifica cuando derivar a un agente humano
- **Interfaz Web Interactiva**: Chat en tiempo real con historial de conversaciones
- **Base de Datos**: Almacena conversaciones y datos de productos/pedidos

## 🛠️ Stack Tecnológico

- **Backend**: FastAPI (Python)
- **Base de Datos**: SQLite con SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **IA**: Integración con APIs de modelos de lenguaje (HuggingFace/OpenAI)
- **Validación**: Pydantic para validación de datos
- **Servidor**: Uvicorn (ASGI)

## 📁 Estructura del Proyecto

```
ecommerce-chatbot/
├── app/
│   ├── models/           # Modelos de base de datos y Pydantic
│   ├── services/         # Lógica de negocio y servicios de IA
│   ├── routers/          # Endpoints de la API
│   └── __init__.py
├── static/
│   ├── css/             # Estilos CSS
│   └── js/              # Scripts JavaScript
├── templates/           # Plantillas HTML
├── data/               # Datos de inicialización
├── main.py             # Aplicación principal
├── requirements.txt    # Dependencias Python
├── .env               # Variables de entorno
└── README.md          # Esta documentación
```

## 🔧 Instalación y Configuración

### 1. Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### 2. Instalación

```bash
# Clonar o descargar el proyecto
cd ecommerce-chatbot

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración

1. **Variables de entorno**: Edita el archivo `.env`
   ```env
   DATABASE_URL=sqlite:///./chatbot.db
   HUGGINGFACE_API_KEY=tu_api_key_aqui  # Opcional
   OPENAI_API_KEY=tu_api_key_aqui       # Opcional
   ```

2. **Datos iniciales**: Los datos de muestra se cargan automáticamente al iniciar

## 🚦 Uso

### Iniciar el servidor

```bash
# Desde la carpeta del proyecto
python main.py
```

El servidor se iniciará en: `http://localhost:8000`

### Interfaz Web

1. Abre tu navegador en `http://localhost:8000`
2. Comienza a chatear con el asistente virtual
3. Prueba diferentes tipos de consultas:
   - "Estado del pedido ORD001"
   - "¿Tienen laptops disponibles?"
   - "¿Cuál es su política de devoluciones?"
   - "Necesito hablar con una persona"

### API Endpoints

- `POST /api/chat` - Enviar mensaje al chatbot
- `GET /api/chat/history` - Obtener historial de conversaciones
- `GET /api/chat/health` - Verificar estado del servicio

## 🤖 Funcionalidades del Chatbot

### Tipos de Intención Soportados

1. **Consulta de Pedidos**
   - Palabras clave: pedido, orden, estado, seguimiento
   - Ejemplo: "¿Dónde está mi pedido ORD001?"

2. **Consulta de Productos**
   - Palabras clave: producto, disponible, precio, stock
   - Ejemplo: "¿Tienen laptops disponibles?"

3. **Políticas de Empresa**
   - Palabras clave: política, horario, devolución, envío
   - Ejemplo: "¿Cuál es su horario de atención?"

4. **Información General**
   - Saludos, despedidas, ayuda general
   - Ejemplo: "Hola, ¿en qué me puedes ayudar?"

5. **Escalación Humana**
   - Palabras clave: persona, agente humano, problema
   - Ejemplo: "Necesito hablar con una persona"

## 📊 Base de Datos

### Tablas Principales

- **conversaciones**: Historial de chats
- **pedidos**: Información de pedidos de clientes
- **productos**: Catálogo de productos
- **info_empresa**: Políticas y información corporativa

## 🔌 Integración con IA

El chatbot puede usar diferentes modelos de IA:

1. **HuggingFace API** (Gratuito) - Configurar `HUGGINGFACE_API_KEY`
2. **OpenAI API** (Pago) - Configurar `OPENAI_API_KEY`
3. **Respuestas Predefinidas** (Sin API) - Funciona sin configuración

## 🎨 Personalización

### Agregar Nuevas Intenciones

1. Edita `app/services/ai_service.py` en la clase `IntentClassifier`
2. Agrega patrones regex para la nueva intención
3. Implementa el generador de respuestas en `app/services/database_service.py`

### Modificar la Interfaz

1. **Estilos**: Edita `static/css/style.css`
2. **Funcionalidad**: Modifica `static/js/chat.js`
3. **Estructura**: Actualiza `templates/index.html`

### Cargar Datos Personalizados

1. Coloca archivos Excel en la carpeta raíz
2. Modifica `app/services/data_loader.py` para procesar tus datos
3. Ajusta los modelos de base de datos según necesites

## 🔒 Consideraciones de Seguridad

- El chatbot usa SQLite local (no recomendado para producción)
- Validación básica de entrada implementada
- Para producción, considerar PostgreSQL/MySQL y autenticación

## 🚀 Despliegue

### Opciones Gratuitas

1. **Heroku** (con limitaciones)
2. **Railway** 
3. **Render**
4. **Vercel** (para aplicaciones serverless)

### Configuración de Producción

```bash
# Instalar con dependencias de producción
pip install gunicorn

# Ejecutar con Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📈 Métricas y Análisis

El chatbot registra automáticamente:
- Todas las conversaciones
- Intenciones clasificadas
- Timestamps de interacciones

Puedes analizar estos datos para:
- Mejorar respuestas
- Identificar patrones de uso
- Optimizar clasificación de intenciones

## 🐛 Solución de Problemas

### Problemas Comunes

1. **Error de conexión a BD**: Verificar permisos de archivo
2. **API de IA no funciona**: Verificar API keys en `.env`
3. **Puerto ocupado**: Cambiar puerto en `.env`

### Logs y Debug

```bash
# Ejecutar en modo debug
python main.py --reload
```

## 🤝 Contribución

Para contribuir al proyecto:

1. Hacer fork del repositorio
2. Crear rama para nueva funcionalidad
3. Implementar cambios
4. Enviar pull request

## 📝 Licencia

Este proyecto es de código abierto para fines educativos y de demostración.

## 📞 Soporte

Para soporte técnico o preguntas:
- Revisar documentación en código
- Verificar logs de error
- Consultar endpoints de salud: `/api/chat/health`

---

**Desarrollado con ❤️ usando FastAPI + AI**
