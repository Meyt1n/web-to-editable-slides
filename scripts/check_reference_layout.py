"""Check declared reference regions against scene objects and optional actual PPTX.

Codex supplies the regions after looking at the image. This does not detect regions,
judge generated artwork, or turn geometry agreement into a visual fidelity score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from template_pack import inside


KINDS={'text':{'text'},'image':{'image'},'table':{'table'},'chart':{'chart'},
       'diagram':{'text','shape','line','table','chart'}}
CRITICAL={'text','image','table','chart'}


def raw_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_box(value, *, normalized=False):
    if not isinstance(value,list) or len(value)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):
        raise ValueError('Region bounds must contain four finite numbers')
    x,y,w,h=value
    if x<0 or y<0 or w<=0 or h<=0 or normalized and (x+w>1.000001 or y+h>1.000001):
        raise ValueError('Region bounds must be positive and stay inside the reference frame')
    return value


def _union(boxes):
    x=min(b[0] for b in boxes);y=min(b[1] for b in boxes)
    return [x,y,max(b[0]+b[2] for b in boxes)-x,max(b[1]+b[3] for b in boxes)-y]


def _actual_pages(pptx):
    prs=Presentation(pptx);size=[prs.slide_width.pt,prs.slide_height.pt];pages=[]
    for slide in prs.slides:
        elements=[]
        for shape in slide.shapes:
            kind='image' if shape.shape_type==MSO_SHAPE_TYPE.PICTURE else 'chart' if shape.has_chart else 'table' if shape.has_table else 'text' if shape.has_text_frame and (shape.text or shape.shape_type==MSO_SHAPE_TYPE.TEXT_BOX) else 'shape'
            elements.append(dict(elementId=shape.name,elementType=kind,
                bounds=[shape.left.pt,shape.top.pt,shape.width.pt,shape.height.pt],
                content=dict(text=shape.text) if kind=='text' else {}))
        pages.append(elements)
    return size,pages


def check(scene_file,review_file=None,pptx=None,*,tolerance=0.015):
    scene_file=Path(scene_file).resolve();root=scene_file.parent
    scene=json.loads(scene_file.read_text('utf-8-sig'))
    review_file=Path(review_file) if review_file else root/'reference-review.json'
    reviews=json.loads(review_file.read_text('utf-8-sig'))
    if not isinstance(reviews,dict):raise ValueError('Reference review must map page ids to objects')
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<=tolerance<=0.05:
        raise ValueError('Layout tolerance must be between 0 and 0.05 of the canvas')
    size=scene.get('size',[960,540])
    if not isinstance(size,list) or len(size)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in size):
        raise ValueError('Scene requires positive canvas dimensions')
    actual_size,actual_pages=_actual_pages(pptx) if pptx else (None,None)
    report=dict(ok=True,errors=[],pages=[],tolerance=tolerance,
        scope='Declared region geometry, object types and source asset/prompt hashes; Codex must separately inspect reference, artwork, fonts, cropping and actual rendered output')
    if actual_pages is not None and len(actual_pages)!=len(scene['pages']):report['errors'].append('Actual PPTX slide count differs from scene')
    if actual_size and abs((actual_size[0]/actual_size[1])/(size[0]/size[1])-1)>0.015:report['errors'].append('Actual PPTX aspect ratio differs from scene')
    for index,page in enumerate(scene['pages']):
        sid=page['id'];prefix=f'Page {sid}: ';errors=[];regions=[]
        reference=inside(root,page.get('reference'))
        item=reviews.get(str(sid),{})
        if not isinstance(item,dict) or item.get('reference_sha256')!=raw_hash(reference):
            raise ValueError(prefix+'reference review is missing or belongs to another image')
        if not isinstance(item.get('regions'),list) or not item['regions']:
            raise ValueError(prefix+'Codex must record non-empty regions after inspecting the reference')
        crop=reference_box(item.get('reference_crop',[0,0,1,1]),normalized=True)
        frame=reference_box(item.get('reference_frame',[0,0,1,1]),normalized=True)
        with Image.open(reference) as image:rw,rh=image.size
        if abs((rw*crop[2]/(rh*crop[3]))/(size[0]*frame[2]/(size[1]*frame[3]))-1)>0.015:errors.append('Reference aspect ratio differs; agree on canvas/cropping before reconstruction')
        source={e['elementId']:e for e in page['elements']}
        if len(source)!=len(page['elements']):raise ValueError(prefix+'duplicate scene elementId')
        targets={};named=set()
        for region in item['regions']:
            if not isinstance(region,dict):raise ValueError(prefix+'regions must be objects')
            rid=region.get('id');kind=region.get('kind');ids=region.get('elementIds')
            if not isinstance(rid,str) or not rid.strip() or rid in named:raise ValueError(prefix+'region ids must be unique and non-empty')
            named.add(rid)
            if not isinstance(kind,str) or kind not in KINDS:raise ValueError(prefix+'unsupported region kind')
            bounds=reference_box(region.get('bounds'),normalized=True)
            expected=[frame[0]+bounds[0]*frame[2],frame[1]+bounds[1]*frame[3],bounds[2]*frame[2],bounds[3]*frame[3]]
            if not isinstance(ids,list) or not ids or any(not isinstance(key,str) or not key.strip() for key in ids):raise ValueError(prefix+rid+' needs elementIds')
            for key in ids:
                if key in targets:raise ValueError(prefix+'an element cannot be assigned to multiple regions: '+key)
                targets[key]=region
            if kind=='image':
                if len(ids)!=1:raise ValueError(prefix+rid+' image regions identify one independent image each')
                asset=region.get('asset',{})
                if not isinstance(asset,dict) or asset.get('method') not in ['imagegen','original']:raise ValueError(prefix+rid+' image needs asset method imagegen/original')
                file=inside(root,asset.get('file'))
                if asset.get('sha256')!=raw_hash(file):errors.append(rid+': image asset hash changed')
                e=source.get(ids[0],{})
                if e.get('elementType')=='image' and inside(root,e.get('src'))!=file:errors.append(rid+': scene uses a different image asset')
                if asset['method']=='imagegen':
                    prompt=inside(root,asset.get('prompt_file'))
                    text=prompt.read_text('utf-8-sig')
                    if not text.strip() or asset.get('prompt_sha256')!=hashlib.sha256(text.encode('utf8')).hexdigest():errors.append(rid+': imagegen prompt is missing or changed')
            regions.append(dict(id=rid,kind=kind,reference_bounds=bounds,expected=expected,element_ids=ids))
        def inspect_elements(elements,canvas,label):
            by_id={e['elementId']:e for e in elements}
            if len(by_id)!=len(elements):errors.append(label+': duplicate object names')
            for e in elements:
                if e['elementType'] in CRITICAL and e['elementId'] not in targets:errors.append(label+': unmapped content object '+e['elementId'])
            for region in regions:
                ids=region['element_ids'];rid=region['id'];kind=region['kind']
                if any(key not in by_id for key in ids):errors.append(label+': '+rid+' target is missing');continue
                es=[by_id[key] for key in ids]
                if any(e['elementType'] not in KINDS[kind] for e in es):errors.append(label+': '+rid+' object type differs from reference region')
                boxes=[]
                for e in es:
                    b=reference_box(e['bounds']);boxes.append([b[0]/canvas[0],b[1]/canvas[1],b[2]/canvas[0],b[3]/canvas[1]])
                    if e.get('opacity',1)==0:errors.append(label+': '+rid+' target is fully transparent')
                    if label=='pptx' and e['elementType']=='text' and source.get(e['elementId'],{}).get('elementType')=='text':
                        normalize=lambda s:s.replace('\r\n','\n').replace('\v','\n')
                        if normalize(e['content']['text'])!=normalize(source[e['elementId']]['content'].get('text','')):errors.append(label+': '+rid+' text differs from scene')
                actual=_union(boxes);deltas=[round(abs(a-b),6) for a,b in zip(actual,region['expected'])]
                region[label]=dict(bounds=[round(v,6) for v in actual],delta=deltas)
                if any(delta>tolerance for delta in deltas):errors.append(label+': '+rid+' position/size differs from reference region')
        inspect_elements(page['elements'],size,'scene')
        if actual_pages is not None and index<len(actual_pages):inspect_elements(actual_pages[index],actual_size,'pptx')
        report['pages'].append(dict(id=sid,reference_crop=crop,reference_frame=frame,regions=regions,ok=not errors))
        report['errors'].extend(prefix+e for e in errors)
    report['ok']=not report['errors']
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene',type=Path);parser.add_argument('--review',type=Path)
    parser.add_argument('--pptx',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:report=check(args.scene,args.review,args.pptx)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded+'\n',encoding='utf8')
    print(encoded);raise SystemExit(0 if report['ok'] else 1)
