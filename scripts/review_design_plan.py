"""Review declared slide design intent; warnings are suggestions, not visual scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_handoff import validate


def review(brief: dict) -> dict:
    result={'errors':[],'suggestions':[],'summary':{},
            'scope':'Declared plan only; does not inspect actual typography, layout or images'}
    try:
        validate(brief)
    except ValueError as exc:
        result['errors'].append(str(exc));result['ok']=False;return result
    slides=sorted(brief['slides'],key=lambda s:s['id'])
    design=brief.get('design',{});mode=design.get('mode','enhance')
    profiles=design.get('font_profiles',{})
    declared=[s for s in slides if s.get('layout')]
    result['summary']={'mode':mode,'pages':len(slides),'declared_layouts':len(declared),
                       'distinct_layouts':len({s['layout'] for s in declared})}
    def suggest(code,pages,message):
        result['suggestions'].append({'code':code,'pages':pages,'message':message})
    for name,roles in profiles.items():
        if len(set(roles.values()))>3:
            suggest('many-font-families',[],f'Profile {name} has more than three families; check that each role is needed')
    for slide in slides:
        name=slide.get('font_profile')
        if name and name not in profiles:
            result['errors'].append(f'Slide {slide["id"]}: undefined font profile {name}')
        if slide.get('layout')=='data-focus' and not slide.get('data_source') and not slide.get('data_is_illustrative'):
            suggest('missing-data-source',[slide['id']],'Choose a data source or clearly label illustrative data; do not invent performance')
        if declared and not slide.get('layout'):
            suggest('unspecified-layout',[slide['id']],'Record the intended layout before judging sequence variety')
    if mode!='fidelity':
        run=[];last=None
        for slide in slides+[{'id':None}]:
            current=slide.get('layout')
            if current==last and current:
                run.append(slide['id'])
            else:
                if len(run)>=3:
                    suggest('repeated-layout',run[:],f'{last} repeats consecutively; keep it when comparison benefits, otherwise vary the structure')
                run=[slide['id']] if current else [];last=current
    result['ok']=not result['errors']
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('brief',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        result=review(json.loads(args.brief.read_text('utf-8-sig')))
    except (ValueError,OSError) as exc:
        parser.error(str(exc))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf8')
    print(text)
    return 0 if result['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
