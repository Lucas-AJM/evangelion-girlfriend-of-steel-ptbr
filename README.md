# Evangelion: Girlfriend of Steel – ferramentas para tradução PT-BR

Ferramentas usadas na tradução para português do Brasil de *Shin Seiki Evangelion: Tetsu no Girlfriend* (PC).

**Este repositório não contém arquivos do jogo nem o texto do roteiro.** Você precisa ter sua própria cópia do jogo.

## Ferramentas
- `bp2tool.py`: extrai e reempacota o `TEXTBMP.DAT` (imagens de texto em formato BP2).
- `render_pt.py`: desenha as falas em português como imagens PNG no estilo do jogo.

Requisitos: Python 3 e Pillow (`pip install pillow`). O `render_pt.py` também precisa de uma fonte `texgyreheroscn-regular.otf` na mesma pasta (TeX Gyre Heros Cn, licença GUST Font License).

## Uso
```
python bp2tool.py unpack TEXTBMP.DAT TEXTBMP.TXT pasta_png
python render_pt.py traducao_pt.csv pasta_saida
python bp2tool.py pack TEXTBMP.DAT TEXTBMP.TXT pasta_saida NOVO_TEXTBMP.DAT NOVO_TEXTBMP.TXT
```
Faça sempre backup dos arquivos originais antes de substituir qualquer coisa.

## Créditos
- Jogo original: seus respectivos autores e detentores dos direitos (mantidos intactos).
- Ferramentas e adaptação PT-BR: Lucas_AJM.

Projeto de fã, sem fins lucrativos e sem vínculo com os detentores dos direitos.
