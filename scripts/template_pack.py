"""Package model-extracted reference observations; this script does not analyze images."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
from pathlib import Path


def inside(root:Path,relative:str)->Path:
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or re.match(r'^[A-Za-z]:',relative):
        raise ValueError('Template resource paths must be relative')
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Template resource escapes its directory')
    return path


def validate_template(data:dict,root:Path|None=None)->dict:
    if not isinstance(data,dict) or data.get('schema_version')!='1.0':
        raise ValueError('Template schema_version must be 1.0')
    for field in ['id','version']:
        if not isinstance(data.get(field),str) or not data[field].strip():
            raise ValueError(f'Template requires {field}')
    canvas=data.get('canvas',[])
    if not isinstance(canvas,list) or len(canvas)!=2 or any(type(n) not in [int,float] or not math.isfinite(n) or n<=0 for n in canvas):
        raise ValueError('Template canvas must contain two positive dimensions')
    palette=data.get('palette',{})
    if not isinstance(palette,dict) or not palette or any(not isinstance(k,str) or not k.strip() or
            not isinstance(c,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',c) for k,c in palette.items()):
        raise ValueError('Template palette must use named HEX6 colors')
    resources=data.get('resources',{})
    if not isinstance(resources,dict):
        raise ValueError('Template resources must be an object')
    fonts=resources.get('fonts',{})
    typography=data.get('typography',{})
    if not isinstance(fonts,dict) or not fonts or not isinstance(typography,dict) or not typography:
        raise ValueError('Template requires font resources and typography roles')
    for role,settings in typography.items():
        if not isinstance(settings,dict) or not isinstance(settings.get('family'),str) or settings['family'] not in fonts:
            raise ValueError(f'Font role {role} must name a declared resource')
        if type(settings.get('size')) not in [int,float] or not math.isfinite(settings['size']) or settings['size']<=0:
            raise ValueError(f'Font role {role} requires a finite positive size')
    paths=[]
    background=resources.get('background')
    if background is not None:paths.append(background)
    for family,settings in fonts.items():
        if not isinstance(family,str) or not family.strip() or not isinstance(settings,dict):
            raise ValueError('Font resources must map non-empty family names to objects')
        if 'system_font' in settings and type(settings['system_font']) is not bool:
            raise ValueError(f'Font {family}: system_font must be true or false')
        if settings.get('system_font') is True:
            if 'file' in settings or 'license_file' in settings:
                raise ValueError(f'Font {family}: system fonts cannot also declare redistributed files')
            continue
        if not settings.get('file') or not settings.get('license_file'):
            raise ValueError('Redistributed fonts require both file and license_file')
        paths.extend([settings['file'],settings['license_file']])
    references=data.get('references',[])
    if not isinstance(references,list) or not references or any(not isinstance(r,dict) or
            not isinstance(r.get('id'),str) or not r['id'].strip() or not r.get('file') for r in references):
        raise ValueError('A reference-derived template must identify its source images')
    if len({r['id'] for r in references})!=len(references):
        raise ValueError('Template reference ids must be unique')
    paths.extend(r['file'] for r in references)
    layouts=data.get('layouts',{})
    if not isinstance(layouts,dict) or not layouts or not isinstance(data.get('components'),dict) or not data['components']:
        raise ValueError('Template requires layout skeletons and component styles')
    for name,layout in layouts.items():
        if not isinstance(layout,dict) or not isinstance(layout.get('slots'),dict) or not layout['slots']:
            raise ValueError(f'Layout {name} requires slots')
        for slot,value in layout['slots'].items():
            boxes=value if isinstance(value,list) and value and isinstance(value[0],list) else [value]
            for box in boxes:
                if not isinstance(box,list) or len(box)!=4 or any(type(n) not in [int,float] or not math.isfinite(n) for n in box):
                    raise ValueError(f'Invalid slot {name}.{slot}')
                x,y,w,h=box
                if min(x,y)<0 or min(w,h)<=0 or x+w>canvas[0]+.1 or y+h>canvas[1]+.1:
                    raise ValueError(f'Slot {name}.{slot} is outside the canvas')
    for field in ['adaptations','variation_rules']:
        if field in data and (not isinstance(data[field],list) or not all(isinstance(v,str) for v in data[field])):
            raise ValueError(f'Template {field} must be a list of strings')
    for relative in paths:
        path=inside(root or Path.cwd(),relative)
        if root is not None and not path.is_file():
            raise ValueError(f'Missing template resource: {relative}')
    return data


def load_template(path:Path)->dict:
    return validate_template(json.loads(path.read_text('utf-8-sig')),path.resolve().parent)


def describe(data:dict)->str:
    lines=[f'# {data.get("title",data["id"])}','',f'模板：`{data["id"]}` / `{data["version"]}`',
           f'画幅：{data["canvas"][0]} × {data["canvas"][1]}',
           '状态：已整理参数（prepared）；脚本不代表视觉检查通过。','','## 来源与观测','']
    for ref in data['references']:
        lines.append(f'- [{ref["id"]}]({ref["file"]})：{ref.get("role","")}；{ref.get("observation","")}')
    lines+=['','## 固定规范','', '配色：'+'；'.join(f'{k}={v}' for k,v in data['palette'].items())]
    for role,value in data['typography'].items():
        lines.append(f'- {role}：{value["family"]}，{value["size"]} pt')
    lines+=['- 网格：'+json.dumps(data.get('grid',{}),ensure_ascii=False),
            '- 原生组件：'+'、'.join(data['components']),
            '','## 页型骨架','']
    for key,value in data['layouts'].items():
        lines.append(f'- `{key}`：{value.get("description","")}；槽位：'+ '、'.join(value['slots']))
    lines+=['','## 近似、可变项与使用方式','']
    lines+=['- '+v for v in data.get('adaptations',[])]
    lines+=['- '+v for v in data.get('variation_rules',[])]
    lines+=['- 后续设计绑定模板ID与版本，先读取页型槽位和组件；文字与事实来自页面内容，不从模板复制。',
            '- 需要新页型时在这些规则内扩展变体，保留修改说明；模板结构检查不能代替样页与整套导图。']
    return '\n'.join(lines).rstrip()+'\n'


def prepare(observations:Path,source_dir:Path,output:Path,force:bool=False)->Path:
    source_dir,output=source_dir.resolve(),output.resolve()
    if source_dir==output or source_dir.is_relative_to(output):
        raise ValueError('Output cannot replace or contain the source directory')
    if output.exists() and any(output.iterdir()) and not force:
        raise ValueError('Output is not empty; choose a new directory or --force')
    data=copy.deepcopy(json.loads(observations.read_text('utf-8-sig')))
    validate_template(data,source_dir)
    sources=[r['file'] for r in data['references']]
    if data['resources'].get('background'):
        sources.append(data['resources']['background'])
    for settings in data['resources']['fonts'].values():
        if not settings.get('system_font'):
            sources.extend([settings['file'],settings['license_file']])
    if any(inside(source_dir,relative).is_relative_to(output) for relative in sources):
        raise ValueError('Output must not contain source resources, even with --force')
    for index,reference in enumerate(data['references'],1):
        origin=inside(source_dir,reference['file'])
        relative=f'references/{index:02}{origin.suffix.lower()}'
        (output/relative).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(origin,output/relative)
        reference['file']=relative;reference['sha256']=hashlib.sha256(origin.read_bytes()).hexdigest()
    background=data['resources'].get('background')
    if background:
        origin=inside(source_dir,background);relative='media/background'+origin.suffix.lower()
        (output/relative).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(origin,output/relative);data['resources']['background']=relative
    for index,settings in enumerate(data['resources']['fonts'].values(),1):
        if settings.get('system_font') is True:continue
        for field in ['file','license_file']:
            origin=inside(source_dir,settings[field])
            suffix=origin.suffix.lower() if field=='file' else '-license'+origin.suffix.lower()
            relative=f'media/fonts/font-{index}'+suffix
            (output/relative).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(origin,output/relative);settings[field]=relative
    data['status']='prepared'
    validate_template(data,output)
    (output/'template.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'TEMPLATE.md').write_text(describe(data),encoding='utf8')
    return output/'template.json'


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    setup=commands.add_parser('prepare');setup.add_argument('observations',type=Path)
    setup.add_argument('--source-dir',type=Path,required=True);setup.add_argument('--output-dir',type=Path,required=True)
    setup.add_argument('--force',action='store_true')
    check=commands.add_parser('check');check.add_argument('template',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='prepare':
            path=prepare(args.observations,args.source_dir,args.output_dir,args.force);data=load_template(path)
        else:data=load_template(args.template)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
    print(json.dumps({'id':data['id'],'version':data['version'],'layouts':list(data['layouts']),
                      'scope':'Structure and packaged resources only; reference interpretation is supplied by the model'},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
