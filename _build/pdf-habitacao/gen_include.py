"""Gera _includes/conclusoes-habitacao.html a partir dos dados do PDF (conclusoes.py)."""

import sys
from pathlib import Path

SP = Path(__file__).resolve().parent  # a cópia do repo é a fonte (não o scratchpad)
sys.path.insert(0, str(SP / "modelo"))
import conclusoes as c

CSS = """
<style>
.cx{--verde:#1B4D20;--folha:#2E7D32;--musgo:#A5C79A;--papel:#FBF9F4;--terra:#D9642B;--ceu:#2A78D6;--cinza:#6B726C;--tinta:#1F2420;
 --fd:"Sitka Display","Sitka Heading",Georgia,serif;margin:2rem 0 2.6rem;border-radius:10px;overflow:hidden;background:var(--papel);border:1px solid #dfe6da;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--tinta)}
.cx *{box-sizing:border-box}
.cx .topo{position:relative;background:var(--verde);color:#fff;padding:1.6rem 1.6rem 5.4rem}
.cx .topo .im{position:absolute;right:0;top:0;width:44%;height:100%;object-fit:cover;object-position:60% 40%;margin:0;border-radius:0;max-width:none}
.cx .topo .veu{position:absolute;right:0;top:0;width:44%;height:100%;background:linear-gradient(90deg,var(--verde) 0%,rgba(27,77,32,.55) 45%,rgba(27,77,32,0) 100%)}
.cx .kick{position:relative;font-size:.72rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--musgo)}
.cx .tit{position:relative;font:700 2.3rem/1.05 var(--fd);color:#fff;margin:.3rem 0 .7rem}
.cx .tese{position:relative;font:400 1.02rem/1.45 var(--fd);color:#e6f0e1;max-width:34rem;margin:0}
.cx .nums{position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin:-4.2rem 1.2rem 0;z-index:2}
.cx .nums div{background:#fff;border-top:3px solid var(--cor);border-radius:3px;padding:.6rem .7rem .7rem;box-shadow:0 2px 8px rgba(0,0,0,.10)}
.cx .nums b{display:block;font:700 1.55rem/1 var(--fd);color:var(--cor);white-space:nowrap}
.cx .nums span{display:block;font-size:.72rem;line-height:1.3;color:#2b322c;margin-top:.35rem}
.cx .ceu{--cor:var(--ceu)}.cx .terra{--cor:var(--terra)}.cx .folha{--cor:var(--folha)}
.cx .sec{font-size:.7rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--folha);margin:0 0 .7rem}
.cx .choques{padding:1.5rem 1.6rem 0}
.cx .cs{display:grid;grid-template-columns:repeat(5,1fr);gap:.8rem}
.cx .cs div{border-left:3px solid var(--terra);padding-left:.6rem}
.cx .cs i{display:block;font-style:normal;font-size:.62rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--cinza)}
.cx .cs b{display:block;font:700 1.2rem/1.1 var(--fd);color:var(--verde);margin:.15rem 0;white-space:nowrap}
.cx .cs span{display:block;font-size:.72rem;line-height:1.3}
.cx .ver{padding:1.6rem 1.6rem .4rem}
.cx .ln{display:grid;grid-template-columns:3rem 1fr 8.6rem;gap:.9rem;align-items:center;padding:.7rem 0;border-top:1px solid #dfe6da}
.cx .ln:first-of-type{border-top:none}
.cx .ic{display:flex;align-items:center;justify-content:center;width:2.8rem;height:2.8rem;border-radius:50%;background:color-mix(in srgb,var(--c) 13%,white)}
.cx .ic svg{width:1.75rem;height:1.75rem;fill:none;stroke:var(--c);stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.cx .ok{--c:var(--folha)}.cx .dep{--c:var(--ceu)}.cx .nao{--c:var(--terra)}.cx .peq{--c:#6f776f}
.cx .selo{text-align:center;font-size:.62rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#fff;padding:.32rem .4rem;border-radius:3px;white-space:nowrap;background:var(--c)}
.cx .peq .selo{background:#8a918a}
.cx .ln h3{font:700 1rem/1.2 var(--fd);color:var(--verde);margin:0}
.cx .ln .ef{font-size:.84rem;font-weight:600;line-height:1.35;margin:.15rem 0 0;color:#1e2620}
.cx .ln .ev{font-size:.76rem;line-height:1.35;margin:.15rem 0 0;color:var(--cinza)}
.cx .pacote{background:var(--verde);color:#fff;padding:1.4rem 1.6rem 1.2rem;margin-top:1rem}
.cx .pacote .k{font-size:.7rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--musgo)}
.cx .pacote h4{font:700 1.3rem/1.15 var(--fd);color:#fff;margin:.3rem 0 .9rem}
.cx .passos{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem}
.cx .passo{background:#255a2a;padding:.7rem 1.1rem .8rem .8rem;clip-path:polygon(0 0,calc(100% - .8rem) 0,100% 50%,calc(100% - .8rem) 100%,0 100%)}
.cx .passo:last-child{clip-path:none;padding-right:.8rem}
.cx .passo .h{font:700 1.05rem/1 var(--fd);color:#ffa77a}
.cx .passo .d{font-size:.76rem;line-height:1.35;color:#dcead6;margin-top:.35rem}
.cx .terr{margin:1rem 0 0;font-size:.8rem;line-height:1.45;color:#dcead6;border-top:1px solid #3f7344;padding-top:.8rem}
.cx .terr.nic{margin-top:.4rem;border-top:none;padding-top:0}
.cx .terr b,.cx .rod b{color:#ffa77a}
.cx .rod{margin:.8rem 0 0;font-size:.72rem;line-height:1.4;color:#9fbf9e;display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap}
@media (max-width:700px){
 .cx .topo{padding:1.2rem 1.1rem 5rem}.cx .topo .im,.cx .topo .veu{display:none}
 .cx .tit{font-size:1.9rem}
 .cx .nums{grid-template-columns:repeat(2,1fr);margin:-3.6rem .8rem 0}
 .cx .choques,.cx .ver{padding-left:1.1rem;padding-right:1.1rem}
 .cx .cs{grid-template-columns:repeat(2,1fr)}
 .cx .ln{grid-template-columns:2.8rem 1fr;gap:.7rem}
 .cx .ln .selo{grid-column:2;justify-self:start;padding:.28rem .7rem}
 .cx .pacote{padding:1.2rem 1.1rem}
 .cx .passos{grid-template-columns:1fr}
 .cx .passo,.cx .passo:last-child{clip-path:none;padding:.7rem .9rem}
}
</style>
"""


