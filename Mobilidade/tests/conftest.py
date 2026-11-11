import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # carto.py, nav.py na raiz

CAMPOS = ["recebido_utc", "observado_utc", "veiculo", "lon", "lat",
          "velocidade", "direccao", "linha", "sentido", "viagem"]


@pytest.fixture
def pasta_csv(tmp_path):
    """Devolve escrever(nome, linhas) -> Path; cada linha é um dict com as chaves de CAMPOS (omissas = '')."""
    def escrever(nome, linhas):
        f = tmp_path / nome
        with open(f, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPOS)
            w.writeheader()
            for l in linhas:
                w.writerow({k: l.get(k, "") for k in CAMPOS})
        return tmp_path
    return escrever
