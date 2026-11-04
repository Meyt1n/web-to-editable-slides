"""Declared layout contracts and real export geometry; fixtures do not claim OCR."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image
from pptx import Presentation
import yaml

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from auto_deck import initialize,record_reference,status,write,digest
from check_reference_layout import check,raw_hash
from native_renderer import build
from test_automation import fixture


def mapped_fixture(root,*,photo=False):
    scene=fixture(root)
    regions=[dict(id='title',kind='text',bounds=[40/960,40/540,600/960,60/540],elementIds=['title'])]
    if photo:
        Image.new('RGB',(400,100),'green').save(root/'media/photo.png')
        scene['pages'][0]['elements'].append(dict(elementId='photo',elementType='image',bounds=[100,200,400,200],src='media/photo.png',fit=dict(mode='cover'),raster_reason='Synthetic image fixture'))
        regions.append(dict(id='photo',kind='image',bounds=[100/960,200/540,400/960,200/540],elementIds=['photo'],asset=dict(method='original',file='media/photo.png',sha256=raw_hash(root/'media/photo.png'))))
    review={'1':dict(reference_sha256=raw_hash(root/'references/one.png'),observations='Synthetic geometry fixture, not a visual assessment',regions=regions)}
    write(root/'scene.json',scene);write(root/'reference-review.json',review)
    return scene,review


class ReferenceLayoutTests(unittest.TestCase):
    def test_supplied_reference_is_preserved_without_imagegen_attestation_or_prompt_invalidation(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/'task'
            brief=dict(title='复刻',purpose='讲解',audience='同学',style='跟随参考',slides=[dict(id=1,title='第一页',key_points=['原文'],visual_prompt='保留参考布局')])
            initialize(brief,project)
            ref=root/'ref.png';Image.new('RGB',(160,90),'white').save(ref);original=ref.read_bytes()
            record_reference(project,1,ref);state=json.loads((project/'workflow.json').read_text('utf8'));entry=state['pages'][0]['reference']
            self.assertEqual(entry['tool'],'user_reference');self.assertNotIn('prompt_sha256',entry)
            self.assertEqual((project/entry['file']).read_bytes(),original)
            (project/'prompts/01.txt').write_text('Changed wording for the editable deck',encoding='utf8')
            self.assertEqual(status(project)['stage'],'visual_analysis')
            (project/entry['file']).write_bytes(b'changed source')
            self.assertEqual(status(project)['tasks'][0]['action'],'restore_selected_reference')

    def test_new_fidelity_tasks_request_regions_but_explicit_enhancement_does_not(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/'ref.png';Image.new('RGB',(160,90),'white').save(image)
            for mode in ['fidelity','enhance']:
                brief=dict(title='样例',purpose='阅读',audience='同学',style='浅色',design=dict(mode=mode),slides=[dict(id=1,title='一页',key_points=['原文'],visual_prompt='保持构图')])
                project=root/mode;initialize(brief,project);record_reference(project,1,image)
                ref=json.loads((project/'workflow.json').read_text('utf8'))['pages'][0]['reference']
                write(project/'reference-review.json',{'1':dict(reference_sha256=ref['sha256'],observations='Fixture')})
                result=status(project)
                self.assertEqual(result['tasks'][0]['action'],'map_reference_regions' if mode=='fidelity' else 'write_template_and_scene')

    def test_moved_region_wrong_object_type_and_unmapped_text_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);scene,review=mapped_fixture(root)
            self.assertTrue(check(root/'scene.json')['ok'])
            for mutate in [lambda s:s['pages'][0]['elements'][0]['bounds'].__setitem__(0,200),
                           lambda s:s['pages'][0]['elements'][0].__setitem__('elementType','image'),
                           lambda s:s['pages'][0]['elements'].append(dict(elementId='extra',elementType='text',bounds=[40,150,300,40],content=dict(text='Unexpected footer')))]:
                changed=copy.deepcopy(scene);mutate(changed);write(root/'scene.json',changed)
                self.assertFalse(check(root/'scene.json')['ok'])

    def test_real_export_detects_contain_gaps_and_cover_preserves_the_image_region(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();scene,review=mapped_fixture(src,photo=True)
            scene['pages'][0]['elements'][-1]['fit']['mode']='contain';write(src/'scene.json',scene)
            self.assertTrue(check(src/'scene.json')['ok'])
            contain=build(src/'scene.json',root/'contain');report=check(src/'scene.json',pptx=contain)
            self.assertFalse(report['ok']);self.assertTrue(any('pptx: photo position/size' in e for e in report['errors']))
            scene['pages'][0]['elements'][-1]['fit']['mode']='cover';write(src/'scene.json',scene)
            cover=build(src/'scene.json',root/'cover');self.assertTrue(check(src/'scene.json',pptx=cover)['ok'])

    def test_changed_image_asset_or_generation_prompt_invalidates_the_record(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);scene,review=mapped_fixture(root,photo=True)
            (root/'prompts').mkdir();prompt=root/'prompts/photo.txt';prompt.write_text('Synthetic prompt fixture; no imagegen call is asserted',encoding='utf8')
            asset=review['1']['regions'][-1]['asset'];asset.update(method='imagegen',prompt_file='prompts/photo.txt',prompt_sha256=digest(prompt));write(root/'reference-review.json',review)
            self.assertTrue(check(root/'scene.json')['ok'])
            prompt.write_text('changed',encoding='utf8');self.assertFalse(check(root/'scene.json')['ok'])
            asset['prompt_sha256']=digest(prompt);write(root/'reference-review.json',review)
            Image.new('RGB',(400,100),'blue').save(root/'media/photo.png');self.assertFalse(check(root/'scene.json')['ok'])

    def test_duplicate_region_targets_and_invalid_boxes_cannot_bypass_checks(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);scene,review=mapped_fixture(root)
            for bounds in [[0,0,float('nan'),1],[0.8,0,0.5,0.2],[0,0,0,1]]:
                changed=copy.deepcopy(review);changed['1']['regions'][0]['bounds']=bounds;write(root/'reference-review.json',changed)
                with self.assertRaises(ValueError):check(root/'scene.json')
            duplicate=copy.deepcopy(review['1']['regions'][0]);duplicate['id']='duplicate';review['1']['regions'].append(duplicate);write(root/'reference-review.json',review)
            with self.assertRaises(ValueError):check(root/'scene.json')

    def test_non_widescreen_reference_keeps_both_pptx_and_pptd_canvas(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();scene,review=mapped_fixture(src)
            scene['size']=[960,640]
            template=json.loads((src/'template/template.json').read_text('utf8'));template['canvas']=[960,640];write(src/'template/template.json',template)
            Image.new('RGB',(240,160),'ivory').save(src/'references/one.png')
            review['1']['reference_sha256']=raw_hash(src/'references/one.png');review['1']['regions'][0]['bounds']=[40/960,40/640,600/960,60/640]
            write(src/'scene.json',scene);write(src/'reference-review.json',review)
            deck=build(src/'scene.json',root/'build');self.assertTrue(check(src/'scene.json',pptx=deck)['ok'])
            prs=Presentation(deck);self.assertEqual([prs.slide_width.pt,prs.slide_height.pt],[960,640])
            manifest=yaml.safe_load(deck.with_suffix('.pptd').read_text('utf8'));self.assertEqual(manifest['size'],[960,640])

    def test_requested_widescreen_padding_maps_original_positions_without_stretching(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();scene,review=mapped_fixture(src)
            Image.new('RGB',(240,180),'ivory').save(src/'references/one.png')
            review['1'].update(reference_sha256=raw_hash(src/'references/one.png'),reference_frame=[0.125,0,0.75,1])
            scene['pages'][0]['elements'][0]['bounds']=[150,40,450,60]
            write(src/'scene.json',scene);write(src/'reference-review.json',review)
            deck=build(src/'scene.json',root/'build');self.assertTrue(check(src/'scene.json',pptx=deck)['ok'])

    def test_reference_crop_excludes_window_chrome_without_changing_the_original(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);scene,review=mapped_fixture(root)
            Image.new('RGB',(200,160),'ivory').save(root/'references/one.png');original=(root/'references/one.png').read_bytes()
            review['1'].update(reference_sha256=raw_hash(root/'references/one.png'),reference_crop=[0.1,0.25,0.8,0.5625])
            write(root/'reference-review.json',review)
            self.assertTrue(check(root/'scene.json')['ok'])
            self.assertEqual((root/'references/one.png').read_bytes(),original)


if __name__=='__main__':unittest.main()
