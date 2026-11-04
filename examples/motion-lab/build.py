"""Original native animation specimens; a compiler probe, not an imagegen run."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from native_renderer import build
from motion_presets import (staggered_reveal,process_flow,compare_then_decide,
                            evidence_reveal,focus_pulse,replace_state,handwriting_groups)


def create(output: Path, *, autoplay=False):
    output=output.resolve()
    if output.exists():raise ValueError('Choose a new output directory')
    source=output/'source';(source/'template').mkdir(parents=True)
    # This declared reference is a synthetic layout fixture, not a generated design.
    (source/'template/layout.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540" fill="#F7F8FA"/><path d="M56 138H904 M56 478H904" stroke="#D8DEE7"/></svg>',encoding='utf8')
    template=dict(schema_version='1.0',id='motion-lab',version='1',canvas=[960,540],
        palette=dict(ink='#182C47',accent='#315ECC',muted='#586A80',paper='#FBF7EF'),
        resources=dict(fonts={family:dict(system_font=True) for family in ['Noto Sans SC','Long Cang']}),
        typography=dict(body=dict(family='Noto Sans SC',size=22),handwriting=dict(family='Long Cang',size=42)),
        references=[dict(id='synthetic-layout-fixture',file='layout.svg')],
        layouts=dict(content=dict(slots=dict(title=[56,48,848,76],body=[56,150,848,300]))),
        components=dict(rule=dict(color='#D8DEE7',width=1)))
    (source/'template/template.json').write_text(json.dumps(template,ensure_ascii=False,indent=2),encoding='utf8')
    pages=[]
    def text(page,key,value,box,size=24,color='#182C47',family='Noto Sans SC',bold=False):
        page['elements'].append(dict(elementId=key,elementType='text',bounds=box,
            content=dict(text=value,fontFamily=family,fontSize=size,color=color,bold=bold,wrap=False)))
        return key
    def shape(page,key,box,fill,kind='rect'):
        page['elements'].append(dict(elementId=key,elementType='shape',shapeName=kind,bounds=box,
            fill=dict(type='solid',color=fill),border=dict(style='solid',color=fill,width=0.5)))
        return key
    def line(page,key,box,points,color='#315ECC',width=2):
        page['elements'].append(dict(elementId=key,elementType='line',bounds=box,viewBox=box[2:],points=points,
            border=dict(style='solid',color=color,width=width)))
        return key
    def page(title,subtitle,paper=False):
        p=dict(id=len(pages)+1,pageType='content',layout='content',background=dict(type='solid',color='#FBF7EF' if paper else '#F7F8FA'),elements=[],animations=[])
        text(p,'title',title,[56,44,848,58],34,bold=True)
        text(p,'subtitle',subtitle,[58,109,844,30],15,color='#586A80')
        line(p,'footer-rule',[56,479,848,1],'0,0 848,0',color='#D8DEE7',width=1)
        text(p,'footer','原生动画小样 · 所有文字、线条与图表均可编辑',[56,492,790,25],12,color='#586A80')
        text(p,'number',f'{len(pages)+1:02}',[863,488,43,30],17,color='#315ECC')
        pages.append(p)
        return p

    p=page('动画，先服务表达','错峰入场：一次点击展开一组内容，再把注意力交给关键句。')
    for i,(label,body) in enumerate([('阅读顺序','先看主张，再看依据'),('讲解停顿','把选择权留给讲者'),('重点回看','轻微放大，再回到原位')]):
        y=177+i*75
        text(p,f'n{i}',f'0{i+1}',[58,y,60,40],24,color='#315ECC')
        text(p,f'label{i}',label,[145,y,220,42],27,bold=True)
        text(p,f'body{i}',body,[410,y+2,475,40],23)
    p['animations']=staggered_reveal([f'{kind}{i}' for i in range(3) for kind in ['n','label','body']],autoplay=autoplay,stagger_ms=70)
    p['animations']+=focus_pulse('label2',trigger='afterPrevious' if autoplay else 'onClick')

    p=page('流程推进','每次点击推进一步：连接关系先出现，下一步随后进入。')
    xs=[58,370,682]
    for i,(label,body) in enumerate([('观察','收集线索'),('推理','连接证据'),('行动','形成方案')]):
        shape(p,f'band{i}',[xs[i],198,220,8],'#315ECC')
        text(p,f'step{i}',label,[xs[i],228,220,62],37,bold=True)
        text(p,f'detail{i}',body,[xs[i],312,220,40],22,color='#586A80')
    for i in range(2):line(p,f'arrow{i}',[290+312*i,259,65,20],'0,10 62,10 52,1 62,10 52,19')
    p['animations']=process_flow([[f'band{i}',f'step{i}',f'detail{i}'] for i in range(3)],['arrow0','arrow1'],autoplay=autoplay)

    p=page('左右对比，再给判断','三次点击：方案甲 → 方案乙 → 选择依据。')
    shape(p,'left-bg',[56,174,408,190],'#E8EEF9');shape(p,'right-bg',[496,174,408,190],'#E5F0EC')
    text(p,'left','方案甲',[82,198,350,52],31,bold=True)
    text(p,'left-detail','路径短，适合快速验证',[82,273,350,45],23)
    text(p,'right','方案乙',[522,198,350,52],31,bold=True)
    text(p,'right-detail','覆盖广，适合持续建设',[522,273,350,45],23)
    text(p,'verdict','先验证，再扩展。',[80,402,800,55],32,color='#315ECC',bold=True)
    p['animations']=compare_then_decide(['left','left-detail'],['right','right-detail'],['verdict'],autoplay=autoplay)

    p=page('证据揭示，解释随后','图表保持可见；对主张、标注和结论分组，不伪造图表逐项动画。')
    p['elements'].append(dict(elementId='data',elementType='chart',bounds=[56,185,435,245],
        data=dict(cols=['阶段','数值'],rows=[['前期',8],['后期',14]]),
        series=[dict(type='bar',name='示例',encode=dict(x='阶段',y='数值'),fill='#315ECC')],
        dataSource=dict(status='demo',label='仅作动画编排示例'),
        style=dict(background='#F7F8FA',textColor='#586A80',gridColor='#D8DEE7',minimum=0,maximum=16,majorUnit=4,dataLabels=True,labelFormat='0',fontSize=14,pointColors=['#A7B8D8','#315ECC'])))
    text(p,'source','示例数据，不对应实测结果',[66,438,420,26],13,color='#586A80')
    text(p,'claim','先说观察',[554,184,330,48],29,bold=True)
    text(p,'proof','后期数值高于前期',[554,258,330,50],24,color='#315ECC')
    text(p,'takeaway','结论仍需更多证据。',[554,350,350,50],25,bold=True)
    p['animations']=evidence_reveal(['claim'],['proof'],['takeaway'],autoplay=autoplay)

    p=page('状态替换，让旧信息退场','一次点击：旧状态淡出，再展示新状态；两个版本仍是独立可编辑对象。')
    text(p,'old-label','旧状态',[80,189,200,38],18,color='#586A80')
    text(p,'old','草稿：等待复核',[80,240,760,64],38,color='#586A80')
    text(p,'new-label','新状态',[80,336,200,38],18,color='#315ECC')
    text(p,'new','已复核，可以发布',[80,386,780,64],38,color='#315ECC',bold=True)
    p['animations']=replace_state(['old'],['new'],autoplay=autoplay)

    p=page('手写板书，按推导顺序落笔','每个知识点一次点击，词段、连线与强调线在组内连续展开。',paper=True)
    groups=[]
    for i,(value,x) in enumerate([('先观察',66),('找证据',378),('下结论',690)]):
        word=text(p,f'word{i}',value,[x,222,218,82],50,family='Long Cang')
        stroke=line(p,f'underline{i}',[x+4,323,200,7],'0,2 95,0 200,3',color='#9D3145',width=2.5)
        units=[]
        if i:
            shaft=line(p,f'shaft{i}',[292+312*(i-1),266,62,3],'0,1 62,0',width=2)
            tip=line(p,f'tip{i}',[343+312*(i-1),258,12,18],'0,0 11,8 0,17',width=2)
            units.extend([dict(elementId=shaft,durationMs=240),dict(elementId=tip,durationMs=90)])
        units.extend([dict(elementId=word,text=value,durationMs=320),dict(elementId=stroke,durationMs=260)])
        groups.append(units)
    p['animations']=handwriting_groups(groups,autoplay=autoplay)
    text(p,'note','用原生词段与线条模拟书写；不冒充真实笔尖轨迹。',[72,400,820,36],19,color='#586A80')

    scene=dict(version=1,title='原生动画风格小样',size=[960,540],template_file='template/template.json',pages=pages)
    file=source/'scene.json';file.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf8')
    result=build(file,output/'project')
    print(f'Built {len(pages)} original specimens: {result}')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--autoplay',action='store_true')
    args=parser.parse_args();create(args.output_dir,autoplay=args.autoplay)
