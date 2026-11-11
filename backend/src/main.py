
"""Deterministic synthetic OEE generator, analyzer, validator and exporter."""
import argparse, csv, hashlib, json, random, collections, heapq
from datetime import datetime, date, timedelta
from pathlib import Path

SEED=20261022
FIELDS={
 'plant':['plant_id','name','status'],
 'line':['line_id','plant_id','name','status'],
 'machine':['machine_id','line_id','name','status'],
 'shift':['shift_id','plant_id','shift_date','code','start_at','end_at','planned_break_minutes'],
 'product':['product_id','name','status'],
 'machine_product':['machine_id','product_id','ideal_cycle_seconds','effective_from','effective_to'],
 'production_order':['order_id','machine_id','shift_id','product_id','status','planned_units'],
 'downtime_reason':['reason_id','description','category','planned'],
 'state_event':['event_id','machine_id','order_id','shift_id','start_at','end_at','state','reason_id','observed_ideal_cycle_seconds','issue_type'],
 'production_count':['count_id','order_id','machine_id','shift_id','at','delta_total','correction_of','issue_type'],
 'quality_inspection':['inspection_id','order_id','machine_id','shift_id','at','scrap_units','rework_units','issue_type'],
 'oee_aggregate':['aggregate_id','machine_id','shift_id','planned_minutes','run_minutes','total_units','good_units','availability','performance','quality','oee','status'],
 'ground_truth':['issue_id','entity','record_id','issue_type','expected_decision'],
}
def stamp(d, hour, minute=0):return (datetime.combine(d,datetime.min.time())+timedelta(hours=hour,minutes=minute)).isoformat(timespec='seconds')
def save(out,table,rows):
 with (out/(table+'.csv')).open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS[table]);w.writeheader();w.writerows(rows)
