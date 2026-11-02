"""Use an installed PPTD image exporter, loading packaged fonts before taking images."""
from __future__ import annotations

import argparse
import base64
import importlib
import json
from pathlib import Path
import sys


def font_payload(font_map: Path) -> list[dict]:
    values=json.loads(font_map.read_text('utf-8-sig'))
    if not isinstance(values,dict) or not values:
        raise ValueError('Font map must be a non-empty family-to-file object')
    payload=[]
    for family,relative in values.items():
        if not isinstance(family,str) or not family.strip() or not isinstance(relative,str):
            raise ValueError('Font family and path must be strings')
        path=font_map.resolve().parent/relative
        data=path.read_bytes()
        opentype=data[:4]==b'OTTO'
        payload.append({'family':family,'base64':base64.b64encode(data).decode('ascii'),
                        'mime':'font/otf' if opentype else 'font/ttf',
                        'format':'opentype' if opentype else 'truetype'})
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--font-map',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--renderer-scripts',type=Path,help='Installed open-kimi-ppt/scripts directory; not bundled here')
    args=parser.parse_args()
    try:
        # Avoid the backend's pip --user auto-install inside an isolated virtualenv.
        import websocket
        from PIL import Image
        import yaml
        fonts=font_payload(args.font_map)
        scripts=args.renderer_scripts
        if scripts is None:
            scripts=next((Path.home()/base/'skills/open-kimi-ppt/scripts' for base in ['.agents','.codex']
                          if (Path.home()/base/'skills/open-kimi-ppt/scripts/export_images.py').is_file()),None)
        if scripts is None or not (scripts/'export_images.py').is_file():
            raise ValueError('An installed open-kimi-ppt image exporter is required; supply --renderer-scripts')
        if args.output_dir.exists():
            raise ValueError('Choose a new output directory')
        sys.path.insert(0,str(scripts.resolve()))
        backend=importlib.import_module('export_images')
        original=backend.select_image_format
        def select_with_fonts(browser):
            cdp=backend.browser_cdp_url(browser)
            expression='''(() => {
                const fonts=FONT_PAYLOAD;
                document.documentElement.dataset.localFontsReady='loading';
                const style=document.createElement('style');
                style.dataset.packagedFonts='true';
                style.textContent=fonts.map(item=>
                    '@font-face{font-family:'+JSON.stringify(item.family)+';font-style:normal;font-weight:400;src:url(data:'+item.mime+';base64,'+item.base64+') format("'+item.format+'");}'
                ).join('\\n');
                document.head.appendChild(style);
                Promise.all(fonts.map(async item => {
                    const bytes=Uint8Array.from(atob(item.base64), c => c.charCodeAt(0));
                    const face=new FontFace(item.family,bytes.buffer,{style:'normal',weight:'400'});
                    await face.load(); document.fonts.add(face);
                })).then(() => document.fonts.ready).then(() => {
                    document.documentElement.dataset.localFontsReady='ready';
                }).catch(error => {
                    document.documentElement.dataset.localFontsError=String(error);
                    document.documentElement.dataset.localFontsReady='error';
                }); return fonts.map(item=>item.family);
            })()'''.replace('FONT_PAYLOAD',json.dumps(fonts))
            backend.evaluate_in_page(cdp,backend.PAGE_URL_HINT,expression)
            browser.run(['wait','--fn',"['ready','error'].includes(document.documentElement.dataset.localFontsReady)"],timeout=60)
            state=backend.evaluate_in_page(cdp,backend.PAGE_URL_HINT,
                "({status:document.documentElement.dataset.localFontsReady,error:document.documentElement.dataset.localFontsError,loaded:[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family)})")
            if state.get('status')!='ready':raise ValueError(f'Packaged fonts failed to load: {state}')
            (args.output_dir.parent/'source-font-load.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
            original(browser)
        backend.select_image_format=select_with_fonts
        result=backend.export_images(args.manifest,args.output_dir)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except ImportError as exc:
        parser.error(f'{exc}; install PyYAML Pillow websocket-client in the active Python environment')
    except (ValueError,OSError) as exc:parser.error(str(exc))


if __name__=='__main__':main()
