from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
import webbrowser
from dotenv import load_dotenv

from app.routers import chat
from app.models.supabase_client import supabase_client

# Cargar variables de entorno
load_dotenv()

# Inicializar FastAPI
app = FastAPI(
    title="E-commerce Chatbot API",
    description="Chatbot simple para servicio al cliente de comercio electrónico",
    version="1.0.0"
)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Headers para optimización y caching
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Cache para archivos estáticos
    if request.url.path.startswith("/static/"):
        if any(request.url.path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg"]):
            response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 año
        
    # Headers de seguridad básicos
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# Incluir routers
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Página principal del chatbot"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check del servidor principal"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "Waver E-commerce Chatbot is running",
        "features": [
            "Dark/Light Theme Toggle",
            "Message Status Indicators", 
            "Accessibility (WCAG 2.1)",
            "Keyboard Navigation",
            "Smart Auto-scroll",
            "Enhanced Animations"
        ]
    }

@app.on_event("startup")
async def startup_event():
    """Verificar conexión a Supabase y mostrar URLs de acceso."""
    port = int(os.getenv("PORT", 8000))
    bind_all = os.getenv("BIND_ALL", "0") in ("1", "true", "TRUE")
    if supabase_client.verify_connection():
        print("✅ Conectado a Supabase")
    else:
        print("❌ No se pudo verificar conexión a Supabase. Revisa credenciales.")
    print("📄 UI: http://localhost:{p}/  | API Docs: http://localhost:{p}/docs | Health: http://localhost:{p}/api/chat/health".format(p=port))
    if bind_all:
        print("🌐 Escuchando en 0.0.0.0 (todas las interfaces). Usa la IP local de tu máquina si accedes desde otro dispositivo.")
    if os.getenv("OPEN_BROWSER", "0") in ("1", "true", "TRUE"):
        try:
            webbrowser.open(f"http://localhost:{port}/")
        except Exception:
            pass

if __name__ == "__main__":
    bind_all = os.getenv("BIND_ALL", "0") in ("1", "true", "TRUE")
    # Para desarrollo local usar 127.0.0.1; 0.0.0.0 es solo un comodín de escucha y no siempre navegable.
    host = "0.0.0.0" if bind_all else os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    print(f"Iniciando servidor en {host}:{port} (reload={debug})")
    uvicorn.run("main:app", host=host, port=port, reload=debug)
