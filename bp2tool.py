#!/usr/bin/env python3
"""
bp2tool.py - extrai e reempacota o TEXTBMP.DAT de Shin Seiki Evangelion: Tetsu no Girlfriend (PC).

Uso:
    python bp2tool.py unpack TEXTBMP.DAT TEXTBMP.TXT pasta_png
    python bp2tool.py pack   TEXTBMP.DAT TEXTBMP.TXT pasta_png NOVO_TEXTBMP.DAT NOVO_TEXTBMP.TXT

Requer: Python 3 e Pillow (pip install pillow)

Formato do .BP2 (descoberto por engenharia reversa do ADV2.EXE):
    6 x u32 : 999, versao(2 ou 3), 0, bytes_por_faixa, n_faixas, bytes_da_cauda
    54 bytes: cabecalho BMP normal (24 bits)
    blocos  : [u32 tamanho][dados], um por faixa de 8 linhas, e por fim a "cauda" crua
    cada faixa e um RLE decodificado COLUNA por COLUNA (8 linhas por coluna), com fluxo
    de tokens continuo:  u16 contagem
        bit 15 ligado -> repete a mesma cor 'contagem' vezes
                         v2: cor = 3 bytes (B,G,R)   v3: cor = 1 byte (cinza)
        bit 15 desligado -> 'contagem' pixels literais (v2: 3 bytes cada, v3: 1 byte cada)
    a cauda sao as ultimas (altura - 8*n_faixas) linhas, em bytes crus (24 bits).
As linhas ficam na ordem da memoria do BMP (de baixo para cima), com stride multiplo de 4.
"""
import struct, sys, os, io

# ---------------------------------------------------------------- leitura / decodificacao
def load_index(txt):
    return [(n, int(s), int(o)) for n, s, o in
            (l.strip().split(',') for l in open(txt) if l.strip())]

def split_blocks(blob):
    p, out = 78, []
    while p + 4 <= len(blob):
        L = struct.unpack_from('<I', blob, p)[0]
        out.append(bytes(blob[p + 4:p + 4 + L]))
        p += 4 + L
    if p != len(blob):
        raise ValueError('blocos nao fecham no fim do arquivo')
    return out

def decode_strip(data, w, rows, stride, ver):
    out = bytearray(stride * rows)
    p = cnt = 0
    color = None
    bpp = 3 if ver == 2 else 1
    for x in range(w):
        for y in range(rows):
            while cnt == 0:
                c = struct.unpack_from('<H', data, p)[0]
                p += 2
                if c & 0x8000:
                    cnt = c & 0x7fff
                    color = data[p:p + bpp]
                    p += bpp
                else:
                    cnt, color = c, None
            if color is None:
                px = data[p:p + bpp]
                p += bpp
            else:
                px = color
            if ver == 3:
                px = bytes(px) * 3
            o = y * stride + 3 * x
            out[o:o + 3] = px
            cnt -= 1
    return out

