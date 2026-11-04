"""Regression checks for offline font embedding and traceable visual comparisons."""
import json
from pathlib import Path
import sys
import importlib.util
import shutil
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_slides import compare
from render_pptd import font_payload
from template_pack import prepare,load_template
from review_design_plan import review


class ProductionToolsTests(unittest.TestCase):
    def test_reading_room_sources_build_from_packaged_inputs_offline(self):
        import yaml
        example=ROOT/'examples/reading-room'
        spec=importlib.util.spec_from_file_location('reading_room_example',example/'build.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/'project';shutil.copytree(example/'input',folder)
            prepare(example/'observations.json',folder,folder/'template')
            module.build(folder)
            plan=json.loads((folder/'design-plan.json').read_text('utf8'))
            self.assertTrue(review(plan,load_template(folder/'template/template.json'),True)['ok'])
            manifest=yaml.safe_load((folder/'reading-room.pptd').read_text('utf8'))
            self.assertEqual(len(manifest['pages']),5)
            counts={'table':0,'image':0}
            for relative in manifest['pages']:
                page=yaml.safe_load((folder/relative).read_text('utf8'))
                for element in page['elements']:
                    x,y,w,h=element['bounds']
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,960.1);self.assertLessEqual(y+h,540.1)
                    if element['elementType'] in counts:counts[element['elementType']]+=1
                    if element['elementType']=='image':
                        self.assertEqual(element['src'],'media/reading-room.png')
                        self.assertTrue((folder/element['src']).is_file())
            self.assertEqual(counts,{'table':1,'image':2})

    def test_packaged_font_map_is_relative_and_carries_actual_bytes(self):
        import base64
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'font.ttf').write_bytes(b'font fixture')
            path=folder/'fonts.json';path.write_text(json.dumps({'Example':'font.ttf'}),encoding='utf8')
            payload=font_payload(path)
            self.assertEqual(payload[0]['family'],'Example')
            self.assertEqual(base64.b64decode(payload[0]['base64']),b'font fixture')
            self.assertEqual(payload[0]['format'],'truetype')
            (folder/'font.ttf').write_bytes(b'OTTO fixture')
            self.assertEqual(font_payload(path)[0]['format'],'opentype')

    def test_invalid_font_map_reports_an_error(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'fonts.json'
            for value in [[],{}, {'Example':42}]:
                path.write_text(json.dumps(value),encoding='utf8')
                with self.assertRaises(ValueError):font_payload(path)

    def test_comparison_preserves_input_and_reports_ratio_mismatch(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            Image.new('RGB',(160,90),'red').save(folder/'reference.png')
            Image.new('RGB',(120,90),'blue').save(folder/'render.png')
            source=(folder/'reference.png').read_bytes()
            pairs=folder/'pairs.json'
            pairs.write_text(json.dumps([{'id':2,'reference':'reference.png','rendered':'render.png'}]),encoding='utf8')
            report=compare(pairs,folder/'review',320)
            self.assertTrue(report['pairs'][0]['aspect_ratio_mismatch'])
            self.assertEqual((folder/'reference.png').read_bytes(),source)
            self.assertTrue((folder/'review/02-comparison.png').is_file())
            self.assertEqual(len(report['pairs'][0]['reference_sha256']),64)

    def test_missing_pair_does_not_write_a_partial_review(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);pairs=folder/'pairs.json'
            pairs.write_text(json.dumps([{'id':1,'reference':'missing.png','rendered':'missing.png'}]),encoding='utf8')
            with self.assertRaises(OSError):compare(pairs,folder/'review')
            self.assertFalse((folder/'review').exists())

    def test_comparison_uses_the_reference_canvas_instead_of_forcing_widescreen(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            Image.new('RGB',(160,120),'white').save(folder/'reference.png')
            Image.new('RGB',(320,240),'blue').save(folder/'render.png')
            pairs=folder/'pairs.json';pairs.write_text(json.dumps([dict(id=1,reference='reference.png',rendered='render.png')]),encoding='utf8')
            compare(pairs,folder/'review',320)
            with Image.open(folder/'review/01-comparison.png') as image:self.assertEqual(image.size,(664,280))

    def test_comparison_applies_the_declared_crop_and_page_frame_without_editing_source(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);reference=Image.new('RGB',(80,80),'black');reference.paste('blue',(0,10,80,70));reference.save(folder/'ref.png')
            original=(folder/'ref.png').read_bytes();Image.new('RGB',(320,180),'blue').save(folder/'render.png')
            pairs=folder/'pairs.json';pairs.write_text(json.dumps([dict(id=1,reference='ref.png',rendered='render.png',reference_crop=[0,0.125,1,0.75],reference_frame=[0.125,0,0.75,1],canvas_size=[320,180])]),encoding='utf8')
            result=compare(pairs,folder/'review',320)
            self.assertFalse(result['pairs'][0]['aspect_ratio_mismatch'])
            self.assertEqual(result['pairs'][0]['original_reference_size'],[80,80])
            with Image.open(folder/'review/01-comparison.png') as image:
                self.assertEqual(image.getpixel((0,50)),(211,214,206))
                self.assertEqual(image.getpixel((50,50)),(0,0,255))
            self.assertEqual((folder/'ref.png').read_bytes(),original)


if __name__=='__main__':unittest.main()
