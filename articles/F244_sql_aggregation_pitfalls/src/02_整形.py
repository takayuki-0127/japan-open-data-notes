"""02 整形：公開データの表（retail・item_dim・holidays）と、架空のネット書店の注文データを作って保存する。"""
import os, lib
ROOT = lib.ROOT
retail, dim, hol = lib.load_retail()
retail.to_csv(os.path.join(ROOT, "data", "retail.csv"), index=False)
dim.to_csv(os.path.join(ROOT, "data", "item_dim.csv"), index=False)
hol.to_csv(os.path.join(ROOT, "data", "holidays.csv"), index=False)
sim = lib.simulate(seed=1)
for k, v in sim.items():
    v.to_csv(os.path.join(ROOT, "data", "sim", f"{k}.csv.gz"), index=False)
fix = lib.simulate(**lib.FIXTURE_EDGE)
for k, v in fix.items():
    v.to_csv(os.path.join(ROOT, "data", "fixture", f"{k}.csv"), index=False)
print({k: len(v) for k, v in sim.items()}, {k: len(v) for k, v in fix.items()})
