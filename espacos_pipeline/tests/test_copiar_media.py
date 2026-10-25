import hashlib
from pathlib import Path

from PIL import Image

from espacos_pipeline.copiar_media import copiar_media


def _foto(p: Path, tam=(3000, 2000)):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", tam, (10, 120, 30)).save(p, "JPEG", quality=95)
    return p


def test_foto_grande_e_reduzida(tmp_path):
    o = _foto(tmp_path / "orig" / "01.jpg")
    dest = tmp_path / "media" / "x"
    rel = copiar_media("x", [o], dest)
    assert rel == ["x/01.jpg"]
    with Image.open(dest / "01.jpg") as im:
        assert max(im.size) == 1400


def test_foto_pequena_nao_e_ampliada(tmp_path):
    o = _foto(tmp_path / "orig" / "p.jpg", (400, 300))
    dest = tmp_path / "media" / "x"
    copiar_media("x", [o], dest)
    with Image.open(dest / "p.jpg") as im:
        assert im.size == (400, 300)


def test_extensoes_excluidas_ignoradas(tmp_path):
    o = tmp_path / "orig"
    o.mkdir()
    for n in ("a.doc", "b.docx", "Thumbs.db", "c.mno", "d.html", "e.swf"):
        (o / n).write_bytes(b"x")
    dest = tmp_path / "media" / "x"
    assert copiar_media("x", [o / n for n in ("a.doc", "b.docx", "Thumbs.db", "c.mno", "d.html", "e.swf")], dest) == []
    assert not dest.exists() or list(dest.iterdir()) == []


def test_pdf_copiado_sem_alteracao(tmp_path):
    o = tmp_path / "orig" / "m.pdf"
    o.parent.mkdir()
    o.write_bytes(b"%PDF-1.4 conteudo")
    dest = tmp_path / "media" / "x"
    rel = copiar_media("x", [o], dest)
    assert rel == ["x/m.pdf"]
    assert hashlib.sha256((dest / "m.pdf").read_bytes()).digest() == hashlib.sha256(o.read_bytes()).digest()


def test_pasta_e_expandida_e_ignora_miniaturas(tmp_path):
    o = tmp_path / "orig"
    _foto(o / "fotos" / "01.jpg")
    _foto(o / "fotos" / "peq" / "01.jpg", (100, 80))
    (o / "ficha.html").write_text("x")
    rel = copiar_media("x", [o], tmp_path / "media" / "x")
    assert rel == ["x/01.jpg"]


def test_duplicados_entre_origens_e_colisao_de_nomes(tmp_path):
    a = _foto(tmp_path / "a" / "01.jpg", (500, 500))
    b = tmp_path / "b" / "01.jpg"
    b.parent.mkdir()
    b.write_bytes(a.read_bytes())  # igual: deduplica
    c = _foto(tmp_path / "c" / "01.jpg", (600, 400))  # diferente, mesmo nome
    rel = copiar_media("x", [a, b, c], tmp_path / "media" / "x")
    assert rel == ["x/01.jpg", "x/01-2.jpg"]