def build(out,days=2,machines=6,events=300,records=900,seed=SEED):
 if min(days,machines,events,records)<1:raise ValueError('All scales must be positive')
 rng=random.Random(seed);out.mkdir(parents=True,exist_ok=True)
 data={k:[] for k in FIELDS};truth=data['ground_truth']
 data['plant']=[dict(plant_id='PLANT-001',name='Demo Factory',status='ACTIVE')]
 data['line']=[dict(line_id=f'LINE-{i:03}',plant_id='PLANT-001',name=f'Line {i}',status='ACTIVE') for i in range(1,6)]
 data['machine']=[dict(machine_id=f'MCH-{i:03}',line_id=f'LINE-{((i-1)%5)+1:03}',name=f'Machine {i}',status='ACTIVE') for i in range(1,machines+1)]
 data['product']=[dict(product_id=f'PROD-{i:03}',name=f'Product {i}',status='ACTIVE') for i in range(1,21)]
 start=date(2026,1,1)
 for m in data['machine']:
  for prod in data['product']:
   data['machine_product'].append(dict(machine_id=m['machine_id'],product_id=prod['product_id'],ideal_cycle_seconds=round(rng.uniform(12,55),2),effective_from='2026-01-01',effective_to=''))
 for d in range(days):
  dt=start+timedelta(days=d)
  for code,h in [('A',6),('B',14),('C',22)]:
   sid=f'SHIFT-{dt.isoformat()}-{code}'
   data['shift'].append(dict(shift_id=sid,plant_id='PLANT-001',shift_date=dt.isoformat(),code=code,start_at=stamp(dt,h),end_at=stamp(dt,h+8),planned_break_minutes=30))
 data['downtime_reason']=[dict(reason_id='R-BREAK',description='Scheduled break',category='BREAK',planned='true'),dict(reason_id='R-FAIL',description='Equipment fault',category='FAILURE',planned='false'),dict(reason_id='R-CHANGE',description='Product changeover',category='CHANGEOVER',planned='false'),dict(reason_id='R-MICRO',description='Micro-stop',category='MICRO_STOP',planned='false')]
 # Every machine/shift has an order and a complete non-overlapping timeline.
 orders=[];segments=[];sequence=collections.Counter()
 for s in data['shift']:
  shift_start=datetime.fromisoformat(s['start_at'])
  for m in data['machine']:
   idx=len(orders)+1;pid=f'PROD-{rng.randint(1,20):03}';oid=f'PO-2026-{idx:06}'
   order=dict(order_id=oid,machine_id=m['machine_id'],shift_id=s['shift_id'],product_id=pid,status='COMPLETED',planned_units=600)
   orders.append(order)
   # 480 minutes = 30 planned break + 10 changeover + 5 fault + 3 microstop + 432 run.
   pattern=[('RUN',120,None),('BREAK',30,'R-BREAK'),('RUN',120,None),('CHANGEOVER',10,'R-CHANGE'),('RUN',100,None),('DOWN',5,'R-FAIL'),('RUN',60,None),('MICRO_STOP',3,'R-MICRO'),('RUN',32,None)]
   minute=0
   for state,duration,reason in pattern:
    sequence[m['machine_id']]+=1
    eid=f"EVT-{m['machine_id']}-{sequence[m['machine_id']]:06}"
    a=shift_start+timedelta(minutes=minute);b=a+timedelta(minutes=duration);minute+=duration
    segments.append(dict(event_id=eid,machine_id=m['machine_id'],order_id=oid,shift_id=s['shift_id'],start_at=a.isoformat(timespec='seconds'),end_at=b.isoformat(timespec='seconds'),state=state,reason_id=reason or '',issue_type=''))
 data['production_order']=orders
 # Scale event volume by subdividing RUN intervals, preserving time accounting.
 base=len(segments)
 if events<base:events=base
 # Heap avoids scanning all events on every split (important at full scale).
 heap=[]
 for i,e in enumerate(segments):
  if e['state']=='RUN':
   duration=(datetime.fromisoformat(e['end_at'])-datetime.fromisoformat(e['start_at'])).total_seconds()
   if duration>=2:heapq.heappush(heap,(-duration,i))
 while len(segments)<events and heap:
  neg_duration,ix=heapq.heappop(heap)
  e=segments[ix];a=datetime.fromisoformat(e['start_at']);b=datetime.fromisoformat(e['end_at'])
  if (b-a).total_seconds()<2:continue
  mid=a+timedelta(seconds=int((b-a).total_seconds()//2))
  if mid<=a or mid>=b:continue
  e['end_at']=mid.isoformat(timespec='seconds');sequence[e['machine_id']]+=1
  extra=dict(e,event_id=f"EVT-{e['machine_id']}-{sequence[e['machine_id']]:06}",start_at=mid.isoformat(timespec='seconds'),end_at=b.isoformat(timespec='seconds'))
  segments.append(extra)
  for j in (ix,len(segments)-1):
   part=segments[j];dur=(datetime.fromisoformat(part['end_at'])-datetime.fromisoformat(part['start_at'])).total_seconds()
   if dur>=2:heapq.heappush(heap,(-dur,j))
 # Record the cycle-time setting observed on each event for comparison with master data.
 order_by_id={o['order_id']:o for o in orders}
 ideal_by_pair={(r['machine_id'],r['product_id']):r['ideal_cycle_seconds'] for r in data['machine_product']}
 for event in segments:
  order=order_by_id[event['order_id']]
  event['observed_ideal_cycle_seconds']=ideal_by_pair[(event['machine_id'],order['product_id'])]
 data['state_event']=segments
 # Counts reflect machine speed, not independent random numbers.
 # Split each order's production across count records while retaining totals.
 norders=len(orders);records=max(records,norders*2)
 ncounts=records//2;nqc=records-ncounts
 count_seq=collections.Counter()
 shift_lookup={s['shift_id']:s for s in data['shift']}
 ideals={(x['machine_id'],x['product_id']):float(x['ideal_cycle_seconds']) for x in data['machine_product']}
 run_seconds=432*60
 targets={}
 for o in orders:
  efficiency=rng.uniform(0.75,0.98)
  targets[o['order_id']]=max(1,round(run_seconds/ideals[(o['machine_id'],o['product_id'])]*efficiency))
 count_slots=collections.Counter(orders[i%norders]['order_id'] for i in range(ncounts))
 remaining=dict(targets)
 for i in range(ncounts):
  o=orders[i%norders];oid=o['order_id'];count_seq[oid]+=1;k=count_seq[oid]
  slots=count_slots[oid]
  delta=remaining[oid]//slots
  if remaining[oid]%slots:delta+=1
  remaining[oid]-=delta;count_slots[oid]-=1
  data['production_count'].append(dict(count_id=f"CNT-{oid}-{k:06}",order_id=oid,machine_id=o['machine_id'],shift_id=o['shift_id'],at=shift_lookup[o['shift_id']]['start_at'],delta_total=delta,correction_of='',issue_type=''))
 # Quality inspections use a small, deterministic reject rate per order.
 qc_slots=collections.Counter(orders[i%norders]['order_id'] for i in range(nqc))
 scrap_remaining={oid:round(qty*rng.uniform(0.005,0.035)) for oid,qty in targets.items()}
 for i in range(nqc):
  o=orders[i%norders];oid=o['order_id'];slots=qc_slots[oid]
  scrap_delta=(scrap_remaining[oid]+slots-1)//slots
  scrap_remaining[oid]-=scrap_delta;qc_slots[oid]-=1
  data['quality_inspection'].append(dict(inspection_id=f'QC-2026-{i+1:06}',order_id=oid,machine_id=o['machine_id'],shift_id=o['shift_id'],at=shift_lookup[o['shift_id']]['start_at'],scrap_units=scrap_delta,rework_units=0,issue_type=''))
 # Label anomalies without corrupting unrelated records.
 def mark(entity,row,issue,decision):
  row['issue_type']=issue;truth.append(dict(issue_id=f'ISSUE-{len(truth)+1:05}',entity=entity,record_id=row[{'state_event':'event_id','production_count':'count_id','quality_inspection':'inspection_id'}[entity]],issue_type=issue,expected_decision=decision))
 if len(segments)>2:
  target=segments[-1]
  # Create a genuine overlap with the preceding event on the same machine.
  predecessors=[e for e in segments[:-1] if e['machine_id']==target['machine_id'] and e['shift_id']==target['shift_id'] and e['end_at']<=target['start_at']]
  if predecessors:
   previous=max(predecessors,key=lambda e:e['end_at'])
   target['start_at']=(datetime.fromisoformat(previous['end_at'])-timedelta(minutes=1)).isoformat(timespec='seconds')
   mark('state_event',target,'OVERLAPPING_STATE','FLAG_EXCLUDE')
 if data['production_count']:
  c=data['production_count'][-1];c['delta_total']=-99;mark('production_count',c,'NEGATIVE_WITHOUT_CORRECTION','FLAG_EXCLUDE')
 if data['quality_inspection']:
  q=data['quality_inspection'][-1];q['scrap_units']=99999;mark('quality_inspection',q,'SCRAP_EXCEEDS_TOTAL','FLAG_EXCLUDE')
 # Wrong machine/product ideal cycle: observed setting differs from master data.
 if len(segments)>5:
  cycle_target=segments[-5]
  cycle_target['observed_ideal_cycle_seconds']=round(float(cycle_target['observed_ideal_cycle_seconds'])*1.5,2)
  mark('state_event',cycle_target,'WRONG_IDEAL_CYCLE_TIME','REVIEW_MASTER_DATA')
 # Actual DOWN interval overlaps the recorded planned BREAK event on same shift.
 if len(segments)>5:
  down_target=segments[-3]
  breaks=[e for e in segments if e['machine_id']==down_target['machine_id'] and e['shift_id']==down_target['shift_id'] and e['state']=='BREAK']
  if breaks:
   planned_break=breaks[0]
   begin=datetime.fromisoformat(planned_break['start_at'])+timedelta(minutes=5)
   down_target['start_at']=begin.isoformat(timespec='seconds')
   down_target['end_at']=(begin+timedelta(minutes=10)).isoformat(timespec='seconds')
   down_target['state']='DOWN'
   down_target['reason_id']='R-FAIL'
   mark('state_event',down_target,'DOWNTIME_OVERLAPS_BREAK','REVIEW_SCHEDULE')
 # Compute OEE from clean source rows only; quarantine all labelled exceptions.
 clean_events=[e for e in segments if not e['issue_type']]
 counts=collections.Counter();scrap=collections.Counter()
 for c in data['production_count']:
  if not c['issue_type']:counts[c['order_id']]+=int(c['delta_total'])
 for q in data['quality_inspection']:
  if not q['issue_type']:scrap[q['order_id']]+=int(q['scrap_units'])
 ideals={(x['machine_id'],x['product_id']):float(x['ideal_cycle_seconds']) for x in data['machine_product']}
 for o in orders:
  relevant=[e for e in clean_events if e['order_id']==o['order_id']]
  run=sum((datetime.fromisoformat(e['end_at'])-datetime.fromisoformat(e['start_at'])).total_seconds()/60 for e in relevant if e['state']=='RUN')
  planned=450.0;total=counts[o['order_id']];good=max(0,total-scrap[o['order_id']]);ideal=ideals[(o['machine_id'],o['product_id'])]
  a=run/planned;p=total*ideal/(run*60) if run else 0;q=good/total if total else 0
  # Out-of-range performance is an exception, not silently clipped.
  status='REVIEW' if p>1 or p<0 or a>1 or any(e['order_id']==o['order_id'] for e in segments if e['issue_type']) else 'OK'
  data['oee_aggregate'].append(dict(aggregate_id=f"OEE-{o['order_id']}",machine_id=o['machine_id'],shift_id=o['shift_id'],planned_minutes=planned,run_minutes=round(run,5),total_units=total,good_units=good,availability=round(a,6),performance=round(p,6),quality=round(q,6),oee=round(a*p*q,6),status=status))
 for table,rows in data.items():save(out,table,rows)
 validation=validate(data)
 (out/'validation_summary.json').write_text(json.dumps(validation,indent=2))
 manifest={'seed':seed,'days':days,'machines':machines,'requested_events':events,'requested_count_inspection_records':records,'row_counts':{k:len(v) for k,v in data.items()},'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob('*.csv'))},'provenance':'Fully synthetic; no external source data'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 return manifest,validation

def validate(data):
 errors=[];pk={'plant':'plant_id','line':'line_id','machine':'machine_id','shift':'shift_id','product':'product_id','production_order':'order_id','downtime_reason':'reason_id','state_event':'event_id','production_count':'count_id','quality_inspection':'inspection_id','oee_aggregate':'aggregate_id','ground_truth':'issue_id'}
 for t,k in pk.items():
  vals=[r[k] for r in data[t]]
  if len(vals)!=len(set(vals)):errors.append(f'Duplicate PK in {t}')
 lookup={t:{r[k] for r in data[t]} for t,k in pk.items()}
 for t,refs in {'line':{'plant_id':'plant'},'machine':{'line_id':'line'},'shift':{'plant_id':'plant'},'production_order':{'machine_id':'machine','shift_id':'shift','product_id':'product'},'state_event':{'machine_id':'machine','order_id':'production_order','shift_id':'shift'},'production_count':{'order_id':'production_order','machine_id':'machine','shift_id':'shift'},'quality_inspection':{'order_id':'production_order','machine_id':'machine','shift_id':'shift'}}.items():
  for r in data[t]:
   for field,parent in refs.items():
    if r[field] not in lookup[parent]:errors.append(f'Broken FK {t}.{field}')
 for r in data['state_event']:
  if not r['issue_type'] and r['start_at']>=r['end_at']:errors.append('Invalid state interval')
 return {'status':'PASS' if not errors else 'FAIL','structural_errors':errors,'labelled_anomalies':len(data['ground_truth']),'note':'Structural checks only. Independently validate all five intentional anomalies using src/validator.py.'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='outputs/starter');ap.add_argument('--profile',choices=['starter','full'],default='starter');ap.add_argument('--seed',type=int,default=SEED);args=ap.parse_args()
 cfg=dict(days=2,machines=6,events=300,records=900) if args.profile=='starter' else dict(days=90,machines=30,events=100000,records=500000)
 manifest,validation=build(Path(args.out),seed=args.seed,**cfg)
 print(json.dumps({'rows':manifest['row_counts'],'validation':validation},indent=2))
if __name__=='__main__':main()
