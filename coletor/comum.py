"""Funções compartilhadas pelos robôs: sessão HTTP, normalização e classificação."""
import re
import time
import unicodedata
from datetime import datetime, timezone, timedelta

import requests

BRT = timezone(timedelta(hours=-3))

UFS_ALVO = {"PR", "SC", "RS", "SP", "MG", "RJ", "ES"}

ESTADO_PARA_UF = {
    "parana": "PR", "santa catarina": "SC", "rio grande do sul": "RS",
    "sao paulo": "SP", "minas gerais": "MG", "rio de janeiro": "RJ",
    "espirito santo": "ES",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def sessao():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return s


def pausa(seg=1.0):
    """Espera entre pedidos para não pesar no site do leiloeiro."""
    time.sleep(seg)


def sem_acento(txt):
    txt = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in txt if not unicodedata.combining(c)).lower()


def num_br(txt):
    """'87.000,00' -> 87000.0 ; vazio -> None"""
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return float(txt) if txt else None
    t = re.sub(r"[^\d,.-]", "", str(txt))
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t)
        return v if v > 0 else None
    except ValueError:
        return None


def ano_modelo(txt):
    """'2014/2015' -> 2015 ; '26/27' -> 2027 ; '2024' -> 2024"""
    if not txt:
        return None
    nums = re.findall(r"\d{2,4}", str(txt))
    if not nums:
        return None
    n = int(nums[-1])
    if n < 100:
        n += 2000 if n <= 40 else 1900
    return n if 1950 <= n <= 2035 else None


def uf_de(texto):
    """Acha a UF no fim de 'Curitiba - PR' ou 'Curitiba/PR' ou pelo nome do estado."""
    if not texto:
        return None
    m = re.search(r"[-/\s]([A-Z]{2})\s*$", texto.strip())
    if m:
        return m.group(1)
    return ESTADO_PARA_UF.get(sem_acento(texto).strip())


def categoria(titulo, extra=""):
    t = sem_acento(f"{titulo} {extra}")
    if re.search(r"\bmoto|motociclet|\bcg ?1[256]0|\bfan\b|\bbiz\b|\bpop ?1|\bxre\b|\bcb ?\d|\bnmax|\bfactor|\bfazer\b|\bscooter|\bpcx\b|\bcrosser|\bbros\b|yamaha|kawasaki|suzuki/(?:gs|dl|v-?strom|burgman)|harley|triumph|ducati|dafra|shineray|haojue", t):
        return "moto"
    if re.search(r"caminh|trator|onibus|micro-?onibus|semi-?reb|reboque|carreta|cavalo mec|scania|\biveco\b|new holland|\bcase\b|retroescav|escavad|empilhad|colheitad|volvo/fh|m\.?benz/(?:atego|axor|accelo|actros|\d{3,4})|vw/\d{1,2}\.\d{3}|\bvuc\b", t):
        return "pesado"
    return "carro"


def origem_de(*textos):
    t = sem_acento(" ".join(x or "" for x in textos))
    if re.search(r"judicial|vara |penhor|execucao fiscal|trabalhista", t):
        return "judicial"
    if re.search(r"financ|consorcio|alienacao fiduciaria|banco|bank|credito|credit|aymore|safra|bradesco|itau|santander|\bbv\b|\bpan\b|omni|capital s|leasing|retomad", t):
        return "financeira"
    if re.search(r"segur|sinistr|colisao|enchente|roubo|furto|indeniza", t):
        return "seguradora"
    if re.search(r"locadora|frota|localiza|movida|unidas|rent", t):
        return "locadora"
    if re.search(r"detran|\bprf\b|apreen|patio|remocao|rodoviaria|prefeitura|municipio|transito", t):
        return "apreensao"
    return "outros"


def monta_de(*textos):
    t = sem_acento(" ".join(x or "" for x in textos))
    if re.search(r"sucata|grande monta|irrecuperavel|baixa definitiva", t):
        return "grande"
    if "media monta" in t:
        return "media"
    if "pequena monta" in t:
        return "pequena"
    if re.search(r"sinistr|colisao|danificad|avariad|enchente|incendio", t):
        return "sinistro"
    if re.search(r"nao aplicavel|sem sinistro|bom estado|conservado|circulacao", t):
        return "sem"
    return None


def iso_brt(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BRT)
    return dt.isoformat()


def data_br(txt, hora="10:00"):
    """'25/11/2026' ou '23/11/26' (+ hora) -> ISO em horário de Brasília"""
    if not txt:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", txt)
    if not m:
        return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    h = re.search(r"(\d{1,2}):(\d{2})", hora or "") or re.search(r"(\d{1,2}):(\d{2})", txt[m.end():])
    hh, mm = (int(h.group(1)), int(h.group(2))) if h else (10, 0)
    try:
        return iso_brt(datetime(y, mth, d, hh, mm))
    except ValueError:
        return None


def lote(**k):
    """Formato único de cada carro, igual para todos os leiloeiros."""
    base = dict(
        id=None, fonte=None, leiloeiro=None, titulo=None, ano=None,
        cidade=None, uf=None, lance=None, lance_tipo=None, avaliacao=None,
        encerra=None, origem=None, monta=None, comitente=None, tipo="extrajudicial",
        categoria="carro", link=None, foto=None, obs=None,
    )
    base.update(k)
    if base["titulo"]:
        base["titulo"] = re.sub(r"\s+", " ", base["titulo"]).strip()
    return base
