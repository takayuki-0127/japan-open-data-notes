from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data'/'raw'; DATA=ROOT/'data'; RES=ROOT/'results'; FIG=ROOT/'figures'
for p in (DATA,RES,FIG): p.mkdir(exist_ok=True)
SEED=121
