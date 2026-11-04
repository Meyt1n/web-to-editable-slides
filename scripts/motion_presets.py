"""PPTD entrance groups for lessons; callers choose targets and verify exported playback."""
from __future__ import annotations

import math


def reveal_groups(groups: list[list[str]], *, autoplay: bool = False) -> list[dict]:
    """Start each knowledge point with a click; reveal its related objects together."""
    if not isinstance(groups,list) or not groups:raise ValueError('Provide non-empty reveal groups')
    seen=set()
    for group in groups:
        if not isinstance(group,list) or not group:raise ValueError('Each reveal group needs element ids')
        for key in group:
            if not isinstance(key,str) or not key.strip() or key in seen:
                raise ValueError('Entrance targets must have non-empty, unique element ids')
            seen.add(key)
    result=[]
    for group in groups:
        for i,key in enumerate(group):
            item=dict(elementId=key,effect='wipe-in' if i==0 else 'fade-in',
                      trigger=('afterPrevious' if autoplay else 'onClick') if i==0 else 'withPrevious',
                      durationMs=600 if i==0 else 500,delayMs=0 if i==0 else 120)
            if i==0:item['direction']='right'
            result.append(item)
    return result


def question_answer(question_ids: list[str], answer_ids: list[str]) -> list[dict]:
    """Two explicit clicks: show the question, then reveal the answer/explanation."""
    return reveal_groups([question_ids,answer_ids])


def title_entrance(element_id: str) -> list[dict]:
    """Automatic restrained wipe for a cover or chapter title."""
    if not isinstance(element_id,str) or not element_id.strip():raise ValueError('A title element id is required')
    return [dict(elementId=element_id,effect='wipe-in',direction='down',trigger='afterPrevious',durationMs=1100,delayMs=0)]


def handwriting_groups(groups: list[list[dict]], *, autoplay: bool = False, gap_ms: int = 30) -> list[dict]:
    """Reveal ordered words/phrases/strokes; each knowledge point gets one click.

    Units refer to existing editable objects or intentionally rasterized artwork.
    Wipes simulate writing; they do not trace the inside of a glyph or curved path.
    """
    def milliseconds(value,positive=False):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or positive and value<=0:
            raise ValueError('Handwriting timing must be finite and nonnegative; durations must be positive')
        return round(value)
    gap=milliseconds(gap_ms)
    if not isinstance(groups,list) or not groups:raise ValueError('Provide handwriting groups in reading/drawing order')
    if type(autoplay) is not bool:raise ValueError('autoplay must be boolean')
    result=[];seen=set()
    for group_index,group in enumerate(groups):
        if not isinstance(group,list) or not group:raise ValueError('Each handwriting group needs units')
        previous_gap=0
        for i,unit in enumerate(group):
            if not isinstance(unit,dict) or set(unit)-{'elementId','text','durationMs','direction','gapAfterMs'}:
                raise ValueError('A handwriting unit needs elementId and optional text/durationMs/direction/gapAfterMs')
            key=unit.get('elementId')
            if not isinstance(key,str) or not key.strip() or key in seen:raise ValueError('Handwriting targets must be non-empty and unique')
            seen.add(key)
            text=unit.get('text','')
            if not isinstance(text,str):raise ValueError('Unit text is a timing hint, not rendered content')
            default=min(380,max(140,110+25*len(text.strip())+(-12,8,0)[i%3])) if text.strip() else 250
            duration=milliseconds(unit.get('durationMs',default),True)
            if duration<1:raise ValueError('Handwriting duration must round to at least 1 ms')
            direction=unit.get('direction','left')
            if direction not in ['left','right','up','down']:raise ValueError('Choose an explicit supported wipe direction')
            trigger='afterPrevious' if autoplay or i else 'onClick'
            result.append(dict(elementId=key,effect='wipe-in',direction=direction,trigger=trigger,
                durationMs=duration,delayMs=450 if autoplay and group_index and not i else previous_gap))
            previous_gap=milliseconds(unit.get('gapAfterMs',gap))
    return result
