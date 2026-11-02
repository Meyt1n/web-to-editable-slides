"""Inspect declared fonts, background layers and animation timing without copying source content."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import posixpath
import zipfile
from xml.etree import ElementTree as ET

from check_pptx import NS,inspect


def analyze(path: Path) -> dict:
    structure=inspect(path)
    if not structure['ok']:raise ValueError('; '.join(structure['errors']))
    report={'slides':[],'explicit_font_uses':{},'scope':'Native font declarations and XML layers; image lettering and perceived background contrast require visual review'}
    total=Counter()
    with zipfile.ZipFile(path) as z:
        presentation=ET.fromstring(z.read('ppt/presentation.xml'))
        canvas=presentation.find('p:sldSz',NS);cw,ch=int(canvas.get('cx')),int(canvas.get('cy'))
        for page in structure['slides']:
            root=ET.fromstring(z.read(page['part']));fonts=Counter()
            for node in root.findall('.//a:rPr',NS)+root.findall('.//a:defRPr',NS):
                for tag in ['latin','ea','cs']:
                    child=node.find('a:'+tag,NS)
                    if child is not None and child.get('typeface'):fonts[child.get('typeface')]+=1
            total.update(fonts)
            background=root.find('p:cSld/p:bg',NS)
            relations={};part=page['part'];rels=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
            if rels in z.namelist():
                relations={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read(rels))}
            pictures=[]
            for pic in root.findall('.//p:pic',NS):
                transform=pic.find('p:spPr/a:xfrm',NS);extent=transform.find('a:ext',NS) if transform is not None else None
                blip=pic.find('.//a:blip',NS);rid=blip.get('{'+NS['r']+'}embed') if blip is not None else None
                ratio=(int(extent.get('cx'))*int(extent.get('cy'))/(cw*ch)) if extent is not None else None
                pictures.append({'relationship_target':relations.get(rid),'area_fraction':round(ratio,4) if ratio is not None else None,
                                 'background_candidate':ratio is not None and ratio>.8})
            report['slides'].append({'index':page['index'],'fonts':dict(fonts),
                'background_colors':[n.get('val') for n in background.findall('.//a:srgbClr',NS)] if background is not None else [],
                'background_inherited':background is None,'pictures':pictures,
                'animations':page['animations'],'valid_root_fade':page['valid_root_fade']})
    report['explicit_font_uses']=dict(total)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pptx',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        report=analyze(args.pptx);args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    except (ValueError,OSError,ET.ParseError,KeyError) as exc:parser.error(str(exc))
    print(json.dumps({'pages':len(report['slides']),'font_declarations':report['explicit_font_uses'],'report':str(args.output)},ensure_ascii=False))
