"""Validate a project brief and write a Markdown handoff without uploading files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STATUSES = {'verified', 'demo', 'concept', 'planned', 'unspecified'}


def design_mode(brief: dict) -> str:
    """Preserve page references by default unless the user chose a mode."""
    return brief.get('design', {}).get('mode') or (
        'fidelity' if any(slide.get('reference') for slide in brief['slides']) else 'enhance')


def _text(value, field: str, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        requirement = 'a string' if allow_empty else 'a non-empty string'
        raise ValueError(f'{field} must be {requirement}')


def _texts(value, field: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{field} must be a list of strings')


def validate(brief: dict) -> dict:
    if not isinstance(brief, dict) or not isinstance(brief.get('project'), str) or not brief['project'].strip():
        raise ValueError('project must be a non-empty string')
    slides = brief.get('slides')
    if not isinstance(slides, list) or not slides:
        raise ValueError('slides must be a non-empty list')
    ids = set()
    for slide in slides:
        if not isinstance(slide, dict):
            raise ValueError('Each slide must be an object')
        sid = slide.get('id')
        if type(sid) is not int or sid < 1 or sid in ids:
            raise ValueError('Slide ids must be unique positive integers')
        ids.add(sid)
        if not isinstance(slide.get('title'), str) or not slide['title'].strip():
            raise ValueError(f'Slide {sid} requires a title')
        if not isinstance(slide.get('status', 'unspecified'), str) or slide.get('status', 'unspecified') not in STATUSES:
            raise ValueError(f'Unknown status on slide {sid}')
        for key in ['key_points', 'assets', 'layout_constraints', 'typography_constraints', 'image_plan']:
            if key in slide:
                _texts(slide[key], f'Slide {sid}.{key}')
        for key in ['reference', 'reference_prompt', 'layout', 'font_profile', 'density',
                    'color_mode', 'focal_point', 'visual', 'notes', 'data_source']:
            if key in slide:
                _text(slide[key], f'Slide {sid}.{key}', allow_empty=key not in ['reference_prompt', 'data_source'])
        if 'data_is_illustrative' in slide and type(slide['data_is_illustrative']) is not bool:
            raise ValueError(f'Slide {sid}.data_is_illustrative must be true or false')
    if 'imagegen_allowed' in brief and type(brief['imagegen_allowed']) is not bool:
        raise ValueError('imagegen_allowed must be true or false')
    if 'purpose' in brief:
        _text(brief['purpose'], 'purpose', allow_empty=True)
    style = brief.get('style', {})
    if not isinstance(style, dict):
        raise ValueError('style must be an object')
    for key in ['ratio', 'description']:
        if key in style:
            _text(style[key], f'style.{key}', allow_empty=True)
    if 'colors' in style:
        _texts(style['colors'], 'style.colors')
    if 'asset_priority' in brief:
        _texts(brief['asset_priority'], 'asset_priority')
    if 'conversations' in brief:
        if not isinstance(brief['conversations'], list) or any(not isinstance(c, dict) for c in brief['conversations']):
            raise ValueError('conversations must be a list of objects')
        for item in brief['conversations']:
            for key in ['role', 'location', 'visibility']:
                if key in item:
                    _text(item[key], f'conversations.{key}', allow_empty=True)
    design=brief.get('design',{})
    if not isinstance(design,dict):
        raise ValueError('design must be an object')
    if design.get('mode','enhance') not in ['fidelity','enhance','explore']:
        raise ValueError('Unknown design mode')
    if 'constants' in design:
        _texts(design['constants'], 'design.constants')
    profiles=design.get('font_profiles',{})
    if not isinstance(profiles,dict) or any(not isinstance(v,dict) for v in profiles.values()):
        raise ValueError('font_profiles must map profile names to role objects')
    for profile in profiles.values():
        if any(not isinstance(value,str) or not value.strip() for value in profile.values()):
            raise ValueError('Font role values must be non-empty strings')
    if 'template' in design:
        binding=design['template']
        if not isinstance(binding,dict) or any(not isinstance(binding.get(k),str) or not binding[k].strip() for k in ['id','version']):
            raise ValueError('Template binding requires non-empty id and version')
        if 'file' in binding and (not isinstance(binding['file'],str) or not binding['file'].strip()):
            raise ValueError('Template binding file must be a non-empty path string')
    for item in [design]+slides:
        if 'template_override' in item:
            override=item['template_override']
            if not isinstance(override,dict) or not isinstance(override.get('reason'),str) or not override['reason'].strip():
                raise ValueError('Template overrides require an explicit reason')
    return brief


def render(brief: dict) -> str:
    validate(brief)
    style = brief.get('style', {})
    lines = [f'# {brief["project"]}：制作交接', '',
             f'用途：{brief.get("purpose", "待说明")}',
             f'画幅：{style.get("ratio", "以用户要求为准")}',
             f'风格：{style.get("description", "沿用参考图")}',
             f'主色：{", ".join(style.get("colors", []))}',
             f'imagegen使用意向：{brief.get("imagegen_allowed", "未说明")}（仍以宿主能力与会话权限为准）', '']
    if brief.get('design') or any(slide.get('reference') for slide in brief['slides']):
        design=brief.get('design', {})
        lines += ['## 设计约定','',f'模式：{design_mode(brief)}']
        if design.get('template'):
            binding=design['template']
            lines += [f'- 使用模板：{binding["id"]} / {binding["version"]}',
                      f'- 模板位置：{binding.get("file","由调用方提供")}（先读取规范与相应页型，再制作页面）']
        for name,roles in design.get('font_profiles',{}).items():
            lines += [f'- 字体方案 {name}：'+ '；'.join(f'{role}={family}' for role,family in roles.items())]
        if design.get('constants'):
            lines += ['- 保持：'+'、'.join(design['constants'])]
        if design.get('template_override'):
            lines += ['- 模板变更原因：'+design['template_override']['reason']]
        lines += ['']
    if brief.get('asset_priority'):
        lines += ['素材优先顺序：' + ' → '.join(brief['asset_priority']), '']
    if brief.get('conversations'):
        lines += ['## 内容与提示词来源', '']
        for item in brief['conversations']:
            lines += [f'- {item.get("role", "资料")}：{item.get("location", "未提供")}；可见范围：{item.get("visibility", "unspecified")}']
        lines += ['']
    for slide in sorted(brief['slides'], key=lambda value: value['id']):
        lines += [f'## {slide["id"]:02} {slide["title"]}', '',
                  f'参考：{slide.get("reference", "未提供")}',
                  f'事实状态：{slide.get("status", "unspecified")}', '']
        if slide.get('reference_prompt'):
            lines += ['对应提示词或来源：'+slide['reference_prompt'], '']
        for field,label in [('layout','布局'),('font_profile','字体方案'),('density','阅读密度'),
                            ('color_mode','明暗'),('focal_point','视觉重点'),('visual','素材用途')]:
            if slide.get(field):lines += [f'{label}：{slide[field]}']
        if any(slide.get(field) for field in ['layout','font_profile','focal_point']):lines += ['']
        for field,label in [('layout_constraints','保留的参考排版'),
                            ('typography_constraints','字体与层级约束'),('image_plan','图片来源与处理计划')]:
            if slide.get(field):
                lines += [label+'：']+['- '+value for value in slide[field]]+['']
        lines += ['- ' + point for point in slide.get('key_points', [])]
        if slide.get('assets'):
            lines += ['', '素材位置：'] + ['- ' + asset for asset in slide['assets']]
        if slide.get('notes'):
            lines += ['', '制作说明：' + slide['notes']]
        if slide.get('data_source'):
            lines += ['', '数据来源：' + slide['data_source']]
        if 'data_is_illustrative' in slide:
            lines += ['', '示意数据：' + ('是（须在页面注明，不作为成果证据）' if slide['data_is_illustrative'] else '否')]
        if slide.get('template_override'):
            lines += ['', '模板变更原因：'+slide['template_override']['reason']]
        lines += ['']
    return '\n'.join(lines).rstrip()+'\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('brief', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        text = render(json.loads(args.brief.read_text(encoding='utf-8-sig')))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    print(f'Wrote {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
