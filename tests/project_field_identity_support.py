"""Recorded Project response shapes and an isolated API simulator for #2713."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "tests/fixtures/project-field-identity.json").read_text())

# Runs only behind the temporary `gh` executable created below; never calls a network API.
MOCK = """#!/usr/bin/env python3
import base64,json,os,sys
from pathlib import Path
p=Path(os.environ['IDENTITY_STATE'])
s=json.loads(p.read_text())
a=sys.argv[1:]
with p.with_suffix('.log').open('a') as f: f.write(json.dumps(a)+'\\n')
def out(x): print(json.dumps(x)); sys.exit(0)
def save(): p.write_text(json.dumps(s))
def arg(n): return a[a.index(n)+1]
def issuevalues():
 return [{'issue_field_name':k,'single_select_option':{'name':v}} for k,v in s['issue_values'].items()]
def item():
 return {'id':101,'content':{'id':1311,'number':1311,'repository':{'full_name':'basefoundry/base'}},'fields':[
  {'id':f['id'],'name':f['name'],'value':{'name':{'raw':s['values'].get(str(f['id']), '')}}}
  for f in s['fields']]}
def gqlitem():
 vals=[]
 for f in s['fields']:
  v=s['values'].get(str(f['id']), '')
  if s.get('bad_readback') and s.get('edits') and f['id']==11: v=''
  if s.get('bad_readback') and s.get('edits') and f['id']==900: v='P2'
  if v: vals.append({'name':v,'field':{'id':'F'+str(f['id']),'name':f['name'],'isIssueField':'issue_field_id' in f}})
 return {'data':{'node':{'id':'PVTI_item','fieldValues':{'nodes':vals}}}}
def update(fid,oid):
 fid=str(fid).removeprefix('F')
 f=next(f for f in s['fields'] if str(f['id'])==fid)
 assert 'issue_field_id' not in f, 'attempted Project write to displayed issue field'
 s['values'][fid]=next(o['name']['raw'] for o in f['options'] if o['id']==oid)
 s.setdefault('edits',[]).append(fid); save()
if a[:2]==['project','list']:
 if s['fallback']:
  print('GraphQL: API rate limit already exceeded',file=sys.stderr);sys.exit(1)
 out({'projects':[{'title':'base','number':1}]})
if a[:2]==['project','view']: print('PVT_project');sys.exit(0)
if a[:2]==['project','item-add']: print('PVTI_item');sys.exit(0)
if a[:2]==['project','item-edit']:
 update(arg('--field-id'),arg('--single-select-option-id'));sys.exit(0)
if a[:2]==['api','graphql']:
 query=next(x for x in a if x.startswith('query='))
 if 'fields(first:' in query:
  out({'data':{'node':{'fields':{'nodes':[
   {'id':'F'+str(f['id']),'name':f['name'],'isIssueField':'issue_field_id' in f,
    'options':[{'id':o['id'],'name':o['name']['raw']} for o in f['options']]} for f in s['fields']]}}}})
 out(gqlitem())
endpoint=next((x for x in a if x.startswith(('repos/','orgs/','users/'))),'')
method=arg('--method') if '--method' in a else 'GET'
if endpoint.endswith('contents/.github/base-project.yml'):
 source='' if s['mode']=='unset' else '  field_source: '+s['mode']+'\\n'
 config='project:\\n'+source+'  issue_defaults:\\n    priority: '+('Medium' if s['mode']!='unset' else 'P2')+'\\n    size: S\\n    effort: Small\\n    area: Product\\n    initiative: Adoption Polish\\n'
 print(base64.b64encode(config.encode()).decode());sys.exit(0)
if endpoint=='repos/basefoundry/base/issues/1311': out({'id':1311,'number':1311,'state':'open','html_url':'https://github.com/basefoundry/base/issues/1311','title':'fixture'})
if 'issue-fields?' in endpoint: out([{'id':43373537,'name':'Priority'},{'id':43373540,'name':'Effort'}])
if endpoint.endswith('issue-field-values'):
 if method=='POST':
  payload=json.load(sys.stdin)
  for u in payload['issue_field_values']: s['issue_values'][{43373537:'Priority',43373540:'Effort'}[u['field_id']]]=u['value']
  save()
 out(issuevalues())
if endpoint=='users/basefoundry': out({'type':'Organization'})
if '/projectsV2?' in endpoint: out([{'number':1,'title':'base'}])
if '/fields' in endpoint: out(s['fields'])
if '/items' in endpoint:
 if method=='PATCH':
  payload=json.load(sys.stdin)
  for u in payload['fields']: update(u['id'],u['value'])
 if endpoint.endswith('/items'):
  if '--slurp' in a: out([[item()]])
  out([item()])
 out(item())
raise AssertionError(a)
"""


# pylint: disable=too-many-arguments
def run_identity_intake(
    tmp_path,
    *,
    case,
    mode,
    fallback=False,
    preserve=False,
    workflow=".github/workflows/project-intake.yml",
    bad_readback=False,
):
    fields = FIXTURES[case]["fields"]
    values = {str(f["id"]): ("High" if f["id"] == 900 else "") for f in fields}
    if preserve:
        values.update({"11": "P1", "12": "M", "13": "CLI", "14": "Contract Hardening"})
    state = {
        "fields": fields,
        "values": values,
        "issue_values": {"Priority": "High", "Effort": "Large"} if preserve else {},
        "mode": mode,
        "fallback": fallback,
        "bad_readback": bad_readback,
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state))
    mock = tmp_path / "gh"
    mock.write_text(MOCK.replace("#!/usr/bin/env python3", "#!" + sys.executable))
    mock.chmod(0o755)
    env = os.environ.copy()
    env.update(
        IDENTITY_STATE=str(state_path),
        PATH=str(tmp_path) + ":" + env["PATH"],
        GH_TOKEN="fixture",
        BASE_PROJECT_OWNER="basefoundry",
        BASE_PROJECT_TITLE="base",
        BASE_PROJECT_ISSUE_NUMBER="1311",
        GITHUB_REPOSITORY="basefoundry/base",
        BASE_PROJECT_DEFAULT_OPEN_STATUS="Backlog",
        BASE_PROJECT_DEFAULT_CLOSED_STATUS="Done",
    )
    run = yaml.safe_load((ROOT / workflow).read_text())["jobs"]["sync"]["steps"][0]["run"]
    result = subprocess.run(["bash", "-c", run], env=env, capture_output=True, text=True, timeout=30, check=False)
    return (
        result,
        json.loads(state_path.read_text()),
        [json.loads(x) for x in state_path.with_suffix(".log").read_text().splitlines()],
    )
