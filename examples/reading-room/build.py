"""Author the reading-room field trial from its observed template, not slide bitmaps."""
from pathlib import Path
import argparse
import json
import shutil
import sys
from urllib.parse import urlencode

import yaml
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from template_pack import load_template


def build(root: Path):
    root = root.resolve()
    template = load_template(root / 'template/template.json')
    (root/'pages').mkdir(parents=True,exist_ok=True)
    palette, types = template['palette'], template['typography']
    pages, slide_records = [], []
    elements = []

    def add(kind, box, **kwargs):
        item = dict(elementId=f'e{len(elements) + 1}', elementType=kind, bounds=box, **kwargs)
        elements.append(item)

    def text(value, box, role='body', size=None, color='ink', align='left'):
        cfg = types[role]
        add('text', box, content=dict(text=value, fontFamily=cfg['family'],
            fontSize=size or cfg['size'], color=palette.get(color, color),
            bold=cfg.get('bold',False),
            lineHeight=1.08, align=[align, 'middle'], wrap=False))

    def rect(box, fill='paper', stroke=None, width=.8, ellipse=False):
        kwargs = dict(shapeName='ellipse' if ellipse else 'rect',
                      fill=dict(type='solid', color=palette.get(fill, fill)))
        if stroke:
            kwargs['border'] = dict(style='solid', width=width, color=palette.get(stroke, stroke))
        add('shape', box, **kwargs)

    def line(x1, y1, x2, y2, color='line', width=.8):
        w, h = max(abs(x2-x1), .1), max(abs(y2-y1), .1)
        add('line', [min(x1,x2), min(y1,y2), w,h], viewBox=[w,h],
            points=f'{0 if x2>=x1 else w},{0 if y2>=y1 else h} {w if x2>=x1 else 0},{h if y2>=y1 else 0}',
            border=dict(style='solid', width=width, color=palette[color]))

    def photo(box):
        add('image', box, src='media/reading-room.png', fit=dict(mode='cover'))

    def begin(layout, label, title=None):
        nonlocal elements
        elements = []
        slots = template['layouts'][layout]['slots']
        text(label, slots['eyebrow'], 'label', size=12)
        if title:
            text(title, slots['title'], 'heading')
        return slots

    def finish(layout, title, note, number):
        slots = template['layouts'][layout]['slots']
        box = slots['footer']
        text(note, [box[0],box[1],box[2]-90,box[3]], 'label', size=10)
        text(f'{number:02} / 05', [box[0]+box[2]-70,box[1],70,box[3]], 'label', size=10, align='right')
        pages.append(dict(pageType='cover' if number==1 else 'final' if number==5 else 'content',
                          background=dict(type='solid',color=palette['paper']), elements=elements))
        slide_records.append(dict(id=number,title=title,layout=layout,status='concept',
            reference=f'references/{["01-cover","02-zones","03-journey","04-program","05-pilot"][number-1]}.png',
            reference_prompt=f'prompts.json: slides[{number-1}].prompt',
            font_profile='observed',layout_constraints=[template['layouts'][layout]['description']],
            typography_constraints=['使用已打包字体，保留标题断行与层级'],
            image_plan=['空间图为imagegen概念图，其余文字、流程、表格和分区原生重建']))

    s=begin('editorial-cover','SHIGUANG READING ROOM')
    photo(s['photo'])
    for value,box in zip(['拾光','书屋'],s['title_lines']):
        text(value,box,'display')
    rect(s['accent'],'terracotta')
    text('让阅读成为邻里日常',s['subtitle'],'heading',size=26)
    text('社区共享阅读空间\n概念提案',s['body'],size=14)
    finish('editorial-cover','拾光书屋','虚构概念 · 空间与服务设计',1)

    s=begin('zoning-plan','拾光书屋 / 空间分区','让不同的阅读方式，都有位置')
    x,y,w,h=s['plan']
    # Three spatial regions and structural walls, not content cards.
    rect([x,y,334,202],'pale');rect([x+334,y,252,202],'beige')
    rect([x,y+202,w,105],'#D5AA91')
    for wall in [[x,y,w,10],[x,y,10,h],[x+w-10,y,10,h],[x+326,y,10,202],[x,y+198,w,9],
                 [x,y+h-9,258,9],[x+326,y+h-9,260,9]]:
        rect(wall,'ink')
    def shelf(b):
        rect(b,'paper','ink',.6)
        xx,yy,ww,hh=b
        if ww>hh:
            for dx in range(4,int(ww)-2,6):line(xx+dx,yy+1,xx+dx,yy+hh-1,'ink',.4)
        else:
            for dy in range(4,int(hh)-2,6):line(xx+1,yy+dy,xx+ww-1,yy+dy,'ink',.4)
    for b in [[x+12,y+42,15,144],[x+w-30,y+17,15,171],[x+18,y+231,15,60],
              [x+50,y+h-27,170,15],[x+374,y+h-27,150,15],[x+341,y+177,160,15]]:shelf(b)
    for dx in range(28,320,68):
        rect([x+dx,y+18,25,23],'paper','ink',.6)
    def table(tx,ty,tw,th):
        for dx in [tw*.2,tw*.5,tw*.8]:
            rect([tx+dx-8,ty-12,16,20],'paper','ink',.6,True)
            rect([tx+dx-8,ty+th-8,16,20],'paper','ink',.6,True)
        rect([tx,ty,tw,th],'beige','ink',.7)
        rect([tx+tw*.38,ty+th*.3,19,12],'paper','ink',.4)
    table(x+107,y+102,130,40);table(x+399,y+64,86,68)
    rect([x+103,y+242,112,23],'beige','ink',.7)
    rect([x+379,y+238,135,27],'beige','ink',.7)
    text('安静阅览',[x+104,y+53,150,28],'heading',size=17,align='center')
    text('邻里共读',[x+383,y+150,126,28],'heading',size=17,align='center')
    text('借还与展示',[x+241,y+232,135,25],'heading',size=17,align='center')
    # Door leaves and entrance indicator remain separate editable shapes.
    line(x+258,y+h-7,x+258,y+h-38,'ink');line(x+326,y+h-7,x+326,y+h-38,'ink')
    line(x+258,y+h-38,x+291,y+h-6,'ink');line(x+326,y+h-38,x+293,y+h-6,'ink')
    add('shape',[x+283,y+h+2,16,23],shapeName='upArrow',fill=dict(type='solid',color=palette['ink']))
    note_x,note_y,note_w,_=s['notes']
    for idx,(heading,detail) in enumerate([('安静阅览','靠窗座位，适合独处'),('邻里共读','共读桌，容纳小组交流'),('借还与展示','入口书架，方便借还')]):
        yy=note_y+idx*116
        text(f'{idx+1:02}',[note_x,yy,54,54],'number',size=41,color='terracotta' if idx==2 else 'sage')
        text(heading,[note_x+57,yy+7,160,32],'heading',size=23)
        text(detail,[note_x+57,yy+46,160,25],size=13.6)
        line(note_x,yy+84,note_x+note_w,yy+84,'terracotta' if idx==2 else 'sage')
    finish('zoning-plan','空间分区','功能关系示意 · 非施工图',2)

    s=begin('service-journey','拾光书屋 / 借阅体验','从走进书屋，到带走一本书')
    text('清楚的指引，让第一次到访也从容',s['subtitle'],size=22)
    x,y,w,h=s['timeline'];line(x,y+h/2,x+w,y+h/2,'ink',1)
    for idx,(heading,detail) in enumerate([('到访','看见开放与活动信息'),('选书','按主题寻找感兴趣的书'),('借阅','登记借阅与归还日期'),('归还','放回借还台，完成确认')]):
        xx=x+w*idx/3
        rect([xx-32,y,64,64],'terracotta' if idx==2 else 'sage',ellipse=True)
        text(f'{idx+1:02}',[xx-30,y+6,60,50],'number',size=30,color='white',align='center')
        text(heading,[xx-75,y+80,150,43],'heading',size=31,align='center')
        text(detail,[xx-100,y+130,200,30],size=15.5,align='center')
    rect([58,416,64,3],'terracotta')
    text('借阅规则简洁，现场指引清晰',s['conclusion'],'heading',size=28)
    finish('service-journey','借阅体验','服务流程草案 · 待试点验证',3)

    s=begin('weekly-table','拾光书屋 / 一周活动')
    text('用轻量活动，连接附近的人',s['title'],'heading',size=51)
    data=[['时段','活动','适合参与者','准备事项'],
          ['周三晚间','安静共读','希望专注阅读的邻居','自带一本书'],
          ['周六上午','亲子故事','儿童与陪同家长','准备绘本与坐垫'],
          ['周日下午','换书小集','愿意分享旧书的居民','登记书况与交换意向']]
    rows=[]
    for i,row in enumerate(data):
        rows.append([dict(text=value,fontFamily=types['body']['family'],fontSize=18,
            color=palette['white'] if i==0 else palette['ink'],align=['left','middle'],
            fill=dict(type='solid',color=palette['ink'] if i==0 else '#E9EBE0' if i==2 else palette['paper']),
            border=dict(style='solid',width=.5,color='#DBDBCF')) for value in row])
    add('table',s['table'],columnWidths=[.19,.21,.31,.29],rowHeights=[.22,.26,.26,.26],rows=rows)
    rect([62,447,166,3],'terracotta')
    text('活动安排为示例，正式时段与规则待社区协商。',s['note'],size=14)
    finish('weekly-table','一周活动','虚构概念 · 活动样例',4)

    s=begin('pilot-close','拾光书屋 / 试点计划')
    photo(s['photo'])
    text('先从一个角落，\n开始一段共读时光',s['title'],'heading',size=46)
    x,y,w,h=s['timeline'];line(52,y+h/2,468,y+h/2,'sage',1)
    for i,(heading,detail) in enumerate([('准备','整理书目与场地'),('开放','发布指引与活动'),('调整','收集反馈再优化')]):
        xx=x+w*i/2
        rect([xx-6,y+4,12,12],'terracotta',ellipse=True)
        text(heading,[xx-60,y+28,120,35],'heading',size=23,align='center')
        text(detail,[xx-78,y+66,156,25],size=14,align='center')
    rect([48,410,75,3],'terracotta')
    text('下一步：确定场地、共建伙伴与试点规则',s['next_step'],'heading',size=18)
    finish('pilot-close','试点计划','虚构概念 · 待社区讨论',5)

    # Fail on missing glyphs before exporting, including table cells.
    chars={family:set() for family in {v['family'] for v in types.values()}}
    for page in pages:
        for element in page['elements']:
            contents=([element['content']] if element['elementType']=='text' else
                      [c for row in element.get('rows',[]) for c in row])
            for item in contents:
                chars[item['fontFamily']].update(c for c in item['text'] if not c.isspace())
    fonts={types['body']['family']:'media/body.ttf',types['heading']['family']:'media/heading.ttf'}
    custom=[]
    for family,relative in fonts.items():
        with TTFont(root/relative) as font:
            missing=chars[family]-set(chr(c) for c in font.getBestCmap())
        if missing:raise ValueError(f'Missing glyphs in {family}: {sorted(missing)}')
        # This editor accepts Google Fonts CSS URLs only; data: CSS is silently ignored.
        # Local font files are retained separately for offline PPTX embedding.
        query=urlencode({'family':family+':wght@400','text':''.join(sorted(chars[family]))})
        custom.append(dict(family=family,src='https://fonts.googleapis.com/css2?'+query))
    paths=[]
    for i,page in enumerate(pages,1):
        relative=f'pages/{i:02}.page';paths.append(relative)
        (root/relative).write_text(yaml.safe_dump(page,allow_unicode=True,sort_keys=False),encoding='utf8')
    manifest=dict(version='v2',title='拾光书屋｜社区共享阅读空间',size=template['canvas'],customFonts=custom,pages=paths)
    (root/'reading-room.pptd').write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False),encoding='utf8')
    plan=dict(project='拾光书屋｜虚构概念提案',style=dict(ratio='16:9',colors=[palette[k] for k in ['paper','ink','sage','terracotta']]),
        design=dict(mode='fidelity',template=dict(id=template['id'],version=template['version'],file='template/template.json'),
        font_profiles=dict(observed={k:v['family'] for k,v in types.items()})),slides=slide_records)
    (root/'design-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    shutil.copy2(Path(__file__).with_name('prompts.json'),root/'prompts.json')
    shutil.copy2(Path(__file__).with_name('asset-prompt.txt'),root/'asset-prompt.txt')
    (root/'font-map.json').write_text(json.dumps(fonts,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Authored {len(pages)} editable pages: {root / "reading-room.pptd"}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    build(parser.parse_args().project)
