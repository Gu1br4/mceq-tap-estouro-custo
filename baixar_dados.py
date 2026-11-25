"""Baixa a base SEERA (Zenodo, DOI 10.5281/zenodo.3987969) para dados/brutos/.

Uso:  python baixar_dados.py
O arquivo só é baixado se ainda não existir; o MD5 é conferido em seguida.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://zenodo.org/records/3987969/files/The_SEERA_Dataset.zip?download=1"
MD5_ESPERADO = "b1ea3e8eb763415f0679a6fc6618de96"
DESTINO = Path(__file__).resolve().parent / "dados" / "brutos" / "The_SEERA_Dataset.zip"


def md5(caminho: Path) -> str:
    h = hashlib.md5()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def garantir_dados() -> Path:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    if not DESTINO.exists():
        print(f"Baixando {URL} ...")
        urllib.request.urlretrieve(URL, DESTINO)
    obtido = md5(DESTINO)
    if obtido != MD5_ESPERADO:
        sys.exit(f"MD5 diferente do esperado ({obtido} != {MD5_ESPERADO}). Apague o arquivo e baixe de novo.")
    print(f"OK: {DESTINO.name} (md5 {obtido})")
    return DESTINO


if __name__ == "__main__":
    garantir_dados()
