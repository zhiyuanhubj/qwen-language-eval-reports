"""Strict declared-answer exact match; custom subset protocol, no LLM judge."""
import argparse,collections,json,re
from decimal import Decimal,InvalidOperation
from pathlib import Path

def extract(text,kind):
 lines=re.findall(r'^\s*ANSWER:\s*(.*?)\s*$',text or '',re.M|re.I)
 if not lines:return None,'missing_answer_line'
 if kind=='multiple_choice_exact':
  if not re.fullmatch(r'[A-Z]',lines[-1],re.I):return None,'invalid_choice_format'
  return lines[-1].upper(),'ok'
 value=lines[-1]
 if not re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',value):return None,'invalid_numeric_format'
 try:return str(Decimal(value.replace(',','')).normalize()),'ok'
 except InvalidOperation:return None,'invalid_number'

def evaluate(answers,rows):
 byid={x['id']:x for x in rows if x.get('status')=='ok'};results=[]
 for ident,gold in answers.items():
  r=byid.get(ident,{});final=r.get('final_answer') or '';pred,status=extract(final,gold['metric'])
  expected=gold['answer'] if gold['metric']=='multiple_choice_exact' else str(Decimal(gold['answer'].replace(',','')).normalize())
  rawpred,rawstatus=extract(r.get('reasoning') or '',gold['metric']) if not final else (None,'not_used')
  results.append(dict(id=ident,dataset=gold['dataset'],answered=bool(r),expected=expected,prediction=pred,correct=pred==expected,parse_status=status,final_missing=not bool(final),raw_only_prediction=rawpred,raw_only_correct=(rawpred==expected if not final else None)))
 groups={}
 for group in ['all72']+sorted({x['dataset'] for x in results}):
  rs=results if group=='all72' else [x for x in results if x['dataset']==group];n=len(rs);completed=sum(x['answered'] for x in rs)
  groups[group]=dict(correct=sum(x['correct'] for x in rs),expected=n,answered=completed,complete=completed==n,provisional=completed<n,accuracy_percent=round(100*sum(x['correct'] for x in rs)/n,2),parse_failures=sum(x['parse_status']!='ok' for x in rs),missing_final=sum(x['final_missing'] for x in rs),raw_only_correct=sum(x['raw_only_correct'] is True for x in rs))
 return dict(protocol='custom_subset_strict_answer_line_v1',note='Missing/invalid final counts incorrect; raw-only answers reported separately, never silently credited. Not official full-benchmark results.',groups=groups,items=results)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--suite',type=Path,required=True);p.add_argument('--responses',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 answers=json.loads((a.suite/'benchmark-answers.json').read_text());rows=[json.loads(l) for l in a.responses.read_text().split('\n') if l]
 a.output.write_text(json.dumps(evaluate(answers,rows),ensure_ascii=False,indent=2))
