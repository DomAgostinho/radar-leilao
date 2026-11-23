"""Favareto Leilões (Curitiba/PR) — páginas HTML simples, uma por edital."""
import re
from bs4 import BeautifulSoup
from comum import checar, sessao, pausa, num_br, ano_modelo, data_br, categoria, origem_de, monta_de, lote

BASE = "https://www.favaretoleiloes.com.br"


def coletar():
    s = sessao()
    home = checar(s.get(BASE + "/", timeout=30))
    home.encoding = home.apparent_encoding or "latin-1"
    html = home.text
    ids = list(dict.fromkeys(re.findall(r"/edital/(\d+)", html)))
    texto_home = BeautifulSoup(html, "html.parser").get_text(" ")
    datas = re.findall(r"Leil[ãa]o\s+(\d{2}/\d{2}/\d{4})[^\n]{0,40}?(\d{1,2}:\d{2})", texto_home)

    lotes = []
    for i, eid in enumerate(ids):
        pausa(1.5)
        url = f"{BASE}/edital/{eid}/"
        r = checar(s.get(url, timeout=30))
        r.encoding = r.apparent_encoding or "latin-1"
        soup = BeautifulSoup(r.text, "html.parser")
        if i < len(datas):
            encerra = data_br(datas[i][0], datas[i][1])
        else:
            h3 = soup.find("h3")
            encerra = data_br(h3.get_text(" ") if h3 else "")
        comitente = None
        for tr in soup.find_all("tr"):
            g = tr.find("td", class_="grupo")
            if g:
                comitente = g.get_text(" ", strip=True)
                continue
            td_lote = tr.find("td", id=re.compile(r"^lote\d+"))
            if not td_lote:
                continue
            tds = tr.find_all("td")
            if len(tds) < 7:
                continue
            numero = td_lote.get_text(strip=True)
            desc = tds[1].get_text(" ", strip=True)
            estado = tds[2].get_text(" ", strip=True)
            situacao = tds[3].get_text(" ", strip=True)
            ref = tds[5].get_text(" ", strip=True)
            valor = num_br(tds[6].get_text(strip=True))
            partes = [p.strip() for p in desc.split(",")]
            titulo = partes[0] if partes else desc
            ano = ano_modelo(partes[1]) if len(partes) > 1 else None
            if "encerr" in situacao.lower() or "vendid" in situacao.lower():
                continue
            lotes.append(lote(
                id=f"favareto-{eid}-{numero}",
                fonte="favareto", leiloeiro="Favareto Leilões",
                titulo=titulo, ano=ano, cidade="Curitiba", uf="PR",
                lance=valor, lance_tipo="inicial" if "INICIAL" in ref.upper() else "atual",
                encerra=encerra, comitente=comitente,
                origem=origem_de(comitente, estado),
                monta=monta_de(estado),
                categoria=categoria(desc),
                link=url, obs=estado or None,
            ))
    return lotes
