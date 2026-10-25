"""Create a relative-path image inventory and numbered contact sheet."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}


def inventory(root: Path, output_dir: Path, columns: int = 4) -> dict:
    root, output_dir = root.resolve(), output_dir.resolve()
    if not root.is_dir():
        raise ValueError(f'Input directory does not exist: {root}')
    if columns < 1 or columns > 12:
        raise ValueError('columns must be between 1 and 12')
    if output_dir == root or root.is_relative_to(output_dir):
        raise ValueError('Output must not be the input directory or an ancestor of it')
    paths = sorted((p for p in root.rglob('*') if p.is_file() and
                    p.suffix.lower() in EXTENSIONS and
                    not p.resolve().is_relative_to(output_dir)),
                   key=lambda p: p.relative_to(root).as_posix().casefold())
    output_dir.mkdir(parents=True, exist_ok=True)
    entries, failures, thumbs = [], [], []
    for p in paths:
        relative = p.relative_to(root).as_posix()
        try:
            with Image.open(p) as source:
                im = ImageOps.exif_transpose(source).convert('RGBA')
                alpha = im.getchannel('A')
                entries.append({'id': len(entries) + 1, 'file': relative,
                                'width': im.width, 'height': im.height,
                                'has_transparency': alpha.getextrema()[0] < 255,
                                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
                base = Image.new('RGBA', im.size, '#EDF3ED')
                base.alpha_composite(im)
                thumbs.append(ImageOps.contain(base.convert('RGB'), (300, 180)))
        except (OSError, ValueError) as exc:
            failures.append({'file': relative, 'error': type(exc).__name__})
    result = {'images': entries, 'unreadable': failures}
    (output_dir / 'inventory.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if entries:
        rows = math.ceil(len(entries) / columns)
        sheet = Image.new('RGB', (columns * 320, rows * 220), '#FAFCF9')
        draw = ImageDraw.Draw(sheet)
        for i, thumb in enumerate(thumbs):
            x, y = (i % columns) * 320, (i // columns) * 220
            draw.text((x + 12, y + 8), f'{i + 1:02}  {entries[i]["width"]}x{entries[i]["height"]}', fill='#164B3B')
            sheet.paste(thumb, (x + (320 - thumb.width) // 2, y + 30))
        sheet.save(output_dir / 'contact-sheet.jpg', quality=90)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--columns', type=int, default=4)
    args = parser.parse_args()
    try:
        result = inventory(args.directory, args.output_dir, args.columns)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({'images': len(result['images']), 'unreadable': len(result['unreadable'])}))
    return 0 if not result['unreadable'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
