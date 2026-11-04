"""Small native animation writer, checked against locally Office-authored samples.

Directions name the starting edge for fly-in and the OOXML wipe filter for wipes.
durationMs is the complete effect span, including both halves of a pulse.
"""
from __future__ import annotations

import math

from pptx.oxml.xmlchemy import OxmlElement


PHASES = {'appear':'entr', 'fade-in':'entr', 'wipe-in':'entr', 'fly-in':'entr',
          'zoom-in':'entr', 'pulse':'emph', 'fade-out':'exit', 'wipe-out':'exit'}
DIRECTIONS = {'up':1, 'right':2, 'down':4, 'left':8}


def milliseconds(value, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Animation timing must be finite and nonnegative')
    result = round(value)
    if positive and result < 1:
        raise ValueError('Animation duration must round to at least 1 ms')
    return result


def animation_plan(animations, element_types):
    """Validate lifecycles and resolve explicit offsets inside each click group."""
    if not isinstance(animations, list):
        raise ValueError('animations must be a list')
    rows = []
    group = -1
    previous_start = previous_duration = 0
    allowed = {'elementId','effect','trigger','durationMs','delayMs','direction','scale'}
    for item in animations:
        if not isinstance(item, dict) or set(item)-allowed:
            raise ValueError('Unsupported animation fields')
        key, effect = item.get('elementId'), item.get('effect')
        if not isinstance(key, str) or key not in element_types:
            raise ValueError('Animation target must be an existing elementId')
        if element_types[key] in ['table','chart']:
            raise ValueError('Native table/chart object animations are not supported')
        if not isinstance(effect, str) or effect not in PHASES:
            raise ValueError('Unsupported native animation effect')
        trigger = item.get('trigger','onClick')
        if trigger not in ['onClick','withPrevious','afterPrevious']:
            raise ValueError('Unsupported animation trigger')
        directional = effect in ['wipe-in','wipe-out','fly-in']
        direction = item.get('direction','left' if effect=='fly-in' else 'right')
        if not isinstance(direction, str) or direction not in DIRECTIONS or 'direction' in item and not directional:
            raise ValueError('direction is supported only for fly-in and wipes: up/right/down/left')
        duration = milliseconds(item.get('durationMs',600),positive=True)
        if effect=='pulse':
            duration = max(2,2*round(duration/2))
        scale = item.get('scale',1.08)
        if 'scale' in item and effect!='pulse':
            raise ValueError('scale is supported only for pulse')
        if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=1:
            raise ValueError('Pulse scale must be a finite factor greater than 1')
        delay = milliseconds(item.get('delayMs',0))
        if not rows or trigger=='onClick':
            group += 1
            start = delay
        else:
            start = previous_start + (previous_duration if trigger=='afterPrevious' else 0) + delay
        rows.append(dict(elementId=key,effect=effect,phase=PHASES[effect],trigger=trigger,
                         durationMs=duration,direction=direction,scale=scale,group=group,start=start))
        previous_start,previous_duration = start,duration

    # A first entrance starts hidden; a first emphasis/exit acts on static content.
    first = {}
    for row in rows:first.setdefault(row['elementId'],row['phase'])
    visible = {key:first.get(key)!='entr' for key in element_types}
    intervals = {}
    for row in rows:
        key,phase = row['elementId'],row['phase']
        if phase=='entr' and visible[key]:
            raise ValueError('An already visible target needs an exit before another entrance')
        if phase!='entr' and not visible[key]:
            raise ValueError('Emphasis/exit needs a visible target; reveal it first')
        slot = intervals.setdefault((row['group'],key),[])
        start,end = row['start'],row['start']+row['durationMs']
        if any(start < old_end and old_start < end for old_start,old_end in slot):
            raise ValueError('Animations on the same target must not overlap within a click group')
        slot.append((start,end))
        visible[key] = phase!='exit'
    return rows


def add_timing(slide, animations, shape_ids):
    rows = animation_plan(animations,{key:'shape' for key in shape_ids})
    if not rows:
        return
    def node(tag, parent=None, **attrs):
        result = OxmlElement(tag)
        for key,value in attrs.items():result.set(key,str(value))
        if parent is not None:parent.append(result)
        return result
    timing = node('p:timing')
    slide._element.insert_element_before(timing,'p:extLst')
    counter = iter(range(1,100000))
    def time(parent, **attrs):return node('p:cTn',parent,id=next(counter),**attrs)
    def condition(parent, delay):node('p:cond',node('p:stCondLst',parent),delay=delay)
    def behavior(parent, shape_id, duration, *, attr=None, delay=None, hold=True, additive=False):
        result = node('p:cBhvr',parent,**({'additive':'base'} if additive else {}))
        clock = time(result,dur=duration,**({'fill':'hold'} if hold else {}))
        if delay is not None:condition(clock,delay)
        node('p:spTgt',node('p:tgtEl',result),spid=shape_id)
        if attr:node('p:attrName',node('p:attrNameLst',result)).text=attr
        return result
    def visibility(parent, shape_id, value, delay):
        setter = node('p:set',parent)
        behavior(setter,shape_id,1,attr='style.visibility',delay=delay)
        node('p:strVal',node('p:to',setter),val=value)
    def interpolate(parent, shape_id, attr, start, end, duration, *, additive=False):
        anim = node('p:anim',parent,calcmode='lin',valueType='num')
        behavior(anim,shape_id,duration,attr=attr,additive=additive)
        values = node('p:tavLst',anim)
        for when,value in [(0,start),(100000,end)]:
            node('p:fltVal' if isinstance(value,(int,float)) else 'p:strVal',
                 node('p:val',node('p:tav',values,tm=when)),val=value)

    root = time(node('p:par',node('p:tnLst',timing)),dur='indefinite',restart='never',nodeType='tmRoot')
    sequence = node('p:seq',node('p:childTnLst',root),concurrent=1,nextAc='seek')
    main = time(sequence,dur='indefinite',nodeType='mainSeq')
    main_children = node('p:childTnLst',main)
    groups = {}
    builds_by_shape = {}
    for row in rows:
        groups.setdefault(row['group'],[]).append(row)
        shape_id=shape_ids[row['elementId']]
        builds=builds_by_shape.setdefault(shape_id,[])
        row['buildGroup']=len(builds)
        builds.append(row['buildGroup'])
    for group in groups.values():
        outer = time(node('p:par',main_children),fill='hold')
        condition(outer,'indefinite' if group[0]['trigger']=='onClick' else 0)
        inner = time(node('p:par',node('p:childTnLst',outer)),fill='hold')
        condition(inner,0)
        children = node('p:childTnLst',inner)
        for row in group:
            effect,phase,direction = row['effect'],row['phase'],row['direction']
            duration,shape_id = row['durationMs'],shape_ids[row['elementId']]
            preset = {'appear':1,'fade-in':10,'fade-out':10,'wipe-in':22,'wipe-out':22,
                      'fly-in':2,'zoom-in':23,'pulse':6}[effect]
            subtype = DIRECTIONS[direction] if effect in ['wipe-in','wipe-out','fly-in'] else 16 if effect=='zoom-in' else 0
            clock = time(node('p:par',children),presetID=preset,presetClass=phase,
                         presetSubtype=subtype,fill='hold',grpId=row['buildGroup'],
                         nodeType={'onClick':'clickEffect','withPrevious':'withEffect','afterPrevious':'afterEffect'}[row['trigger']],
                         **({'autoRev':1} if effect=='pulse' else {}))
            if effect=='appear':clock.set('dur',str(duration))
            condition(clock,row['start'])
            actions = node('p:childTnLst',clock)
            if phase=='entr':visibility(actions,shape_id,'visible',0)
            if effect in ['fade-in','fade-out','wipe-in','wipe-out']:
                anim = node('p:animEffect',actions,transition='out' if phase=='exit' else 'in',
                            filter=f'wipe({direction})' if effect.startswith('wipe') else 'fade')
                behavior(anim,shape_id,duration,hold=phase=='entr')
            elif effect=='fly-in':
                x = '0-#ppt_w/2' if direction=='left' else '1+#ppt_w/2' if direction=='right' else '#ppt_x'
                y = '0-#ppt_h/2' if direction=='up' else '1+#ppt_h/2' if direction=='down' else '#ppt_y'
                interpolate(actions,shape_id,'ppt_x',x,'#ppt_x',duration,additive=True)
                interpolate(actions,shape_id,'ppt_y',y,'#ppt_y',duration,additive=True)
            elif effect=='zoom-in':
                for attr in ['ppt_w','ppt_h']:interpolate(actions,shape_id,attr,0,'#'+attr,duration)
            elif effect=='pulse':
                anim = node('p:animScale',actions)
                behavior(anim,shape_id,duration//2)
                factor = round(row['scale']*100000)
                node('p:by',anim,x=factor,y=factor)
            if phase=='exit':visibility(actions,shape_id,'hidden',max(0,duration-1))
    builds = node('p:bldLst',timing)
    # Office drops later effects when one shape reuses the same build group.
    # Build groups identify occurrences on a shape, not presenter click groups.
    for shape_id,occurrences in builds_by_shape.items():
        for occurrence in occurrences:node('p:bldP',builds,spid=shape_id,grpId=occurrence,animBg=1)
    for name,event in [('prevCondLst','onPrev'),('nextCondLst','onNext')]:
        node('p:sldTgt',node('p:tgtEl',node('p:cond',node('p:'+name,sequence),evt=event,delay=0)))
