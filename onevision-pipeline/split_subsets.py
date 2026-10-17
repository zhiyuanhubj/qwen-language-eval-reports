"""Partition one canonical inventory by subset, preserving all task identities."""
import argparse,collections,hashlib,json
from pathlib import Path

def split(manifest,parts,selected=None):
 assert parts>0
 groups=collections.defaultdict(list)
 for task in manifest['tasks']:groups[task['subset']].append(task)
 if selected:
  unknown=set(selected)-set(groups)
  if unknown:raise ValueError(f'Unknown subsets: {sorted(unknown)}')
  groups={k:v for k,v in groups.items() if k in selected}
 assert groups,'Empty selection'
 assert parts<=len(groups),'More parts than selected subsets'
 assigned=[[] for _ in range(parts)];loads=[0]*parts
 for subset,tasks in sorted(groups.items(),key=lambda kv:(-sum(t['rows'] for t in kv[1]),kv[0])):
  i=min(range(parts),key=lambda i:(loads[i],i));assigned[i].extend(tasks);loads[i]+=sum(t['rows'] for t in tasks)
 keys=[t['key'] for tasks in assigned for t in tasks];assert len(keys)==len(set(keys))
 assert set(keys)=={t['key'] for tasks in groups.values() for t in tasks}
 return [{**manifest,'source_root':'SUPPLY_LOCAL_SOURCE_ROOT','tasks':tasks,'rows':sum(t['rows'] for t in tasks),'subsets':len({t['subset'] for t in tasks}),'assignment_part':i+1} for i,tasks in enumerate(assigned)]
def main():
 p=argparse.ArgumentParser();p.add_argument('inventory',type=Path);p.add_argument('--parts',type=int,required=True);p.add_argument('--completed-dir',type=Path,help='Existing filtering tasks directory; skip tasks with done.json and no unresolved errors');p.add_argument('--subsets',help='Comma-separated exact names; omit for all');p.add_argument('--output',type=Path,required=True);a=p.parse_args();raw=a.inventory.read_bytes();m=json.loads(raw)
 if a.completed_dir:
  def unfinished(t):
   p=a.completed_dir/t['key']/'done.json'
   return not (p.exists() and json.loads(p.read_text()).get('unresolved_errors')==0)
  m={**m,'tasks':[t for t in m['tasks'] if unfinished(t)]}
 plans=split(m,a.parts,a.subsets.split(',') if a.subsets else None);a.output.mkdir(parents=True,exist_ok=True)
 summary={'parent_inventory_sha256':hashlib.sha256(raw).hexdigest(),'parts':[]}
 for i,plan in enumerate(plans,1):
  d=a.output/f'part-{i:02}';d.mkdir(exist_ok=False);(d/'inventory.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));subsets=sorted({t['subset'] for t in plan['tasks']});(d/'subsets.txt').write_text('\n'.join(subsets)+'\n');(d/'source-files.txt').write_text('\n'.join(sorted({t['file'] for t in plan['tasks']}))+'\n');summary['parts'].append({'part':i,'rows':plan['rows'],'tasks':len(plan['tasks']),'subsets':subsets})
 (a.output/'assignments.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
