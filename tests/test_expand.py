import shutil, json, numpy as np, pandas as pd, pytest
from pathlib import Path
import open_pcm_expand_basic as X
from open_pcm_expand_basic.__main__ import main

CASE=Path(__file__).resolve().parents[1]/'examples'/'toy_3bus'

@pytest.fixture(scope='module')
def res():
    return X.expand(X.Case(str(CASE)))

def copy(tmp_path):
    d=tmp_path/'c'; shutil.copytree(CASE,d); return d

def test_toy_builds_and_serves_load(res):
    b=res['builds'].set_index('name')
    assert b.MW.sum()>100
    assert res['cost']['unserved_MWh']<1
    assert (b.MW<=pd.read_csv(CASE/'candidates_gen.csv').set_index('name').max_mw.reindex(b.index).fillna(1e9)+1e-6).all()

def test_cost_split_adds_up(res):
    c=res['cost']
    assert c['annual_capex_usd']==pytest.approx(res['builds'].annual_capex_usd.sum())
    assert c['total_usd']==pytest.approx(c['annual_capex_usd']+c['operating_usd'])
    assert c['operating_usd']>0

def test_expensive_candidates_are_not_built(tmp_path):
    d=copy(tmp_path)
    g=pd.read_csv(d/'candidates_gen.csv'); g['capex_usd_kw']=1e6; g.to_csv(d/'candidates_gen.csv',index=False)
    l=pd.read_csv(d/'candidates_lines.csv'); l['capex_usd_mw']=1e9; l.to_csv(d/'candidates_lines.csv',index=False)
    r=X.expand(X.Case(str(d)))
    assert r['builds'].MW.max()<1e-3

def test_line_built_to_reach_cheap_supply(tmp_path):
    # Only cheap supply is at bus 1, existing links are small: a new line should be built.
    d=copy(tmp_path)
    g=pd.read_csv(d/'candidates_gen.csv'); g=g[g.name=='New CCGT 2'].assign(node=1,name='CCGT 1',fuel_usd_mmbtu=2.0)
    g.to_csv(d/'candidates_gen.csv',index=False)
    r=X.expand(X.Case(str(d))); b=r['builds'].set_index('name')
    assert b.loc['CCGT 1','MW']>100
    assert b.loc[['L13 new','L12 upgrade'],'MW'].sum()>50

def test_bad_candidate_node(tmp_path):
    d=copy(tmp_path)
    g=pd.read_csv(d/'candidates_gen.csv'); g.loc[0,'node']=9; g.to_csv(d/'candidates_gen.csv',index=False)
    with pytest.raises(ValueError, match='node=9'): X.Case(str(d))

def test_missing_candidate_files_means_dispatch_only(tmp_path):
    d=copy(tmp_path); (d/'candidates_gen.csv').unlink(); (d/'candidates_lines.csv').unlink()
    r=X.expand(X.Case(str(d)))
    assert r['builds'].empty and r['cost']['annual_capex_usd']==0

def test_cli(tmp_path, capsys):
    main([str(CASE),str(tmp_path/'out')])
    assert (tmp_path/'out'/'builds.csv').exists() and (tmp_path/'out'/'prices.csv').exists()
    assert json.load(open(tmp_path/'out'/'cost.json'))['total_usd']>0
    assert 'total' in capsys.readouterr().out
