"""Make reference/render pairs for visual review; no pixel similarity score is implied."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from template_pack import inside


def compare(pairs_file: Path, output: Path, width: int = 800) -> dict:
    if not 320 <= width <= 2400:
        raise ValueError('Panel width must be between 320 and 2400')
    if output.exists():
        raise ValueError('Choose a new output directory')
    pairs=json.loads(pairs_file.read_text('utf-8-sig'))
    if not isinstance(pairs,list) or not pairs:
        raise ValueError('Pairs must be a non-empty list')
    seen=set(); sources=[]
    for pair in pairs:
        if not isinstance(pair,dict) or type(pair.get('id')) is not int or pair['id']<1 or pair['id'] in seen:
            raise ValueError('Each pair needs a unique positive integer id')
        seen.add(pair['id'])
        sources.append((pair['id'],inside(pairs_file.resolve().parent,pair.get('reference')),
                        inside(pairs_file.resolve().parent,pair.get('rendered'))))
    # Decode everything before writing, so a missing page cannot yield a partial "review".
    panels=[]; report={'pairs':[],'scope':'Side-by-side visual review only; no automatic fidelity score'}
    for sid,ref,render in sources:
        with Image.open(ref) as im: left=im.convert('RGB')
        with Image.open(render) as im: right=im.convert('RGB')
        height=round(width*9/16)
        sheet=Image.new('RGB',(2*width+24,height+40),'#E6E7E1')
        draw=ImageDraw.Draw(sheet)
        draw.text((8,10),f'P{sid:02} REFERENCE',fill='#233F35')
        draw.text((width+24,10),f'P{sid:02} ACTUAL RENDER',fill='#233F35')
        for offset,im in [(0,left),(width+24,right)]:
            panel=ImageOps.pad(im,(width,height),color='#D3D6CE',method=Image.Resampling.LANCZOS)
            sheet.paste(panel,(offset,40))
        panels.append((sid,sheet))
        report['pairs'].append({'id':sid,'file':f'{sid:02}-comparison.png',
            'reference_size':list(left.size),'rendered_size':list(right.size),
            'aspect_ratio_mismatch':abs(left.width/left.height-right.width/right.height)>.015,
            'reference_sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),
            'rendered_sha256':hashlib.sha256(render.read_bytes()).hexdigest()})
    output.mkdir(parents=True)
    for sid,sheet in panels:sheet.save(output/f'{sid:02}-comparison.png')
    thumb_width=1200
    thumbs=[ImageOps.contain(sheet,(thumb_width,1000),method=Image.Resampling.LANCZOS) for _,sheet in panels]
    overview=Image.new('RGB',(thumb_width,sum(im.height+12 for im in thumbs)+12),'#E6E7E1')
    y=12
    for im in thumbs:overview.paste(im,(0,y));y+=im.height+12
    overview.save(output/'overview.jpg',quality=92)
    (output/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pairs',type=Path,help='JSON [{id,reference,rendered}], paths relative to this JSON')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--width',type=int,default=800)
    args=parser.parse_args()
    try:
        report=compare(args.pairs,args.output_dir,args.width)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps({'pages':len(report['pairs']),'overview':str(args.output_dir/'overview.jpg')}))


if __name__=='__main__':main()