def build():
    nums = "".join(
        f'<div class="{k}"><b>{n}</b><span>{d}</span></div>' for n, d, k in c.NUMEROS
    )
    chq = "".join(
        f"<div><i>{a}</i><b>{n}</b><span>{d}</span></div>" for a, n, d in c.CHOQUES
    )
    ver = "".join(
        f'<div class="ln {cl}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true">{c.ICONOS[k]}</svg></span>'
        f'<div><h3>{m}</h3><p class="ef">{e}</p><p class="ev">{v}</p></div>'
        f'<span class="selo">{s}</span></div>'
        for k, (s, cl, m, e, v) in enumerate(c.MEDIDAS)
    )
    pas = "".join(
        f'<div class="passo"><div class="h">{h}</div><div class="d">{d}</div></div>'
        for h, d in c.PASSOS
    )
    body = f"""<section class="cx" aria-label="Síntese">
<div class="topo"><img class="im" src="{{{{ site.baseurl }}}}/assets/images/habitacao-ilustracao-casas.jpg" alt=""><div class="veu"></div>
 <div class="kick">Ler primeiro</div><div class="tit" role="heading" aria-level="2">Síntese</div>
 <p class="tese">{c.TESE}</p></div>
<div class="nums">{nums}</div>
<div class="choques"><p class="sec">Cinco choques na procura (aumentos fortes de pessoas ou de dinheiro à procura de casa; o 1.º, uma tendência longa)</p><div class="cs">{chq}</div></div>
<div class="ver"><p class="sec">O que dizem os estudos sobre cada medida</p>{ver}</div>
</section>
"""
    return CSS.strip("\n") + "\n" + c._nb(body)


out = Path(
    r"C:\Users\quent\OneDrive\Claude\Porto Verde\_includes\conclusoes-habitacao.html"
)
out.write_text(build(), encoding="utf-8")
print("ok", out.stat().st_size)
