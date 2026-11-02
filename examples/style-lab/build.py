"""Original font/background/animation specimen inspired by general reference techniques."""
from pathlib import Path
import argparse
from collections import defaultdict
import json
import sys
from urllib.parse import urlencode

import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from backgrounds import background,copy_asset
from motion_presets import title_entrance,reveal_groups,question_answer
from prepare_fonts import prepare


def build(output: Path):
    if output.exists():raise ValueError('Choose a new project directory')
    output.mkdir(parents=True);(output/'pages').mkdir()
    (output/'media').mkdir()
    for asset in ['ink-atmosphere','ink-content','warm-paper']:copy_asset(asset,output/'media')
    pages=[];font_text=defaultdict(str)
    def page(recipe,kind='content',watermark='学'):
        asset=('ink-atmosphere' if kind=='cover' else 'ink-content') if recipe=='ink-culture' else 'warm-paper' if recipe=='warm-paper' else None
        cfg=background(recipe,watermark,atmosphere=f'media/{asset}.png' if asset else None)
        return dict(pageType=kind,background=cfg['background'],elements=cfg['elements'],animations=[]),cfg['palette']
    def text(p,value,box,family='Noto Sans SC',size=22,color='#F5F1DF',bold=False):
        key=f'fg-{len(p["elements"])+1}'
        p['elements'].append(dict(elementId=key,elementType='text',bounds=box,
            content=dict(text=value,fontFamily=family,fontSize=size,color=color,bold=bold,align=['left','middle'],wrap=False)))
        return key
    p,c=page('ink-culture','cover')
    text(p,'字体 · 背景 · 讲解节奏',[58,48,700,26],size=14,color=c['accent'])
    title=text(p,'让页面有气质\n让内容有次序',[58,128,710,206],'Ma Shan Zheng',70)
    text(p,'原生字体与分层背景设计小样',[62,372,680,36],size=23)
    text(p,'书法承担短标题，正文承担清晰表达。',[62,426,700,30],size=17,color=c['ink'])
    p['animations']=title_entrance(title);pages.append(p)
    p,c=page('ink-culture',watermark='序')
    key=text(p,'先看到问题，再展开解释',[58,55,820,78],'Long Cang',56)
    p['animations']=[dict(elementId=key,effect='fade-in',trigger='afterPrevious',durationMs=600)]
    groups=[]
    labels=[('问题','明确本页需要回答什么'),('线索','给出观察与已知条件'),('解释','说明条件之间的关系'),('结论','回到问题，形成判断')]
    for i,(name,detail) in enumerate(labels):
        y=177+i*72
        n=text(p,f'{i+1:02}',[60,y,64,45],'Barlow Condensed',32,c['accent'])
        word=text(p,name,[150,y-3,150,52],'Ma Shan Zheng',36)
        desc=text(p,detail,[337,y+5,560,35],size=20)
        groups.append([word,n,desc])
    p['animations']+=reveal_groups(groups)
    pages.append(p)
    p,c=page('warm-paper')
    text(p,'六种字体，各有位置',[58,45,820,65],'ZCOOL XiaoWei',41,c['ink'])
    samples=[('Ma Shan Zheng','文化标题','笔墨之间，留有余地'),('Long Cang','手写点缀','把想法写给你'),
        ('ZCOOL XiaoWei','人文编辑','文字有层次，阅读有方向'),('ZCOOL KuaiLe','亲和短标题','和好奇心一起出发'),
        ('Noto Sans SC','清晰正文','正文保持清楚、稳定与可读'),('Barlow Condensed','数字与短英文','0123456789 / DESIGN')]
    for i,(family,role,sample) in enumerate(samples):
        y=127+i*53
        text(p,role,[60,y,154,40],size=15,color=c['muted'])
        text(p,sample,[240,y,660,46],family,28,c['ink'])
    pages.append(p)
    p,c=page('warm-paper','content')
    text(p,'先观察，再解释',[58,48,800,72],'Ma Shan Zheng',48,c['ink'])
    qlabel=text(p,'问题',[62,157,130,55],'Ma Shan Zheng',32,c['accent'])
    question=text(p,'你看到了哪些线索？',[220,157,620,55],size=29,color=c['ink'])
    alabel=text(p,'解释',[62,273,130,55],'Ma Shan Zheng',32,c['accent'])
    answer=text(p,'说明这些线索支持什么判断。',[220,273,620,55],size=27,color=c['ink'])
    text(p,'留出思考时间，再点击展开。',[62,386,720,40],size=18,color=c['muted'])
    p['animations']=question_answer([qlabel,question],[alabel,answer]);pages.append(p)
    p,c=page('quiet-tech','final')
    text(p,'背景服务内容',[58,55,800,76],size=45,bold=True)
    for i,(title,body) in enumerate([('建立主次','正文区对比清楚，纹理退到边缘。'),('保持连续','底色、装饰位置和细线在页间保持联系。'),('安排节奏','背景保持稳定，问题与答案按讲解展开。')]):
        text(p,f'{i+1:02}',[62,172+i*91,65,42],'Barlow Condensed',32,c['accent'])
        text(p,title,[160,168+i*91,600,40],size=25,bold=True)
        text(p,body,[160,210+i*91,680,29],size=17,color=c['muted'])
    pages.append(p)
    for p in pages:
        for e in p['elements']:
            if e['elementType']=='text':font_text[e['content']['fontFamily']]+=e['content']['text']
    requests=[dict(family=family,text=value) for family,value in font_text.items()]
    pack=prepare(requests,output/'media/fonts')
    mapping={family:'media/fonts/'+file for family,file in pack['font_map'].items()}
    aliases={font['requested_family']:font['family'] for font in pack['fonts']}
    page_paths=[]
    for i,p in enumerate(pages,1):
        for e in p['elements']:
            if e['elementType']=='text':e['content']['fontFamily']=aliases[e['content']['fontFamily']]
        relative=f'pages/{i:02}.page';page_paths.append(relative)
        (output/relative).write_text(yaml.safe_dump(p,allow_unicode=True,sort_keys=False),encoding='utf8')
    custom=[dict(family=family,src='https://fonts.googleapis.com/css2?'+urlencode({'family':family})) for family in mapping]
    manifest=dict(version='v2',title='字体、背景与讲解节奏｜设计能力小样',size=[960,540],customFonts=custom,pages=page_paths)
    (output/'style-lab.pptd').write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False),encoding='utf8')
    (output/'font-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'font-requests.json').write_text(json.dumps(requests,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Built {len(pages)} pages with {len(mapping)} font families: {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    build(parser.parse_args().output_dir)
