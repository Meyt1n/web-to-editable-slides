"""Native lifecycle, timing and geometry checks, independent of slide appearance."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pptx import Presentation
from pptx.util import Pt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_motion import add_timing,animation_plan
from inspect_design import timing_groups
from check_pptx import NS,animation_summary
from check_motion import compare_motion
from motion_presets import (staggered_reveal,process_flow,compare_then_decide,
                            evidence_reveal,focus_pulse,replace_state)


def exported(cues,names,save_to=None):
    prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6]);ids={}
    for index,name in enumerate(names):
        shape=slide.shapes.add_textbox(Pt(40),Pt(40+40*index),Pt(400),Pt(35))
        shape.name=name;shape.text=name;ids[name]=shape.shape_id
    add_timing(slide,cues,ids)
    with TemporaryDirectory() as tmp:
        path=Path(tmp)/'motion.pptx';prs.save(path)
        if save_to is not None:Path(save_to).write_bytes(path.read_bytes())
        with ZipFile(path) as z:return ET.fromstring(z.read('ppt/slides/slide1.xml'))


class NativeMotionTests(unittest.TestCase):
    def test_one_editable_target_can_enter_pulse_exit_and_reenter(self):
        cues=[dict(elementId='same',effect='fade-in',trigger='onClick',durationMs=200),
              dict(elementId='same',effect='pulse',trigger='afterPrevious',durationMs=600,delayMs=50),
              dict(elementId='same',effect='fade-out',trigger='afterPrevious',durationMs=300,delayMs=40),
              dict(elementId='same',effect='zoom-in',trigger='afterPrevious',durationMs=400,delayMs=100)]
        root=exported(cues,['same']);groups=timing_groups(root);effects=groups[0]['effects']
        self.assertEqual([e['preset_class'] for e in effects],['entr','emph','exit','entr'])
        self.assertEqual([e['start_ms'] for e in effects],[0,250,890,1290])
        self.assertEqual([e['duration_ms'] for e in effects],[200,600,300,400])
        self.assertEqual(groups[0]['duration_ms_estimate'],1690)
        self.assertEqual({n.get('grpId') for n in root.findall('.//p:bldP',NS)},{'0','1','2','3'})
        self.assertEqual(len(root.findall('.//p:sp',NS)),1)
        self.assertEqual(animation_summary(root)['missing_targets'],[])
        exit_row=root.find('.//p:cTn[@presetClass="exit"]',NS)
        self.assertEqual(exit_row.find('.//p:animEffect',NS).get('transition'),'out')
        self.assertEqual(exit_row.find('.//p:set/p:to/p:strVal',NS).get('val'),'hidden')
        self.assertEqual(exit_row.find('.//p:set/p:cBhvr/p:cTn/p:stCondLst/p:cond',NS).get('delay'),'299')

    def test_fly_and_zoom_export_real_position_and_size_interpolation(self):
        for direction,attr,start in [('left','ppt_x','0-#ppt_w/2'),('right','ppt_x','1+#ppt_w/2'),
                                     ('up','ppt_y','0-#ppt_h/2'),('down','ppt_y','1+#ppt_h/2')]:
            with self.subTest(direction=direction):
                root=exported([dict(elementId='item',effect='fly-in',direction=direction)],['item'])
                values={anim.find('p:cBhvr/p:attrNameLst/p:attrName',NS).text:
                        anim.find('p:tavLst/p:tav/p:val/p:strVal',NS).get('val') for anim in root.findall('.//p:anim',NS)}
                self.assertEqual(values[attr],start)
                self.assertEqual(animation_summary(root)['behaviors']['anim'],2)
                self.assertFalse(root.findall('.//p:animEffect',NS))
        root=exported([dict(elementId='item',effect='zoom-in')],['item'])
        self.assertEqual({n.text for n in root.findall('.//p:anim/p:cBhvr/p:attrNameLst/p:attrName',NS)}, {'ppt_w','ppt_h'})
        self.assertEqual(len(root.findall('.//p:anim/p:tavLst/p:tav[@tm="0"]/p:val/p:fltVal[@val="0"]',NS)),2)
        self.assertEqual(timing_groups(root)[0]['effects'][0]['duration_ms'],600)

    def test_invalid_lifecycles_overlaps_options_and_numbers_fail_early(self):
        invalid=[
            [dict(elementId='a',effect='fade-in'),dict(elementId='a',effect='fade-in')],
            [dict(elementId='a',effect='fade-out'),dict(elementId='a',effect='pulse')],
            [dict(elementId='a',effect='fade-in'),dict(elementId='a',effect='pulse',trigger='withPrevious')],
            [dict(elementId='a',effect='fade-in',durationMs=float('nan'))],
            [dict(elementId='a',effect='fade-in',durationMs=True)],
            [dict(elementId='a',effect='pulse',scale=1)],
            [dict(elementId='a',effect='fade-in',direction='left')],
            [dict(elementId='a',effect='fade-in',repeat=2)],
            [dict(elementId='missing',effect='fade-in')],
        ]
        for cues in invalid:
            with self.subTest(cues=cues):
                with self.assertRaises(ValueError):animation_plan(cues,{'a':'text'})
        with self.assertRaises(ValueError):animation_plan([dict(elementId='a',effect='pulse')],{'a':'chart'})

    def test_initial_static_exit_is_valid_and_appear_dwell_is_reported(self):
        root=exported(replace_state(['old'],['new']),['old','new'])
        effects=timing_groups(root)[0]['effects']
        self.assertEqual([e['preset_class'] for e in effects],['exit','entr'])
        self.assertEqual(effects[1]['start_ms'],360)
        root=exported([dict(elementId='a',effect='appear',durationMs=120)],['a'])
        self.assertEqual(timing_groups(root)[0]['duration_ms_estimate'],120)

    def test_recipes_preserve_semantic_clicks_and_connector_dependencies(self):
        cues=process_flow([['a'],['b'],['c']],['ab','bc'])
        groups=timing_groups(exported(cues,['a','b','c','ab','bc']))
        self.assertEqual([g['trigger'] for g in groups],['onClick']*3)
        self.assertEqual([e['target_name'] for e in groups[1]['effects']],['ab','b'])
        self.assertGreaterEqual(groups[1]['effects'][1]['start_ms'],groups[1]['effects'][0]['duration_ms'])
        compare=compare_then_decide(['left'],['right'],['decision'])
        self.assertEqual([c.get('direction') for c in compare],['left','right',None])
        groups=timing_groups(exported(evidence_reveal(['claim'],['proof'],['meaning']),['claim','proof','meaning']))
        self.assertEqual(len(groups),3)
        self.assertEqual([e['start'] for e in animation_plan(staggered_reveal(['x','y','z']),dict.fromkeys(['x','y','z'],'text'))],[0,100,200])

    def test_autoplay_and_focus_do_not_create_extra_clicks(self):
        cues=compare_then_decide(['left'],['right'],['decision'],autoplay=True)
        cues+=focus_pulse('decision',trigger='afterPrevious')
        root=exported(cues,['left','right','decision']);summary=animation_summary(root)
        self.assertNotIn('clickEffect',summary['triggers'])
        self.assertEqual(summary['preset_classes'],{'entr':3,'emph':1})
        self.assertEqual(len(timing_groups(root)),1)

    def test_roundtrip_comparison_detects_changed_pulse_amount(self):
        with TemporaryDirectory() as tmp:
            before=Path(tmp)/'before.pptx';after=Path(tmp)/'after.pptx'
            exported(focus_pulse('a',scale=1.08),['a'],before)
            exported(focus_pulse('a',scale=1.15),['a'],after)
            self.assertTrue(compare_motion(before,before)['ok'])
            self.assertFalse(compare_motion(before,after)['ok'])


if __name__=='__main__':unittest.main()
