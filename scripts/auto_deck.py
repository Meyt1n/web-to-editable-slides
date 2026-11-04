"""Persist an agent-run brief → imagegen → visual review → native deck workflow.

The host agent calls imagegen and looks at images. This CLI never pretends to own
those capabilities or silently substitutes a paid API.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

if sys.version_info<(3,10):raise SystemExit('Python 3.10+ required. Run scripts/doctor.py to select a ready interpreter before creating a task.')

from PIL import Image
from template_pack import inside


def read(path):return json.loads(Path(path).read_text('utf-8-sig'))
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
def digest(path):
    path=Path(path)
    # Git and different operating systems may change EOLs without changing a prompt.
    if path.suffix.lower()=='.json':
        data=json.dumps(read(path),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
    else:data=path.read_text('utf-8-sig').encode('utf8') if path.suffix.lower() in ['.txt','.md','.yaml','.yml','.pptd','.page'] else path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def make_prompt(brief,page):
    size=brief.get('size',[960,540])
    return '\n'.join([
        f'Use case: productivity-visual. Create ONE complete presentation reference slide, aspect ratio {size[0]:g}:{size[1]:g}.',
        'This is a design reference for later rebuilding with native editable text, shapes, tables and images.',
        'Shared art direction: '+brief['style'],
        'Audience: '+brief['audience']+'. Purpose: '+brief['purpose'],
        f"Slide {page['id']}: {page['title']}",
        'Exact content (use these facts only; do not add claims or data):',
        json.dumps(page['key_points'],ensure_ascii=False),
        'Page composition and imagery: '+page['visual_prompt'],
        'Typography: clear Chinese hierarchy, generous readable body text; reserve short expressive type for headings.',
        'Keep spelling and reading order correct. No extra logos, watermarks, fake statistics or unrelated decoration.',
        'One slide only. Do not draw a contact sheet, monitor frame, PowerPoint UI, page number label or 3D perspective.',
    ])


def initialize(brief,output):
    if not isinstance(brief,dict):raise ValueError('Brief must be an object')
    for key in ['title','purpose','audience','style']:
        if not isinstance(brief.get(key),str) or not brief[key].strip():raise ValueError('Brief requires '+key)
    pages=brief.get('slides')
    if not isinstance(pages,list) or not pages:raise ValueError('Brief needs an agent-designed slide outline')
    design=brief.get('design',{})
    if not isinstance(design,dict) or design.get('mode','fidelity') not in ['fidelity','enhance','explore']:raise ValueError('Choose design.mode fidelity/enhance/explore')
    size=brief.get('size',[960,540])
    if not isinstance(size,list) or len(size)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in size):raise ValueError('Brief size must contain two positive dimensions')
    ids=set()
    for page in pages:
        if not isinstance(page,dict) or type(page.get('id')) is not int or page['id']<=0 or page['id'] in ids:
            raise ValueError('Slide ids must be unique positive integers')
        ids.add(page['id'])
        for key in ['title','visual_prompt']:
            if not isinstance(page.get(key),str) or not page[key].strip():raise ValueError('Each slide requires '+key)
        if not isinstance(page.get('key_points'),list) or not page['key_points'] or not all(isinstance(s,str) and s.strip() for s in page['key_points']):
            raise ValueError('Each slide requires non-empty key_points')
    output=Path(output)
    if output.exists():raise ValueError('Choose a new project directory; resume existing projects with status')
    output.mkdir(parents=True)
    for folder in ['prompts','references','media']:(output/folder).mkdir()
    write(output/'brief.json',brief)
    state={'version':1,'title':brief['title'],'design_mode':design.get('mode','fidelity'),'pages':[]}
    for page in sorted(pages,key=lambda p:p['id']):
        prompt=f"prompts/{page['id']:02}.txt"
        (output/prompt).write_text(make_prompt(brief,page)+'\n',encoding='utf8',newline='\n')
        state['pages'].append({'id':page['id'],'prompt':prompt,'attempts':[]})
    write(output/'workflow.json',state)
    return status(output)


def record_image(project,page_id,image,tool='imagegen',style_references=None):
    project=Path(project);state=read(project/'workflow.json')
    page=next((p for p in state['pages'] if p['id']==page_id),None)
    if page is None:raise ValueError('Unknown page id')
    if tool not in ['imagegen','user_reference']:raise ValueError('Use actual imagegen results or explicitly register a user reference')
    image=Path(image).resolve()
    with Image.open(image) as opened:
        opened.verify();kind=opened.format
    if kind not in ['PNG','JPEG']:raise ValueError('Reference must be a PNG or JPEG image')
    relative=f"references/{page_id:02}-v{len(page['attempts'])+1:02}."+('png' if kind=='PNG' else 'jpg')
    shutil.copy2(image,project/relative)
    entry={'file':relative,'sha256':digest(project/relative),
           'tool':tool,'recorded_at':datetime.now(timezone.utc).isoformat()}
    if tool=='imagegen':
        entry['prompt_sha256']=digest(inside(project,page['prompt']))
        entry['input_images']=[{'file':name,'role':'style_reference','sha256':digest(inside(project,name))} for name in (style_references or [])]
        snapshot=f"prompts/{page_id:02}-v{len(page['attempts'])+1:02}.txt"
        shutil.copy2(inside(project,page['prompt']),project/snapshot);entry['prompt_file']=snapshot
    page['attempts'].append(entry);page['reference']=entry
    write(project/'workflow.json',state)
    return status(project)


def record_reference(project,page_id,image):
    """Keep a supplied layout reference without pretending imagegen created it."""
    return record_image(project,page_id,image,tool='user_reference')


def status(project):
    project=Path(project);state=read(project/'workflow.json');tasks=[];references={}
    for page in state['pages']:
        ref=page.get('reference')
        if not ref:
            tasks.append({'action':'call_imagegen','page':page['id'],'prompt':page['prompt']});continue
        path=inside(project,ref['file'])
        inputs_valid=all(inside(project,item['file']).is_file() and digest(inside(project,item['file']))==item['sha256'] for item in ref.get('input_images',[]))
        generated=ref.get('tool')!='user_reference'
        if not path.is_file() or digest(path)!=ref['sha256'] or generated and digest(inside(project,page['prompt']))!=ref['prompt_sha256'] or not inputs_valid:
            tasks.append({'action':'regenerate_changed_reference' if generated else 'restore_selected_reference','page':page['id']});continue
        references[page['id']]=ref
    if tasks:return {'stage':'generation','tasks':tasks}
    review=read(project/'reference-review.json') if (project/'reference-review.json').is_file() else {}
    if not isinstance(review,dict):raise ValueError('Reference review must map page ids to objects')
    for page_id,ref in references.items():
        item=review.get(str(page_id),{})
        if not isinstance(item,dict):item={}
        if item.get('reference_sha256')!=ref['sha256'] or not isinstance(item.get('observations'),str) or not item['observations'].strip():
            tasks.append({'action':'inspect_reference_image','page':page_id,'file':ref['file']})
        elif state.get('design_mode')=='fidelity' and (not isinstance(item.get('regions'),list) or not item['regions']):
            tasks.append({'action':'map_reference_regions','page':page_id,'file':ref['file']})
    if tasks:return {'stage':'visual_analysis','tasks':tasks}
    if not (project/'scene.json').is_file():return {'stage':'reconstruction','tasks':[{'action':'write_template_and_scene','file':'scene.json'}]}
    if (project/'completion.json').is_file():
        receipt=read(project/'completion.json')
        if receipt.get('scene_sha256')==digest(project/'scene.json') and (state.get('design_mode')!='fidelity' or receipt.get('reference_review_sha256')==digest(project/'reference-review.json')):
            return {'stage':'complete','receipt':receipt,'scope':'Agent visual-review assertions plus checked file hashes; no cross-player guarantee'}
    local=read(project/'run-local.json') if (project/'run-local.json').is_file() else {}
    if local.get('scene_sha256')==digest(project/'scene.json') and (state.get('design_mode')!='fidelity' or local.get('reference_review_sha256')==digest(project/'reference-review.json')):
        path=Path(local['build_dir'])/local['pptx']
        if path.is_file() and digest(path)==local.get('pptx_sha256'):
            return {'stage':'rendering','tasks':[{'action':'render_compare_and_finish','build_dir':local['build_dir']}],
                    'scope':'Local continuation pointer; excluded from public replay packages'}
    return {'stage':'ready_to_compile','tasks':[{'action':'compile','scene':'scene.json'}]}


def compile_project(project,output):
    from native_renderer import build
    project=Path(project)
    result=status(project)
    if result['stage'] not in ['ready_to_compile','rendering']:raise ValueError('Incomplete workflow: '+json.dumps(result,ensure_ascii=False))
    state=read(project/'workflow.json');scene=read(project/'scene.json')
    refs={p['id']:p['reference'] for p in state['pages']}
    if [p['id'] for p in scene['pages']]!=[p['id'] for p in state['pages']]:raise ValueError('Scene page order differs from approved outline')
    for p in scene['pages']:
        if p.get('reference')!=refs[p['id']]['file']:raise ValueError('Scene must bind the current reference for each page')
    if state.get('design_mode')=='fidelity':
        from check_reference_layout import check
        layout=check(project/'scene.json')
        if not layout['ok']:raise ValueError('Reference layout mismatch: '+'; '.join(layout['errors']))
    deck=build(project/'scene.json',Path(output))
    if state.get('design_mode')=='fidelity':
        layout=check(project/'scene.json',pptx=deck)
        write(Path(output)/'reference-layout-report.json',layout)
        if not layout['ok']:raise ValueError('Exported reference layout mismatch: '+'; '.join(layout['errors']))
    for file in ['brief.json','workflow.json','reference-review.json']:shutil.copy2(project/file,Path(output)/file)
    shutil.copytree(project/'prompts',Path(output)/'prompts')
    write(project/'run-local.json',dict(scene_sha256=digest(project/'scene.json'),reference_review_sha256=digest(project/'reference-review.json'),build_dir=str(Path(output).resolve()),pptx=deck.name,pptx_sha256=digest(deck)))
    return {'pptx':str(deck),'stage':'structure_checked','next':'Render the exported PPTX, inspect every page and compare it with its reference; record visual QA separately.'}


def finish(project,build_dir):
    """Require matching structure, actual renders, references and a visual-QA record."""
    from check_pptx import inspect
    project=Path(project);build_dir=Path(build_dir)
    if status(project)['stage'] not in ['ready_to_compile','rendering']:raise ValueError('Source workflow is incomplete or already completed')
    qa=read(build_dir/'visual-qa.json');scene=read(project/'scene.json');state=read(project/'workflow.json')
    pptx=inside(build_dir,qa['pptx'])
    if qa.get('pptx_sha256')!=digest(pptx) or not inspect(pptx,require_fade=True)['ok']:raise ValueError('QA PPTX hash or structure is invalid')
    if qa.get('scene_sha256')!=digest(project/'scene.json'):raise ValueError('QA belongs to an older scene')
    if digest(build_dir/'scene.json')!=digest(project/'scene.json'):raise ValueError('Build belongs to an older scene; recompile before finishing')
    ids=[p['id'] for p in scene['pages']]
    if [p.get('id') for p in qa.get('pages',[])]!=ids:raise ValueError('Visual QA must cover every page in order')
    refs={p['id']:p['reference'] for p in state['pages']}
    for item in qa['pages']:
        rendered=inside(build_dir,item['rendered'])
        with Image.open(rendered) as image:image.verify()
        if item.get('rendered_sha256')!=digest(rendered) or item.get('reference_sha256')!=refs[item['id']]['sha256']:raise ValueError('QA render or reference hash mismatch')
        if item.get('result')!='pass' or not isinstance(item.get('findings'),str) or not item['findings'].strip():raise ValueError('Every page needs an explicit visual-review result and findings')
    if not isinstance(qa.get('renderer'),str) or not qa['renderer'].strip():raise ValueError('Record the actual renderer')
    receipt={'scene_sha256':digest(project/'scene.json'),'pptx_sha256':digest(pptx),'pages':len(ids),'renderer':qa['renderer'],'visual_qa_sha256':digest(build_dir/'visual-qa.json'),'assertion_scope':'Model visual comparison; hash and PPTX structure checks are deterministic'}
    if state.get('design_mode')=='fidelity':
        from check_reference_layout import check
        if digest(build_dir/'reference-review.json')!=digest(project/'reference-review.json'):raise ValueError('Build belongs to an older reference layout review')
        layout=check(project/'scene.json',pptx=pptx)
        if not layout['ok']:raise ValueError('Final reference layout mismatch: '+'; '.join(layout['errors']))
        write(build_dir/'reference-layout-report.json',layout)
        receipt['reference_review_sha256']=digest(project/'reference-review.json')
        receipt['reference_layout_sha256']=digest(build_dir/'reference-layout-report.json')
    if any(page.get('animations') for page in scene['pages']):
        from check_motion import compare_motion
        motion=compare_motion(build_dir/'deck.pptx',pptx)
        if not motion['ok']:raise ValueError('Animation preservation failed: '+'; '.join(motion['errors']))
        write(build_dir/'motion-preservation.json',motion)
        receipt['motion_preservation_sha256']=digest(build_dir/'motion-preservation.json')
    write(project/'completion.json',receipt);write(build_dir/'completion.json',receipt)
    return {'stage':'complete','receipt':receipt}


def qa_skeleton(project,build_dir,pptx_name='deck.pptx',render_dir='rendered',renderer=''):
    """Fill hashes and comparison sheets; only the agent can fill visual findings."""
    from check_pptx import inspect
    from compare_slides import compare
    project=Path(project);build_dir=Path(build_dir)
    if (build_dir/'visual-qa.json').exists():raise ValueError('visual-qa.json already exists; preserve its findings or use a new build')
    if not isinstance(renderer,str) or not renderer.strip():raise ValueError('Name the actual renderer')
    state=read(project/'workflow.json');pptx=inside(build_dir,pptx_name)
    reviews=read(project/'reference-review.json')
    scene=read(project/'scene.json')
    if not inspect(pptx,require_fade=True)['ok']:raise ValueError('PPTX structure must pass before visual QA')
    pages=[];pairs=[]
    for i,p in enumerate(state['pages'],1):
        relative=f'{render_dir}/{i:02}.png';path=inside(build_dir,relative)
        with Image.open(path) as image:image.verify()
        ref=p['reference']
        if digest(inside(build_dir,ref['file']))!=ref['sha256']:raise ValueError('Build reference does not match the current task')
        pages.append(dict(id=p['id'],rendered=relative,rendered_sha256=digest(path),reference_sha256=ref['sha256'],result='pending',findings=''))
        pair=dict(id=p['id'],reference=ref['file'],rendered=relative)
        observation=reviews.get(str(p['id']),{})
        if 'reference_crop' in observation:pair['reference_crop']=observation['reference_crop']
        if 'reference_frame' in observation:pair.update(reference_frame=observation['reference_frame'],canvas_size=scene.get('size',[960,540]))
        pairs.append(pair)
    pair_file=build_dir/'qa-pairs.json';write(pair_file,pairs)
    for i in range(1,1000):
        comparison=build_dir/f'qa-comparison-{i:02}'
        if not comparison.exists():break
    compare(pair_file,comparison)
    write(build_dir/'visual-qa.json',dict(pptx=pptx_name,pptx_sha256=digest(pptx),scene_sha256=digest(project/'scene.json'),renderer=renderer,pages=pages))
    return dict(stage='visual_review_pending',qa='visual-qa.json',comparison=str(comparison/'overview.jpg'),next='Actually inspect each comparison, fix issues, then fill result/findings and run finish; pending is never a pass')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('brief',type=Path);init.add_argument('--output-dir',type=Path,required=True)
    show=sub.add_parser('status');show.add_argument('project',type=Path)
    record=sub.add_parser('record-image');record.add_argument('project',type=Path);record.add_argument('--page',type=int,required=True);record.add_argument('--image',type=Path,required=True);record.add_argument('--style-reference',action='append',default=[])
    supplied=sub.add_parser('record-reference');supplied.add_argument('project',type=Path);supplied.add_argument('--page',type=int,required=True);supplied.add_argument('--image',type=Path,required=True)
    compile=sub.add_parser('compile');compile.add_argument('project',type=Path);compile.add_argument('--output-dir',type=Path,required=True)
    final=sub.add_parser('finish');final.add_argument('project',type=Path);final.add_argument('--build-dir',type=Path,required=True)
    qa=sub.add_parser('qa-skeleton');qa.add_argument('project',type=Path);qa.add_argument('--build-dir',type=Path,required=True);qa.add_argument('--pptx',default='deck.pptx');qa.add_argument('--render-dir',default='rendered');qa.add_argument('--renderer',required=True)
    args=parser.parse_args()
    try:
        if args.command=='init':result=initialize(read(args.brief),args.output_dir)
        elif args.command=='status':result=status(args.project)
        elif args.command=='record-image':result=record_image(args.project,args.page,args.image,style_references=args.style_reference)
        elif args.command=='record-reference':result=record_reference(args.project,args.page,args.image)
        elif args.command=='compile':result=compile_project(args.project,args.output_dir)
        elif args.command=='finish':result=finish(args.project,args.build_dir)
        else:result=qa_skeleton(args.project,args.build_dir,args.pptx,args.render_dir,args.renderer)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
