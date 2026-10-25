"""Behavioral checks for handoff validation, image inventory and PPTX structure."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import json
import sys
import unittest
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_demo import build
from check_pptx import inspect, font_info, NS
from inventory_images import inventory
from make_handoff import render, validate


class HandoffTests(unittest.TestCase):
    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate({'project':'Example','slides':[{'id':1,'title':'A'},{'id':1,'title':'B'}]})

    def test_status_and_permission_are_typed(self):
        for value in [dict(status='finished-maybe'),dict(imagegen_allowed='yes')]:
            brief={'project':'Example','slides':[{'id':1,'title':'A'}]}
            if 'status' in value:
                brief['slides'][0].update(value)
            else:
                brief.update(value)
            with self.assertRaises(ValueError):
                validate(brief)

    def test_ordering_and_fact_state_survive_render(self):
        text=render({'project':'Example','slides':[{'id':9,'title':'Later','status':'planned'},
                                                  {'id':2,'title':'Earlier','status':'concept'}]})
        self.assertLess(text.index('02 Earlier'),text.index('09 Later'))
        self.assertIn('planned',text)
        self.assertIn('concept',text)


class InventoryTests(unittest.TestCase):
    def test_alpha_relative_paths_and_output_exclusion(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);Image.new('RGBA',(20,10),(0,180,90,0)).save(root/'a.png')
            result=inventory(root,root/'output',2)
            self.assertEqual(len(result['images']),1)
            self.assertEqual(result['images'][0]['file'],'a.png')
            self.assertTrue(result['images'][0]['has_transparency'])
            again=inventory(root,root/'output',2)
            self.assertEqual(len(again['images']),1)
            self.assertTrue((root/'output'/'contact-sheet.jpg').is_file())


class PptxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.pptx=build(cls.root/'demo')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_demo_has_native_text_fades_and_self_contained_sources(self):
        result=inspect(self.pptx,require_fade=True)
        self.assertTrue(result['ok'],result['errors'])
        self.assertEqual(len(result['slides']),3)
        self.assertTrue(all(s['editable_text_boxes']>=5 for s in result['slides']))
        import yaml
        manifest=yaml.safe_load((self.pptx.parent/'green-sprout.pptd').read_text('utf-8'))
        for page in manifest['pages']:
            data=yaml.safe_load((self.pptx.parent/page).read_text('utf-8'))
            for element in data['elements']:
                if element['elementType']=='image':
                    self.assertTrue((self.pptx.parent/element['src']).is_file())

    def test_nested_transition_is_rejected(self):
        output=self.root/'bad-fade.pptx'
        with ZipFile(self.pptx) as source,ZipFile(output,'w',ZIP_DEFLATED) as target:
            for name in source.namelist():
                data=source.read(name)
                if name=='ppt/slides/slide1.xml':
                    root=ET.fromstring(data);transition=root.find('p:transition',NS)
                    root.remove(transition);root.find('p:cSld',NS).append(transition)
                    data=ET.tostring(root)
                target.writestr(name,data)
        result=inspect(output,require_fade=True)
        self.assertFalse(result['ok'])
        self.assertTrue(any('transition' in e for e in result['errors']))

    def test_missing_image_target_is_rejected(self):
        output=self.root/'missing-image.pptx'
        with ZipFile(self.pptx) as source,ZipFile(output,'w',ZIP_DEFLATED) as target:
            removed=False
            for name in source.namelist():
                if name.startswith('ppt/media/') and not removed:
                    removed=True;continue
                target.writestr(name,source.read(name))
        result=inspect(output)
        self.assertFalse(result['ok'])
        self.assertTrue(any('Missing relationship target' in e for e in result['errors']))

    def test_html_is_not_a_font_and_absent_fonts_fail_when_required(self):
        self.assertFalse(font_info('font.fntdata',b'<html>404</html>')['recognized_header'])
        self.assertFalse(inspect(self.pptx,require_fonts=True)['ok'])


if __name__=='__main__':
    unittest.main()
