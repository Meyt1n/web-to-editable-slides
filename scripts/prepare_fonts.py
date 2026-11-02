"""Subset licensed catalog fonts to assigned text and freeze variable axes for export."""
from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
import shutil

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

CATALOG=Path(__file__).resolve().parents[1]/'assets/fonts/catalog.json'


def prepare(requests: list, output: Path, catalog_path: Path = CATALOG) -> dict:
    if output.exists():raise ValueError('Choose a new font output directory')
    if not isinstance(requests,list) or not requests:raise ValueError('fonts must be a non-empty request list')
    catalog={item['family']:item for item in json.loads(catalog_path.read_text('utf-8-sig'))['fonts']}
    seen=set();built=[]
    for request in requests:
        if not isinstance(request,dict) or not isinstance(request.get('family'),str) or request['family'] not in catalog:
            raise ValueError('Each font request needs a family present in the catalog')
        family=request['family']
        if family in seen:raise ValueError('Use one weight per family in each font map; declare a separate style pack for alternatives')
        seen.add(family)
        text=request.get('text')
        if not isinstance(text,str) or not text.strip():raise ValueError(f'{family}: assigned text is required')
        chars={ord(c) for c in text if not c.isspace()}
        item=catalog[family];font=TTFont(catalog_path.parent/item['file'])
        try:
            missing=chars-set(font.getBestCmap())
            if missing:raise ValueError(f'{family}: missing assigned glyphs '+''.join(chr(cp) for cp in sorted(missing)))
            axes={}
            if 'fvar' in font:
                for axis in font['fvar'].axes:
                    value=request.get('weight',item.get('default_weight',400)) if axis.axisTag=='wght' else axis.defaultValue
                    if type(value) not in [int,float] or not axis.minValue<=value<=axis.maxValue:
                        raise ValueError(f'{family}: axis {axis.axisTag} is outside its supported range')
                    axes[axis.axisTag]=value
            elif 'weight' in request and request['weight']!=font['OS/2'].usWeightClass:
                raise ValueError(f'{family}: this static font has no requested weight')
            options=subset.Options();options.name_IDs=['*'];options.name_legacy=True;options.name_languages=['*']
            worker=subset.Subsetter(options=options);worker.populate(unicodes=chars);worker.subset(font)
            if axes:font=instantiateVariableFont(font,axes,inplace=True,optimize=True,updateFontNames=True)
            actual=font['name'].getDebugName(1)
            flags=font['OS/2'].fsType
            if flags & (2|0x200) or (flags & 4 and not flags & 8):
                raise ValueError(f'{family}: embedding flags do not allow editable outline embedding')
            buffer=BytesIO();font.save(buffer)
            built.append((item,dict(requested_family=family,family=actual,axes=axes,
                characters=len(chars),source_sha256=item['sha256']),buffer.getvalue()))
        finally:font.close()
    output.mkdir(parents=True)
    mapping={};report=[]
    for i,(item,info,data) in enumerate(built,1):
        if info['family'] in mapping:raise ValueError('Prepared font family names collide')
        relative=f'font-{i}.ttf';(output/relative).write_bytes(data)
        license_name=f'font-{i}-OFL.txt';shutil.copy2(catalog_path.parent/item['license_file'],output/license_name)
        mapping[info['family']]=relative;report.append(dict(info,file=relative,license_file=license_name))
    (output/'font-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'font-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return {'font_map':mapping,'fonts':report}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requests',type=Path,help='JSON list [{family,text,weight?}]; text is the text assigned to that face')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:print(json.dumps(prepare(json.loads(args.requests.read_text('utf-8-sig')),args.output_dir),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))


if __name__=='__main__':main()
