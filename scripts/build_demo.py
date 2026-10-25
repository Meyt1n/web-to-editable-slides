"""Build the fictional plant example as native PPTX plus a self-contained PPTD."""
from __future__ import annotations

import argparse
import base64
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt

ROOT = Path(__file__).resolve().parents[1]
GREEN, CORAL, MUTED, PALE = '#164B3B', '#FF816B', '#52655E', '#EDF7EF'
FONT = 'Reading Text SC'


class Page:
    def __init__(self, slide, kind='content'):
        self.slide, self.kind, self.elements = slide, kind, []

    def record(self, kind, bounds, **kwargs):
        self.elements.append(dict(elementId=f'e{len(self.elements)+1}', elementType=kind,
                                  bounds=list(bounds), **kwargs))

    def shape(self, x, y, w, h, fill='#FFFFFF', circle=False, border=None):
        node = self.slide.shapes.add_shape(MSO_SHAPE.OVAL if circle else MSO_SHAPE.ROUNDED_RECTANGLE,
                                           Pt(x), Pt(y), Pt(w), Pt(h))
        if not circle:
            node.adjustments[0] = .16
        node.fill.solid(); node.fill.fore_color.rgb = RGBColor.from_string(fill[1:])
        if border:
            node.line.color.rgb = RGBColor.from_string(border[1:]); node.line.width = Pt(.9)
        else:
            node.line.fill.background()
        kwargs = dict(shapeName='ellipse' if circle else 'roundRect', fill=dict(type='solid', color=fill))
        if not circle:
            kwargs['adjustments'] = [16000]
        if border:
            kwargs['border'] = dict(style='solid', width=.9, color=border)
        self.record('shape', [x, y, w, h], **kwargs)

    def text(self, text, x, y, w, h, size=20, color=GREEN, bold=False, center=False):
        box = self.slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
        frame = box.text_frame; frame.clear(); frame.word_wrap = True
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        for i, line in enumerate(text.split('\n')):
            paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            paragraph.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
            paragraph.line_spacing = 1.15; paragraph.space_after = Pt(0)
            run = paragraph.add_run(); run.text = line
            run.font.name = FONT; run.font.size = Pt(size); run.font.bold = bold
            run.font.color.rgb = RGBColor.from_string(color[1:])
            rpr = run._r.get_or_add_rPr()
            ea = OxmlElement('a:ea'); ea.set('typeface', FONT); rpr.append(ea)
        self.record('text', [x,y,w,h], content=dict(text=text, fontFamily=FONT, fontSize=size,
                    bold=bold, color=color, align=['center' if center else 'left','middle'],
                    lineHeight=1.15, wrap=True))

    def image(self, name, x, y, w, h, media, cover=False):
        with Image.open(media/name) as source:
            iw, ih = source.size
        if cover:
            picture = self.slide.shapes.add_picture(str(media/name), Pt(x),Pt(y),width=Pt(w),height=Pt(h))
            if iw/ih > w/h:
                excess = (1 - (w/h)/(iw/ih))/2
                picture.crop_left = picture.crop_right = excess
            else:
                excess = (1 - (iw/ih)/(w/h))/2
                picture.crop_top = picture.crop_bottom = excess
        else:
            scale=min(w/iw,h/ih); rw,rh=iw*scale,ih*scale
            self.slide.shapes.add_picture(str(media/name),Pt(x+(w-rw)/2),Pt(y+(h-rh)/2),width=Pt(rw),height=Pt(rh))
        self.record('image',[x,y,w,h],src='media/'+name,fit=dict(mode='cover' if cover else 'contain'))

    def finish(self):
        transition = OxmlElement('p:transition'); transition.set('spd','med')
        transition.append(OxmlElement('p:fade'))
        self.slide._element.insert_element_before(transition,'p:timing','p:extLst')
        return dict(pageType=self.kind,background=dict(type='solid',color='#FAFCF8'),elements=self.elements)


