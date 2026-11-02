"""Font preparation, background layers and exported animation target integrity."""
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
import importlib.util
import sys
import unittest

from fontTools.ttLib import TTFont
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_fonts import prepare
from backgrounds import background,RECIPES,copy_asset,ASSET_ROOT
from motion_presets import reveal_groups,question_answer,title_entrance
import hashlib
import json
from check_pptx import NS,animation_summary


class ArtDirectionTests(unittest.TestCase):
    def test_variable_body_font_is_static_and_contains_assigned_characters(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/'fonts'
            report=prepare([{'family':'Noto Sans SC','text':'正文清晰ABC123','weight':400}],folder)
            item=report['fonts'][0]
            with TTFont(folder/item['file']) as font:
                self.assertNotIn('fvar',font)
                self.assertEqual(font['OS/2'].usWeightClass,400)
                self.assertTrue(all(ord(c) in font.getBestCmap() for c in '正文清晰ABC123'))
            self.assertTrue((folder/item['license_file']).is_file())

    def test_missing_characters_do_not_silently_fallback(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/'fonts'
            with self.assertRaisesRegex(ValueError,'missing assigned glyphs'):
                prepare([{'family':'Barlow Condensed','text':'中文'}],folder)
            self.assertFalse(folder.exists())

    def test_malformed_family_is_a_validation_error(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):prepare([{'family':[],'text':'A'}],Path(tmp)/'fonts')

    def test_background_layers_fit_canvas_and_watermark_stays_subdued(self):
        for name in RECIPES:
            data=background(name)
            ids=[]
            for e in data['elements']:
                ids.append(e['elementId']);x,y,w,h=e['bounds']
                self.assertGreaterEqual(min(x,y,w,h),0)
                self.assertLessEqual(x+w,960);self.assertLessEqual(y+h,540)
                if e['elementId']=='bg-watermark':self.assertLessEqual(e['opacity'],.08)
            self.assertEqual(len(ids),len(set(ids)))
        painted=background('ink-culture',atmosphere='media/background.png')
        self.assertEqual(painted['elements'][0]['src'],'media/background.png')

    def test_animation_reports_trigger_and_missing_shape_targets(self):
        p='{'+NS['p']+'}'
        root=ET.Element(p+'sld');ET.SubElement(root,p+'cNvPr',id='3')
        timing=ET.SubElement(root,p+'timing')
        node=ET.SubElement(timing,p+'cTn',nodeType='clickEffect')
        effect=ET.SubElement(node,p+'animEffect',filter='wipe(right)')
        behavior=ET.SubElement(effect,p+'cBhvr');ET.SubElement(behavior,p+'cTn',dur='600')
        target=ET.SubElement(behavior,p+'spTgt',spid='3')
        data=animation_summary(root)
        self.assertEqual(data['missing_targets'],[])
        self.assertEqual(data['triggers'],{'clickEffect':1})
        self.assertEqual(data['duration_ms'],[600])
        target.set('spid','999')
        self.assertEqual(animation_summary(root)['missing_targets'],['999'])

    def test_style_lab_is_self_contained_and_animates_foreground_only(self):
        spec=importlib.util.spec_from_file_location('style_lab_build',ROOT/'examples/style-lab/build.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/'demo';module.build(folder)
            manifest=yaml.safe_load((folder/'style-lab.pptd').read_text('utf8'))
            self.assertEqual(len(manifest['pages']),5)
            for rel in manifest['pages']:
                page=yaml.safe_load((folder/rel).read_text('utf8'));ids={e['elementId'] for e in page['elements']}
                for animation in page['animations']:
                    self.assertIn(animation['elementId'],ids)
                    self.assertTrue(animation['elementId'].startswith('fg-'))
                for element in page['elements']:
                    if element['elementType']=='image':self.assertTrue((folder/element['src']).is_file())

    def test_catalog_backgrounds_keep_provenance_and_do_not_replace_dependencies(self):
        catalog=json.loads((ASSET_ROOT/'catalog.json').read_text('utf8'))
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/'media'
            for item in catalog['assets']:
                packed=copy_asset(item['id'],folder)
                self.assertEqual(hashlib.sha256((folder/item['file']).read_bytes()).hexdigest(),item['sha256'])
                self.assertTrue((folder/item['prompt_file']).is_file())
                x,y,w,h=packed['safe_zone'];self.assertLessEqual(x+w,960);self.assertLessEqual(y+h,540)
                data=background(item['recipe'],atmosphere='media/'+item['file'])
                self.assertEqual(data['elements'][0]['elementType'],'image')
            (folder/'warm-paper.png').write_bytes(b'unrelated user file')
            with self.assertRaisesRegex(ValueError,'Refusing to replace'):copy_asset('warm-paper',folder)
            self.assertEqual((folder/'warm-paper.png').read_bytes(),b'unrelated user file')

    def test_question_answer_waits_for_two_separate_clicks(self):
        animations=question_answer(['question','hint'],['answer','reason'])
        self.assertEqual([a['elementId'] for a in animations if a['trigger']=='onClick'],['question','answer'])
        self.assertEqual([a['trigger'] for a in animations],['onClick','withPrevious','onClick','withPrevious'])
        self.assertTrue(all(a['durationMs']>0 for a in animations))
        self.assertTrue(all(a['trigger']!='onClick' for a in reveal_groups([['one'],['two']],autoplay=True)))
        self.assertEqual(title_entrance('title')[0]['direction'],'down')
        for bad in [[],[['a'],[]],[['a'],['a']],[['']]]:
            with self.assertRaises(ValueError):reveal_groups(bad)


if __name__=='__main__':unittest.main()
