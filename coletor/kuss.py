"""Claudio Kuss Leilões (Curitiba/PR) — lista de lotes vem de json_edital.php."""
import re
from bs4 import BeautifulSoup
from comum import sessao, pausa, num_br, ano_modelo, data_br, categoria, origem_de, lote

BASE = "https://www.claudiokussleiloes.com.br"

COMB = {"E": "Elétrico", "D": "Diesel", "F": "Flex", "G": "Gasolina", "A": "Álcool", "H": "Híbrido"}


def coletar():
    s = sessao()
    home = s.get(BASE + "/", timeout=30).text
    soup = BeautifulSoup(home, "html.parser")
    texto = soup.get_text("\n")
    ids = list(dict.fromkeys(re.findall(r"relacao-foto/(\d+)", home)))
    # "24/11/2026 às 10:00 horas\nVeículos - Financeiras"
    blocos = re.findall(r"(\d{2}/\d{2}/\d{4})\s*às\s*(\d{1,2}:\d{2})[^\n]*\n\s*([^\n]+)", texto)
    s.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": BASE + "/"})

    lotes = []
    for i, lid in enumerate(ids):
        data, hora, titulo_leilao = blocos[i] if i < len(blocos) else ("", "", "")
        encerra = data_br(data, hora)
        url = f"{BASE}/relacao-foto/{lid}"
        pausa(1.0)
        q = s.post(BASE + "/json_edital.php", data={"leilaoID": lid, "op": "Q", "pag": 1, "loteado": "S", "pesq": ""}, timeout=30).json()
        paginas = int(q.get("qtdePag") or 0)
        for pag in range(1, paginas + 1):
            pausa(0.8)
            r = s.post(BASE + "/json_edital.php", data={"leilaoID": lid, "op": "P", "pag": pag, "loteado": "S", "pesq": ""}, timeout=30).json()
            itens = r.values() if isinstance(r, dict) else r
            for v in itens:
                bem = v.get("bem") or ""
                logo = (v.get("logo") or "").split("/")[-1].replace("logo_", "").split(".")[0]
                tem_lance = "online" in (v.get("usuario") or "").lower() or "id:" in (v.get("usuario") or "").lower()
                lotes.append(lote(
                    id=f"kuss-{lid}-{v.get('seq')}",
                    fonte="kuss", leiloeiro="Claudio Kuss Leilões",
                    titulo=re.sub(r"^(IMP|I)\s+", "", bem), ano=ano_modelo(v.get("ano")),
                    cidade="Curitiba", uf="PR",
                    lance=num_br(v.get("valor")), lance_tipo="atual" if tem_lance else "inicial",
                    encerra=encerra, comitente=logo.upper() or None,
                    origem=origem_de(titulo_leilao) if titulo_leilao else "financeira",
                    monta=None, categoria=categoria(bem),
                    link=url, foto=v.get("foto"),
                    obs=COMB.get(v.get("comb") or "", None),
                ))
    return lotes
