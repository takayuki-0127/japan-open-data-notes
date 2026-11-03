"""本体：5つのモデルを、ランダム分割（70:30、5回）で比べる。

python 03_分析.py tune   … RSF・GBM の設定を1回目の分割の学習データの中で選ぶ（results/tuning.csv）
python 03_分析.py main   … 5回の分割で5モデル（results/main_metrics.csv、results/calibration_main.csv）
"""
import sys, time, json
import numpy as np, pandas as pd
from common import DATA, RES, SEED
from models import design, fit_predict, G
from metrics import evaluate

MODELS = ["Cox", "Cox＋交互作用", "RSF", "GBM-Cox", "GBM-離散時間"]


def load(event="E"):
    s = pd.read_parquet(DATA / "sample100k.parquet")
    mr = pd.read_parquet(DATA / "muni_rate_outside.parquet")
    s = s.merge(mr, on="muni", how="left")
    s["lmuni_rate"] = np.log(s.muni_rate.fillna(mr.muni_rate.median()))
    s["T"] = np.ceil(s["T"] * 12) / 12          # 月単位に切り上げ（RSF の記憶量を抑えるため。全モデル共通）
    s["E"] = s[event]
    return s


def params():
    p = RES / "tuning_best.json"
    return json.loads(p.read_text()) if p.exists() else {"RSF": {}, "GBM-Cox": {}, "GBM-離散時間": {}}


def run(models, tr, te, featset="all", seed=SEED, tau=8.0, tag=None, par=None):
    par = par or params()
    Xtr = design(tr, featset); Xte = design(te, featset, ref=Xtr.columns)
    out, cal = [], []
    for m in models:
        t0 = time.time()
        S = fit_predict(m, Xtr, tr["T"].values, tr["E"].values, Xte, seed=seed, params=par.get(m, {}))
        r, c = evaluate(S, tr["T"].values, tr["E"].values, te["T"].values, te["E"].values, tau=tau)
        r.update(model=m, sec=round(time.time() - t0, 1), **(tag or {}))
        out.append(r); cal += [{**x, "model": m, **(tag or {})} for x in c]
        print(r, flush=True)
    return out, cal


def split(s, seed, frac=0.7):
    rng = np.random.default_rng(seed); m = rng.random(len(s)) < frac
    return s[m].reset_index(drop=True), s[~m].reset_index(drop=True)


if __name__ == "__main__":
    stage = sys.argv[1]
    s = load()
    if stage == "tune":
        tr, _ = split(s, 0)
        a, b = split(tr, 99, 0.75)       # 学習データの中をさらに分ける（評価用の30%は使わない）
        rows = []
        grid = {"RSF": [{"leaf": l, "mf": f} for l in (20, 60, 150) for f in ("sqrt", 0.5)],
                "GBM-Cox": [{"depth": d, "mcw": w} for d in (2, 4, 6) for w in (20, 100)],
                "GBM-離散時間": [{"depth": d, "mcw": w} for d in (2, 4, 6) for w in (20, 100)]}
        best = {}
        for m, gl in grid.items():
            for g in gl:
                o, _ = run([m], a, b, par={m: g}, tag={"cfg": json.dumps(g)})
                rows += o
            df = pd.DataFrame([r for r in rows if r["model"] == m])
            best[m] = json.loads(df.sort_values("IBS").iloc[0]["cfg"])
        pd.DataFrame(rows).to_csv(RES / "tuning.csv", index=False)
        (RES / "tuning_best.json").write_text(json.dumps(best, ensure_ascii=False))
        print(best)
    if stage == "main":
        rows, cals = [], []
        for k in range(5):
            tr, te = split(s, k)
            o, c = run(MODELS, tr, te, seed=k, tag={"split": k})
            rows += o; cals += c
            pd.DataFrame(rows).to_csv(RES / "main_metrics.csv", index=False)
            pd.DataFrame(cals).to_csv(RES / "calibration_main.csv", index=False)
