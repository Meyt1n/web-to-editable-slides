"""Reference-derived template packaging and actual downstream parameter inheritance."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import copy
import json
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from template_pack import prepare,load_template,validate_template
from build_demo import build
from check_pptx import NS
from make_handoff import render
from review_design_plan import review


class TemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.path=prepare(ROOT/'examples/template-extraction/observations.json',ROOT,cls.root/'template')
        cls.template=load_template(cls.path)
        cls.brief=json.loads((ROOT/'examples/green-sprout/brief.json').read_text('utf8'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pack_is_self_contained_and_not_marked_visually_approved(self):
        self.assertEqual(self.template['status'],'prepared')
        self.assertTrue((self.path.parent/'TEMPLATE.md').is_file())
        self.assertTrue(all((self.path.parent/r['file']).is_file() for r in self.template['references']))
        for resource in self.template['resources']['fonts'].values():
            self.assertTrue((self.path.parent/resource['file']).is_file())
            self.assertTrue((self.path.parent/resource['license_file']).is_file())

    def test_out_of_scope_source_is_rejected_before_copying(self):
        data=copy.deepcopy(self.template);data['references'][0]['file']='../outside.png'
        path=self.root/'outside-observation.json';path.write_text(json.dumps(data),encoding='utf8')
        output=self.root/'bad-pack'
        with self.assertRaisesRegex(ValueError,'escapes'):
            prepare(path,self.path.parent,output)
        self.assertFalse(output.exists())

    def test_overflowing_template_slot_is_rejected(self):
        data=copy.deepcopy(self.template);data['layouts']['hero-split']['slots']['title']=[950,0,200,80]
        with self.assertRaisesRegex(ValueError,'outside'):
            validate_template(data)

    def test_production_requires_loaded_template_and_matching_binding(self):
        self.assertFalse(review({'project':'No template','slides':[{'id':1,'title':'A'}]},require_template=True)['ok'])
        wrong=copy.deepcopy(self.brief);wrong['design']['template']['version']='different'
        self.assertFalse(review(wrong,self.template,True)['ok'])
        self.assertTrue(review(self.brief,self.template,True)['ok'])

    def test_font_palette_and_unlisted_layout_drift_are_caught(self):
        cases=[]
        changed=copy.deepcopy(self.brief);changed['style']['colors'][0]='#1010AB';cases.append(changed)
        changed=copy.deepcopy(self.brief);changed['design']['font_profiles']['from-template']['body']='Unrelated Font';cases.append(changed)
        changed=copy.deepcopy(self.brief);changed['slides'][0]['layout']='unlisted';cases.append(changed)
        for brief in cases:
            self.assertFalse(review(brief,self.template,True)['ok'])

    def test_documented_layout_extension_is_explicit_and_reported(self):
        brief=copy.deepcopy(self.brief);brief['slides'][0]['layout']='custom-evidence'
        brief['slides'][0]['template_override']={'reason':'Use the common grid for a new evidence layout'}
        result=review(brief,self.template,True)
        self.assertTrue(result['ok']);self.assertTrue(any(s['code']=='template-override' for s in result['suggestions']))

    def test_handoff_includes_template_identity_and_source(self):
        text=render(self.brief)
        self.assertIn(self.template['id'],text);self.assertIn(self.template['version'],text)
        self.assertIn('template/template.json',text)

    def test_generated_pptx_reads_changed_color_geometry_and_type_size(self):
        source=self.root/'custom-template';shutil.copytree(self.path.parent,source)
        data=copy.deepcopy(self.template);data['version']='1.1.0';data['palette']['accent']='#7060AF'
        data['typography']['display']['size']=68
        data['layouts']['hero-split']['slots']['title'][0]=70
        custom=source/'custom.json';custom.write_text(json.dumps(data),encoding='utf8')
        pptx=build(self.root/'custom-deck',template=custom)
        with ZipFile(pptx) as archive:
            root=ET.fromstring(archive.read('ppt/slides/slide1.xml'))
            shape=next(s for s in root.findall('.//p:sp',NS) if ''.join(n.text or '' for n in s.findall('.//a:t',NS))=='绿芽')
            self.assertEqual(shape.find('p:spPr/a:xfrm/a:off',NS).get('x'),str(70*12700))
            self.assertEqual(shape.find('.//a:rPr',NS).get('sz'),'6800')
            colors={e.get('val') for e in root.findall('.//a:srgbClr',NS)}
            self.assertIn('7060AF',colors);self.assertNotIn('FF816B',colors)
        snapshot=load_template(pptx.parent/'template/template.json')
        self.assertEqual(snapshot['version'],'1.1.0')
        plan=json.loads((pptx.parent/'design-plan.json').read_text('utf8'))
        self.assertTrue(review(plan,snapshot,True)['ok'])


if __name__=='__main__':
    unittest.main()
