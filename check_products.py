#!/usr/bin/env python3
"""
Verificar los productos exactos en Supabase
"""

from dotenv import load_dotenv
from supabase import create_client
import os
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obtener TODOS los productos
response = client.table('Productos').select('*').execute()
productos = response.data if response.data else []

print(f"Total de productos: {len(productos)}\n")

# Productos en stock
en_stock = [p for p in productos if p.get('availability') == 'En stock']
print(f"Productos en stock: {len(en_stock)}\n")

print("LISTA COMPLETA DE PRODUCTOS EN STOCK:")
print("="*60)
for i, p in enumerate(en_stock, 1):
    print(f"{i}. {p.get('product_name', 'Sin nombre')} (ID: {p.get('product_id', 'N/A')})")
    print(f"   Campos disponibles: {list(p.keys())}")
    if i == 1:  # Mostrar todos los campos del primer producto
        print(f"   Datos completos del primer producto:")
        for key, value in p.items():
            print(f"     - {key}: {value}")
    print()

# Verificar si hay campo price
if productos:
    first = productos[0]
    print(f"\n¿Existe campo 'price'? {'price' in first}")
    print(f"Campos disponibles en productos: {list(first.keys())}")
