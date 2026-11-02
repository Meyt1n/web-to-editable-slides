"""PPTD entrance groups for lessons; callers choose targets and verify exported playback."""
from __future__ import annotations


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
