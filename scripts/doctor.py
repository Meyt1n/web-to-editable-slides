"""Select a Codex/project Python without writing into the installed skill."""
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


def diagnose(extra=None,workspace=None):
    workspace=Path(workspace or Path.cwd()).resolve()
    candidates=[Path(extra)] if extra else []
    candidates += [workspace/'.venv/Scripts/python.exe',workspace/'.venv/bin/python',Path(sys.executable)]
    results=[];seen=set()
    for path in candidates:
        if not path.is_file() or str(path.resolve()) in seen:continue
        seen.add(str(path.resolve()))
        try:
            result=subprocess.run([str(path),'-c',PROBE],capture_output=True,text=True,timeout=20)
            if result.returncode:raise ValueError('probe_failed')
            item=json.loads(result.stdout)
            if not isinstance(item,dict) or not isinstance(item.get('version'),list) or not isinstance(item.get('missing'),list):raise ValueError('invalid_probe')
            item['ready']=item['version']>=[3,10] and not item['missing']
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            item=dict(executable=str(path),ready=False,reason='probe_timeout' if isinstance(exc,subprocess.TimeoutExpired) else 'probe_failed')
        results.append(item)
    selected=next((r for r in results if r['ready']),None)
    return dict(execution_target='codex',workspace=str(workspace),ready=selected is not None,selected=selected,candidates=results,
                requirements=str(ROOT/'requirements.txt'),
                next_action='Use selected executable for every following command in this workspace' if selected else 'Use the Codex workspace runtime, create a workspace venv and install requirements; then recheck',
                codex_session_checks=['Use the current Codex model for visual inspection',
                                      'Use the built-in imagegen tool exposed to this Codex session',
                                      'Check the actual PPTX renderer separately; Python readiness is not visual QA'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--python');parser.add_argument('--workspace',type=Path);args=parser.parse_args()
    result=diagnose(args.python,args.workspace);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ready'] else 2)
