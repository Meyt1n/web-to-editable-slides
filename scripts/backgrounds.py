"""Editable PPTD background layers: base, edge atmosphere, watermark and quiet content area."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ASSET_ROOT=Path(__file__).resolve().parents[1]/'assets/backgrounds'


def copy_asset(asset_id: str, media_dir: Path) -> dict:
    """Copy an original catalog background, its prompt and provenance into a project."""
    entries=json.loads((ASSET_ROOT/'catalog.json').read_text('utf8'))['assets']
    item=next((entry for entry in entries if entry['id']==asset_id),None)
    if item is None:raise ValueError(f'Unknown background asset: {asset_id}')
    source=ASSET_ROOT/item['file']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError(f'Background asset hash mismatch: {asset_id}')
    media_dir=Path(media_dir)
    files={item['file']:source.read_bytes(),item['prompt_file']:(ASSET_ROOT/item['prompt_file']).read_bytes(),
           asset_id+'-asset.json':(json.dumps(item,ensure_ascii=False,indent=2)+'\n').encode('utf8')}
    for name,data in files.items():
        target=media_dir/name
        if target.exists() and target.read_bytes()!=data:raise ValueError(f'Refusing to replace background dependency: {target}')
    media_dir.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(media_dir/name).write_bytes(data)
    return dict(item)

RECIPES={
    'ink-culture':{'base':'#013025','ink':'#F5F1DF','accent':'#D9B872','muted':'#AEBBAE','safe_zone':[56,58,680,400]},
    'warm-paper':{'base':'#F5F0E5','ink':'#273F35','accent':'#A77740','muted':'#5B6D60','safe_zone':[56,58,840,420]},
    'quiet-tech':{'base':'#14232F','ink':'#F3F4EF','accent':'#8FB8A7','muted':'#A8B5BB','safe_zone':[56,58,700,410]},
}


def background(recipe: str, watermark: str = '学', family: str = 'Ma Shan Zheng', atmosphere: str | None = None) -> dict:
    if recipe not in RECIPES:raise ValueError(f'Unknown background recipe: {recipe}')
    cfg=RECIPES[recipe];elements=[]
    if atmosphere:
        elements.append(dict(elementId='bg-atmosphere',elementType='image',bounds=[0,0,960,540],src=atmosphere,fit=dict(mode='cover')))
    def shape(box,fill,opacity=1,path=None,border=None):
        element=dict(elementId=f'bg-{len(elements)+1}',elementType='shape',bounds=box,
                     shapeName='custom' if path else 'rect',fill=dict(type='solid',color=fill),opacity=opacity)
        if path:element.update(path=path,viewBox=[960,180])
        if border:element['border']=dict(style='solid',width=.6,color=border)
        elements.append(element)
    if recipe=='ink-culture':
        # Original geometric approximation of distant ink ridges; no source artwork is copied.
        if not atmosphere:
            shape([0,360,960,180],'#46644E',.17,'M0 130 C130 160 180 15 310 95 C420 155 500 25 615 105 C740 150 820 15 960 95 L960 180 L0 180 Z')
            shape([0,400,960,140],'#799074',.10,'M0 120 C140 30 230 160 380 80 C520 5 610 145 760 70 C860 20 910 85 960 25 L960 180 L0 180 Z')
        elements.append(dict(elementId='bg-watermark',elementType='text',bounds=[747,95,210,300],opacity=.055,
            content=dict(text=watermark,fontFamily=family,fontSize=168,color=cfg['ink'],align=['center','middle'],wrap=False)))
    elif recipe=='warm-paper':
        shape([0,0,960,16],'#E5D8BF',.7)
        shape([0,524,960,16],'#E5D8BF',.7)
        for i in range(12):shape([26+i*81,18+(i*41)%480,30,1],'#B7A486',.11)
    else:
        for x in range(36,960,60):shape([x,0,.5,540],'#6B9387',.10)
        for y in range(30,540,60):shape([0,y,960,.5],'#6B9387',.10)
        shape([748,110,150,150],cfg['base'],1,border='#355345')
        shape([772,134,150,150],cfg['base'],1,border='#355345')
    return {'background':dict(type='solid',color=cfg['base']),'elements':elements,
            'safe_zone':cfg['safe_zone'],'palette':cfg}
