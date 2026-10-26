"""Design intent checks and native multi-font gallery behavior."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hashlib
import json
import sys
import unittest

import yaml
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_gallery import build, PROFILES, FONT, SERIF, PLAY, NUMERIC
from check_pptx import inspect, NS
from make_handoff import render, validate
from review_design_plan import review


class DesignPlanTests(unittest.TestCase):
    def repeated(self,mode):
        return {'project':'Test','design':{'mode':mode},'slides':[
            {'id':i,'title':f'Slide {i}','layout':'cards'} for i in range(1,5)]}

    def test_enhancement_suggests_review_of_repetition(self):
        report=review(self.repeated('enhance'))
        self.assertTrue(report['ok'])
        warnings=[w for w in report['suggestions'] if w['code']=='repeated-layout']
        self.assertEqual(warnings[0]['pages'],[1,2,3,4])

    def test_faithful_copy_does_not_demand_layout_changes(self):
        report=review(self.repeated('fidelity'))
        self.assertFalse(any(w['code']=='repeated-layout' for w in report['suggestions']))

    def test_undefined_profile_is_a_structural_error(self):
        brief=self.repeated('enhance');brief['slides'][0]['font_profile']='absent'
        self.assertFalse(review(brief)['ok'])

    def test_data_visualization_requires_a_source_or_illustration_label(self):
        brief={'project':'Test','slides':[{'id':1,'title':'Data','layout':'data-focus'}]}
        self.assertTrue(any(w['code']=='missing-data-source' for w in review(brief)['suggestions']))
        brief['slides'][0]['data_is_illustrative']=True
        self.assertFalse(any(w['code']=='missing-data-source' for w in review(brief)['suggestions']))

    def test_font_and_layout_intent_survive_handoff(self):
        brief={'project':'Test','design':{'mode':'enhance','font_profiles':PROFILES},
               'slides':[{'id':1,'title':'Cover','layout':'hero-split','font_profile':'editorial',
                          'density':'low','focal_point':'Product'}]}
        text=render(brief)
        for expected in [SERIF,'hero-split','editorial','Product','enhance']:
            self.assertIn(expected,text)

    def test_per_page_reference_prompt_and_constraints_survive_handoff(self):
        brief={'project':'Test','slides':[{'id':1,'title':'Process',
               'reference':'references/02.png','reference_prompt':'prompts.md: Process; equivalent reconstruction',
               'layout_constraints':['Left subject, four columns on right','Preserve left-to-right arrows'],
               'typography_constraints':['Heavy green heading, two text levels'],
               'image_plan':['media/plant.png -> imagegen background cleanup; preserve sensor shape']}]}
        result=render(brief)
        for field in ['reference_prompt','layout_constraints','typography_constraints','image_plan']:
            values=brief['slides'][0][field]
            for value in values if isinstance(values,list) else [values]:
                self.assertIn(value,result)
        self.assertLess(result.index('references/02.png'),result.index('Left subject'))

    def test_reference_constraints_reject_ambiguous_field_types(self):
        for field,value in [('reference_prompt',{}),('layout_constraints','three columns'),
                            ('typography_constraints',[23]),('image_plan',{'image':'unknown'})]:
            brief={'project':'Test','slides':[{'id':1,'title':'A',field:value}]}
            with self.assertRaises(ValueError):validate(brief)


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.folder=Path(cls.temp.name)/'gallery'
        cls.pptx=build(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_eight_native_layouts_and_four_declared_font_families(self):
        report=inspect(self.pptx,require_fade=True)
        self.assertTrue(report['ok'],report['errors'])
        self.assertEqual(len(report['slides']),8)
        self.assertTrue(all(s['editable_text_boxes']>=3 for s in report['slides']))
        fonts=set()
        with ZipFile(self.pptx) as archive:
            for page in report['slides']:
                root=ET.fromstring(archive.read(page['part']))
                fonts.update(n.get('typeface') for n in root.findall('.//a:rPr/a:latin',NS))
        self.assertEqual(fonts,{FONT,SERIF,PLAY,NUMERIC})
        plan=json.loads((self.folder/'design-plan.json').read_text('utf8'))
        self.assertEqual(len({s['layout'] for s in plan['slides']}),8)
        self.assertFalse(review(plan)['suggestions'])

    def test_actual_glyphs_and_element_bounds(self):
        manifest=yaml.safe_load((self.folder/'design-gallery.pptd').read_text('utf8'))
        cmaps={}
        for p in (self.folder/'media/fonts').glob('*.ttf'):
            font=TTFont(p);cmaps[font['name'].getDebugName(1)]=font.getBestCmap()
        self.assertNotIn(ord('中'),cmaps[NUMERIC])
        for rel in manifest['pages']:
            page=yaml.safe_load((self.folder/rel).read_text('utf8'))
            for e in page['elements']:
                x,y,w,h=e['bounds']
                self.assertGreaterEqual(min(x,y,w,h),0)
                self.assertLessEqual(x+w,960.2);self.assertLessEqual(y+h,540.2)
                if e['elementType']=='text':
                    content=e['content'];cmap=cmaps[content['fontFamily']]
                    self.assertTrue(all(c.isspace() or ord(c) in cmap for c in content['text']))

    def test_bundled_font_sources_match_recorded_hashes_and_licenses(self):
        folder=ROOT/'assets/fonts'
        for item in json.loads((folder/'catalog.json').read_text('utf8'))['fonts']:
            self.assertEqual(hashlib.sha256((folder/item['file']).read_bytes()).hexdigest(),item['sha256'])
            self.assertIn('SIL OPEN FONT LICENSE',(folder/item['license_file']).read_text('utf8'))


if __name__=='__main__':
    unittest.main()
