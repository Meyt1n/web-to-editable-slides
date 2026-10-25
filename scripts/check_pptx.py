"""Inspect native objects, resources, embedded fonts and root-level slide fades."""
from __future__ import annotations

import argparse
import json
import posixpath
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def font_info(name: str, data: bytes) -> dict:
    valid, kind = False, 'unknown or obfuscated'
    if len(data) >= 36 and struct.unpack_from('<H', data, 34)[0] == 0x504C:
        valid = len(data) > 4096 and struct.unpack_from('<I', data)[0] == len(data)
        kind = 'EOT'
    elif len(data) > 4096 and data[:4] in [b'\x00\x01\x00\x00', b'OTTO', b'ttcf']:
        valid, kind = True, 'OpenType/TrueType'
    return {'part': name, 'bytes': len(data), 'format': kind, 'recognized_header': valid}


def inspect(path: Path, require_fade: bool = False, require_fonts: bool = False) -> dict:
    report = {'slides': [], 'fonts': [], 'external_relationships': [], 'errors': [], 'warnings': []}
    try:
        with zipfile.ZipFile(path) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError(f'ZIP CRC failure: {damaged}')
            main = ET.fromstring(archive.read('ppt/presentation.xml'))
            rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
            targets = {r.get('Id'): r.get('Target') for r in rels}
            ordered = main.find('p:sldIdLst', NS)
            if ordered is None or not len(ordered):
                raise ValueError('Presentation has no slides')
            for i, entry in enumerate(ordered, 1):
                target = targets[entry.get('{' + NS['r'] + '}id')]
                part = posixpath.normpath('ppt/' + target) if not target.startswith('/') else target.lstrip('/')
                root = ET.fromstring(archive.read(part))
                text_boxes = [shape for shape in root.findall('.//p:sp', NS)
                              if ''.join(shape.itertext()).strip() and
                              any(node.text for node in shape.findall('.//a:t', NS))]
                transitions = root.findall('p:transition', NS)
                nested_transitions = root.findall('.//p:transition', NS)
                tags = [node.tag.split('}')[-1] for node in root]
                valid_order = False
                if len(transitions) == 1:
                    index = tags.index('transition')
                    valid_order = index > tags.index('cSld')
                    if 'clrMapOvr' in tags:
                        valid_order &= index > tags.index('clrMapOvr')
                    for later in ['timing', 'extLst']:
                        if later in tags:
                            valid_order &= index < tags.index(later)
                fade = len(transitions) == 1 and transitions[0].find('p:fade', NS) is not None and valid_order
                item = {'index': i, 'part': part, 'editable_text_boxes': len(text_boxes),
                        'shapes': len(root.findall('.//p:sp', NS)),
                        'pictures': len(root.findall('.//p:pic', NS)),
                        'tables': len(root.findall('.//a:tbl', NS)), 'valid_root_fade': fade}
                report['slides'].append(item)
                if not text_boxes and item['pictures']:
                    report['warnings'].append(f'Slide {i}: image page without native text; review whether intentional')
                if nested_transitions and (len(nested_transitions) != 1 or not valid_order):
                    report['errors'].append(f'Slide {i}: transition is nested, duplicated or in invalid order')
                if require_fade and not fade:
                    report['errors'].append(f'Slide {i}: a valid root-level fade is required')
            for name in archive.namelist():
                if name.startswith('ppt/fonts/') and not name.endswith('/'):
                    report['fonts'].append(font_info(name, archive.read(name)))
                if name.endswith('.rels'):
                    relations = ET.fromstring(archive.read(name))
                    for relation in relations:
                        if relation.get('TargetMode') == 'External':
                            report['external_relationships'].append({'part': name, 'target': relation.get('Target')})
                            continue
                        target = relation.get('Target', '')
                        if name == '_rels/.rels':
                            owner_dir = ''
                        else:
                            owner_dir = posixpath.dirname(posixpath.dirname(name))
                        resolved = posixpath.normpath(posixpath.join(owner_dir, target)) if not target.startswith('/') else target.lstrip('/')
                        if resolved not in archive.namelist():
                            report['errors'].append(f'Missing relationship target: {resolved}')
            if require_fonts and (not report['fonts'] or not all(f['recognized_header'] for f in report['fonts'])):
                report['errors'].append('Valid embedded font binaries are required; headers are not sufficient for playback compatibility')
            report['font_families'] = [n.get('typeface') for n in main.findall('.//p:embeddedFont/p:font', NS)]
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['ok'] = not report['errors']
    report['scope'] = 'Structure only; visual layout and cross-application playback require rendering'
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path)
    parser.add_argument('--require-fade', action='store_true')
    parser.add_argument('--require-fonts', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect(args.pptx, args.require_fade, args.require_fonts)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding='utf-8')
    print(serialized)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
