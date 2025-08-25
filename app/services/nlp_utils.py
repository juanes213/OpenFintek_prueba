import re
import unicodedata
from typing import List

SPANISH_STOPWORDS = {
    "hola","buenas","buenos","dias","tardes","noches","dime","decime","oye","por","favor",
    "porfa","que","qué","cual","cuál","como","cómo","cuando","cuándo","donde","dónde",
    "ahi","ahí","aqui","aquí","el","la","los","las","de","del","al","y","o","u","en","para",
    "si","sí","no","con","sobre","acerca","esto","eso","esa","ese","un","una","unos","unas",
    "hay","base","datos","productos","producto","estado","pedido","pedidos","quiero","necesito",
    "saber","informacion","información","dame","me","puedes","puede","consultar"
}

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def normalize_text(text: str) -> str:
    text = strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_product_codes(text: str) -> List[str]:
    t = normalize_text(text)
    codes = re.findall(r"\b(?:prd|prod)[-_]?\d+\b", t, flags=re.IGNORECASE)
    return list({c.upper().replace("_","-") for c in codes})

def extract_order_codes(text: str) -> List[str]:
    t = normalize_text(text)
    codes = re.findall(r"\b(?:ord|ped|order)[-_]?\d+\b", t, flags=re.IGNORECASE)
    return list({c.upper().replace("_","-") for c in codes})

def extract_keywords(text: str, min_len: int = 3, max_kw: int = 5) -> List[str]:
    t = normalize_text(text)
    tokens = [w for w in t.split() if len(w) >= min_len and w not in SPANISH_STOPWORDS]
    tokens = [w for w in tokens if not re.match(r"^(?:prd|prod|ord|ped)[-_]?\d+$", w)]
    uniq: List[str] = []
    for w in tokens:
        if w not in uniq:
            uniq.append(w)
    return uniq[:max_kw]
