"""Diagnóstico rápido: mostra o que cada site devolve para o servidor do GitHub."""
import re, sys
sys.path.insert(0, "coletor")
from comum import sessao
s = sessao()
for url in ["https://www.favaretoleiloes.com.br/", "https://www.favaretoleiloes.com.br/edital/1656/", "https://www.palaciodosleiloes.com.br/site/"]:
    try:
        r = s.get(url, timeout=30)
        t = r.content.decode("latin-1", "replace")
        print("==", url, r.status_code, len(t), r.headers.get("server"), r.url)
        print("  editais:", re.findall(r"/edital/(\d+)", t)[:5], "leiloes:", re.findall(r"leilao_pesquisa=(\d+)", t)[:8])
        print("  trecho:", re.sub(r"\s+", " ", t)[:400])
        if "palacio" in url:
            ids = re.findall(r"leilao_pesquisa=(\d+)", t)
            if ids:
                r2 = s.post("https://www.palaciodosleiloes.com.br/site/camada_ajax/coluna_esquerda_m_home.php?quebra=0.5",
                            data={"opcao": "listar_lote", "leilao_pesquisa": ids[0], "paginacao": 0},
                            headers={"X-Requested-With": "XMLHttpRequest", "Referer": url}, timeout=30)
                print("  listar_lote:", r2.status_code, len(r2.content), r2.content[:300])
    except Exception as e:
        print("==", url, "ERRO", e)
