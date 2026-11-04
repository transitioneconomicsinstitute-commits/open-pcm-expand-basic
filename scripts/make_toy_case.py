"""Write the synthetic 3-bus example. All numbers are invented."""
import json, os, sys, numpy as np, pandas as pd

def main(out):
    rng=np.random.default_rng(7); os.makedirs(out,exist_ok=True)
    h=np.arange(8760); hod=h%24; doy=h//24
    load=0.65+0.2*np.sin((hod-14)/24*2*np.pi)+0.08*np.cos(doy/365*2*np.pi)+rng.normal(0,0.02,8760)
    load=np.clip(load/load.max(),0.3,1)
    solar=np.clip(np.sin((hod-6)/12*np.pi),0,None)*(0.85+0.15*np.sin(doy/365*2*np.pi))
    wind=np.clip(0.35+0.2*np.sin(doy/365*2*np.pi+1)+rng.normal(0,0.12,8760),0,1)
    pd.DataFrame(dict(hour=h,load=load.round(4),solar=solar.round(4),wind=wind.round(4))).to_csv(f'{out}/profiles.csv',index=False)
    pd.DataFrame([dict(node=1,name='West',peak_MW=300),dict(node=2,name='Centre',peak_MW=500),dict(node=3,name='East',peak_MW=200)]).to_csv(f'{out}/nodes.csv',index=False)
    pd.DataFrame([dict(name='Old coal',node=1,type='thermal',mw=450,heat_rate=10.0,fuel_usd_mmbtu=3.0,vom=4,profile=''),
                  dict(name='Old peaker',node=2,type='thermal',mw=250,heat_rate=11.5,fuel_usd_mmbtu=8.0,vom=6,profile='')]).to_csv(f'{out}/generators.csv',index=False)
    pd.DataFrame([dict(name='L12',**{'from':1,'to':2},MVA=250,x_pu=0.1,loss_pct=1.5),
                  dict(name='L23',**{'from':2,'to':3},MVA=150,x_pu=0.1,loss_pct=1.5)]).to_csv(f'{out}/branches.csv',index=False)
    pd.DataFrame([dict(name='New CCGT 2',node=2,type='thermal',capex_usd_kw=1000,life=25,max_mw=600,heat_rate=6.8,fuel_usd_mmbtu=8.0,vom=3,fom_usd_kw_yr=15,profile=''),
                  dict(name='Solar 3',node=3,type='solar',capex_usd_kw=700,life=25,max_mw=800,vom=0,fom_usd_kw_yr=12,profile='solar'),
                  dict(name='Wind 1',node=1,type='wind',capex_usd_kw=1300,life=25,max_mw=500,vom=0,fom_usd_kw_yr=35,profile='wind')]).to_csv(f'{out}/candidates_gen.csv',index=False)
    pd.DataFrame([dict(name='L13 new',**{'from':1,'to':3},max_mw=400,capex_usd_mw=200000,life=40,loss_pct=2.0),
                  dict(name='L12 upgrade',**{'from':1,'to':2},max_mw=300,capex_usd_mw=150000,life=40,loss_pct=1.5)]).to_csv(f'{out}/candidates_lines.csv',index=False)
    json.dump(dict(base_year=2030,discount_rate=0.08,voll_usd_mwh=3000,ref_node=1),open(f'{out}/case.json','w'),indent=1)

if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else 'examples/toy_3bus')
