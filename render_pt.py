#!/usr/bin/env python3
"""
render_pt.py - desenha as falas em portugues como imagens PNG (36 px de altura, estilo do jogo).

Uso:   python render_pt.py traducao_pt.csv pasta_saida
Requer: Python 3, Pillow e o arquivo texgyreheroscn-regular.otf na mesma pasta deste script.

So gera PNG para as linhas cujo 'portugues' e diferente do 'original'.
Linhas iguais (alemao, reticencias, creditos) mantem a imagem original.
Depois, para gerar o DAT:
   python bp2tool.py pack TEXTBMP.DAT TEXTBMP.TXT pasta_saida NOVO_TEXTBMP.DAT NOVO_TEXTBMP.TXT
"""
import csv, os, sys, math
from PIL import Image, ImageFont, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, 'texgyreheroscn-regular.otf')
CAP, LEFT, RIGHT, BASE, MAXW = 20, 3, 4, 27, 1280    # altura da maiuscula, margens, linha de base, largura maxima

_f0 = ImageFont.truetype(FONT_PATH, 200)
_bb = _f0.getbbox('H')
SIZE = 200 * CAP / (_bb[3] - _bb[1])
FONT = ImageFont.truetype(FONT_PATH, SIZE)

def render(text):
    w = math.ceil(FONT.getlength(text)) + LEFT + RIGHT
    im = Image.new('L', (w, 36), 0)
    ImageDraw.Draw(im).text((LEFT, BASE), text, font=FONT, fill=255, anchor='ls')
    if w > MAXW:                                   # comprime so se passar do limite do jogo
        im = im.resize((MAXW, 36), Image.LANCZOS)
    return im

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    csv_path, outdir = sys.argv[1:]
    os.makedirs(outdir, exist_ok=True)
    n = 0
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            pt = (r['portugues'] or '').strip()
            if pt and pt != r['original']:
                render(pt).convert('RGB').save(os.path.join(outdir, r['id'] + '.png'))
                n += 1
    print('%d imagens geradas em %s' % (n, outdir))
