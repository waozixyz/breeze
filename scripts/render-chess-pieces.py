#!/usr/bin/env python3
"""Render Chess's flat pieces to assets/chess/pieces/*.png.

The pieces are drawn here as SVG in a 100 x 100 box, in the app's palette:
ivory pieces outlined in earth brown, pine pieces with sky-blue details, and
the light orange accent only on the king's cross and the queen's top jewel.
Pass --preview FILE to also write one image of every piece on board squares.
"""
from pathlib import Path
import argparse
import io

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'assets/chess/pieces'
SIZE = 160

COLORS = {
    'white': {'fill': '#f6f1e7', 'edge': '#6e4c36', 'detail': '#6e4c36'},
    'black': {'fill': '#1e4a40', 'edge': '#10302a', 'detail': '#a8c8d2'},
}
ACCENT = '#f2a65e'
SHADOW = '<ellipse cx="50" cy="90" rx="29" ry="4" fill="#1e4a40" opacity="0.18"/>'
BASE = '<rect x="24" y="78" width="52" height="10" rx="4" class="body"/>'

# Each piece: body shapes (filled and outlined), then detail lines.
PIECES = {
    'pawn': [
        '<path class="body" d="M33 79C35 67 42 59 44 51H56C58 59 65 67 67 79Z"/>',
        '<rect class="body" x="37" y="44" width="26" height="8" rx="3"/>',
        '<circle class="body" cx="50" cy="31" r="12"/>',
        BASE,
    ],
    'rook': [
        '<path class="body" d="M33 79L36 45H64L67 79Z"/>',
        '<rect class="body" x="30" y="40" width="40" height="7" rx="2"/>',
        '<path class="body" d="M28 20V41H72V20H63V27H55V20H45V27H37V20Z"/>',
        BASE,
        '<path class="detail" d="M38 58H62"/>',
    ],
    'knight': [
        '<path class="body" d="M31 79C30 67 36 58 45 52C38 51 31 50 27 45C23 40 25 33 31 28L41 22'
        'C43 16 49 12 55 13L58 8L62 15C71 19 76 31 74 45C72 59 69 69 71 79Z"/>',
        BASE,
        '<circle class="eye" cx="43" cy="29" r="2.6"/>',
        '<path class="detail" d="M61 18C68 26 70 39 66 55"/>',
        '<path class="detail" d="M29 41C31 42 33 42 35 41"/>',
    ],
    'bishop': [
        '<path class="body" d="M34 79C36 66 42 59 44 55H56C58 59 64 66 66 79Z"/>',
        '<rect class="body" x="36" y="49" width="28" height="7" rx="3"/>',
        '<path class="body" d="M50 17C38 26 33 38 39 49H61C67 38 62 26 50 17Z"/>',
        '<circle class="body" cx="50" cy="13" r="4.5"/>',
        BASE,
        '<path class="detail" d="M55 27L46 39"/>',
    ],
    'queen': [
        '<path class="body" d="M30 79C34 65 40 55 42 47H58C60 55 66 65 70 79Z"/>',
        '<path class="body" d="M24 26L34 47H66L76 26L64 37L60 19L54 35L50 15L46 35L40 19L36 37Z"/>',
        '<rect class="body" x="33" y="44" width="34" height="7" rx="3"/>',
        '<circle class="body" cx="24" cy="24" r="3.8"/>',
        '<circle class="body" cx="40" cy="17" r="3.8"/>',
        '<circle class="accent" cx="50" cy="12" r="4.2"/>',
        '<circle class="body" cx="60" cy="17" r="3.8"/>',
        '<circle class="body" cx="76" cy="24" r="3.8"/>',
        BASE,
    ],
    'king': [
        '<path class="body" d="M30 79C34 65 40 55 42 47H58C60 55 66 65 70 79Z"/>',
        '<path class="body" d="M29 31C29 42 35 47 40 47H60C65 47 71 42 71 31C63 26 56 29 50 34'
        'C44 29 37 26 29 31Z"/>',
        '<rect class="body" x="33" y="44" width="34" height="7" rx="3"/>',
        '<path class="accent" d="M47 7H53V14H60V20H53V31H47V20H40V14H47Z"/>',
        BASE,
        '<path class="detail" d="M38 38H62"/>',
    ],
}


def svg(color, kind):
    palette = COLORS[color]
    style = (
        f'.body{{fill:{palette["fill"]};stroke:{palette["edge"]};stroke-width:3;stroke-linejoin:round}}'
        f'.detail{{fill:none;stroke:{palette["detail"]};stroke-width:2.4;stroke-linecap:round}}'
        f'.eye{{fill:{palette["detail"]}}}'
        f'.accent{{fill:{ACCENT};stroke:{palette["edge"]};stroke-width:2.4;stroke-linejoin:round}}'
    )
    shapes = ''.join(PIECES[kind])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{SIZE}" height="{SIZE}">'
            f'<style>{style}</style>{SHADOW}{shapes}</svg>')


def render(color, kind):
    data = cairosvg.svg2png(bytestring=svg(color, kind).encode(), output_width=SIZE, output_height=SIZE)
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview')
    arguments = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for color in COLORS:
        for kind in PIECES:
            image = render(color, kind)
            rendered[(color, kind)] = image
            # Fixed PNG settings keep repeated renders byte-identical.
            image.save(OUTPUT / f'{color}-{kind}.png', optimize=True)
    if arguments.preview:
        cell = SIZE
        sheet = Image.new('RGBA', (cell * 6, cell * 2), '#dde9e5')
        for row, color in enumerate(COLORS):
            for column, kind in enumerate(PIECES):
                square = '#dde9e5' if (row + column) % 2 == 0 else '#7fa69a'
                tile = Image.new('RGBA', (cell, cell), square)
                tile.alpha_composite(rendered[(color, kind)])
                sheet.paste(tile, (column * cell, row * cell))
        sheet.save(arguments.preview)


if __name__ == '__main__':
    main()
