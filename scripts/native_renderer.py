"""Repository-owned scene → editable PPTX/PPTD renderer; no browser/WASM backend.

Supports a documented PPTD subset and rejects unsupported features explicitly.
Visual understanding and content design belong to the host agent.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import json
import math
from pathlib import Path
import re
import shutil
import sys

if sys.version_info<(3,10):raise SystemExit('Python 3.10+ required. Run scripts/doctor.py to select a ready interpreter.')

from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData,XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE,XL_DATA_LABEL_POSITION,XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR,PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt

from build_demo import write_project
from check_pptx import inspect
from prepare_fonts import prepare
from template_pack import inside,load_template


def number(value,positive=False):
    if type(value) not in (int,float) or not math.isfinite(value) or (positive and value<=0):raise ValueError('Expected a finite '+('positive ' if positive else '')+'number')
    return value


def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Use explicit HEX6 colors')
    return RGBColor.from_string(value[1:])


def node(tag,parent=None,**attrs):
    item=OxmlElement(tag)
    for key,value in attrs.items():item.set(key,str(value))
    if parent is not None:parent.append(item)
    return item


def solid(fill,cfg,opacity=1):
    if cfg is None or cfg.get('type')=='none':fill.background();return
    if cfg.get('type')!='solid':raise ValueError('Native renderer supports solid fills only')
    fill.solid();fill.fore_color.rgb=color(cfg['color'])
    if opacity!=1:node('a:alpha',fill.fore_color._xClr,val=round(opacity*100000))


def format_text(frame,content):
    if not isinstance(content.get('text'),str):raise ValueError('Text must be a plain string')
    frame.clear();frame.word_wrap=content.get('wrap',True)
    frame.margin_left=frame.margin_right=frame.margin_top=frame.margin_bottom=0
    align=content.get('align',['left','middle'])
    frame.vertical_anchor={'top':MSO_ANCHOR.TOP,'middle':MSO_ANCHOR.MIDDLE,'bottom':MSO_ANCHOR.BOTTOM}[align[1]]
    for i,line in enumerate(content['text'].split('\n')):
        paragraph=frame.paragraphs[0] if i==0 else frame.add_paragraph()
        paragraph.alignment={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[align[0]]
        paragraph.line_spacing=number(content.get('lineHeight',1.15),True);paragraph.space_after=Pt(0)
        run=paragraph.add_run();run.text=line;run.font.name=content['fontFamily']
        run.font.size=Pt(number(content.get('fontSize',22),True));run.font.bold=bool(content.get('bold',False))
        run.font.color.rgb=color(content.get('color','#222222'))
        rpr=run._r.get_or_add_rPr();node('a:ea',rpr,typeface=content['fontFamily'])


def custom_geometry(shape,element):
    view=element.get('viewBox',[element['bounds'][2],element['bounds'][3]])
    if len(view)!=2:raise ValueError('Custom path viewBox is [width,height]')
    for n in view:number(n,True)
    pen=RecordingPen();parse_path(element['path'],pen)
    sp=shape._element.spPr
    for existing in list(sp):
        if existing.tag.endswith(('}prstGeom','}custGeom')):sp.remove(existing)
    geom=node('a:custGeom');sp.insert(1,geom)
    for tag in ['avLst','gdLst','ahLst','cxnLst']:node('a:'+tag,geom)
    node('a:rect',geom,l='0',t='0',r='w',b='h')
    path=node('a:path',node('a:pathLst',geom),w=round(view[0]*1000),h=round(view[1]*1000))
    for operation,points in pen.value:
        tag={'moveTo':'moveTo','lineTo':'lnTo','curveTo':'cubicBezTo','qCurveTo':'quadBezTo','closePath':'close','endPath':None}.get(operation)
        if operation not in ['moveTo','lineTo','curveTo','qCurveTo','closePath','endPath']:raise ValueError('Unsupported SVG path operation')
        if tag is None:continue
        cmd=node('a:'+tag,path)
        for point in points:
            if point is None:raise ValueError('Implicit quadratic closing points are unsupported')
            node('a:pt',cmd,x=round(number(point[0])*1000),y=round(number(point[1])*1000))


def chart_data(element):
    if not isinstance(element.get('dataSource'),dict) or element['dataSource'].get('status') not in ['demo','verified'] or not element['dataSource'].get('label'):
        raise ValueError('Chart requires dataSource status and label; never infer values from a picture')
    cols=element['data']['cols'];rows=element['data']['rows'];series=element['series']
    if not cols or len(set(cols))!=len(cols) or any(not isinstance(c,str) or not c.strip() for c in cols) or not rows or any(len(row)!=len(cols) for row in rows):raise ValueError('Invalid chart data table')
    kinds={s['type'] for s in series}
    if len(kinds)!=1 or not kinds<={'bar','line','scatter'}:raise ValueError('Native renderer supports homogeneous bar, line or scatter charts')
    kind=next(iter(kinds));data=XyChartData() if kind=='scatter' else CategoryChartData()
    for i,s in enumerate(series):
        x=cols.index(s['encode']['x']);y=cols.index(s['encode']['y'])
        values=[number(row[y]) for row in rows]
        if kind=='scatter':
            target=data.add_series(s.get('name',cols[y]))
            for row,value in zip(rows,values):target.add_data_point(number(row[x]),value)
        else:
            categories=[str(row[x]) for row in rows]
            if i==0:data.categories=categories
            elif categories!=[str(row[cols.index(series[0]['encode']['x'])]) for row in rows]:raise ValueError('Category charts must share the x column')
            data.add_series(s.get('name',cols[y]),values)
    return kind,data


def validate_chart_style(element):
    style=element.get('style',{})
    allowed={'background','textColor','gridColor','minimum','maximum','majorUnit','numberFormat','labelFormat','dataLabels','fontSize','pointColors'}
    if not isinstance(style,dict) or set(style)-allowed:raise ValueError('Unsupported native chart style fields')
    for key in ['background','textColor','gridColor']:
        if key in style:color(style[key])
    for key in ['minimum','maximum','majorUnit','fontSize']:
        if key in style:number(style[key],key in ['majorUnit','fontSize'])
    if 'minimum' in style and 'maximum' in style and style['minimum']>=style['maximum']:raise ValueError('Chart minimum must be smaller than maximum')
    for key in ['numberFormat','labelFormat']:
        if key in style and (not isinstance(style[key],str) or not style[key].strip()):raise ValueError('Chart number formats must be non-empty strings')
    if 'dataLabels' in style and type(style['dataLabels']) is not bool:raise ValueError('Chart dataLabels must be boolean')
    if 'pointColors' in style:
        colors=style['pointColors']
        if not isinstance(colors,list) or len(colors)!=len(element['data']['rows']):raise ValueError('Chart pointColors must match data rows')
        if len(element['series'])!=1 or element['series'][0]['type']!='bar':raise ValueError('Point colors are supported on single-series bar charts')
        for value in colors:color(value)


def format_chart(chart,element,family):
    style=element.get('style',{})
    chart.has_title=False
    chart.font.name=family;chart.font.size=Pt(style.get('fontSize',14))
    if 'textColor' in style:chart.font.color.rgb=color(style['textColor'])
    if chart.has_legend:
        chart.legend.position=XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout=False
    for axis in [chart.category_axis,chart.value_axis]:
        axis.tick_labels.font.name=family;axis.tick_labels.font.size=Pt(style.get('fontSize',14))
        if 'textColor' in style:axis.tick_labels.font.color.rgb=color(style['textColor'])
        if 'gridColor' in style:axis.format.line.color.rgb=color(style['gridColor'])
    value_axis=chart.value_axis
    for key,property_name in [('minimum','minimum_scale'),('maximum','maximum_scale'),('majorUnit','major_unit')]:
        if key in style:setattr(value_axis,property_name,style[key])
    if 'numberFormat' in style:
        value_axis.tick_labels.number_format=style['numberFormat'];value_axis.tick_labels.number_format_is_linked=False
    if 'gridColor' in style:
        value_axis.has_major_gridlines=True
        value_axis.major_gridlines.format.line.color.rgb=color(style['gridColor'])
        value_axis.major_gridlines.format.line.width=Pt(.5)
    if 'background' in style:
        props=chart._chartSpace.find('{http://schemas.openxmlformats.org/drawingml/2006/chart}spPr')
        if props is None:
            props=node('c:spPr')
            chart._chartSpace.insert_element_before(props,'c:txPr','c:externalData','c:printSettings','c:userShapes','c:extLst')
        for child in list(props):
            if child.tag.endswith(('}solidFill','}noFill','}ln')):props.remove(child)
        node('a:srgbClr',node('a:solidFill',props),val=style['background'][1:])
        node('a:noFill',node('a:ln',props))
    if style.get('dataLabels'):
        plot=chart.plots[0];plot.has_data_labels=True;labels=plot.data_labels
        labels.show_value=True;labels.show_legend_key=False;labels.show_category_name=False;labels.show_series_name=False
        if element['series'][0]['type']=='bar':labels.position=XL_DATA_LABEL_POSITION.OUTSIDE_END
        labels.font.name=family;labels.font.size=Pt(style.get('fontSize',14))
        if 'textColor' in style:labels.font.color.rgb=color(style['textColor'])
        labels.number_format=style.get('labelFormat',style.get('numberFormat','0.##'));labels.number_format_is_linked=False
    if 'pointColors' in style:
        for point,fill in zip(chart.series[0].points,style['pointColors']):
            point.format.fill.solid();point.format.fill.fore_color.rgb=color(fill);point.format.line.fill.background()


def validate(scene,root):
    if not isinstance(scene,dict) or scene.get('version')!=1:raise ValueError('Scene version must be 1')
    if set(scene)-{'version','title','size','template_file','pages','font_weights'}:raise ValueError('Unsupported scene fields')
    if not isinstance(scene.get('title'),str) or not scene['title'].strip():raise ValueError('Scene requires a title')
    size=scene.get('size',[960,540])
    if not isinstance(size,list) or len(size)!=2:raise ValueError('Scene size is [width,height]')
    for v in size:number(v,True)
    template=load_template(inside(root,scene['template_file']))
    if scene['template_file']!='template/template.json':raise ValueError('Keep the self-contained template at template/template.json')
    if template['canvas']!=size:raise ValueError('Scene and template canvas differ')
    pages=scene.get('pages');page_ids=set()
    if not isinstance(pages,list) or not pages:raise ValueError('Scene requires pages')
    for page in pages:
        if not isinstance(page,dict):raise ValueError('Each page must be an object')
        if set(page)-{'id','pageType','layout','reference','background','elements','animations','notes'}:raise ValueError('Unsupported page fields')
        if type(page.get('id')) is not int or page['id']<=0 or page['id'] in page_ids:raise ValueError('Page ids must be unique positive integers')
        page_ids.add(page['id'])
        if page['layout'] not in template['layouts']:raise ValueError('Page must use a declared template layout')
        if 'reference' in page and (not isinstance(page['reference'],str) or not page['reference'].startswith('references/') or not inside(root,page['reference']).is_file()):raise ValueError('Page references belong in references/ and must exist')
        if 'notes' in page and not isinstance(page['notes'],str):raise ValueError('Speaker notes must be text')
        color(page.get('background',{}).get('color','#FFFFFF'))
        if page.get('background',{}).get('type','solid')!='solid':raise ValueError('Unsupported page background')
        ids=set()
        if not isinstance(page.get('elements'),list) or not page['elements']:raise ValueError('Page requires elements')
        for e in page['elements']:
            if not isinstance(e,dict):raise ValueError('Each element must be an object')
            key=e.get('elementId')
            if not isinstance(key,str) or not key.strip() or key in ids:raise ValueError('Element ids must be non-empty and unique per page')
            ids.add(key)
            if e.get('elementType') not in ['text','shape','line','image','table','chart']:raise ValueError('Unsupported element type')
            supported={'elementId','elementType','bounds','opacity'}|{
                'text':{'content'},'shape':{'shapeName','fill','border','path','viewBox'},
                'line':{'points','viewBox','border'},'image':{'src','fit','raster_reason'},
                'table':{'rows','columnWidths','rowHeights'},'chart':{'data','series','fontFamily','legend','dataSource','style'}
            }[e['elementType']]
            if set(e)-supported:raise ValueError('Unsupported element fields: '+', '.join(sorted(set(e)-supported)))
            box=e.get('bounds')
            if not isinstance(box,list) or len(box)!=4:raise ValueError('Element bounds are [x,y,width,height]')
            x,y,w,h=[number(v) for v in box]
            if min(x,y)<0 or min(w,h)<=0 or x+w>size[0]+.1 or y+h>size[1]+.1:raise ValueError('Element is outside the canvas: '+key)
            if any(k in e for k in ['shadow','flipH','flipV','rotation']):raise ValueError('Unsupported transform/shadow; use a capable backend or adapt explicitly')
            opacity=number(e.get('opacity',1))
            if not 0<=opacity<=1:raise ValueError('Opacity must be in [0,1]')
            if e['elementType'] in ['image','table','chart'] and opacity!=1:raise ValueError('Whole image/table/chart opacity is unsupported')
            if e['elementType']=='image':
                if not e.get('raster_reason'):raise ValueError('Each image needs raster_reason to disclose its editable boundary')
                source=inside(root,e['src'])
                if not e['src'].startswith('media/') or e['src'].startswith('media/fonts/'):raise ValueError('Image dependencies belong in media/, outside reserved media/fonts/')
                with Image.open(source) as image:
                    if image.format not in ['PNG','JPEG']:raise ValueError('Use PNG/JPEG assets for this renderer')
                    image.verify()
                if e.get('fit',{}).get('mode','contain') not in ['cover','contain']:raise ValueError('Unsupported image fit')
            if e['elementType']=='shape' and e.get('shapeName','rect') not in ['rect','roundRect','ellipse','custom']:raise ValueError('Unsupported native shape')
            if e['elementType']=='table':
                rows=e['rows'];widths=e['columnWidths'];heights=e['rowHeights']
                if not rows or not widths or len(rows)!=len(heights) or any(len(row)!=len(widths) for row in rows):raise ValueError('Invalid table dimensions')
                if any(not isinstance(cell,dict) for row in rows for cell in row):raise ValueError('Table cells must be style objects')
                for values in [widths,heights]:
                    if any(number(v,True)>1 for v in values) or abs(sum(values)-1)>.001:raise ValueError('Table dimensions must be positive ratios summing to 1')
                if any(cell.get('rowSpan',1)!=1 or cell.get('colSpan',1)!=1 for row in rows for cell in row):raise ValueError('Merged tables need another backend or an explicit unmerged design')
            contents=[e['content']] if e['elementType']=='text' else [cell for row in e['rows'] for cell in row] if e['elementType']=='table' else []
            for content in contents:
                if not isinstance(content,dict):raise ValueError('Text/cells must be style objects')
                allowed={'text','fontFamily','fontSize','color','bold','align','lineHeight','wrap'}|({'fill'} if e['elementType']=='table' else set())
                if set(content)-allowed:raise ValueError('Unsupported text/cell style fields')
                if not isinstance(content.get('text',''),str):raise ValueError('Only plain text is supported')
                number(content.get('fontSize',22),True);number(content.get('lineHeight',1.15),True);color(content.get('color','#222222'))
                align=content.get('align',['left','middle'])
                if not isinstance(align,list) or len(align)!=2 or align[0] not in ['left','center','right'] or align[1] not in ['top','middle','bottom']:raise ValueError('Unsupported text alignment')
            for fill in ([e['fill']] if 'fill' in e else [])+[cell['fill'] for cell in contents if 'fill' in cell]:
                if fill.get('type') not in ['solid','none']:raise ValueError('Unsupported fill; choose a capable backend or adapt explicitly')
                if fill.get('type')=='solid':color(fill['color'])
            if e['elementType']=='chart':chart_data(e);validate_chart_style(e)
        seen=set()
        for animation in page.get('animations',[]):
            if animation['elementId'] not in ids or animation['elementId'] in seen:raise ValueError('Entrance animations require unique existing targets')
            seen.add(animation['elementId'])
            if next(e for e in page['elements'] if e['elementId']==animation['elementId'])['elementType'] in ['table','chart']:raise ValueError('Native table/chart entrance animations are not supported')
            if animation['effect'] not in ['fade-in','wipe-in','appear']:raise ValueError('Native renderer supports appear/fade-in/wipe-in entrance animations')
            if animation.get('trigger','onClick') not in ['onClick','afterPrevious','withPrevious']:raise ValueError('Unsupported animation trigger')
            if animation.get('direction','right') not in ['up','down','left','right']:raise ValueError('Unsupported animation direction')
            number(animation.get('durationMs',600),True)
            if number(animation.get('delayMs',0))<0:raise ValueError('Animation delay must be nonnegative')
            if any(k in animation for k in ['repeat','path','easing','amount','color']):raise ValueError('Unsupported animation parameter')
    return template


def add_timing(slide,animations,shape_ids):
    if not animations:return
    timing=node('p:timing');slide._element.append(timing);counter=iter(range(1,100000))
    def time(parent,**attrs):return node('p:cTn',parent,id=next(counter),**attrs)
    def condition(parent,delay):node('p:cond',node('p:stCondLst',parent),delay=delay)
    root=time(node('p:par',node('p:tnLst',timing)),dur='indefinite',restart='never',nodeType='tmRoot')
    seq=node('p:seq',node('p:childTnLst',root),concurrent='1',nextAc='seek')
    main=time(seq,dur='indefinite',nodeType='mainSeq');main_children=node('p:childTnLst',main)
    groups=[]
    for a in animations:
        if not groups or a.get('trigger','onClick')=='onClick':groups.append([])
        groups[-1].append(a)
    builds=node('p:bldLst',timing)
    for group_id,group in enumerate(groups):
        outer=time(node('p:par',main_children),fill='hold');condition(outer,'indefinite' if group[0].get('trigger','onClick')=='onClick' else '0')
        inner=time(node('p:par',node('p:childTnLst',outer)),fill='hold');condition(inner,0);children=node('p:childTnLst',inner)
        previous_start=previous_duration=0
        for i,a in enumerate(group):
            trigger=a.get('trigger','onClick');duration=a.get('durationMs',600)
            start=a.get('delayMs',0)+(previous_start+(previous_duration if trigger=='afterPrevious' else 0) if i else 0)
            effect=a['effect'];wipe=effect=='wipe-in';direction=a.get('direction','right')
            effect_time=time(node('p:par',children),presetID=22 if wipe else 10 if effect=='fade-in' else 1,presetClass='entr',presetSubtype={'down':4,'left':8,'up':1,'right':2}[direction] if wipe else 0,fill='hold',grpId=group_id,nodeType={'onClick':'clickEffect','withPrevious':'withEffect','afterPrevious':'afterEffect'}[trigger])
            condition(effect_time,start);actions=node('p:childTnLst',effect_time)
            visibility=node('p:set',actions);behavior=node('p:cBhvr',visibility);condition(time(behavior,dur=1,fill='hold'),0)
            shape_id=shape_ids[a['elementId']];node('p:spTgt',node('p:tgtEl',behavior),spid=shape_id)
            node('p:attrName',node('p:attrNameLst',behavior)).text='style.visibility';node('p:strVal',node('p:to',visibility),val='visible')
            if effect!='appear':
                behavior=node('p:cBhvr',node('p:animEffect',actions,transition='in',filter=f'wipe({direction})' if wipe else 'fade'))
                time(behavior,dur=round(duration));node('p:spTgt',node('p:tgtEl',behavior),spid=shape_id)
            node('p:bldP',builds,spid=shape_id,grpId=group_id,animBg=1)
            previous_start=start;previous_duration=duration
    for name,event in [('prevCondLst','onPrev'),('nextCondLst','onNext')]:
        node('p:sldTgt',node('p:tgtEl',node('p:cond',node('p:'+name,seq),evt=event,delay=0)))


def build(scene_file:Path,output:Path)->Path:
    scene_file=Path(scene_file).resolve();root=scene_file.parent
    scene=json.loads(scene_file.read_text('utf-8-sig'));template=validate(scene,root);source_scene=copy.deepcopy(scene)
    output=Path(output).resolve()
    if output.exists() or root.is_relative_to(output):raise ValueError('Choose a fresh output directory separate from the source')
    fonts=defaultdict(str)
    for page in scene['pages']:
        for e in page['elements']:
            contents=[e['content']] if e['elementType']=='text' else [cell for row in e['rows'] for cell in row] if e['elementType']=='table' else []
            for content in contents:
                family=content.get('fontFamily','Noto Sans SC');content['fontFamily']=family;fonts[family]+=content.get('text','')
            if e['elementType']=='chart':fonts[e.get('fontFamily','Noto Sans SC')]+=json.dumps(e['data'],ensure_ascii=False)+''.join(s.get('name','') for s in e['series'])+'0123456789.-% '
    if not fonts:raise ValueError('A scene needs native text or native chart labels')
    pack=prepare([dict(family=f,text=t,**({'weight':scene['font_weights'][f]} if f in scene.get('font_weights',{}) else {})) for f,t in fonts.items()],output/'media/fonts')
    aliases={f['requested_family']:f['family'] for f in pack['fonts']}
    mapping={f:'media/fonts/'+p for f,p in pack['font_map'].items()}
    (output/'pages').mkdir();(output/'references').mkdir()
    shutil.copytree(inside(root,scene['template_file']).parent,output/'template')
    prs=Presentation();prs.slide_width=Pt(scene.get('size',[960,540])[0]);prs.slide_height=Pt(scene.get('size',[960,540])[1]);prs.core_properties.title=scene['title'];prs.core_properties.author='';prs.core_properties.last_modified_by=''
    specs=[];report=[]
    for page in scene['pages']:
        slide=prs.slides.add_slide(prs.slide_layouts[6]);solid(slide.background.fill,page.get('background',{'type':'solid','color':'#FFFFFF'}))
        if 'notes' in page:slide.notes_slide.notes_text_frame.text=page['notes']
        ids={};rasters=[]
        if page.get('reference'):
            source=inside(root,page['reference']);target=output/page['reference'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        for e in page['elements']:
            kind=e['elementType'];x,y,w,h=e['bounds'];args=[Pt(v) for v in [x,y,w,h]]
            if kind=='text':
                e['content']['fontFamily']=aliases[e['content']['fontFamily']]
                shape=slide.shapes.add_textbox(*args);format_text(shape.text_frame,e['content'])
                if e.get('opacity',1)!=1:
                    for run in shape.text_frame.paragraphs:
                        for item in run.runs:node('a:alpha',item.font.color._xClr,val=round(e['opacity']*100000))
            elif kind in ['shape','line']:
                name=e.get('shapeName','rect');shape=slide.shapes.add_shape({'rect':MSO_SHAPE.RECTANGLE,'roundRect':MSO_SHAPE.ROUNDED_RECTANGLE,'ellipse':MSO_SHAPE.OVAL,'custom':MSO_SHAPE.RECTANGLE}[name],*args)
                if kind=='line' or name=='custom':
                    if kind=='line':
                        e['shapeName']='custom';e['viewBox']=e.get('viewBox',[w,h]);e['path']='M'+e['points'].replace(' ',' L')
                    custom_geometry(shape,e)
                solid(shape.fill,e.get('fill') if kind!='line' else None,e.get('opacity',1))
                border=e.get('border')
                if border:
                    shape.line.color.rgb=color(border['color']);shape.line.width=Pt(number(border.get('width',1),True))
                    if e.get('opacity',1)!=1:node('a:alpha',shape.line.color._xClr,val=round(e['opacity']*100000))
                else:shape.line.fill.background()
            elif kind=='image':
                source=inside(root,e['src']);dest=inside(output,e['src']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
                with Image.open(source) as im:iw,ih=im.size
                cover=e.get('fit',{}).get('mode','contain')=='cover'
                if cover:
                    shape=slide.shapes.add_picture(str(dest),*args)
                    if iw/ih>w/h:shape.crop_left=shape.crop_right=(1-(w/h)/(iw/ih))/2
                    else:shape.crop_top=shape.crop_bottom=(1-(iw/ih)/(w/h))/2
                else:
                    scale=min(w/iw,h/ih);rw,rh=iw*scale,ih*scale
                    shape=slide.shapes.add_picture(str(dest),Pt(x+(w-rw)/2),Pt(y+(h-rh)/2),width=Pt(rw),height=Pt(rh))
                rasters.append({'elementId':e['elementId'],'reason':e['raster_reason'],'file':e['src']})
            elif kind=='table':
                shape=slide.shapes.add_table(len(e['rows']),len(e['columnWidths']),*args);table=shape.table
                table.first_row=False;table.horz_banding=False
                for i,ratio in enumerate(e['columnWidths']):table.columns[i].width=Pt(w*ratio)
                for i,ratio in enumerate(e['rowHeights']):table.rows[i].height=Pt(h*ratio)
                for r,row in enumerate(e['rows']):
                    for c,cell in enumerate(row):
                        cell['fontFamily']=aliases[cell['fontFamily']];target=table.cell(r,c);solid(target.fill,cell.get('fill',{'type':'solid','color':'#FFFFFF'}));format_text(target.text_frame,dict(cell,text=cell.get('text','')))
            else:
                kind_chart,data=chart_data(e)
                shape=slide.shapes.add_chart({'bar':XL_CHART_TYPE.COLUMN_CLUSTERED,'line':XL_CHART_TYPE.LINE,'scatter':XL_CHART_TYPE.XY_SCATTER}[kind_chart],*args,data)
                chart=shape.chart;chart.has_legend=bool(e.get('legend',len(e['series'])>1))
                for series,cfg in zip(chart.series,e['series']):
                    if cfg.get('fill'):
                        series.format.fill.solid();series.format.fill.fore_color.rgb=color(cfg['fill'])
                format_chart(chart,e,aliases.get(e.get('fontFamily','Noto Sans SC'),e.get('fontFamily','Noto Sans SC')))
            # python-pptx preset shapes otherwise inherit theme effects (often a shadow).
            if kind not in ['table','chart']:shape.shadow.inherit=False
            shape.name=e['elementId'];ids[e['elementId']]=shape.shape_id
        transition=node('p:transition',spd='med');node('p:fade',transition);slide._element.insert_element_before(transition,'p:timing','p:extLst')
        add_timing(slide,page.get('animations',[]),ids)
        specs.append({k:copy.deepcopy(page[k]) for k in ['pageType','background','elements','animations','notes'] if k in page})
        report.append({'id':page['id'],'native_objects':len(page['elements'])-len(rasters),'raster_objects':rasters,'reference':page.get('reference')})
    deck=write_project(prs,specs,output,'deck',mapping,scene['title'],body_font=aliases.get('Noto Sans SC',next(iter(mapping))))
    for name,data in [('font-map.json',mapping),('scene.json',source_scene),('editability-report.json',report),('structure-report.json',inspect(deck,require_fade=True))]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not inspect(deck,require_fade=True)['ok']:raise ValueError('Export failed structure validation; inspect structure-report.json')
    return deck


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('scene',type=Path);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    try:print(build(args.scene,args.output_dir))
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
