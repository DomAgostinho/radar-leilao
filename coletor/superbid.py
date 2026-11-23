"""Plataforma Superbid (API pública offer-query).

Uma única fonte cobre vários leiloeiros que vendem por ela: Kron/Kronberg (PR/SC),
Sold, Monzon, Marangoni, Eckert, RMoysés, Total Leilões e outros.
"""
import re
from datetime import datetime
from comum import (sessao, pausa, ano_modelo, categoria, origem_de, monta_de,
                   lote, uf_de, UFS_ALVO, sem_acento, iso_brt)

API = "https://offer-query.superbid.net/offers/"
PULAR_SUB = re.compile(r"pe[cç]a|pneu|acess[oó]rio|roda|som|bateria|sucata ferrosa|aeronave|embarca|n[aá]utic", re.I)


def slug(txt):
    t = sem_acento(txt)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:90]


def prop(o, chave):
    for g in ((o.get("product") or {}).get("template") or {}).get("groups") or []:
        for p in g.get("properties") or []:
            if p.get("id") == chave:
                return p.get("value")
    return None


def coletar():
    s = sessao()
    s.headers.update({"Accept": "application/json", "Origin": "https://www.superbid.net", "Referer": "https://www.superbid.net/"})
    lotes, pagina, tamanho = [], 1, 100
    while True:
        params = {
            "filter": "product.productType.description:carros-motos",
            "locale": "pt_BR", "orderBy": "endDate:asc",
            "pageNumber": pagina, "pageSize": tamanho, "portalId": "[2,15]",
            "requestOrigin": "store", "searchType": "opened",
            "timeZoneId": "America/Sao_Paulo",
        }
        j = s.get(API, params=params, timeout=40).json()
        ofertas = j.get("offers") or []
        for o in ofertas:
            prod = o.get("product") or {}
            loc = prod.get("location") or {}
            uf = uf_de(loc.get("city") or "") or uf_de(loc.get("state") or "")
            if uf not in UFS_ALVO:
                continue
            sub = ((prod.get("subCategory") or {}).get("description") or "")
            titulo = prod.get("shortDesc") or ""
            if PULAR_SUB.search(sub) or re.match(r"\s*\d+\s*pneus?", titulo, re.I):
                continue
            auc = o.get("auction") or {}
            det = o.get("offerDetail") or {}
            desc = re.sub(r"<[^>]+>", " ", (o.get("offerDescription") or {}).get("offerDescription") or "")
            judicial = any("judicial" in (m.get("subMarketplaceDesc") or "").lower() for m in auc.get("subMarketplaces") or [])
            tem_lance = bool(o.get("hasBids"))
            lance = det.get("currentMaxBid") if tem_lance else (det.get("initialBidValue") or o.get("price"))
            # Em leilão judicial a 1ª praça costuma ser o valor de avaliação.
            estagios = ((auc.get("eventPipeline") or {}).get("stages") or [])
            avaliacao = estagios[0].get("initialBidValue") if judicial and len(estagios) > 1 else None
            fim = o.get("endDate")
            try:
                encerra = iso_brt(datetime.strptime(fim, "%Y-%m-%d %H:%M:%S")) if fim else None
            except ValueError:
                encerra = None
            cat = "moto" if re.search(r"moto", sub, re.I) else ("pesado" if re.search(r"caminh|[oô]nibus|m[aá]quina|trator|implement|reboque", sub, re.I) else categoria(titulo))
            cidade = re.sub(r"\s*-\s*[A-Z]{2}\s*$", "", loc.get("city") or "")
            lotes.append(lote(
                id=f"superbid-{o.get('id')}",
                fonte="superbid",
                leiloeiro=((o.get("store") or {}).get("name") or "Superbid").title(),
                titulo=titulo, ano=ano_modelo(prop(o, "anomodelo")) or ano_modelo(titulo),
                cidade=cidade or None, uf=uf,
                lance=lance, lance_tipo="atual" if tem_lance else "inicial",
                avaliacao=avaliacao, encerra=encerra,
                comitente=(o.get("manager") or {}).get("name"),
                tipo="judicial" if judicial else "extrajudicial",
                origem="judicial" if judicial else origem_de(titulo, desc, auc.get("desc")),
                monta=monta_de(titulo, desc),
                categoria=cat,
                link=f"https://www.superbid.net/oferta/{slug(titulo)}-{o.get('id')}",
                foto=prod.get("thumbnailUrl"),
                obs=(auc.get("judicialPracaDescription") if judicial else None),
            ))
        total = j.get("total") or 0
        if not ofertas or pagina * tamanho >= total or pagina >= 60:
            break
        pagina += 1
        pausa(1.0)
    return lotes
