"""Source-server smoke for the declarative Doudizhu flow."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import Request, urlopen
from pocker_agent.game_rules import DoudizhuRule
from pocker_agent.tools.plans import plan_for_rules
ROOT=Path(__file__).resolve().parents[1]
rules=DoudizhuRule(schema_version='0.2',game_id='ddz-http',title='斗地主',deck={'suits':['S','H','D','C'],'ranks':['3','4','5','6','7','8','9','10','J','Q','K','A','2','BJ','RJ']},players={'min_players':3,'max_players':3,'starting_hand_size':17},max_rounds=1,kind='doudizhu')
port=5187; data=Path(tempfile.mkdtemp(prefix='ddz-http-',dir=ROOT/'.validation'))
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),POCKER_AGENT_DATA_DIR=str(data))
p=subprocess.Popen([sys.executable,'-m','uvicorn','pocker_agent.api:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
def req(path,body=None):
 q=Request('http://127.0.0.1:'+str(port)+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urlopen(q,timeout=10) as x:return json.load(x)
try:
 for _ in range(50):
  try:req('/health');break
  except Exception:time.sleep(.1)
 b=req('/api/runtime/sessions',{'rules':rules.model_dump(mode='json'),'tool_plan':plan_for_rules(rules),'seed':9})
 assert b['execution_mode']=='tool_flow' and b['legal_actions']==['bid:*']
 calls=set()
 for action in ('bid:1','bid:2','bid:3'):
  b=req('/api/runtime/sessions/'+b['session_id']+'/actions/'+action,{'revision':b['revision']})['state']
  calls |= {(e['tool'],e['operation']) for e in b['tool_events'] if e['event']=='tool_called'}
 assert b['phase']=='play' and b['legal_actions']==['play:*','pass'] and ('doudizhu_turn','play') in calls
 print(json.dumps({'execution_mode':b['execution_mode'],'phase':b['phase'],'players':len(b['players']),'tool_calls':sorted(calls)}))
finally:p.terminate();p.wait(timeout=5)
