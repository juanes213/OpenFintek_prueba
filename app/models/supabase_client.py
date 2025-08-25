"""Cliente de Supabase (solo datos reales, sin mock)."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class SupabaseClient:
    """Wrapper mínimo para Supabase"""
    def __init__(self):
        self.client: Client | None = None
        self._init()

    def _init(self):
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"❌ Error conectando a Supabase: {e}")
        else:
            print("❌ SUPABASE_URL / SUPABASE_KEY no configurados")

    def verify_connection(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.table('Pedidos').select('order_id').limit(1).execute()
            return True
        except Exception as e:
            print(f"⚠️ Verificación falló: {e}")
            return False

    def get_client(self) -> Client | None:
        return self.client

supabase_client = SupabaseClient()

def get_supabase_client() -> Client | None:
    return supabase_client.get_client()