def bp2_to_bmp(blob):
    magic, ver, h2, h3, h4, h5 = struct.unpack('<6I', blob[:24])
    if magic != 999 or ver not in (2, 3):
        raise ValueError('BP2 desconhecido: %r' % ((magic, ver),))
    bm = bytearray(blob[24:78])
    w, h = struct.unpack('<ii', bm[18:26])
    stride = ((3 * w + 3) // 4) * 4
    blocks = split_blocks(blob)
    pix = bytearray()
    for s in blocks[:h4]:                 # h4 = numero de faixas de 8 linhas
        pix += decode_strip(s, w, 8, stride, ver)
    for s in blocks[h4:]:                 # cauda crua (ausente quando a altura e multiplo de 8)
        pix += s
    assert len(pix) == stride * h, (len(pix), stride * h)
    return bytes(bm) + bytes(pix)

# ---------------------------------------------------------------- codificacao
def _runs(pixels):
    i, n = 0, len(pixels)
    while i < n:
        j = i + 1
        while j < n and pixels[j] == pixels[i]:
            j += 1
        yield pixels[i], j - i
        i = j

def encode_strip(rows_bytes, w, stride, ver):
    """rows_bytes: bytes de 8 linhas (stride*8). Devolve o fluxo de tokens."""
    bpp = 3 if ver == 2 else 1
    seq = []
    for x in range(w):                     # coluna por coluna, de cima para baixo na memoria
        for y in range(8):
            o = y * stride + 3 * x
            px = bytes(rows_bytes[o:o + 3])
            seq.append(px if ver == 2 else px[:1])
    out = bytearray()
    lit = []

    def flush():
        while lit:
            chunk = lit[:0x7fff]
            del lit[:0x7fff]
            out.extend(struct.pack('<H', len(chunk)))
            for q in chunk:
                out.extend(q)

    for px, n in _runs(seq):
        if n >= 2:
            flush()
            while n > 0:
                m = min(n, 0x7fff)
                out.extend(struct.pack('<H', m | 0x8000))
                out.extend(px)
                n -= m
        else:
            lit.append(px)
    flush()
    return bytes(out)

def bmp_to_bp2(bmp, ver):
    bm = bytearray(bmp[:54])
    w, h = struct.unpack('<ii', bm[18:26])
    stride = ((3 * w + 3) // 4) * 4
    pix = bmp[54:54 + stride * h]
    nstrips = h // 8
    tail_rows = h - 8 * nstrips
    if ver == 3 and any(pix[y * stride + 3 * x] != pix[y * stride + 3 * x + 1] or
                        pix[y * stride + 3 * x] != pix[y * stride + 3 * x + 2]
                        for y in range(8 * nstrips) for x in range(w)):
        ver = 2                            # imagem colorida: nao cabe na versao cinza
    blocks = []
    for k in range(nstrips):
        blocks.append(encode_strip(pix[k * 8 * stride:(k + 1) * 8 * stride], w, stride, ver))
    tail = bytes(pix[nstrips * 8 * stride:])
    bm[2:6] = struct.pack('<I', 54 + stride * h)
    bm[34:38] = struct.pack('<I', stride * h)
    hdr = struct.pack('<6I', 999, ver, 0, 8 * stride, nstrips, tail_rows * stride)
    if tail_rows:
        blocks.append(tail)
    body = b''.join(struct.pack('<I', len(b)) + b for b in blocks)
    return hdr + bytes(bm) + body

# ---------------------------------------------------------------- PNG <-> BMP
def bmp_to_png(bmp, path):
    from PIL import Image
    Image.open(io.BytesIO(bmp)).convert('RGB').save(path)

def png_to_bmp(path):
    from PIL import Image
    im = Image.open(path).convert('RGB')
    w, h = im.size
    stride = ((3 * w + 3) // 4) * 4
    px = im.load()
    pix = bytearray(stride * h)
    for y in range(h):                     # BMP guarda de baixo para cima
        row = h - 1 - y
        for x in range(w):
            r, g, b = px[x, y]
            o = row * stride + 3 * x
            pix[o:o + 3] = bytes((b, g, r))
    bm = bytearray(54)
    bm[0:2] = b'BM'
    bm[2:6] = struct.pack('<I', 54 + len(pix))
    bm[10:14] = struct.pack('<I', 54)
    bm[14:18] = struct.pack('<I', 40)
    bm[18:26] = struct.pack('<ii', w, h)
    bm[26:28] = struct.pack('<H', 1)
    bm[28:30] = struct.pack('<H', 24)
    bm[34:38] = struct.pack('<I', len(pix))
    return bytes(bm) + bytes(pix)

def pixels_only(bmp):
    """Largura, altura e so os bytes de pixel (ignora o preenchimento do fim de cada linha)."""
    w, h = struct.unpack('<ii', bmp[18:26])
    stride = ((3 * w + 3) // 4) * 4
    rows = [bmp[54 + r * stride:54 + r * stride + 3 * w] for r in range(h)]
    return (w, h), b''.join(rows)

# ---------------------------------------------------------------- comandos
def cmd_unpack(dat, txt, outdir):
    os.makedirs(outdir, exist_ok=True)
    data = open(dat, 'rb').read()
    ents = load_index(txt)
    for n, s, o in ents:
        bmp = bp2_to_bmp(data[o:o + s])
        bmp_to_png(bmp, os.path.join(outdir, n[:-4] + '.png'))
    print('%d imagens extraidas em %s' % (len(ents), outdir))

def cmd_pack(dat, txt, indir, new_dat, new_txt):
    data = open(dat, 'rb').read()
    ents = load_index(txt)
    out, idx, changed = bytearray(), [], 0
    for n, s, o in ents:
        orig = data[o:o + s]
        png = os.path.join(indir, n[:-4] + '.png')
        blob = orig
        if os.path.exists(png):
            orig_bmp = bp2_to_bmp(orig)
            new_bmp = png_to_bmp(png)
            if pixels_only(new_bmp) != pixels_only(orig_bmp):
                ver = struct.unpack('<I', orig[4:8])[0]
                blob = bmp_to_bp2(new_bmp, ver)
                changed += 1
        idx.append((n, len(blob), len(out)))
        out += blob
    open(new_dat, 'wb').write(out)
    with open(new_txt, 'w', newline='') as f:
        for n, s, o in idx:
            f.write('%s,%d,%d\r\n' % (n, s, o))
    print('%d imagens reescritas, %d mantidas identicas' % (changed, len(ents) - changed))

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 4 and a[0] == 'unpack':
        cmd_unpack(*a[1:])
    elif len(a) == 6 and a[0] == 'pack':
        cmd_pack(*a[1:])
    else:
        print(__doc__)