def build(output: Path, assets: Path | None = None, force: bool = False) -> Path:
    assets = (assets or ROOT/'assets').resolve(); output=output.resolve()
    if output == assets or assets.is_relative_to(output):
        raise ValueError('Output cannot replace or contain the asset directory')
    if output.exists() and any(output.iterdir()) and not force:
        raise ValueError('Output directory is not empty; choose a new directory or use --force')
    for name in ['template-background.png','product-cutout.png','demo-font.ttf']:
        if not (assets/name).is_file():
            raise ValueError(f'Missing example asset: {name}')
    media=output/'media'; pages=output/'pages'
    media.mkdir(parents=True,exist_ok=True); pages.mkdir(parents=True,exist_ok=True)
    for name in ['template-background.png','product-cutout.png','demo-font.ttf','font-OFL.txt']:
        shutil.copy2(assets/name,media/name)
    prs=Presentation();prs.slide_width=Pt(960);prs.slide_height=Pt(540)
    prs.core_properties.author='';prs.core_properties.last_modified_by=''
    prs.core_properties.title='绿芽｜虚构概念演示';prs.core_properties.subject='Reference images to native editable slides'
    specs=[]

    def fresh(kind):
        p=Page(prs.slides.add_slide(prs.slide_layouts[6]),kind)
        p.image('template-background.png',0,0,960,540,media,True)
        p.shape(793,27,133,35,PALE,border='#D2E8D8')
        p.text('概念演示',803,29,113,30,14,GREEN,True,True)
        return p

    p=fresh('cover')
    p.shape(35,65,433,397,'#FCFFF8')
    p.image('product-cutout.png',448,91,480,382,media)
    p.text('绿芽',57,91,369,109,81,GREEN,True)
    p.text('桌面植物\n养护提醒系统',61,211,380,104,33,GREEN,True)
    p.text('看见植物状态，记住每一次照料。',62,328,373,40,16.4,MUTED)
    for i,t in enumerate(['状态查看','养护提醒','记录管理']):
        x=58+i*127;p.shape(x,397,115,44,PALE,border='#D4E8D8')
        p.text(t,x+4,402,107,31,15,CORAL if i==1 else GREEN,True,True)
    p.text('虚构主题 · 自生成配图 · 用于展示PPT重建方法',51,492,866,26,11.5,MUTED)
    specs.append(p.finish())

    p=fresh('content')
    p.text('从植物状态到养护提醒',37,39,713,65,31,GREEN,True)
    p.image('product-cutout.png',12,164,259,272,media)
    steps=[('采集状态','记录植物当前状态'),('整理信息','形成便于查看的资料'),('形成提醒','提示下一次照料'),('记录照料','留下每一次养护记录')]
    for i,(title,detail) in enumerate(steps):
        x=285+i*158;p.shape(x,155,148,272,'#FCFFF8',border='#D9EADB')
        p.text(f'{i+1:02}',x+15,170,118,60,38,'#77A580',True,True)
        p.shape(x+41,246,66,66,CORAL if i==2 else '#DDEEDD',True)
        p.text(['状态','信息','提醒','记录'][i],x+46,261,56,34,15,'#FFFFFF' if i==2 else GREEN,True,True)
        p.text(title,x+6,333,136,40,19,GREEN,True,True)
        p.text(detail,x+9,379,130,32,10.9,MUTED,False,True)
        if i<3:p.text('→',x+148,272,12,35,17,'#75A77C',True,True)
    p.text('让每一次照料都更清楚。',280,450,630,39,23,MUTED,False,True)
    p.text('流程示意，不包含实测数据',604,501,309,24,11.4,MUTED,False,True)
    specs.append(p.finish())

    p=fresh('chapter')
    p.shape(36,82,478,382,'#FCFFF8')
    p.text('02',59,100,205,105,76,'#77A580',True)
    p.text('养护服务\n与交互设计',61,220,425,107,37,GREEN,True)
    p.text('从状态查看，到提醒与记录',62,343,421,40,18,MUTED)
    for i,t in enumerate(['查看状态','收到提醒','记录照料']):
        p.text('• '+t,64+i*145,408,141,30,13,CORAL if i==1 else GREEN)
    p.image('product-cutout.png',513,111,423,349,media)
    p.text('可复用章节页示例',51,491,866,26,12,MUTED)
    specs.append(p.finish())

    paths=[]
    for i,spec in enumerate(specs,1):
        rel=f'pages/{i:02}.page';paths.append(rel)
        (output/rel).write_text(yaml.safe_dump(spec,allow_unicode=True,sort_keys=False),encoding='utf-8')
    font_b64=base64.b64encode((media/'demo-font.ttf').read_bytes()).decode()
    css=f'@font-face{{font-family:"{FONT}";font-style:normal;font-weight:400;src:url(data:font/ttf;base64,{font_b64})format("truetype");}}'
    manifest=dict(version='v2',title='绿芽｜虚构概念演示',size=[960,540],
                  customFonts=[dict(family=FONT,src='data:text/css;base64,'+base64.b64encode(css.encode()).decode())],
                  pages=paths)
    (output/'green-sprout.pptd').write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False,width=180),encoding='utf-8')
    result=output/'green-sprout.pptx';prs.save(result)
    # Replace template theme defaults too, so Office does not embed unrelated fonts.
    themed=output/'.theme-fonts.pptx'
    with zipfile.ZipFile(result) as source, zipfile.ZipFile(themed,'w',zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            data=source.read(name)
            if name.startswith('ppt/theme/') and name.endswith('.xml'):
                root=ET.fromstring(data)
                for node in root.iter():
                    if node.tag.split('}')[-1] in ['latin','ea','cs','font'] and 'typeface' in node.attrib:
                        node.set('typeface',FONT)
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            elif name=='ppt/presentation.xml':
                root=ET.fromstring(data)
                root.set('saveSubsetFonts','0')
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            target.writestr(name,data)
    themed.replace(result)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--assets-dir',type=Path)
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    try:
        result=build(args.output_dir,args.assets_dir,args.force)
    except (OSError,ValueError) as exc:
        parser.error(str(exc))
    print(f'Built 3 editable slides: {result}')
    print('PPTX fonts are declared, not embedded. Install the OFL font or verify substitution before rendering.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
