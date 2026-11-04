"""Observable workflow invalidation and repository-owned export behavior."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import subprocess
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from PIL import Image
from pptx import Presentation
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from auto_deck import initialize,record_image,status,compile_project,finish,write,digest,qa_skeleton
from native_renderer import build,validate,validate_chart_style
from check_pptx import inspect
from prepare_fonts import prepare
from doctor import diagnose


def fixture(root):
    (root/'template').mkdir();(root/'references').mkdir();(root/'media').mkdir()
    Image.new('RGB',(160,90),'ivory').save(root/'references/one.png')
    Image.new('RGB',(80,90),'green').save(root/'media/subject.png')
    write(root/'template/template.json',dict(schema_version='1.0',id='test',version='1',canvas=[960,540],
        palette=dict(primary='#112233'),resources=dict(fonts={'Noto Sans SC':{'system_font':True}}),
        typography=dict(body=dict(family='Noto Sans SC',size=22)),references=[dict(id='one',file='../references/one.png')],
        layouts=dict(content=dict(slots=dict(body=[40,40,880,460]))),components=dict(rule=dict(width=1))))
    # Template resources must be self-contained, including reference images.
    Image.new('RGB',(160,90),'ivory').save(root/'template/one.png')
    spec=json.loads((root/'template/template.json').read_text('utf8'));spec['references'][0]['file']='one.png';write(root/'template/template.json',spec)
    return dict(version=1,title='任意主题',size=[960,540],template_file='template/template.json',pages=[dict(id=1,layout='content',reference='references/one.png',background=dict(type='solid',color='#FFFFFF'),elements=[dict(elementId='title',elementType='text',bounds=[40,40,600,60],content=dict(text='可编辑正文 ABC',fontFamily='Noto Sans SC',fontSize=28,color='#112233'))],animations=[])])


class AutomationTests(unittest.TestCase):
    def test_preflight_selects_a_ready_interpreter_without_changing_the_project(self):
        result=diagnose(sys.executable)
        self.assertTrue(result['ready']);self.assertEqual(result['selected']['missing'],[])
        self.assertGreaterEqual(result['selected']['version'],[3,10])

    def test_codex_runtime_probe_failure_falls_back_to_active_workspace_venv(self):
        with TemporaryDirectory() as tmp:
            workspace=Path(tmp);venv=workspace/'.venv/Scripts/python.exe';venv.parent.mkdir(parents=True);venv.write_text('test fixture')
            bundled=workspace/'codex-python.exe';bundled.write_text('test fixture')
            def probe(args,**kwargs):
                executable=Path(args[0])
                if executable==bundled:raise subprocess.TimeoutExpired(args,20)
                return SimpleNamespace(returncode=0,stdout=json.dumps(dict(executable=str(executable),version=[3,12,0],missing=[])))
            with patch('doctor.subprocess.run',side_effect=probe):result=diagnose(bundled,workspace)
            self.assertTrue(result['ready']);self.assertEqual(Path(result['selected']['executable']),venv)
            self.assertEqual(result['candidates'][0]['reason'],'probe_timeout')

    def test_packaged_project_resumes_after_text_eol_normalization(self):
        import shutil
        with TemporaryDirectory() as tmp:
            project=Path(tmp)/'project';shutil.copytree(ROOT/'examples/auto-workshop/project',project,ignore=shutil.ignore_patterns('run-local.json','completion.json'))
            self.assertEqual(status(project)['stage'],'ready_to_compile')

    def test_prompt_revisions_invalidate_images_and_snapshots_survive(self):
        brief=dict(title='新主题',purpose='讲解',audience='组织者',style='浅纸',slides=[dict(id=1,title='开始',key_points=['第一步'],visual_prompt='横向流程')])
        with TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/'task';initialize(brief,project)
            image=root/'image.png';Image.new('RGB',(160,90),'white').save(image)
            record_image(project,1,image)
            state=json.loads((project/'workflow.json').read_text('utf8'));attempt=state['pages'][0]['reference']
            self.assertEqual(digest(project/attempt['prompt_file']),attempt['prompt_sha256'])
            snapshot=project/attempt['prompt_file'];snapshot.write_bytes(snapshot.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
            self.assertEqual(digest(snapshot),attempt['prompt_sha256'])
            self.assertEqual(status(project)['stage'],'visual_analysis')
            (project/'prompts/01.txt').write_text('revised prompt',encoding='utf8')
            self.assertEqual(status(project)['tasks'][0]['action'],'regenerate_changed_reference')
            record_image(project,1,image)
            state=json.loads((project/'workflow.json').read_text('utf8'))
            self.assertEqual(len(state['pages'][0]['attempts']),2)
            self.assertNotEqual(state['pages'][0]['attempts'][0]['prompt_file'],state['pages'][0]['attempts'][1]['prompt_file'])

    def test_native_path_table_and_scatter_remain_real_objects(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();scene=fixture(src);elements=scene['pages'][0]['elements']
            elements.append(dict(elementId='curve',elementType='shape',shapeName='custom',bounds=[40,110,300,30],viewBox=[300,30],path='M0 20 C80 0 180 30 300 10',fill=dict(type='none'),border=dict(color='#72896B',width=2)))
            elements.append(dict(elementId='table',elementType='table',bounds=[40,170,300,150],columnWidths=[.5,.5],rowHeights=[.5,.5],rows=[[dict(text='环节'),dict(text='时间')],[dict(text='讨论'),dict(text='10:00')]]))
            elements.append(dict(elementId='scatter',elementType='chart',bounds=[400,170,400,260],fontFamily='Noto Sans SC',data=dict(cols=['x','y'],rows=[[1,3],[2,4]]),series=[dict(type='scatter',encode=dict(x='x',y='y'))],dataSource=dict(status='demo',label='示意')))
            write(src/'scene.json',scene);deck=build(src/'scene.json',root/'build')
            result=inspect(deck,require_fade=True);self.assertTrue(result['ok'],result['errors']);self.assertEqual(result['slides'][0]['editable_table_cells'],4)
            with ZipFile(deck) as z:
                self.assertIn(b'cubicBezTo',z.read('ppt/slides/slide1.xml'))
                self.assertIn(b'scatterChart',z.read('ppt/charts/chart1.xml'))
            output=Presentation(deck)
            self.assertTrue(output.slides[0].shapes[2].has_table);self.assertTrue(output.slides[0].shapes[3].has_chart)
            self.assertFalse(output.slides[0].shapes[1].shadow.inherit)
            self.assertTrue((root/'build/template/one.png').is_file())

    def test_native_chart_retains_data_scales_point_colors_and_labels(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();scene=fixture(src)
            scene['pages'][0]['elements'].append(dict(elementId='groups',elementType='chart',bounds=[40,140,600,300],fontFamily='Noto Sans SC',legend=False,
                data=dict(cols=['国家','值'],rows=[['美国',7.2],['中国',12.05]]),series=[dict(type='bar',name='有效项目数',encode=dict(x='国家',y='值'),fill='#315ECC')],dataSource=dict(status='verified',label='test fixture'),
                style=dict(background='#FFFCF6',minimum=0,maximum=15,majorUnit=3,dataLabels=True,numberFormat='0.00',textColor='#24354B',gridColor='#B9CCD8',fontSize=13,pointColors=['#315ECC','#D9674D'])))
            write(src/'scene.json',scene);deck=build(src/'scene.json',root/'build')
            c=Presentation(deck).slides[0].shapes[1].chart
            self.assertEqual(list(c.series[0].values),[7.2,12.05])
            self.assertEqual((c.value_axis.minimum_scale,c.value_axis.maximum_scale,c.value_axis.major_unit),(0,15,3))
            self.assertTrue(c.plots[0].has_data_labels);self.assertEqual(c.plots[0].data_labels.number_format,'0.00')
            self.assertFalse(c.has_title)
            self.assertEqual(str(c.series[0].points[1].format.fill.fore_color.rgb),'D9674D')
            self.assertEqual(c.font.name,c.category_axis.tick_labels.font.name)
            for bad in [dict(minimum=15,maximum=0),dict(pointColors=['#315ECC']),dict(dataLabels='yes'),dict(unknown=True)]:
                with self.assertRaises(ValueError):validate_chart_style(dict(scene['pages'][0]['elements'][-1],style=bad))

    def test_unsupported_features_fail_before_creating_output(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();base=fixture(src)
            for i,change in enumerate([{'rotation':12},{'bounds':[950,40,600,60]},{'shadow':{}},{'elementType':'unknown'}]):
                scene=copy.deepcopy(base);scene['pages'][0]['elements'][0].update(change);write(src/'scene.json',scene)
                with self.assertRaises(ValueError):build(src/'scene.json',root/f'bad-{i}')
                self.assertFalse((root/f'bad-{i}').exists())

    def test_raster_boundary_is_required_and_reported(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();scene=fixture(src)
            image=dict(elementId='subject',elementType='image',bounds=[700,30,150,180],src='media/subject.png',fit=dict(mode='contain'))
            scene['pages'][0]['elements'].append(image)
            with self.assertRaisesRegex(ValueError,'raster_reason'):validate(scene,src)
            image['raster_reason']='复杂纹理，仅作为独立素材可移动';write(src/'scene.json',scene);build(src/'scene.json',root/'build')
            report=json.loads((root/'build/editability-report.json').read_text('utf8'))
            self.assertEqual(report[0]['native_objects'],1);self.assertEqual(report[0]['raster_objects'][0]['elementId'],'subject')
            self.assertEqual((root/'build/media/subject.png').read_bytes(),(src/'media/subject.png').read_bytes())

    def test_native_animation_click_groups_have_existing_targets(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();scene=fixture(src)
            scene['pages'][0]['animations']=[dict(elementId='title',effect='wipe-in',direction='right',trigger='onClick',durationMs=600)]
            write(src/'scene.json',scene);deck=build(src/'scene.json',root/'build')
            report=inspect(deck,require_fade=True);self.assertEqual(report['slides'][0]['animations']['triggers'],{'clickEffect':1})
            self.assertEqual(report['slides'][0]['animations']['missing_targets'],[])
            scene['pages'][0]['animations'][0]['elementId']='missing'
            with self.assertRaises(ValueError):validate(scene,src)

    def test_compile_requires_current_visual_review_and_finish_rejects_stale_qa(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/'task'
            initialize(dict(title='测试',purpose='阅读',audience='志愿者',style='浅色',slides=[dict(id=1,title='一页',key_points=['说明'],visual_prompt='原生表格')]),project)
            with self.assertRaises(ValueError):compile_project(project,root/'build')
            image=root/'ref.png';Image.new('RGB',(160,90),'white').save(image);record_image(project,1,image)
            scaffold=root/'scaffold';scaffold.mkdir();scene=fixture(scaffold)
            scene['pages'][0]['animations']=[dict(elementId='title',effect='fade-in',durationMs=200),
                dict(elementId='title',effect='pulse',trigger='afterPrevious',durationMs=600)]
            import shutil
            shutil.copytree(scaffold/'template',project/'template')
            state=json.loads((project/'workflow.json').read_text('utf8'));ref=state['pages'][0]['reference'];scene['pages'][0]['reference']=ref['file']
            write(project/'scene.json',scene);write(project/'reference-review.json',{'1':dict(reference_sha256=ref['sha256'],observations='实际测试用参考图，无内容，验证依赖状态',
                regions=[dict(id='title',kind='text',bounds=[40/960,40/540,600/960,60/540],elementIds=['title'])])})
            output=root/'build';compile_project(project,output)
            self.assertEqual(status(project)['stage'],'rendering')
            (output/'rendered').mkdir();Image.new('RGB',(160,90),'white').save(output/'rendered/01.png')
            qa_skeleton(project,output,renderer='unit fixture, not actual PowerPoint')
            self.assertEqual(json.loads((output/'visual-qa.json').read_text('utf8'))['pages'][0]['result'],'pending')
            with self.assertRaises(ValueError):finish(project,output)
            Image.new('RGB',(160,90),'white').save(output/'test-render.png')
            qa=dict(pptx='deck.pptx',pptx_sha256='stale',scene_sha256=digest(project/'scene.json'),renderer='unit fixture; not a visual quality assertion',pages=[dict(id=1,rendered='test-render.png',rendered_sha256=digest(output/'test-render.png'),reference_sha256=ref['sha256'],result='pass',findings='unit fixture')])
            write(output/'visual-qa.json',qa)
            with self.assertRaises(ValueError):finish(project,output)
            with ZipFile(output/'deck.pptx') as original,ZipFile(output/'edited.pptx','w') as edited:
                for item in original.infolist():
                    data=original.read(item.filename)
                    if item.filename=='ppt/slides/slide1.xml':
                        xml=ET.fromstring(data);xml.remove(xml.find('{http://schemas.openxmlformats.org/presentationml/2006/main}timing'))
                        data=ET.tostring(xml,encoding='utf-8')
                    edited.writestr(item,data)
            qa.update(pptx='edited.pptx',pptx_sha256=digest(output/'edited.pptx'));write(output/'visual-qa.json',qa)
            with self.assertRaisesRegex(ValueError,'Animation preservation failed'):finish(project,output)
            moved=Presentation(output/'deck.pptx');moved.slides[0].shapes[0].left+=914400;moved.save(output/'moved.pptx')
            qa.update(pptx='moved.pptx',pptx_sha256=digest(output/'moved.pptx'));write(output/'visual-qa.json',qa)
            with self.assertRaisesRegex(ValueError,'Final reference layout mismatch'):finish(project,output)
            qa.update(pptx='deck.pptx',pptx_sha256=digest(output/'deck.pptx'));write(output/'visual-qa.json',qa);finish(project,output)
            self.assertTrue(json.loads((output/'motion-preservation.json').read_text('utf8'))['ok'])
            self.assertTrue(json.loads((output/'reference-layout-report.json').read_text('utf8'))['ok'])
            self.assertEqual(status(project)['stage'],'complete')
            review=json.loads((project/'reference-review.json').read_text('utf8'));review['1']['observations']='Changed layout observations';write(project/'reference-review.json',review)
            self.assertEqual(status(project)['stage'],'ready_to_compile')
            with self.assertRaisesRegex(ValueError,'older reference layout review'):finish(project,output)
            scene['title']='changed';write(project/'scene.json',scene);self.assertEqual(status(project)['stage'],'ready_to_compile')

    def test_font_preparation_keeps_supported_word_spacing(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'fonts';report=prepare([dict(family='Barlow Condensed',text='A B')],root)
            with TTFont(root/report['fonts'][0]['file']) as font:self.assertIn(32,font.getBestCmap())


if __name__=='__main__':unittest.main()
