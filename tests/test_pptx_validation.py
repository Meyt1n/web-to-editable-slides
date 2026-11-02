"""Small OOXML fixtures exercise actual font links and native table text."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import struct
import sys
import unittest
from xml.etree import ElementTree as ET

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_pptx import NS, font_info, inspect

PKG_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
REL_BASE = NS['r'] + '/'


def small_font():
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(['.notdef', 'A'])
    builder.setupCharacterMap({65: 'A'})
    builder.setupGlyf({name: TTGlyphPen(None).glyph() for name in ['.notdef', 'A']})
    builder.setupHorizontalMetrics({name: (500, 0) for name in ['.notdef', 'A']})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': 'Fixture', 'styleName': 'Regular',
                            'uniqueFontIdentifier': 'Fixture Regular',
                            'fullName': 'Fixture Regular', 'psName': 'Fixture-Regular'})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    output = BytesIO()
    builder.save(output)
    return output.getvalue()


def eot(font, flags=0):
    # Version 1: fixed fields followed by four empty UTF-16 name fields.
    header = bytearray(96)
    struct.pack_into('<IIII', header, 0, len(header) + len(font), len(font), 0x10000, flags)
    struct.pack_into('<H', header, 34, 0x504C)
    return bytes(header) + font


class PptxValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'test.pptx'

    def write_deck(self, *, font=None, declaration=False, font_target='fonts/font1.fntdata',
                   font_type='font', font_external=False, slide_target='slides/slide1.xml',
                   table=False, picture=False, text=None):
        main = ET.Element('{' + NS['p'] + '}presentation')
        listing = ET.SubElement(main, '{' + NS['p'] + '}sldIdLst')
        ET.SubElement(listing, '{' + NS['p'] + '}sldId', {'id': '256', '{' + NS['r'] + '}id': 'rId1'})
        if declaration:
            fonts = ET.SubElement(main, '{' + NS['p'] + '}embeddedFontLst')
            entry = ET.SubElement(fonts, '{' + NS['p'] + '}embeddedFont')
            ET.SubElement(entry, '{' + NS['p'] + '}font', {'typeface': 'Fixture'})
            ET.SubElement(entry, '{' + NS['p'] + '}regular', {'{' + NS['r'] + '}id': 'rId2'})
        rels = ET.Element('{' + PKG_NS + '}Relationships')
        attrs = {'Id': 'rId1', 'Type': REL_BASE + 'slide'}
        if slide_target is not None:
            attrs['Target'] = slide_target
        ET.SubElement(rels, '{' + PKG_NS + '}Relationship', attrs)
        if declaration:
            attrs = {'Id': 'rId2', 'Type': REL_BASE + font_type}
            if font_target is not None:
                attrs['Target'] = font_target
            if font_external:
                attrs['TargetMode'] = 'External'
            ET.SubElement(rels, '{' + PKG_NS + '}Relationship', attrs)
        slide = ET.Element('{' + NS['p'] + '}sld')
        content = ET.SubElement(slide, '{' + NS['p'] + '}cSld')
        tree = ET.SubElement(content, '{' + NS['p'] + '}spTree')
        if text is not None:
            shape = ET.SubElement(tree, '{' + NS['p'] + '}sp')
            ET.SubElement(shape, '{' + NS['a'] + '}t').text = text
        if table:
            frame = ET.SubElement(tree, '{' + NS['p'] + '}graphicFrame')
            native_table = ET.SubElement(frame, '{' + NS['a'] + '}tbl')
            row = ET.SubElement(native_table, '{' + NS['a'] + '}tr')
            cell = ET.SubElement(row, '{' + NS['a'] + '}tc')
            ET.SubElement(cell, '{' + NS['a'] + '}t').text = 'Editable cell'
        if picture:
            ET.SubElement(tree, '{' + NS['p'] + '}pic')
        with ZipFile(self.path, 'w') as archive:
            archive.writestr('ppt/presentation.xml', ET.tostring(main))
            archive.writestr('ppt/_rels/presentation.xml.rels', ET.tostring(rels))
            archive.writestr('ppt/slides/slide1.xml', ET.tostring(slide))
            if font is not None:
                archive.writestr('ppt/fonts/font1.fntdata', font)
        return self.path

    def test_orphan_font_does_not_satisfy_embedding_requirement(self):
        result = inspect(self.write_deck(font=small_font() + b'\x00' * 5000), require_fonts=True)
        self.assertFalse(result['ok'])

    def test_small_valid_linked_font_is_accepted(self):
        data = small_font()
        self.assertLess(len(data), 4096)
        result = inspect(self.write_deck(font=data, declaration=True), require_fonts=True)
        self.assertTrue(result['ok'], result['errors'])
        self.assertTrue(result['fonts'][0]['valid_binary'])
        self.assertTrue(result['fonts'][0]['embedded'])

    def test_forged_font_header_is_rejected(self):
        data = b'\x00\x01\x00\x00' + b'\x00' * 5000
        result = inspect(self.write_deck(font=data, declaration=True), require_fonts=True)
        self.assertFalse(result['ok'])
        self.assertFalse(result['fonts'][0]['valid_binary'])

    def test_eot_checks_payload_instead_of_magic_only(self):
        self.assertTrue(font_info('font.fntdata', eot(small_font()))['valid_binary'])
        self.assertFalse(font_info('font.fntdata', eot(b'\x00' * 5000))['valid_binary'])

    def test_compressed_eot_is_reported_as_unverified(self):
        result = font_info('font.fntdata', eot(b'compressed payload', flags=4))
        self.assertFalse(result['valid_binary'])
        self.assertIn('compressed', result['validation_error'])

    def test_missing_or_wrong_font_relationship_is_rejected(self):
        for options in [dict(font_target=None), dict(font_target='fonts/absent.fntdata'),
                        dict(font_type='image'), dict(font_external=True)]:
            with self.subTest(options=options):
                result = inspect(self.write_deck(font=small_font() + b'\x00' * 5000, declaration=True, **options), require_fonts=True)
                self.assertFalse(result['ok'])
                self.assertTrue(result['errors'])

    def test_missing_slide_target_is_reported_without_crashing(self):
        result = inspect(self.write_deck(slide_target=None))
        self.assertFalse(result['ok'])
        self.assertTrue(any('Target' in error for error in result['errors']))

    def test_native_table_text_prevents_false_image_page_warning(self):
        result = inspect(self.write_deck(table=True, picture=True))
        self.assertTrue(result['ok'], result['errors'])
        self.assertEqual(result['slides'][0]['editable_table_cells'], 1)
        self.assertEqual(result['slides'][0]['editable_text_boxes'], 0)
        self.assertFalse(any('image page' in warning for warning in result['warnings']))

    def test_image_only_page_still_warns(self):
        result = inspect(self.write_deck(picture=True))
        self.assertTrue(any('image page' in warning for warning in result['warnings']))

    def test_whitespace_only_shape_is_not_counted_as_editable_text(self):
        result = inspect(self.write_deck(picture=True, text=' \n\t '))
        self.assertEqual(result['slides'][0]['editable_text_boxes'], 0)
        self.assertTrue(any('image page' in warning for warning in result['warnings']))

    def test_duplicate_relationship_id_is_rejected(self):
        self.write_deck()
        with ZipFile(self.path) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        name = 'ppt/_rels/presentation.xml.rels'
        rels = ET.fromstring(parts[name])
        ET.SubElement(rels, '{' + PKG_NS + '}Relationship', dict(rels[0].attrib))
        parts[name] = ET.tostring(rels)
        with ZipFile(self.path, 'w') as archive:
            for name, data in parts.items():
                archive.writestr(name, data)
        result = inspect(self.path)
        self.assertFalse(result['ok'])
        self.assertTrue(any('duplicate relationship Id' in error for error in result['errors']))


if __name__ == '__main__':
    unittest.main()
