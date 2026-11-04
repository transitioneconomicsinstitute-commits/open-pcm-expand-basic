"""Single-year least-cost expansion.

Candidate generators and candidate lines are added to the OPEN-PCM dispatch LP of a set of
representative days. The objective is annualised capital cost plus operating cost, so the
solve picks how many MW of each candidate to build and how to run the system with it.
"""
import os, numpy as np, pandas as pd
from open_pcm.case import Case as _Base, CAL, crf, num
from open_pcm.model import build, solve

GEN_COLS=['name','node','type','capex_usd_kw','life','max_mw']
LINE_COLS=['name','from','to','max_mw','capex_usd_mw','life']

class Case(_Base):
    """An OPEN-PCM case folder plus candidates_gen.csv and/or candidates_lines.csv."""
    def __init__(s,path,validate=True):
        super().__init__(path,validate=validate)
        def opt(f,cols):
            p=os.path.join(path,f)
            if not os.path.exists(p): return pd.DataFrame(columns=cols)
            d=pd.read_csv(p); miss=[c for c in cols if c not in d.columns]
            if miss: raise ValueError(f'{f} is missing column(s): {", ".join(miss)}')
            return d
        s.cand_gen=opt('candidates_gen.csv',GEN_COLS); s.cand_lines=opt('candidates_lines.csv',LINE_COLS)
        known=set(s.nodes.node.astype(int)); bad=[]
        for f,d,cols in (('candidates_gen.csv',s.cand_gen,['node']),('candidates_lines.csv',s.cand_lines,['from','to'])):
            for i,r in enumerate(d.to_dict('records')):
                for c in cols:
                    if int(r[c]) not in known: bad.append(f'{f} row {i+2} ({r["name"]}): {c}={r[c]} is not a node in nodes.csv')
                for c in ('max_mw','life'):
                    if not num(r.get(c),-1)>0: bad.append(f'{f} row {i+2} ({r["name"]}): {c} must be > 0')
        for i,r in enumerate(s.cand_gen.to_dict('records')):
            if r['type'] not in ('thermal','solar','wind'):
                bad.append(f'candidates_gen.csv row {i+2} ({r["name"]}): type must be thermal, solar or wind')
            elif r['type']!='thermal' and r.get('profile') not in s.profiles.columns:
                bad.append(f'candidates_gen.csv row {i+2} ({r["name"]}): profile {r.get("profile")!r} is not in profiles.csv')
        if bad: raise ValueError('invalid candidates:\n  - '+'\n  - '.join(bad))

def rep_days(days=(15,)):
    """Hour-of-year indices for the given day(s) of every month. Each hour stands for 8760/len(hours) hours."""
    H=[]
    for m in range(1,13):
        for d in days:
            i0=CAL.get_loc(CAL[(CAL.month==m)&(CAL.day==d)&(CAL.hour==0)][0]); H+=range(i0,i0+24)
    return np.array(H)

def expand(case, year=None, hours=None, method='ipm', threads=None):
    """Least-cost builds for one year. Returns dict(builds, cost, prices, model).

    hours defaults to rep_days(). Hourly costs are scaled to a full year by 8760/len(hours).
    """
    y=case.cfg['base_year'] if year is None else year
    H=rep_days() if hours is None else np.asarray(hours)
    scale=8760/len(H); r=case.cfg['discount_rate']
    m=build(case,H,year=y); lp=m['lp']; bal=m['bal']; T=len(H); ni={int(b):i for i,b in enumerate(m['nid'])}
    loss_default=case.cfg['line_loss_frac']; fc=case.cfg['flow_cost_usd_mwh']
    built=[]
    for g in case.cand_gen.to_dict('records'):
        ann=(num(g['capex_usd_kw'])*crf(r,num(g['life']))+num(g.get('fom_usd_kw_yr'),0))*1000/scale
        K=lp.var((1,),ann,0,num(g['max_mw']))
        if g['type']=='thermal':
            cost=num(g.get('heat_rate'),0)*num(g.get('fuel_usd_mmbtu'),0)+num(g.get('vom'),0); cf=np.ones(T)
        else:
            cost=num(g.get('vom'),0); cf=case.profiles[g['profile']].values[H]
        gen=lp.var((T,),cost,0,np.inf)
        row=lp.rows((T,),-np.inf,0); lp.a(row,gen); lp.a(row,np.repeat(K,T),-cf)
        lp.a(bal[ni[int(g['node'])]],gen)
        built.append(dict(name=g['name'],kind='generator',type=g['type'],var=K,gen=gen,ann=ann*scale))
    for l in case.cand_lines.to_dict('records'):
        ann=num(l['capex_usd_mw'])*crf(r,num(l['life']))/scale
        K=lp.var((1,),ann,0,num(l['max_mw'])); loss=num(l.get('loss_pct'),loss_default*100)/100
        ia,ib=ni[int(l['from'])],ni[int(l['to'])]
        fp=lp.var((T,),fc,0,np.inf); fm=lp.var((T,),fc,0,np.inf)
        for f in (fp,fm):
            row=lp.rows((T,),-np.inf,0); lp.a(row,f); lp.a(row,np.repeat(K,T),-1)
        lp.a(bal[ia],fp,-1); lp.a(bal[ia],fm,1-loss); lp.a(bal[ib],fp,1-loss); lp.a(bal[ib],fm,-1)
        built.append(dict(name=l['name'],kind='line',type='line',var=K,gen=None,ann=ann*scale))
    m=solve(m,method=method,threads=threads)
    if m['status']!='Optimal': raise RuntimeError(f'expansion {y}: {m["status"]}')
    x=m['x']
    rows=[dict(year=y,name=b['name'],kind=b['kind'],type=b['type'],MW=float(x[b['var']][0]),
               annual_capex_usd=float(x[b['var']][0])*b['ann']) for b in built]
    builds=pd.DataFrame(rows,columns=['year','name','kind','type','MW','annual_capex_usd'])
    capex=float(builds.annual_capex_usd.sum())
    total=float(np.dot(np.concatenate(lp.c),x))*scale
    use=float(x[m['use']].sum())*scale
    prices=pd.DataFrame((m['dual'][bal]).T,columns=list(m['nid'])); prices.insert(0,'hour',H)
    cost=dict(year=y,total_usd=total,annual_capex_usd=capex,operating_usd=total-capex,unserved_MWh=use)
    return dict(builds=builds,cost=cost,prices=prices,model=m)
