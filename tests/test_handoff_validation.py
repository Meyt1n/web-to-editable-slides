"""Handoff decisions and evidence must survive rendering without silent coercion."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from make_handoff import render, validate
from review_design_plan import review


class HandoffValidationTests(unittest.TestCase):
    def referenced_deck(self):
        return {'project': 'Reference deck', 'slides': [
            {'id': i, 'title': f'Page {i}', 'reference': f'{i}.png', 'layout': 'cards'}
            for i in range(1, 5)]}

    def test_references_default_to_fidelity_without_mutating_input(self):
        brief = self.referenced_deck()
        original = copy.deepcopy(brief)
        result = review(brief)
        self.assertTrue(result['ok'])
        self.assertEqual(result['summary']['mode'], 'fidelity')
        self.assertFalse(any(s['code'] == 'repeated-layout' for s in result['suggestions']))
        self.assertIn('模式：fidelity', render(brief))
        self.assertEqual(brief, original)

    def test_explicit_mode_takes_precedence_and_no_reference_keeps_enhance(self):
        brief = self.referenced_deck()
        brief['design'] = {'mode': 'enhance'}
        self.assertEqual(review(brief)['summary']['mode'], 'enhance')
        self.assertTrue(any(s['code'] == 'repeated-layout' for s in review(brief)['suggestions']))
        for slide in brief['slides']:
            del slide['reference']
        del brief['design']
        self.assertEqual(review(brief)['summary']['mode'], 'enhance')

    def test_chart_evidence_and_illustration_flags_survive_handoff(self):
        brief = {'project': 'Evidence', 'slides': [
            {'id': 1, 'title': 'Measured', 'layout': 'data-focus',
             'data_source': 'results.csv: rows 2–8', 'data_is_illustrative': False},
            {'id': 2, 'title': 'Concept', 'layout': 'data-focus', 'data_is_illustrative': True}]}
        text = render(brief)
        self.assertIn('results.csv: rows 2–8', text)
        self.assertIn('示意数据：否', text)
        self.assertIn('示意数据：是', text)
        self.assertFalse(review(brief)['suggestions'])

    def test_empty_optional_text_remains_compatible_with_draft_briefs(self):
        brief = {'project': 'Draft', 'purpose': '', 'asset_priority': [''],
                 'style': {'description': '', 'ratio': '', 'colors': []},
                 'conversations': [{'role': '', 'location': '', 'visibility': ''}],
                 'design': {'constants': ['']},
                 'slides': [{'id': 1, 'title': 'Page', 'reference': '', 'notes': '',
                             'layout': '', 'font_profile': '', 'key_points': ['']}]}
        self.assertIs(validate(brief), brief)
        self.assertIn('Draft', render(brief))
        self.assertTrue(review(brief)['ok'])
        self.assertEqual(review(brief)['summary']['mode'], 'enhance')

    def test_malformed_optional_fields_return_errors_instead_of_crashing(self):
        cases = [
            {'style': None}, {'style': {'colors': [7]}},
            {'conversations': ['private export']}, {'asset_priority': 'photos'},
            {'design': {'constants': 'Keep colors'}},
        ]
        slide_cases = [
            {'status': []}, {'layout': {}}, {'font_profile': []},
            {'reference': []}, {'data_source': ''}, {'data_is_illustrative': 'false'},
        ]
        for patch in cases + [{'slides': [{'id': 1, 'title': 'Page', **s}]} for s in slide_cases]:
            brief = {'project': 'Invalid', 'slides': [{'id': 1, 'title': 'Page'}], **patch}
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    validate(brief)
                self.assertFalse(review(brief)['ok'])
                with self.assertRaises(ValueError):
                    render(brief)


if __name__ == '__main__':
    unittest.main()
