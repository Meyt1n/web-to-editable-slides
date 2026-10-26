"""Review declared slide design intent; warnings are suggestions, not visual scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from make_handoff import validate
from template_pack import load_template, validate_template


def review(brief: dict, template: dict|None = None, require_template: bool = False) -> dict:
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
    binding=design.get('template')
    if require_template and (not binding or template is None):
        result['errors'].append('A template binding and a loaded template are required before page production')
    if template is not None:
        try:validate_template(template)
        except (ValueError,TypeError) as exc:
            result['errors'].append(str(exc));result['ok']=False;return result
        result['summary']['template']={'id':template['id'],'version':template['version']}
        if not binding or binding['id']!=template['id'] or binding['version']!=template['version']:
            result['errors'].append('Template identity/version does not match the design plan')
        allowed_fonts={role['family'] for role in template['typography'].values()}
        allowed_colors={color.upper() for color in template['palette'].values()}
        def drift(message,slide=None):
            override=(slide or {}).get('template_override') or design.get('template_override')
            if override:
                suggest('template-override',[] if slide is None else [slide['id']],message+'; reason: '+override['reason'])
            else:result['errors'].append(message)
        declared_colors=brief.get('style',{}).get('colors',[])
        if any(color.upper() not in allowed_colors for color in declared_colors):
            drift('Declared palette differs from the bound template')
        for slide in slides:
            if slide.get('layout') not in template['layouts']:
                drift(f'Slide {slide["id"]}: layout is not a variant in the bound template',slide)
            profile=profiles.get(slide.get('font_profile'),{})
            if any(family not in allowed_fonts for family in profile.values()):
                drift(f'Slide {slide["id"]}: font family differs from the bound template',slide)
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
    parser.add_argument('--template',type=Path)
    parser.add_argument('--require-template',action='store_true')
    args=parser.parse_args()
    try:
        brief=json.loads(args.brief.read_text('utf-8-sig'))
        validate(brief)
        path=args.template
        if path is None and brief.get('design',{}).get('template',{}).get('file'):
            path=args.brief.resolve().parent/brief['design']['template']['file']
        template=load_template(path) if path is not None else None
        result=review(brief,template,args.require_template)
    except (ValueError,OSError) as exc:
        parser.error(str(exc))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf8')
    print(text)
    return 0 if result['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
