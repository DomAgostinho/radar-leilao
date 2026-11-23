"""Acha o valor FIPE de cada carro pela API pública da FIPE (fipe.parallelum.com.br).

Como a API gratuita permite ~500 consultas por dia (1.000 com token), tudo fica
guardado em docs/dados/fipe_cache.json por 30 dias e cada execução gasta só
uma parte do limite diário. Os carros que encerram antes têm prioridade.

O casamento título → modelo FIPE é aproximado; por isso o site mostra o
modelo que foi encontrado, para conferir.
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from comum import sem_acento, num_br

API = "https://fipe.parallelum.com.br/api/v2/cars"
CACHE = Path(__file__).resolve().parent.parent / "docs" / "dados" / "fipe_cache.json"
VALIDADE = 30 * 86400
TOKEN = os.environ.get("FIPE_TOKEN", "").strip()
LIMITE_DIA = int(os.environ.get("FIPE_LIMITE", "950" if TOKEN else "450"))

# apelidos que aparecem nos títulos -> trecho do nome da marca na FIPE
MARCAS = [
    (r"chev(?:rolet)?|\bgm\b", "chevrolet"), (r"\bvw\b|volks", "volkswagen"), (r"\bfiat\b", "fiat"),
    (r"\bford\b", "ford"), (r"renault", "renault"), (r"toyota", "toyota"), (r"honda", "honda"),
    (r"hyunda?i|hyunday", "hyundai"), (r"nissan", "nissan"), (r"\bjeep\b", "jeep"), (r"peugeot", "peugeot"),
    (r"citroen", "citroen"), (r"mitsubishi|\bmmc\b", "mitsubishi"), (r"\bkia\b", "kia"),
    (r"m\.?\s?benz|mercedes|\bmb\b", "mercedes-benz"), (r"\bbmw\b", "bmw"), (r"\baudi\b", "audi"),
    (r"volvo", "volvo"), (r"caoa ?chery|chery", "chery"), (r"\bbyd\b", "byd"), (r"\bgwm\b|great wall|haval", "gwm"),
    (r"\bjac\b", "jac"), (r"land ?rover|\blr\b", "land rover"), (r"suzuki", "suzuki"), (r"subaru", "subaru"),
    (r"porsche", "porsche"), (r"dodge", "dodge"), (r"\bram\b", "ram"), (r"chrysler", "chrysler"),
    (r"\bmini\b", "mini"), (r"lexus", "lexus"), (r"troller", "troller"), (r"\beffa\b", "effa"),
    (r"lifan", "lifan"), (r"jaguar", "jaguar"), (r"\bsmart\b", "smart"), (r"jinbei", "jinbei"),
    (r"\bcaoa\b", "chery"), (r"\bomoda\b", "omoda"), (r"\bjaecoo\b", "jaecoo"), (r"\bzeekr\b", "zeekr"),
]
RUIDO = re.compile(r"\b(veiculo|imp|i|automovel|ano|modelo|placa|final|cor|branca|branco|preta|preto|prata|cinza|vermelha|vermelho|azul|"
                   r"verde|bege|dourada|marrom|alcool|gasolina|flex|diesel|eletrico|hibrido|gnv|carroceria|aberta|fechada|cabine|dupla|simples|"
                   r"sucata|aproveitavel|motor|inservivel|recuperado|financiamento|sinistro|pequena|media|grande|monta|ref|lote|\d{4})\b")


class Fipe:
    def __init__(self):
        try:
            self.c = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            self.c = {}
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.c.get("dia") != hoje:
            self.c["dia"], self.c["usados"] = hoje, 0
        for k in ("modelos", "anos", "precos", "casamentos"):
            self.c.setdefault(k, {})
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        if TOKEN:
            self.s.headers["X-Subscription-Token"] = TOKEN
        self.parou = False
        self.agora = time.time()

    def salvar(self):
        CACHE.write_text(json.dumps(self.c, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def _get(self, caminho):
        if self.parou or self.c["usados"] >= LIMITE_DIA:
            self.parou = True
            return None
        time.sleep(0.35)
        r = self.s.get(API + caminho, timeout=25)
        self.c["usados"] += 1
        if r.status_code == 429:
            print("[fipe] limite diário da API atingido")
            self.parou = True
            return None
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()

    def _cacheado(self, grupo, chave, caminho):
        item = self.c[grupo].get(chave) if chave else self.c.get(grupo)
        if item and self.agora - item["ts"] < VALIDADE:
            return item["v"]
        v = self._get(caminho)
        if v is None:
            return item["v"] if item else None
        novo = {"ts": self.agora, "v": v}
        if chave:
            self.c[grupo][chave] = novo
        else:
            self.c[grupo] = novo
        return v

    @staticmethod
    def _cod(x):
        return str(x.get("code") or x.get("codigo"))

    @staticmethod
    def _nome(x):
        return x.get("name") or x.get("nome") or ""

    def marca(self, titulo):
        t = sem_acento(titulo)
        marcas = self._cacheado("marcas", None, "/brands") or []
        for padrao, nome in MARCAS:
            if re.search(padrao, t):
                for m in marcas:
                    if nome in sem_acento(self._nome(m)):
                        return self._cod(m), padrao
        return None, None

    @staticmethod
    def tokens(txt):
        t = sem_acento(txt)
        t = re.sub(r"(\d)\.(\d)", r"\1\2", t)          # 1.0 -> 10
        t = re.sub(r"\b([a-z]{1,3})-(\w)", r"\1\2", t)    # t-cross -> tcross, hb-20 -> hb20
        t = re.sub(r"\b([a-z]{3,})(\d)", r"\1 \2", t)   # tiggo8 -> tiggo 8
        t = re.sub(r"[^a-z0-9]+", " ", t)
        return [w for w in t.split() if w]

    def casar(self, titulo, ano):
        bcod, padrao = self.marca(titulo)
        if not bcod:
            return None
        modelos = self._cacheado("modelos", bcod, f"/brands/{bcod}/models") or []
        resto = re.sub(padrao, " ", sem_acento(titulo))
        resto = RUIDO.sub(" ", resto)
        tt = [w for w in self.tokens(resto) if len(w) > 1 or w.isdigit()]
        if not tt:
            return None
        base = tt[0]
        melhor, nota_m = None, 0
        for m in modelos:
            mt = self.tokens(self._nome(m))
            if base not in mt:
                continue
            nota = 3 + sum(1 for w in tt[1:6] if w in mt) - 0.05 * len(mt)
            if nota > nota_m:
                melhor, nota_m = m, nota
        if not melhor:
            return None
        mcod = self._cod(melhor)
        anos = self._cacheado("anos", f"{bcod}/{mcod}", f"/brands/{bcod}/models/{mcod}/years") or []
        diesel = "diesel" in sem_acento(titulo)
        opcoes = [a for a in anos if self._cod(a).startswith(f"{ano}-")]
        if not opcoes:
            return None
        opcoes.sort(key=lambda a: 0 if self._cod(a).endswith("-3") == diesel else 1)
        ycod = self._cod(opcoes[0])
        return f"{bcod}/{mcod}/{ycod}"

    def preco(self, chave):
        p = self._cacheado("precos", chave, "/brands/{}/models/{}/years/{}".format(*chave.split("/")))
        if not p or isinstance(p, list):
            return None
        valor = num_br(p.get("price") or p.get("Valor"))
        modelo = p.get("model") or p.get("Modelo") or ""
        ano = p.get("modelYear") or p.get("AnoModelo") or ""
        return valor, f"{modelo} {ano}".strip(), p.get("referenceMonth") or p.get("MesReferencia")


def aplicar(lotes, prioridade=lambda l: 0):
    """Completa os campos fipe / fipe_modelo dos carros."""
    f = Fipe()
    feitos = 0
    try:
        for l in sorted(lotes, key=prioridade):
            if l.get("categoria") != "carro":
                continue
            if l.get("fonte") == "copart" and l.get("avaliacao"):
                l["fipe"], l["fipe_modelo"] = l["avaliacao"], "FIPE informada pela Copart"
                continue
            if not l.get("ano") or not l.get("titulo"):
                continue
            chave_c = f"{sem_acento(l['titulo'])}|{l['ano']}"
            cas = f.c["casamentos"].get(chave_c)
            if cas is None or (cas.get("k") is None and f.agora - cas["ts"] > 7 * 86400):
                if f.parou:
                    continue
                try:
                    k = f.casar(l["titulo"], l["ano"])
                except Exception as e:
                    print("[fipe] erro casando", l["titulo"], e)
                    continue
                if f.parou and k is None:
                    continue
                cas = {"k": k, "ts": f.agora}
                f.c["casamentos"][chave_c] = cas
            if not cas.get("k"):
                continue
            try:
                r = f.preco(cas["k"])
            except Exception as e:
                print("[fipe] erro preço", cas["k"], e)
                continue
            if r and r[0]:
                l["fipe"], l["fipe_modelo"], l["fipe_ref"] = r
                feitos += 1
    finally:
        f.salvar()
    print(f"[fipe] {feitos} carros com FIPE; consultas hoje: {f.c['usados']}/{LIMITE_DIA}")
    return feitos
