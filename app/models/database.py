from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cliente de Supabase para operaciones directas
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de la base de datos (PostgreSQL en Supabase)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# Si usamos Supabase, construir la URL de PostgreSQL
if SUPABASE_URL and not DATABASE_URL.startswith("postgresql"):
    # Extraer la parte de la URL de Supabase para PostgreSQL
    # Formato: postgresql://postgres:[password]@[host]:5432/postgres
    SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
    if SUPABASE_DB_PASSWORD:
        host = SUPABASE_URL.replace("https://", "").replace("http://", "")
        DATABASE_URL = f"postgresql://postgres:{SUPABASE_DB_PASSWORD}@db.{host}:5432/postgres"

# Crear engine de SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Crear sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Dependency para obtener sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
