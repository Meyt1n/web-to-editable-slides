"""Find a usable local Python without loading the deck toolchain or writing files."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PROBE="""import sys,json,importlib.util
mods=['PIL','pptx','yaml','fontTools']
print(json.dumps(dict(executable=sys.executable,version=list(sys.version_info[:3]),missing=[m for m in mods if importlib.util.find_spec(m) is None])))
"""


def diagnose(extra=None):
    candidates=[Path(extra)] if extra else []
    candidates += [ROOT/'.venv/Scripts/python.exe',ROOT/'.venv/bin/python',Path(sys.executable)]
    results=[];seen=set()
    for path in candidates:
        if not path.is_file() or str(path.resolve()) in seen:continue
        seen.add(str(path.resolve()))
        result=subprocess.run([str(path),'-c',PROBE],capture_output=True,text=True,timeout=20)
        if result.returncode:continue
        item=json.loads(result.stdout);item['ready']=item['version']>=[3,10] and not item['missing'];results.append(item)
    selected=next((r for r in results if r['ready']),None)
    return dict(ready=selected is not None,selected=selected,candidates=results,
                requirements=str(ROOT/'requirements.txt'),
                next_action='Use selected executable for every following command' if selected else 'Find Python 3.10+ from the host runtime, create a project venv and install requirements; then recheck',
                host_requirements=['imagegen tool for reference generation','visual image inspection','a real PPTX renderer for visual QA'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--python');args=parser.parse_args()
    result=diagnose(args.python);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ready'] else 2)
