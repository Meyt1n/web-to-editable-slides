"""Content-driven motion recipes; callers select real objects and verify playback."""
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


def _unique_groups(groups):
    seen=set()
    if not isinstance(groups,list) or not groups:raise ValueError('Provide non-empty semantic groups')
    for group in groups:
        if not isinstance(group,list) or not group:raise ValueError('Each group needs element ids')
        for key in group:
            if not isinstance(key,str) or not key.strip() or key in seen:raise ValueError('Recipe targets must be non-empty and unique')
            seen.add(key)


def staggered_reveal(element_ids: list[str], *, effect='fade-in', autoplay=False,
                     duration_ms=450, stagger_ms=100, direction=None) -> list[dict]:
    """One click (or automatic start), with overlapping entrances in reading order."""
    _unique_groups([element_ids])
    if type(autoplay) is not bool:raise ValueError('autoplay must be boolean')
    if effect not in ['appear','fade-in','wipe-in','fly-in','zoom-in']:raise ValueError('Choose an entrance effect')
    for value in [duration_ms,stagger_ms]:
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Recipe timing must be finite and nonnegative')
    duration,stagger=round(duration_ms),round(stagger_ms)
    if duration<1:raise ValueError('Recipe duration must round to at least 1 ms')
    if direction is not None and (effect not in ['wipe-in','fly-in'] or direction not in ['up','down','left','right']):raise ValueError('Direction applies only to wipes and fly-ins')
    result=[]
    for i,key in enumerate(element_ids):
        row=dict(elementId=key,effect=effect,durationMs=duration,
                 trigger='withPrevious' if i else 'afterPrevious' if autoplay else 'onClick',delayMs=stagger if i else 0)
        if direction is not None:row['direction']=direction
        result.append(row)
    return result


def process_flow(steps: list[list[str]], connectors: list[str], *, autoplay=False, effect='fade-in', direction=None) -> list[dict]:
    """Each step gets a click; draw its incoming connector before revealing it."""
    if not isinstance(connectors,list) or not isinstance(steps,list) or len(connectors)!=len(steps)-1:
        raise ValueError('A process needs exactly one connector between adjacent steps')
    _unique_groups(steps+([connectors] if connectors else []))
    result=[]
    for i,step in enumerate(steps):
        cues=staggered_reveal(step,effect=effect,direction=direction,autoplay=autoplay,stagger_ms=70)
        if i:
            result.append(dict(elementId=connectors[i-1],effect='wipe-in',direction='left',
                trigger='afterPrevious' if autoplay else 'onClick',durationMs=280,delayMs=400 if autoplay else 0))
            cues[0].update(trigger='afterPrevious',delayMs=40)
        result.extend(cues)
    return result


def compare_then_decide(left_ids: list[str], right_ids: list[str], verdict_ids: list[str], *, autoplay=False) -> list[dict]:
    """Reveal the two alternatives from opposite sides, then the decision."""
    _unique_groups([left_ids,right_ids,verdict_ids])
    result=[]
    for index,(ids,direction) in enumerate([(left_ids,'left'),(right_ids,'right'),(verdict_ids,None)]):
        cues=staggered_reveal(ids,effect='fly-in' if direction else 'zoom-in',direction=direction,autoplay=autoplay)
        if autoplay and index:cues[0]['delayMs']=450
        result.extend(cues)
    return result


def evidence_reveal(claim_ids: list[str], evidence_ids: list[str], takeaway_ids: list[str], *, autoplay=False) -> list[dict]:
    """Keep the claim, evidence and interpretation on three distinct beats."""
    _unique_groups([claim_ids,evidence_ids,takeaway_ids])
    result=[]
    for index,ids in enumerate([claim_ids,evidence_ids,takeaway_ids]):
        cues=staggered_reveal(ids,autoplay=autoplay,duration_ms=400,stagger_ms=90)
        if autoplay and index:cues[0]['delayMs']=500
        result.extend(cues)
    return result


def focus_pulse(element_id: str, *, trigger='onClick', duration_ms=600, scale=1.08) -> list[dict]:
    """Briefly enlarge an already visible object and return to its original size."""
    _unique_groups([[element_id]])
    if trigger not in ['onClick','withPrevious','afterPrevious']:raise ValueError('Unsupported focus trigger')
    if type(duration_ms) not in (int,float) or not math.isfinite(duration_ms) or duration_ms<2:raise ValueError('Pulse needs a finite total duration of at least 2 ms')
    if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=1:raise ValueError('Pulse scale must be greater than 1')
    return [dict(elementId=element_id,effect='pulse',trigger=trigger,durationMs=2*round(duration_ms/2),delayMs=0,scale=scale)]


def replace_state(old_ids: list[str], new_ids: list[str], *, autoplay=False) -> list[dict]:
    """One click clears the old editable layer, then reveals the replacement."""
    _unique_groups([old_ids,new_ids])
    old=staggered_reveal(old_ids,autoplay=autoplay,duration_ms=300,stagger_ms=0)
    for row in old:row['effect']='fade-out'
    new=staggered_reveal(new_ids,duration_ms=450,stagger_ms=80)
    new[0].update(trigger='afterPrevious',delayMs=60)
    return old+new
