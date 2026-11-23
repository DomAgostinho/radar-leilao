"""Palácio dos Leilões (Juatuba/MG e Cajamar/SP) — lotes via coluna_esquerda_m_home.php."""
import re
import random
from bs4 import BeautifulSoup
from comum import sessao, pausa, num_br, ano_modelo, data_br, categoria, origem_de, monta_de, lote, sem_acento

BASE = "https://www.palaciodosleiloes.com.br/site/"
CIDADE_UF = {"juatuba": "MG", "cajamar": "SP", "betim": "MG", "contagem": "MG", "belo horizonte": "MG", "simoes filho": "BA", "catalao": "GO"}
VEICULO = re.compile(r"ve[ií]cul|carro|autom[oó]v|locadora|financiamento|sinistr|frota", re.I)
NAO = re.compile(r"pe[cç]as|materia|eletro|im[oó]ve|j[oó]ia|diversos", re.I)


def texto(el):
    return el.get_text(" ", strip=True) if el else ""


def coletar():
    s = sessao()
    home = s.get(BASE, timeout=30)
    home.encoding = "cp1252"
    soup = BeautifulSoup(home.text, "html.parser")
    leiloes = {}
    for a in soup.find_all("a", href=re.compile(r"leilao_pesquisa=\d+")):
        lid = re.search(r"leilao_pesquisa=(\d+)", a["href"]).group(1)
        bloco = a.find_parent(["div", "article", "li"]) or a
        leiloes.setdefault(lid, texto(bloco)[:300])
    s.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": BASE})

    lotes = []
    for lid, desc_leilao in leiloes.items():
        if desc_leilao and (NAO.search(desc_leilao) and not VEICULO.search(desc_leilao)):
            continue
        for pag in range(0, 40):
            pausa(1.0)
            r = s.post(f"{BASE}camada_ajax/coluna_esquerda_m_home.php?quebra={random.random()}",
                       data={"opcao": "listar_lote", "leilao_pesquisa": lid, "paginacao": pag}, timeout=40)
            html = r.content.decode("cp1252", errors="replace")
            cards = BeautifulSoup(html, "html.parser").select("article.resultado-lote-card--veiculo")
            if not cards:
                break
            for c in cards:
                ident = texto(c.select_one(".resultado-veiculo-identificadores"))
                num = re.search(r"Lote\s*(\d+)", ident)
                titulo = texto(c.select_one(".resultado-veiculo-modelo"))
                esp = texto(c.select_one(".resultado-veiculo-especificacoes"))
                situ = texto(c.select_one(".resultado-veiculo-situacao"))
                com_img = c.select_one(".resultado-veiculo-comitente img")
                comitente = texto(c.select_one(".resultado-veiculo-comitente")) or (com_img.get("alt") if com_img else "")
                corpo = texto(c)
                data = re.search(r"\d{2}/\d{2}/\d{2,4}", corpo)
                hora = re.search(r"Previs[ãa]o\s*(\d{1,2}:\d{2})", corpo)
                local = ""
                m_local = re.search(r"\d{2}/\d{2}/\d{2,4}\s+([A-Za-zÀ-ú ]+?)\s+Previs", corpo)
                if m_local:
                    local = m_local.group(1).strip()
                uf = CIDADE_UF.get(sem_acento(local), None)
                if uf not in ("MG", "SP"):
                    continue
                val = c.select_one(".resultado-veiculo-valor")
                rotulo = texto(val.find("span")) if val else ""
                valor = num_br(texto(val.find("strong"))) if val else None
                onclick = c.select_one("[onclick*=exibir_lote]")
                cod = re.search(r"exibir_lote\((\d+)", onclick["onclick"]).group(1) if onclick else (num.group(1) if num else "")
                img = c.select_one("img.i-p-l")
                lotes.append(lote(
                    id=f"palacio-{lid}-{cod}", fonte="palacio", leiloeiro="Palácio dos Leilões",
                    titulo=titulo, ano=ano_modelo(esp), cidade=local or None, uf=uf,
                    lance=valor, lance_tipo="inicial" if "inicial" in rotulo.lower() else "atual",
                    encerra=data_br(data.group(0), hora.group(1) if hora else "10:00") if data else None,
                    comitente=comitente or None,
                    origem=origem_de(desc_leilao, comitente),
                    monta=monta_de(situ) or ("sinistro" if "sinistr" in desc_leilao.lower() else None),
                    categoria=categoria(titulo),
                    link=f"{BASE}index.php?leilao_pesquisa={lid}",
                    foto=(BASE + img["src"]) if img and img.get("src") and not img["src"].startswith("http") else (img.get("src") if img else None),
                    obs=situ or None,
                ))
    return lotes
