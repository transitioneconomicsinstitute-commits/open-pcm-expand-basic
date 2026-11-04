# open-pcm-expand-basic

A small least-cost expansion tool built on [OPEN-PCM](https://github.com/transitioneconomicsinstitute-commits/open-pcm). Given an OPEN-PCM case and a list of candidate generators and lines, it picks how many MW of each to build in one year so that annualised capital cost plus operating cost is lowest. It is a single linear program solved with HiGHS.

## What it does

- Candidate generators: `thermal`, `solar`, `wind`, each with a capital cost, life, fixed O&M and a build limit.
- Candidate lines between existing buses, with a capital cost per MW, life, losses and a build limit.
- Capital costs are annualised with the case discount rate (`crf` from OPEN-PCM).
- Operations run on 12 representative days (the 15th of each month) using the OPEN-PCM nodal dispatch: existing lines keep their DC power flow, and candidate lines are transport links sized by the build.
- Hourly operating costs are scaled to a full year by 8760 / number of hours.
- Outputs: `builds.csv`, hourly nodal `prices.csv` for the sampled hours, and `cost.json` (total, capital, operating, unserved energy).

## What it does not do

One year only (no multi-year or rolling plans), no storage candidates, no reserves, no unit commitment, no retirements, no scenarios, and no chronological full-year check of the result. Run the chosen builds through OPEN-PCM for a full-year dispatch if you need one.

## Install

```
pip install git+https://github.com/transitioneconomicsinstitute-commits/open-pcm-expand-basic.git
```

For development:

```
pip install -e ".[test]"
```

## Quick start

```
open-pcm-expand-basic examples/toy_3bus out
```

```python
import open_pcm_expand_basic as X
res = X.expand(X.Case('examples/toy_3bus'))
print(res['builds'])
print(res['cost'])
```

## Example data

`examples/toy_3bus` is a synthetic three-bus system written by `scripts/make_toy_case.py`. The numbers are made up and do not describe any real power system. With these inputs the tool builds wind at bus 1, solar at bus 3, some CCGT at bus 2 and both candidate lines.

## Case format

Everything OPEN-PCM reads (`case.json`, `nodes.csv`, `generators.csv`, `branches.csv`, `profiles.csv`), plus either or both of:

| File | Columns |
|---|---|
| `candidates_gen.csv` | `name`, `node`, `type` (`thermal`, `solar`, `wind`), `capex_usd_kw`, `life`, `max_mw`, optional `fom_usd_kw_yr`, `heat_rate`, `fuel_usd_mmbtu`, `vom`, `profile` (solar/wind) |
| `candidates_lines.csv` | `name`, `from`, `to`, `max_mw`, `capex_usd_mw`, `life`, optional `loss_pct` |

Without either file the run is a plain dispatch of the sampled days.

## Tests

```
python -m pytest -q
```

## Licence

MIT. See `LICENSE`.
