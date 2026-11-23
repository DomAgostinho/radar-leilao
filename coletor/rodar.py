"""Roda todos os robôs e grava docs/dados/lotes.json e status.json.

Se um leiloeiro falhar, os carros dele da última coleta boa são mantidos
(até o leilão encerrar), para o site não esvaziar por causa de um erro.
"""
import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import BRT  # noqa: E402
import favareto, kuss, copart, superbid, palacio  # noqa: E402

FONTES = {
    "favareto": ("Favareto Leilões", favareto.coletar),
    "kuss": ("Claudio Kuss Leilões", kuss.coletar),
    "copart": ("Copart", copart.coletar),
    "superbid": ("Superbid (Kron, Sold, Monzon e outros)", superbid.coletar),
    "palacio": ("Palácio dos Leilões", palacio.coletar),
}

SAIDA = Path(__file__).resolve().parent.parent / "docs" / "dados"


def carregar(nome, padrao):
    try:
        return json.loads((SAIDA / nome).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(BRT)
    antigos = carregar("lotes.json", {"lotes": []}).get("lotes", [])
    status_antigo = carregar("status.json", {}).get("fontes", {})
    somente = set(sys.argv[1:])

    todos, status = [], {}
    for chave, (nome, func) in FONTES.items():
        if somente and chave not in somente:
            mantidos = [l for l in antigos if l.get("fonte") == chave]
            todos += mantidos
            status[chave] = status_antigo.get(chave, {"nome": nome})
            continue
        try:
            lotes = func()
            todos += lotes
            status[chave] = {"nome": nome, "ok": True, "qtd": len(lotes), "em": agora.isoformat()}
            print(f"[ok] {chave}: {len(lotes)} lotes")
        except Exception as e:
            mantidos = [l for l in antigos if l.get("fonte") == chave]
            todos += mantidos
            anterior = status_antigo.get(chave, {})
            status[chave] = {"nome": nome, "ok": False, "qtd": len(mantidos), "erro": f"{type(e).__name__}: {e}"[:300],
                             "em": agora.isoformat(), "ultimo_ok": anterior.get("em") if anterior.get("ok") else anterior.get("ultimo_ok")}
            print(f"[ERRO] {chave}: {e}")
            traceback.print_exc()

    # tira encerrados há mais de 6 h e duplicados
    limite = agora - timedelta(hours=6)
    vistos, finais = set(), []
    for l in todos:
        if l["id"] in vistos:
            continue
        vistos.add(l["id"])
        try:
            if l.get("encerra") and datetime.fromisoformat(l["encerra"]) < limite:
                continue
        except ValueError:
            pass
        finais.append(l)
    finais.sort(key=lambda l: l.get("encerra") or "9999")

    (SAIDA / "lotes.json").write_text(json.dumps({"atualizado": agora.isoformat(), "lotes": finais}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SAIDA / "status.json").write_text(json.dumps({"atualizado": agora.isoformat(), "fontes": status}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total: {len(finais)} lotes")


if __name__ == "__main__":
    main()
