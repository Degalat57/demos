"""Artifact inventory only. Does not parse, compile or execute ABAP."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def inventory():
    checks = []
    for filename in ['package.json', 'abaplint.json', 'abap_transpile.json']:
        json.loads((ROOT / filename).read_text())
        checks.append(f'{filename}: valid JSON')
    xml_files = sorted(ROOT.glob('src/*.xml')) + [ROOT / '.abapgit.xml']
    for path in xml_files:
        ET.parse(path)
    checks.append(f'{len(xml_files)} XML files: well formed')
    methods = {}
    for path in sorted(ROOT.glob('src/*.clas.testclasses.abap')):
        text = path.read_text()
        names = re.findall(r'METHODS\s+(\w+)\s+FOR TESTING', text, re.I)
        implementations = re.findall(r'^  METHOD\s+(\w+)\.', text, re.M | re.I)
        assert len(names) == len(set(names)), path.name
        assert sorted(names) == sorted(implementations), path.name
        assert 'RISK LEVEL HARMLESS' in text and 'DURATION SHORT' in text, path.name
        methods[path.name] = names
    count = sum(map(len, methods.values()))
    assert count >= 40
    checks.append(f'{count} unique ABAP Unit method declarations matched to implementations')
    source_files = sorted(ROOT.glob('src/*.abap'))
    for path in source_files:
        text = path.read_text()
        assert not re.search(r'^\s*(?:FORM|PERFORM|TABLES|COMPUTE|MOVE)\b', text, re.M | re.I), path.name
        assert not re.search(r'\bTYPE\s+f\b', text, re.I), path.name
        assert '\t' not in text, path.name
        assert all(line == line.rstrip() for line in text.splitlines()), path.name
        if '.testclasses.' not in path.name:
            assert path.with_suffix('.xml').exists(), path.name
    checks.append('source metadata pairs, selected obsolete statements, binary floats and whitespace: checked')
    production = '\n'.join(p.read_text() for p in source_files if '.testclasses.' not in p.name)
    for construct in ['VALUE', 'REDUCE', 'COND', 'CORRESPONDING', 'decfloat34', 'RAISE EXCEPTION TYPE']:
        assert construct in production, construct
    checks.append('requested modern ABAP constructs present (lexical check)')
    assert all(v is True for v in json.loads((ROOT / 'abaplint.json').read_text())['rules'].values())
    checks.append('configured lint rules enabled')
    return {
        'kind': 'artifact_inventory_only', 'checks': checks,
        'abap_unit_methods_authored': count, 'abap_unit_methods_executed': 0,
        'abaplint_executed': False, 'sap_kernel_used': False,
        'methods': methods,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
    }

if __name__ == '__main__':
    print(json.dumps(inventory(), indent=2))
