"""Detect animations lost or retimed by an editor/embedding round trip.

This compares explicit timing and targets; actual playback remains a separate QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from check_pptx import inspect
from inspect_design import timing_groups


def snapshot(path):
    structure=inspect(path)
    if not structure['ok']:raise ValueError('; '.join(structure['errors']))
    pages=[]
    fields=['target_name','filter','transition','preset_class','preset_id','preset_subtype',
            'behavior_types','auto_reverse','parameters','start_ms','duration_ms']
    with ZipFile(path) as archive:
        for page in structure['slides']:
            groups=timing_groups(ET.fromstring(archive.read(page['part'])))
            if page['animations']['present'] and not groups:
                raise ValueError('Timing is outside the explicit main-sequence comparison scope')
            for group in groups:
                if group['trigger']=='unresolved' or not group['effects'] or any(
                    effect['target_name'] is None or effect['start_ms'] is None or effect['duration_ms'] is None
                    for effect in group['effects']):
                    raise ValueError('Cannot compare unresolved targets or event/sequence/repeat timing')
            pages.append([dict(trigger=g['trigger'],effects=[{field:e.get(field) for field in fields} for e in g['effects']]) for g in groups])
    return pages


def compare_motion(before,after):
    before,after=Path(before),Path(after)
    expected,actual=snapshot(before),snapshot(after)
    errors=[];pages=[]
    if len(expected)!=len(actual):errors.append('Slide count changed')
    for i in range(max(len(expected),len(actual))):
        left=expected[i] if i<len(expected) else None;right=actual[i] if i<len(actual) else None
        ok=left==right
        if not ok:errors.append(f'Slide {i+1}: animation targets, effects, click groups or timing changed')
        pages.append(dict(index=i+1,ok=ok,
                          before_effects=sum(len(g['effects']) for g in left or []),
                          after_effects=sum(len(g['effects']) for g in right or [])))
    return dict(ok=not errors,errors=errors,slides=pages,
                before_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
                after_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),
                scope='Explicit preset rows, named targets, behavior types, native scale/interpolation parameters, click groups and millisecond timing; not rendered motion or cross-player compatibility')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before',type=Path);parser.add_argument('after',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:report=compare_motion(args.before,args.after)
    except (ValueError,OSError) as exc:report=dict(ok=False,errors=[str(exc)])
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded+'\n',encoding='utf8')
    print(encoded);raise SystemExit(0 if report['ok'] else 1)
