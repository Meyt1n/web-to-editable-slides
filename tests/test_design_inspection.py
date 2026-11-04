"""Reference inspection must expose raster text and recurring paper without OCR claims."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from PIL import Image
from pptx import Presentation
from pptx.util import Pt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from inspect_design import analyze


class DesignInspectionTests(unittest.TestCase):
    def test_image_word_candidate_and_shared_resource_do_not_imply_editable_text_or_fixed_bounds(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp);image=folder/'fixture.png';Image.new('RGB',(16,9),'white').save(image)
            prs=Presentation();prs.slide_width=Pt(960);prs.slide_height=Pt(540)
            for i in range(3):
                slide=prs.slides.add_slide(prs.slide_layouts[6])
                paper=slide.shapes.add_picture(str(image),Pt(1 if i==2 else 0),Pt(0),Pt(960),Pt(540));paper.name='shared-paper'
                if not i:
                    word=slide.shapes.add_picture(str(image),Pt(30),Pt(30),Pt(50),Pt(20));word.name='sample_w00'
            path=folder/'input.pptx';prs.save(path)
            # Absolute and relative OPC targets can refer to the same paper resource.
            with ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
            name='ppt/slides/_rels/slide2.xml.rels';rels=ET.fromstring(parts[name])
            for rel in rels:
                if rel.get('Type','').endswith('/image'):rel.set('Target','/ppt/media/image1.png')
            parts[name]=ET.tostring(rels)
            with ZipFile(path,'w') as z:
                for n,data in parts.items():z.writestr(n,data)
            before=path.read_bytes();report=analyze(path)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(report['canvas_points'],[960,540])
            self.assertEqual(report['slides'][0]['word_image_name_candidates'],1)
            self.assertTrue(all(page['native_text_boxes']==0 for page in report['slides']))
            shared=report['recurring_background_candidates'][0]
            self.assertEqual(shared['slides'],[1,2,3]);self.assertTrue(shared['same_resource']);self.assertFalse(shared['same_bounds'])
            self.assertIn('not OCR',report['image_text_scope'])


if __name__=='__main__':unittest.main()
