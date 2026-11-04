import argparse, json, os
from .expand import Case, expand

def main(argv=None):
    p=argparse.ArgumentParser(prog='open-pcm-expand-basic',description='Least-cost generation and line builds for one year.')
    p.add_argument('case'); p.add_argument('out'); p.add_argument('--year',type=int)
    p.add_argument('--threads',type=int)
    a=p.parse_args(argv)
    res=expand(Case(a.case),a.year,threads=a.threads)
    os.makedirs(a.out,exist_ok=True)
    res['builds'].to_csv(os.path.join(a.out,'builds.csv'),index=False)
    res['prices'].to_csv(os.path.join(a.out,'prices.csv'),index=False)
    with open(os.path.join(a.out,'cost.json'),'w') as f: json.dump(res['cost'],f,indent=1)
    b=res['builds']
    for r in b[b.MW>0.5].itertuples(): print(f'{r.name:<16} {r.kind:<9} {r.MW:9.1f} MW')
    print(f"total {res['cost']['total_usd']/1e6:.1f} M USD/yr, unserved {res['cost']['unserved_MWh']:.0f} MWh")

if __name__=='__main__': main()
