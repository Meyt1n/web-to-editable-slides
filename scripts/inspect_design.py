"""Inspect declared fonts, background layers and animation timing without copying source content."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import posixpath
import re
import zipfile
from xml.etree import ElementTree as ET

from check_pptx import NS,inspect,relationship_target


def timing_groups(root) -> list[dict]:
    """Inspect explicit parallel delay trees; do not guess event/sequence timing."""
    timing=root.find('p:timing',NS)
    if timing is None:return []
    parents={child:parent for parent in timing.iter() for child in parent}
    names={node.get('id'):node.get('name') for node in root.findall('.//p:cNvPr',NS)}
    def offset(node,stop,skip=None):
        start=0
        while node is not None and node is not stop:
            if node.tag=='{'+NS['p']+'}seq':return None
            if node.tag=='{'+NS['p']+'}cTn' and node is not skip:
                conditions=node.findall('p:stCondLst/p:cond',NS)
                if len(conditions)>1:return None
                for condition in conditions:
                    delay=condition.get('delay','0')
                    if condition.get('evt') or len(condition) or not delay.isdigit():return None
                    start+=int(delay)
            node=parents.get(node)
        return start
    def reversal(clock):
        if any(key in clock.attrib for key in ['repeatCount','repeatDur','spd']):return None
        value=clock.get('autoRev','0')
        return 2 if value in ['1','true'] else 1 if value in ['0','false'] else None
    groups=timing.findall('.//p:cTn[@nodeType="mainSeq"]/p:childTnLst/p:par',NS)
    result=[]
    for index,group in enumerate(groups,1):
        clock=group.find('p:cTn',NS);conditions=clock.findall('p:stCondLst/p:cond',NS) if clock is not None else []
        clicks=group.findall('.//p:cTn[@nodeType="clickEffect"]',NS)
        trigger='onClick' if clicks else 'automatic' if any(c.get('evt')=='onBegin' or
            c.get('delay')=='0' and not c.get('evt') for c in conditions) else 'unresolved'
        effects=[]
        # A native fly/zoom/pulse has no animEffect filter: inspect the preset row.
        rows=group.findall('.//p:cTn[@presetClass]',NS) or group.findall('.//p:animEffect',NS)
        for row in rows:
            filters=row.findall('.//p:animEffect',NS) if row.tag!='{'+NS['p']+'}animEffect' else [row]
            targets={target.get('spid') for target in row.findall('.//p:spTgt',NS)}
            key=next(iter(targets)) if len(targets)==1 else None
            ends=[]
            for behavior in row.findall('.//p:cBhvr/p:cTn',NS):
                duration=behavior.get('dur','');delay=offset(behavior,row);factor=reversal(behavior)
                ends.append(delay+int(duration)*factor if duration.isdigit() and delay is not None and factor is not None else None)
            factor=reversal(row)
            duration=max(ends)*factor if ends and None not in ends and factor is not None else None
            if row.get('dur','').isdigit() and factor is not None:duration=int(row.get('dur'))*factor
            effects.append(dict(target_id=key,target_name=names.get(key),
                filter=filters[0].get('filter') if len(filters)==1 else None,
                transition=filters[0].get('transition') if len(filters)==1 else None,
                preset_class=row.get('presetClass'),preset_id=row.get('presetID'),preset_subtype=row.get('presetSubtype'),
                auto_reverse=row.get('autoRev','0') in ['1','true'],
                parameters=dict(scale=[dict(n.attrib) for n in row.findall('.//p:animScale/p:by',NS)],
                    interpolation=[dict(attributes=[n.text for n in anim.findall('p:cBhvr/p:attrNameLst/p:attrName',NS)],
                        values=[dict(time=tav.get('tm'),value=dict(tav[0][0].attrib)) for tav in anim.findall('p:tavLst/p:tav',NS) if len(tav) and len(tav[0])])
                        for anim in row.findall('.//p:anim',NS)]),
                behavior_types=sorted({parents[b].tag.split('}')[-1] for b in row.findall('.//p:cBhvr',NS)}),
                start_ms=offset(row,group,clock),duration_ms=duration))
        complete=bool(effects) and all(e['start_ms'] is not None and e['duration_ms'] is not None for e in effects)
        result.append(dict(index=index,trigger=trigger,effects=effects,
            duration_ms_estimate=max(e['start_ms']+e['duration_ms'] for e in effects) if complete else None,
            timing_scope='Explicit parallel delays and simple auto-reverse relative to this group; excludes click pauses. Event/sequence/repeat timing is left unresolved.'))
    return result


def analyze(path: Path) -> dict:
    structure=inspect(path)
    if not structure['ok']:raise ValueError('; '.join(structure['errors']))
    report={'slides':[],'explicit_font_uses':{},'scope':'Native font declarations and XML layers; image lettering and perceived background contrast require visual review'}
    total=Counter()
    with zipfile.ZipFile(path) as z:
        presentation=ET.fromstring(z.read('ppt/presentation.xml'))
        canvas=presentation.find('p:sldSz',NS);cw,ch=int(canvas.get('cx')),int(canvas.get('cy'))
        report['canvas_points']=[round(cw/12700,3),round(ch/12700,3)]
        report['embedded_font_parts']=len(structure['fonts'])
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
                relations={r.get('Id'):r for r in ET.fromstring(z.read(rels))}
            pictures=[]
            for pic in root.findall('.//p:pic',NS):
                props=pic.find('p:nvPicPr/p:cNvPr',NS)
                transform=pic.find('p:spPr/a:xfrm',NS);extent=transform.find('a:ext',NS) if transform is not None else None
                offset=transform.find('a:off',NS) if transform is not None else None
                blip=pic.find('.//a:blip',NS);rid=blip.get('{'+NS['r']+'}embed') if blip is not None else None
                ratio=(int(extent.get('cx'))*int(extent.get('cy'))/(cw*ch)) if extent is not None else None
                relation=relations.get(rid);target=relation.get('Target') if relation is not None else None
                pictures.append({'shape_id':props.get('id') if props is not None else None,
                                 'name':props.get('name') if props is not None else None,
                                 'relationship_target':target,
                                 'resource_part':relationship_target(posixpath.dirname(part),relation) if relation is not None and relation.get('TargetMode')!='External' else None,
                                 'bounds_emu':[int(offset.get('x')),int(offset.get('y')),int(extent.get('cx')),int(extent.get('cy'))] if offset is not None and extent is not None else None,
                                 'area_fraction':round(ratio,4) if ratio is not None else None,
                                 'background_candidate':ratio is not None and ratio>.8})
            report['slides'].append({'index':page['index'],'fonts':dict(fonts),
                'native_text_boxes':page['editable_text_boxes'],'native_shapes':page['shapes'],
                'word_image_name_candidates':sum(bool(re.search(r'_w\d+$',p['name'] or '')) for p in pictures),
                'background_colors':[n.get('val') for n in background.findall('.//a:srgbClr',NS)] if background is not None else [],
                'background_inherited':background is None,'pictures':pictures,
                'animations':page['animations'],'animation_groups':timing_groups(root),
                'transition':page['transition'],'valid_root_fade':page['valid_root_fade']})
    report['explicit_font_uses']=dict(total)
    recurring={}
    for slide in report['slides']:
        for picture in slide['pictures']:
            if picture['background_candidate'] and picture['name']:
                recurring.setdefault(picture['name'],[]).append((slide['index'],picture))
    report['recurring_background_candidates']=[dict(name=name,slides=[i for i,p in entries],
        same_resource=all(p['resource_part'] for i,p in entries) and len({p['resource_part'] for i,p in entries})==1,
        same_bounds=all(p['bounds_emu'] is not None for i,p in entries) and len({tuple(p['bounds_emu'] or []) for i,p in entries})==1)
        for name,entries in recurring.items() if len({i for i,p in entries})>1]
    report['image_text_scope']='Word-image candidates are a naming heuristic, not OCR or font identification; confirm visually.'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pptx',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        report=analyze(args.pptx);args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    except (ValueError,OSError,ET.ParseError,KeyError) as exc:parser.error(str(exc))
    print(json.dumps({'pages':len(report['slides']),'font_declarations':report['explicit_font_uses'],'report':str(args.output)},ensure_ascii=False))
