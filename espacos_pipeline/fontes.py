"""Caminhos das fontes da campanha: repositório no OneDrive (fora de Claude), não copiado para o projecto.

As saídas do pipeline (extraido/, webnode/, reconciliacao.md) continuam em docs/fonte_campanha/.
"""

from pathlib import Path

ARQUIVO = Path(r"C:\Users\quent\OneDrive\Arquivo\Campo Aberto")
PROJECTO = ARQUIVO / "Projectos" / "50 Espacos Verdes"
SITE_ZIP = ARQUIVO / "Internet" / "50 Espacos Verdes"
PDF2016 = (
    ARQUIVO
    / "Internet"
    / "www.campoaberto.pt"
    / "wp-content"
    / "uploads"
    / "2016"
    / "05"
    / "111espacos-TOTAL.pdf"
)
