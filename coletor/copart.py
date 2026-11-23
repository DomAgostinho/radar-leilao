"""Copart Brasil — busca pública /public/lots/search, filtrada por pátio de leilão."""
import re
from datetime import datetime
from comum import sessao, pausa, num_br, ano_modelo, lote, uf_de, UFS_ALVO, iso_brt

BASE = "https://www.copart.com.br"

ORIGEM = {
    "FINANCIAMENTO": "financeira", "CONSÓRCIO": "financeira",
    "FROTA": "locadora", "COLISÃO": "seguradora", "ENCHENTE": "seguradora",
    "ROUBO/FURTO": "seguradora", "AVARIAS EM TRANSPORTE": "seguradora",
}
MONTA = {"PEQUENA MONTA": "pequena", "MÉDIA MONTA": "media", "GRANDE MONTA": "grande", "NÃO APLICÁVEL": "sem"}


def buscar(s, pagina, tamanho, filtros):
    dados = [("query", "*"), ("page", pagina), ("size", tamanho), ("start", pagina * tamanho)]
    dados += [("filter[MISC]", f) for f in filtros]
    r = s.post(BASE + "/public/lots/search", data=dados, timeout=40)
    r.raise_for_status()
    return r.json()["data"]["results"]


def coletar():
    s = sessao()
    s.headers.update({"Accept": "application/json, text/plain, */*", "X-Requested-With": "XMLHttpRequest", "Referer": BASE + "/lotSearchResults/"})
    s.get(BASE + "/", timeout=30)
    base = buscar(s, 0, 1, [])
    patios = []
    for f in base.get("facetFields") or []:
        if f.get("quickPickCode") == "patioleilao":
            for c in f.get("facetCounts") or []:
                nome = c.get("displayName") or ""
                if uf_de(nome) in UFS_ALVO:
                    patios.append((nome, c.get("query")))
    lotes = []
    for nome, q in patios:
        pagina = 0
        while True:
            pausa(1.2)
            res = buscar(s, pagina, 100, [q])
            itens = res.get("content") or []
            for x in itens:
                if x.get("isBin") or x.get("saleType") != "Leilão":
                    continue
                vt = (x.get("vehicleType") or "").lower()
                cat = "moto" if "moto" in vt else ("pesado" if any(k in vt for k in ("caminh", "ônibus", "onibus", "pesad", "máquina", "implement")) else "carro")
                loss = (x.get("lossType") or "").upper()
                dano = (x.get("damageClassification") or "").upper()
                ad = x.get("ad")
                try:
                    encerra = iso_brt(datetime.strptime(ad, "%Y-%m-%d %H:%M:%S")) if ad else None
                except ValueError:
                    encerra = None
                hb = num_br(x.get("hb"))
                cidade = (x.get("syn") or nome).split(" - ")[0].title()
                lotes.append(lote(
                    id=f"copart-{x.get('ln')}", fonte="copart", leiloeiro="Copart",
                    titulo=re.sub(r"^\d{4}\s+", "", x.get("ld") or ""), ano=ano_modelo(x.get("lcy")),
                    cidade=cidade, uf=uf_de(x.get("syn") or nome),
                    lance=hb, lance_tipo="atual" if hb else "sem lance",
                    avaliacao=num_br(x.get("la")), encerra=encerra,
                    comitente=x.get("sellerName") or None,
                    origem=ORIGEM.get(loss, "outros"), monta=MONTA.get(dano),
                    categoria=cat, link=f"{BASE}/lot/{x.get('ln')}",
                    foto=x.get("tims"),
                    obs=" · ".join(v for v in (loss.title(), (x.get("drivabilityRating") or ""), (x.get("dd") or "").title()) if v) or None,
                ))
            total = res.get("totalElements") or 0
            pagina += 1
            if not itens or pagina * 100 >= total or pagina > 40:
                break
    return lotes
