"""Validate user-authored template JSON before packaging any resources."""
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from template_pack import load_template,prepare,validate_template


def minimal_template():
    return {
        'schema_version':'1.0','id':'example','version':'1.0.0','canvas':[960,540],
        'palette':{'ink':'#123456'},
        'resources':{'fonts':{'Example':{'system_font':True}}},
        'typography':{'body':{'family':'Example','size':20}},
        'references':[{'id':'cover','file':'reference.png'}],
        'components':{'card':{'fill':'ink'}},
        'layouts':{'cover':{'slots':{'title':[40,40,880,80]}}},
    }


class TemplateValidationTests(unittest.TestCase):
    def test_malformed_containers_raise_validation_errors(self):
        cases=[
            ('resources',[]),('palette',['#123456']),('typography',[20]),
            ('references',{'cover':'reference.png'}),('layouts',['cover']),
            ('components',['card']),('adaptations','a note'),('variation_rules',[7]),
        ]
        for field,value in cases:
            with self.subTest(field=field):
                data=minimal_template();data[field]=value
                with self.assertRaises(ValueError):
                    validate_template(data)
        for field,value in [('fonts',{'Example':None}),('fonts',[]),('background',False)]:
            with self.subTest(resource=field,value=value):
                data=minimal_template();data['resources'][field]=value
                with self.assertRaises(ValueError):
                    validate_template(data)
        data=minimal_template();data['layouts']['cover']['slots']=['title']
        with self.assertRaisesRegex(ValueError,'slots'):
            validate_template(data)

    def test_font_size_must_be_finite_and_positive(self):
        for size in [float('nan'),float('inf'),-float('inf'),0,-1,True]:
            with self.subTest(size=size):
                data=minimal_template();data['typography']['body']['size']=size
                with self.assertRaisesRegex(ValueError,'size'):
                    validate_template(data)

    def test_reference_ids_are_nonempty_unique_strings(self):
        data=minimal_template();data['references'].append(copy.deepcopy(data['references'][0]))
        with self.assertRaisesRegex(ValueError,'unique'):
            validate_template(data)
        for sid in [5,[],{},' ']:
            with self.subTest(id=sid):
                data=minimal_template();data['references'][0]['id']=sid
                with self.assertRaises(ValueError):
                    validate_template(data)

    def test_system_font_and_redistribution_are_distinct(self):
        self.assertIsNotNone(validate_template(minimal_template()))
        for extra in [{'file':'font.otf'},{'license_file':'LICENSE.txt'},{'system_font':'true'}]:
            with self.subTest(extra=extra):
                data=minimal_template();data['resources']['fonts']['Example'].update(extra)
                with self.assertRaises(ValueError):
                    validate_template(data)
        data=minimal_template();data['resources']['fonts']['Example']={'file':'font.otf'}
        with self.assertRaisesRegex(ValueError,'license_file'):
            validate_template(data)

    def test_pack_preserves_font_format_and_copies_license(self):
        with TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir()
            (source/'reference.png').write_bytes(b'reference fixture')
            (source/'font.OTF').write_bytes(b'OTTO fixture')
            (source/'LICENSE.txt').write_text('Fixture redistribution license',encoding='utf8')
            data=minimal_template()
            data['resources']['fonts']['Example']={'file':'font.OTF','license_file':'LICENSE.txt'}
            observations=source/'observations.json'
            observations.write_text(json.dumps(data),encoding='utf8')
            path=prepare(observations,source,Path(folder)/'pack')
            packed=load_template(path);resource=packed['resources']['fonts']['Example']
            self.assertEqual(Path(resource['file']).suffix,'.otf')
            self.assertEqual((path.parent/resource['file']).read_bytes(),b'OTTO fixture')
            self.assertEqual((path.parent/resource['license_file']).read_text('utf8'),'Fixture redistribution license')

    def test_force_cannot_modify_a_resource_already_in_output(self):
        with TemporaryDirectory() as folder:
            source=Path(folder);output=source/'pack';(output/'references').mkdir(parents=True)
            original=output/'references/01.png';original.write_bytes(b'preserve this source')
            (source/'reference.png').write_bytes(b'new reference')
            data=minimal_template()
            data['references'].append({'id':'second','file':'pack/references/01.png'})
            observations=source/'observations.json'
            observations.write_text(json.dumps(data),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'source resources'):
                prepare(observations,source,output,force=True)
            self.assertEqual(original.read_bytes(),b'preserve this source')
            self.assertFalse((output/'references/02.png').exists())
            self.assertFalse((output/'template.json').exists())

    def test_cli_reports_malformed_resource_without_traceback(self):
        with TemporaryDirectory() as folder:
            data=minimal_template();data['resources']=[]
            path=Path(folder)/'invalid.json';path.write_text(json.dumps(data),encoding='utf8')
            process=subprocess.run([sys.executable,str(ROOT/'scripts/template_pack.py'),'check',str(path)],
                                   capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0)
            self.assertIn('resources must be an object',process.stderr)
            self.assertNotIn('Traceback',process.stderr)


if __name__=='__main__':
    unittest.main()
