"""Inspect native objects, resources, embedded fonts and root-level slide fades."""
from __future__ import annotations

import argparse
from collections import Counter
from io import BytesIO
import json
import posixpath
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools.ttLib import TTCollection, TTFont, TTLibError

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def font_info(name: str, data: bytes) -> dict:
    """Validate readable font tables, not just a signature or arbitrary size cutoff."""
    result = {'part': name, 'bytes': len(data), 'format': 'unknown or obfuscated',
              'recognized_header': False, 'valid_binary': False}
    payload = data
    if data[:4] in (b'\x00\x01\x00\x00', b'OTTO', b'ttcf'):
        result.update(format='OpenType/TrueType', recognized_header=True)
    elif len(data) >= 36 and struct.unpack_from('<H', data, 34)[0] == 0x504C:
        result['format'] = 'EOT'
        total, size, version, flags = struct.unpack_from('<IIII', data)
        minimum = {0x10000: 96, 0x20001: 100, 0x20002: 120}.get(version)
        if minimum is None or total != len(data) or not size or total - size < minimum:
            result['validation_error'] = 'Invalid EOT length, version or font-data bounds'
            return result
        result['recognized_header'] = True
        # EOT's final FontData field contains the sfnt payload (W3C EOT §3/§4.4).
        payload = data[-size:]
        if flags & 0x10000000:
            payload = bytes(value ^ 0x50 for value in payload)
        if flags & 4:
            result['validation_error'] = 'EOT compressed payload cannot be verified by this checker'
            return result
    else:
        result['validation_error'] = 'Unknown or obfuscated font format'
        return result
    font = None
    try:
        font = TTCollection(BytesIO(payload), lazy=False) if payload[:4] == b'ttcf' else TTFont(BytesIO(payload), lazy=False)
        faces = font.fonts if isinstance(font, TTCollection) else [font]
        if not faces:
            raise ValueError('Empty font collection')
        for face in faces:
            if not {'head', 'maxp', 'cmap', 'name'}.issubset(face.keys()):
                raise ValueError('Required font tables are missing')
            face.ensureDecompiled()
        result['valid_binary'] = True
    except (TTLibError, OSError, ValueError, KeyError, IndexError, AssertionError, struct.error) as exc:
        result['validation_error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if font is not None:
            font.close()
    return result


def relationship_target(owner_dir: str, relation: ET.Element) -> str:
    target = relation.get('Target')
    if not target:
        raise ValueError(f'Relationship {relation.get("Id", "(no Id)")} requires a Target')
    return posixpath.normpath(posixpath.join(owner_dir, target)) if not target.startswith('/') else target.lstrip('/')


def animation_summary(root) -> dict:
    timing=root.find('p:timing',NS)
    if timing is None:return {'present':False,'effects':{},'triggers':{},'duration_ms':[], 'missing_targets':[]}
    ids={node.get('id') for node in root.findall('.//p:cNvPr',NS)}
    targets={node.get('spid') for node in timing.findall('.//p:spTgt',NS)+timing.findall('.//p:bldP',NS)}
    triggers=Counter(node.get('nodeType') for node in timing.findall('.//p:cTn',NS)
                     if node.get('nodeType') in ['clickEffect','withEffect','afterEffect'])
    durations={int(node.get('dur')) for node in timing.findall('.//p:cBhvr/p:cTn',NS)
               if node.get('dur','').isdigit() and int(node.get('dur'))>1}
    return {'present':True,'effects':dict(Counter(node.get('filter','unknown') for node in timing.findall('.//p:animEffect',NS))),
            'triggers':dict(triggers),'duration_ms':sorted(durations),
            'missing_targets':sorted(str(target) for target in targets-ids)}


def inspect(path: Path, require_fade: bool = False, require_fonts: bool = False) -> dict:
    report = {'slides': [], 'fonts': [], 'font_families': [], 'external_relationships': [], 'errors': [], 'warnings': []}
    try:
        with zipfile.ZipFile(path) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError(f'ZIP CRC failure: {damaged}')
            main = ET.fromstring(archive.read('ppt/presentation.xml'))
            rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
            targets = {r.get('Id'): r for r in rels}
            ordered = main.find('p:sldIdLst', NS)
            if ordered is None or not len(ordered):
                raise ValueError('Presentation has no slides')
            for i, entry in enumerate(ordered, 1):
                relation = targets[entry.get('{' + NS['r'] + '}id')]
                if relation.get('TargetMode') == 'External' or relation.get('Type') != NS['r'] + '/slide':
                    raise ValueError(f'Slide {i}: expected an internal slide relationship')
                part = relationship_target('ppt', relation)
                root = ET.fromstring(archive.read(part))
                text_boxes = [shape for shape in root.findall('.//p:sp', NS)
                              if ''.join(shape.itertext()).strip() and
                              any(node.text and node.text.strip() for node in shape.findall('.//a:t', NS))]
                text_cells = [cell for cell in root.findall('.//a:tbl/a:tr/a:tc', NS)
                              if any(node.text and node.text.strip() for node in cell.findall('.//a:t', NS))]
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
                        'editable_table_cells': len(text_cells),
                        'shapes': len(root.findall('.//p:sp', NS)),
                        'pictures': len(root.findall('.//p:pic', NS)),
                        'tables': len(root.findall('.//a:tbl', NS)), 'valid_root_fade': fade,
                        'animations':animation_summary(root)}
                report['slides'].append(item)
                if item['animations']['missing_targets']:
                    report['errors'].append(f'Slide {i}: animations reference missing shape ids: '+', '.join(item['animations']['missing_targets']))
                if not text_boxes and not text_cells and item['pictures']:
                    report['warnings'].append(f'Slide {i}: image page without native text; review whether intentional')
                if nested_transitions and (len(nested_transitions) != 1 or not valid_order):
                    report['errors'].append(f'Slide {i}: transition is nested, duplicated or in invalid order')
                if require_fade and not fade:
                    report['errors'].append(f'Slide {i}: a valid root-level fade is required')
            names = set(archive.namelist())
            font_parts = {name for name in names if name.startswith('ppt/fonts/') and not name.endswith('/')}
            embedded_parts = set()
            entries = main.findall('p:embeddedFontLst/p:embeddedFont', NS)
            for entry in entries:
                family = entry.find('p:font', NS)
                if family is None or not family.get('typeface', '').strip():
                    report['errors'].append('Embedded font declaration requires a typeface')
                else:
                    report['font_families'].append(family.get('typeface'))
                variants = [node for node in entry if node.tag in {
                    '{' + NS['p'] + '}' + style for style in ['regular', 'bold', 'italic', 'boldItalic']}]
                if not variants:
                    report['errors'].append('Embedded font declaration has no font-data variant')
                for variant in variants:
                    rid = variant.get('{' + NS['r'] + '}id')
                    relation = targets.get(rid)
                    if relation is None:
                        report['errors'].append(f'Embedded font references missing relationship: {rid}')
                        continue
                    if relation.get('TargetMode') == 'External' or relation.get('Type') != NS['r'] + '/font':
                        report['errors'].append(f'Embedded font {rid} requires an internal font relationship')
                        continue
                    part = relationship_target('ppt', relation)
                    embedded_parts.add(part)
                    if part in names:
                        font_parts.add(part)
            for part in sorted(font_parts):
                info = font_info(part, archive.read(part))
                info['embedded'] = part in embedded_parts
                report['fonts'].append(info)
                if not info['embedded']:
                    report['warnings'].append(f'Font part is not referenced by an embedded font declaration: {part}')
                elif not info['valid_binary']:
                    report['warnings'].append(f'Embedded font binary is unverified: {part}; {info["validation_error"]}')
            for name in sorted(names):
                if name.endswith('.rels'):
                    relations = ET.fromstring(archive.read(name))
                    ids = set()
                    for relation in relations:
                        rid = relation.get('Id')
                        if not rid or rid in ids:
                            report['errors'].append(f'Missing or duplicate relationship Id in {name}: {rid}')
                        ids.add(rid)
                        if relation.get('TargetMode') == 'External':
                            report['external_relationships'].append({'part': name, 'target': relation.get('Target')})
                            continue
                        if name == '_rels/.rels':
                            owner_dir = ''
                        else:
                            owner_dir = posixpath.dirname(posixpath.dirname(name))
                        resolved = relationship_target(owner_dir, relation)
                        if resolved not in names:
                            report['errors'].append(f'Missing relationship target: {resolved}')
            embedded = [info for info in report['fonts'] if info['embedded']]
            if require_fonts and (not entries or not embedded or not all(info['valid_binary'] for info in embedded)):
                report['errors'].append('Valid declared embedded font binaries and internal font relationships are required; playback still requires rendering')
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
