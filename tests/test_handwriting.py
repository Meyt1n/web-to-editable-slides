"""Check ordered writing cues against exported timing, without private deck assets."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pptx import Presentation
from pptx.util import Pt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from motion_presets import handwriting_groups
from native_renderer import add_timing
from inspect_design import timing_groups
from check_pptx import NS,animation_summary


class HandwritingTests(unittest.TestCase):
    def test_words_and_strokes_share_a_click_but_keep_exact_order_and_pauses(self):
        cues=handwriting_groups([
            [dict(elementId='word',text='Example',durationMs=200,gapAfterMs=40),
             dict(elementId='shaft',direction='left',durationMs=300,gapAfterMs=0),
             dict(elementId='arrowhead',direction='down',durationMs=100)],
            [dict(elementId='conclusion',text='Conclusion',durationMs=250)]])
        prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6]);ids={}
        for i,name in enumerate(['word','shaft','arrowhead','conclusion']):
            shape=slide.shapes.add_textbox(Pt(30),Pt(30+i*40),Pt(300),Pt(30));shape.name=name;shape.text=name;ids[name]=shape.shape_id
        add_timing(slide,cues,ids)
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.pptx';prs.save(path)
            with ZipFile(path) as z:root=ET.fromstring(z.read('ppt/slides/slide1.xml'))
        groups=timing_groups(root)
        self.assertEqual([g['trigger'] for g in groups],['onClick','onClick'])
        self.assertEqual([e['target_name'] for e in groups[0]['effects']],['word','shaft','arrowhead'])
        self.assertEqual([e['start_ms'] for e in groups[0]['effects']],[0,240,540])
        self.assertEqual(groups[0]['duration_ms_estimate'],640)
        self.assertEqual(groups[1]['effects'][0]['start_ms'],0)
        self.assertEqual(groups[0]['effects'][-1]['filter'],'wipe(down)')
        self.assertEqual(animation_summary(root)['missing_targets'],[])

    def test_autoplay_has_a_group_pause_and_word_length_only_guides_timing(self):
        cues=handwriting_groups([[dict(elementId='short',text='a'),dict(elementId='long',text='exploration')],[dict(elementId='last')]],autoplay=True)
        self.assertTrue(all(cue['trigger']=='afterPrevious' for cue in cues))
        self.assertLess(cues[0]['durationMs'],cues[1]['durationMs'])
        self.assertEqual(cues[2]['delayMs'],450)
        self.assertTrue(all(0<cue['durationMs']<=380 for cue in cues))

    def test_invalid_units_do_not_produce_an_animation_plan(self):
        for groups in [[],[[]],[[dict(elementId='a'),dict(elementId='a')]],[[dict(elementId='')]],
                       [[dict(elementId='a',durationMs=0)]],[[dict(elementId='a',gapAfterMs=-1)]],
                       [[dict(elementId='a',direction='diagonal')]],[[dict(elementId='a',unknown=1)]]]:
            with self.subTest(groups=groups):
                with self.assertRaises(ValueError):handwriting_groups(groups)

    def test_event_based_offsets_are_left_unresolved(self):
        p='{'+NS['p']+'}';root=ET.Element(p+'sld');timing=ET.SubElement(root,p+'timing')
        main=ET.SubElement(ET.SubElement(timing,p+'tnLst'),p+'cTn',nodeType='mainSeq')
        group=ET.SubElement(ET.SubElement(main,p+'childTnLst'),p+'par')
        clock=ET.SubElement(group,p+'cTn');ET.SubElement(ET.SubElement(clock,p+'stCondLst'),p+'cond',delay='0')
        leaf=ET.SubElement(ET.SubElement(clock,p+'childTnLst'),p+'cTn')
        ET.SubElement(ET.SubElement(leaf,p+'stCondLst'),p+'cond',evt='onEnd',delay='0')
        effect=ET.SubElement(ET.SubElement(leaf,p+'childTnLst'),p+'animEffect',filter='wipe(left)')
        ET.SubElement(ET.SubElement(effect,p+'cBhvr'),p+'cTn',dur='200')
        report=timing_groups(root)[0]
        self.assertIsNone(report['effects'][0]['start_ms']);self.assertIsNone(report['duration_ms_estimate'])


if __name__=='__main__':unittest.main()
