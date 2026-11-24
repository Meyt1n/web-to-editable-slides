"""Build the fieldwork scrapbook sample from its reusable layout and components."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import shutil
from tempfile import TemporaryDirectory

from native_renderer import build
from template_pack import inside, load_template, prepare


TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/templates/fieldwork-scrapbook'


def torn_path(width, height, jitter, seed):
    randomizer = random.Random(seed)
    points = []
    for sx, sy, dx, dy in [(0, 0, width, 0), (width, 0, 0, height),
                           (width, height, -width, 0), (0, height, 0, -height)]:
        steps = max(3, math.ceil((abs(dx) + abs(dy)) / 18))
        for step in range(steps):
            ratio = step / steps
            x, y = sx + ratio * dx, sy + ratio * dy
            inset = randomizer.uniform(0, jitter)
            points.append((x + math.copysign(inset, -dy) if dy else x,
                           y + math.copysign(inset, dx) if dx else y))
    return 'M ' + ' L '.join(f'{x:.2f} {y:.2f}' for x, y in points) + ' Z'


def rotated_inset(box, inner, degrees):
    """Rotate the inset around the frame center, then around its own center."""
    x, y, width, height = box
    ix, iy, iw, ih = inner
    dx, dy = ix + iw / 2 - width / 2, iy + ih / 2 - height / 2
    angle = math.radians(degrees)
    return [x + width / 2 + dx * math.cos(angle) - dy * math.sin(angle) - iw / 2,
            y + height / 2 + dx * math.sin(angle) + dy * math.cos(angle) - ih / 2, iw, ih]


class ScrapbookPage:
    def __init__(self, template, layout, backdrop):
        self.palette = template['palette']
        self.styles = template['typography']
        self.components = template['components']
        self.grid = template['grid']
        self.layout = template['layouts'][layout]
        self.slots = self.layout['slots']
        self.elements = [dict(elementId='旧纸底图', elementType='image',
                              bounds=[0, 0, *template['canvas']], src=backdrop, fit={'mode': 'cover'},
                              raster_reason='无字纸纹、远景和红布装饰')]

    def text(self, key, box, value, role='body', *, center=False, anchor='middle', size=None, rotation=0):
        style = self.styles[role]
        element = dict(elementId=key, elementType='text', bounds=box, content={
            'text': value, 'fontFamily': style['family'], 'fontSize': size or style['size'],
            'bold': style.get('bold', False), 'color': self.palette[style['color']],
            'align': ['center' if center else 'left', anchor], 'lineHeight': style.get('lineHeight', 1.12),
            'wrap': False,
        })
        if rotation:
            element['rotation'] = rotation
        self.elements.append(element)

    def shape(self, key, box, fill, *, kind='rect', edge=None, thickness=1, rotation=0, opacity=1, path=None):
        element = dict(elementId=key, elementType='shape', bounds=box, shapeName=kind,
                       fill={'type': 'solid', 'color': self.palette[fill]} if fill else {'type': 'none'})
        if edge:
            element['border'] = {'color': self.palette[edge], 'width': thickness}
        if rotation:
            element['rotation'] = rotation
        if opacity != 1:
            element['opacity'] = opacity
        if path:
            element.update(shapeName='custom', path=path, viewBox=box[2:])
        self.elements.append(element)
        return element

    def paper(self, key, box, *, swatch=None, rotation=0):
        x, y, w, h = box
        style = self.components['torn-paper']
        path = torn_path(w, h, style['jitter'], key)
        self.shape(key + '投影', [x + 1, y + 2, w, h], 'shadow', opacity=.18, rotation=rotation, path=path)
        self.shape(key, box, swatch or style['fill'], edge=style['edge'],
                   thickness=style['edge-width'], rotation=rotation, path=path)

    def brush(self, key, box, label):
        style = self.components['brush-strip']
        x, y, w, h = box
        self.shape(key + '笔刷底', box, style['fill'], path=torn_path(w, h, style['jitter'], key))
        inset = style['label-inset']
        self.text(key, [x + inset, y, w - 2 * inset, h], label, 'section', center=True)

    def underline(self, key, box):
        _, _, w, h = box
        path = f'M 0 {h*.70} C {w*.28} 0 {w*.67} 0 {w} {h*.30} C {w*.65} {h*.32} {w*.30} {h*.58} 0 {h} Z'
        self.shape(key, box, 'brush', path=path)

    def heading(self, title):
        self.text('页标题', self.slots.get('headline', self.grid['headline']), title, 'heading')
        self.underline('标题下划笔刷', self.grid['headline-rule'])

    def arrow(self, key, box):
        _, _, w, h = box
        shaft = min(w * .6, 11)
        path = f'M 0 {h*.32} H {w-shaft} V 0 L {w} {h/2} L {w-shaft} {h} V {h*.68} H 0 Z'
        self.shape(key, box, 'brush', path=path)

    def strip(self, slot, label, value):
        x, y, w, h = self.grid[slot]
        self.paper(label + '底纸', [x, y, w, h])
        self.brush(label + '条', [x + 10, y + 6, 115, h - 12], label)
        self.text(label + '正文', [x + 137, y + 2, w - 150, h - 4], value)

    def notebook(self, box, label='答'):
        self.paper('笔记纸', box)
        x, y, _, h = box
        style = self.components['notebook']
        diameter, step = style['puncture-diameter'], style['puncture-step']
        for index, offset in enumerate(range(13, int(h) - 9, step), 1):
            self.shape(f'孔{index}', [x + 7, y + offset, diameter, diameter], style['puncture-fill'], kind='ellipse')
        self.brush(label + '栏', [x + 26, y + 8, 76, 32], label)

    def photo(self, key, box, rotation=None, *, source=None):
        """Add an editable frame and a fillable photo slot, or place provided evidence."""
        style = self.components['instant-photo']
        if rotation is None:
            rotation = style['default-rotation']
        self.paper(key + '相纸', box, swatch=style['fill'], rotation=rotation)
        _, _, w, h = box
        left, top, right, bottom = style['inset']
        inset = rotated_inset(box, [left, top, w - left - right, h - top - bottom], rotation)
        if source:
            self.elements.append(dict(elementId=key, elementType='image', bounds=inset, src=source, rotation=rotation,
                                      fit={'mode': style['fit']}, raster_reason='单独嵌入的原始证据图'))
        else:
            placeholder = self.shape(key, inset, style['empty-fill'], edge=style['empty-edge'],
                                     thickness=.55, rotation=rotation)
            placeholder['picturePlaceholder'] = True
        tape = rotated_inset(box, [15, -7, min(84, w * .31), 17], rotation)
        self.shape(key + '胶带', tape, style['tape-fill'], opacity=style['tape-opacity'],
                   rotation=rotation + style['tape-rotation'], path=torn_path(*tape[2:], 2, key + '胶带'))

    def photos(self):
        angles = self.layout['photo_rotations']
        if len(self.slots['photos']) != len(angles):
            raise ValueError('Each photo slot requires an angle')
        for index, (box, rotation) in enumerate(zip(self.slots['photos'], angles), 1):
            self.photo(f'照片{index}', box, rotation)

    def timeline(self, items, rows, *, numbered=True):
        style = self.components['timeline']
        x, first_y, _, first_h = rows[0]
        start_y = first_y + first_h / 2
        last_y = rows[-1][1] + rows[-1][3] / 2
        if numbered:
            self.shape('时间线', [x - 20, start_y, style['line-width'], last_y - start_y], style['color'])
        for index, ((label, value), (x, y, w, h)) in enumerate(zip(items, rows), 1):
            if numbered:
                d = style['node-size']
                self.shape(f'节点{index}', [x - 19 - d / 2, y + h / 2 - d / 2, d, d],
                           'panel', kind='ellipse', edge=style['color'], thickness=1.5)
            self.paper(f'阶段{index}标签', [x, y + 6, 104, h - 12], swatch='accent-paper')
            self.text(f'阶段{index}', [x + 3, y, 98, h], label, 'caption', center=True)
            self.text(f'阶段{index}说明', [x + 117, y, w - 123, h], value, size=15.5)


def create_scene(template, backdrop, cover_landscape):
    layouts = template['layouts']
    pages = []

    def start(layout, heading=None):
        artwork = cover_landscape if layout == 'cover' else backdrop
        page = ScrapbookPage(template, layout, artwork)
        pages.append(dict(id=len(pages) + 1, layout=layout, pageType=layout, elements=page.elements,
                          background={'type': 'solid', 'color': template['palette']['base']}))
        if heading:
            page.heading(heading)
        return page, layouts[layout]['slots']

    page, slots = start('cover')
    page.photos()
    page.text('活动抬头', slots['eyebrow'], '社会实践汇报\n可复用版式示例', center=True, size=20)
    page.text('封面主题', slots['headline'], '一次地方走访', 'display', center=True)
    page.underline('封面下划笔刷', slots['rule'])
    page.paper('副标题底纸', slots['subtitle'], swatch='accent-paper')
    page.text('副标题', slots['subtitle'], '从提问、访谈到现场记录', center=True, size=21)
    page.text('封面落款', slots['credit'], '活动主题与汇报信息', center=True, size=18)

    page, slots = start('origin', '从一个问题出发')
    page.paper('缘起底纸', slots['notes'])
    for index, (title, body) in enumerate([
        ('我的兴趣', '从熟悉的地方选一个具体切口。'),
        ('我的疑问', '把宽泛的话题收成可以访谈的问题。'),
        ('我的计划', '查资料、做访谈，再用现场记录核对。'),
    ]):
        y = 112 + index * 92
        page.brush(f'缘起标签{index}', [47, y, 123, 32], title)
        page.text(f'缘起说明{index}', [47, y + 34, 410, 41], body)
    page.photos()
    for index, (box, label) in enumerate(zip(slots['captions'], ['资料查阅', '访谈对象', '现场走访']), 1):
        page.text(f'方法{index}', box, label, 'caption')
    page.strip('finding', '研究路径', '了解背景       走进现场       汇总发现')

    page, slots = start('interview', '把问题留给受访者')
    page.strip('question', '问', '您最早是怎样接触这项工作的？')
    page.photos()
    page.paper('访谈照片说明底', slots['caption'], swatch='accent-paper')
    page.text('访谈照片说明', slots['caption'], '访谈现场与受访者信息', 'caption', center=True)
    page.notebook(slots['answer'])
    page.timeline([('起点', '交代当时的工作背景'), ('入行', '说明第一次参与的环节'),
                   ('学习', '保留一两个具体例子'), ('变化', '讲清后来的角色变化')], slots['rows'])
    page.strip('finding', '我的发现', '把个人经历放回当时的社区和行业背景。')

    page, slots = start('process', '把经历排成三个阶段')
    page.strip('question', '问', '从起初到现在，哪些环节发生了变化？')
    page.photos()
    for index, (box, label) in enumerate(zip(slots['captions'], ['手工环节', '设备参与', '协作分工']), 1):
        page.text(f'照片说明{index}', box, label, 'caption')
    page.notebook(slots['answer'])
    page.timeline([('第一阶段', '谁参与，主要做什么'), ('第二阶段', '哪些工具或条件发生变化'),
                   ('第三阶段', '有哪些新的分工与协作')], slots['rows'])
    page.strip('finding', '我的发现', '每个阶段配一张对应的证据图。')

    page, slots = start('comparison', '同一个环节的前后对照')
    stamp = page.components['stamp']
    page.shape('年份章边框', slots['stamp'], None, edge=stamp['stroke'],
               thickness=stamp['stroke-width'], rotation=stamp['rotation'])
    page.text('年份章', slots['stamp'], '20XX', 'numeric', center=True, size=32, rotation=stamp['rotation'])
    page.strip('question', '问', '在同一项工作中，哪些变化可被观察和核实？')
    page.photos()
    page.notebook(slots['answer'])
    for index, ((x, y, w, h), title, body) in enumerate(zip(slots['columns'], ['原有做法', '观察到的变化'],
            ['场地和工具\n\n原有工作流程\n\n当时的限制', '对应场景\n\n现在的工作流程\n\n适用范围']), 1):
        page.paper(f'对照卡{index}', [x, y, w, h], swatch='accent-paper')
        page.text(f'对照标题{index}', [x + 13, y + 8, w - 26, 34], title, 'heading', size=22)
        page.text(f'对照正文{index}', [x + 13, y + 57, w - 26, h - 63], body, anchor='top')
    page.arrow('变化方向', [663, 265, 32, 24])
    page.strip('finding', '我的发现', '前后两侧使用相同的观察口径和相近的照片比例。')

    page, slots = start('change-details', '从现场细节说明变化')
    page.strip('question', '问', '变化具体体现在哪几件事上？')
    page.photos()
    page.notebook(slots['answer'])
    page.timeline([('设备', '记录看得见的工具变化'), ('流程', '描述工序和人员分工'),
                   ('质量', '列出现场可观察的标准'), ('市场', '注明资料和例子的出处')], slots['rows'], numbered=False)
    page.strip('finding', '我的发现', '为每一项判断保留资料或现场观察。')

    page, slots = start('field-visit', '走进现场')
    page.photos()
    for index, (box, label) in enumerate(zip(slots['captions'], ['工作环境', '操作过程', '代表产品']), 1):
        page.paper(f'现场标签底{index}', box, swatch='accent-paper')
        page.text(f'现场标签{index}', box, label, 'caption', center=True)
    for key, label, body in [('observation', '走访观察', '写下现场看到的流程、设备与细节。'),
                             ('case', '资料案例', '补充资料里能核实的做法和出处。')]:
        x, y, w, h = slots[key]
        page.paper(label + '底', slots[key])
        page.brush(label, [x + 13, y + 9, 147, 34], label)
        page.text(label + '正文', [x + 16, y + 44, w - 32, h - 47], body)
    page.strip('finding', '我的发现', '现场照片和公开资料各有出处。')

    page, slots = start('takeaways', '把走访写成三个发现')
    for index, ((x, y, w, h), title, body) in enumerate(zip(slots['cards'], ['对现场的认识', '对变化的理解', '我的下一步'],
            ['保留一句具体发现。\n用下方的一张现场图支持。', '联系访谈和实地观察。\n说明它们如何相互印证。', '留下一个可跟进的问题。\n写明还需要哪些材料。']), 1):
        page.paper(f'总结卡{index}', [x, y, w, h])
        page.brush(f'总结标题{index}', [x + 14, y + 12, w - 28, 41], title)
        page.text(f'总结正文{index}', [x + 18, y + 66, w - 36, 80], body, anchor='top')
    page.photos()
    for index, (box, label) in enumerate(zip(slots['keywords'], ['现场', '证据', '行动']), 1):
        page.paper(f'关键字底{index}', box, swatch='accent-paper')
        page.text(f'关键字{index}', box, label, 'caption', center=True)
    page.arrow('关联一', [298, 447, 53, 14])
    page.arrow('关联二', [613, 447, 53, 14])

    page, slots = start('closing')
    page.photos()
    page.text('总结抬头', slots['eyebrow'], '社会实践汇报', 'caption', center=True, size=25)
    page.text('结尾主题', slots['headline'], '感谢聆听', 'closing', center=True)
    page.underline('结尾下划笔刷', slots['rule'])
    page.paper('结语底纸', slots['summary'])
    page.text('结语', slots['summary'], '带着问题走进现场\n用证据理解真实变化', size=25, center=True)
    page.brush('收束', slots['quote'], '回到开场的问题，留下一句回答')
    page.text('致谢', slots['credit'], '感谢参与访谈与走访的伙伴', center=True, size=17)

    return dict(version=1, title=template['title'], size=template['canvas'],
                template_file='template/template.json', font_weights=template['font_weights'], pages=pages)


def build_sample(output, template_dir=TEMPLATE):
    output = Path(output).resolve()
    template_dir = Path(template_dir).resolve()
    if output.exists() or output.is_relative_to(template_dir):
        raise ValueError('Choose a new output directory outside the template')
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='scrapbook-', dir=output.parent) as work:
        work = Path(work)
        path = prepare(template_dir / 'template.json', template_dir, work / 'template')
        template = load_template(path)
        (work / 'media').mkdir()
        assets = {
            'paper-backdrop.png': template['resources']['background'],
            'cover-landscape.png': template['resources']['images']['cover-landscape'],
        }
        for name, source in assets.items():
            shutil.copy2(inside(path.parent, source), work / 'media' / name)
        scene = create_scene(template, 'media/paper-backdrop.png', 'media/cover-landscape.png')
        scene_path = work / 'scene.json'
        scene_path.write_text(json.dumps(scene, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return build(scene_path, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    arguments = parser.parse_args()
    try:
        print(build_sample(arguments.output_dir))
    except (OSError, ValueError) as error:
        parser.error(str(error))
