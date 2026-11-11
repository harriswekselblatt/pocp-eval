"""Evaluation infrastructure. This module never imports POCP implementation code."""
import os, json, pathlib, subprocess, signal, time, hashlib, tarfile, io
ROOT=pathlib.Path(__file__).resolve().parents[1]
BIN=pathlib.Path(os.environ.get('POCP_EVAL_BIN',ROOT/'vendor/npm-pocp-1.2.2/bin/pocp.js')).resolve()
PYTHON=ROOT/'.venv/bin/python'
def environment():
 e=dict(os.environ)
 for k in list(e):
  if k.startswith(('GITHUB_','POCP_SIGN_')) or k in ['CI','GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL']:e.pop(k,None)
 e.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_NAME='Benchmark',GIT_COMMITTER_NAME='Benchmark',GIT_AUTHOR_EMAIL='benchmark@example.invalid',GIT_COMMITTER_EMAIL='benchmark@example.invalid',POCP_BIN=f'node {BIN}',GOROOT=str(ROOT/'vendor/go-runtime/go'))
 e['PATH']=str(ROOT/'vendor/go-runtime/go/bin')+os.pathsep+e['PATH'];return e
def write(p,value):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(json.dumps(value,indent=2)+'\n' if not isinstance(value,str) else value)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def execute(cwd,argv,timeout=180):
 start=time.monotonic();p=subprocess.Popen(argv,cwd=cwd,env=environment(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:out,err=p.communicate(timeout=timeout);state='completed'
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
  state='timeout'
 return dict(argv=argv,exit=p.returncode,execution=state,seconds=time.monotonic()-start,stdout=out,stderr=err)
def checked(cwd,argv):
 r=execute(cwd,argv)
 if r['execution']!='completed' or r['exit']!=0:raise RuntimeError(f'{argv}: {r["stderr"][-1200:]} {r["stdout"][-1200:]}')
 return r['stdout'].strip()
def materialize(target,d,sha=None):
 d=pathlib.Path(d);d.mkdir(parents=True,exist_ok=False);v=ROOT/'vendor'/target
 pins=json.loads((ROOT/'pins/sources.json').read_text());sha=sha or pins[target]['sha']
 data=subprocess.check_output(['git','archive',sha],cwd=v)
 with tarfile.open(fileobj=io.BytesIO(data)) as a:a.extractall(d,filter='data')
 if (v/'node_modules').exists():(d/'node_modules').symlink_to(v/'node_modules',target_is_directory=True)
 return sha
def inventory(d):return {str(p.relative_to(d)):digest(p) for p in sorted(d.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.json'}
