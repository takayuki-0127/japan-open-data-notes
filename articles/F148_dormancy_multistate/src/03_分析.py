"""多状態モデル（活動・清算・合併・登記官による閉鎖、＋閉鎖からの復活）の推定。

1. 制度開始時にあった法人（old）: 全員が 2015年10月に「活動」から始まり、2026年10月まで全員を追えるので、
   Aalen–Johansen の推定値は「その状態にいる割合」の数え上げと一致する。月ごとの遷移強度（ハザード）も出す。
2. 新しく設立された法人（new）: 指定の時期がばらばらで、打ち切りの時点が違うので、指定からの月数で Aalen–Johansen を当てる。
3. 復活（3→0）を入れた多状態の Aalen–Johansen（old の株式会社）。復活の前の閉鎖の時期はデータにないので、
   復活はすべて「登記官による閉鎖」の状態から戻ったと仮定する（頑健性で、閉鎖したすべての状態から戻る仮定も試す）。
"""
import pandas as pd, numpy as np, json
from common import DATA, RES, SEED

old = pd.read_parquet(DATA / "old_cells.parquet")
new = pd.read_parquet(DATA / "new_cells.parquet")
rev = pd.read_parquet(DATA / "revival.parquet")
M = 133  # 2015-10 .. 2026-10 の月数
RN = {1: "清算の結了など", 2: "合併", 3: "登記官による閉鎖"}
out = {}

def old_curves(df, routes=(1, 2, 3)):
    N = df.n.sum()
    ev = df[df.route > 0].groupby(["m", "route"]).n.sum().unstack(fill_value=0).reindex(range(M), fill_value=0)
    for r in routes:
        if r not in ev: ev[r] = 0
    cif = ev.cumsum() / N
    atrisk = N - ev.sum(axis=1).cumsum().shift(fill_value=0)
    haz = ev.div(atrisk, axis=0)
    return N, ev, cif, atrisk, haz

# ---- 1. old: 種別ごとの11年の行き先 ----
rows = []
for k, g in [("すべて", old)] + list(old.groupby("kindj")):
    N, ev, cif, atrisk, haz = old_curves(g)
    end = cif.iloc[-1]
    tot = ev.sum()
    jan = ev[3][[m for m in range(M) if (m + 9) % 12 == 0]].sum()   # m=3 が 2016-01
    rows.append({"種別": k, "法人数_2015年10月": int(N), "清算の結了など": end[1], "合併": end[2], "登記官による閉鎖": end[3],
                 "活動のまま": 1 - end.sum(), "閉鎖のうち登記官による閉鎖の割合": tot[3] / tot.sum(),
                 "登記官による閉鎖のうち1月の割合": jan / max(tot[3], 1)})
t1 = pd.DataFrame(rows); t1.to_csv(RES / "old_routes_by_kind.csv", index=False, encoding="utf-8-sig")
print(t1.round(4).to_string())

# 年ごとの件数（old）
oy = old[old.route > 0].copy(); oy["year"] = 2015 + (oy.m + 9) // 12
ty = oy.groupby(["year", "kindj", "route"]).n.sum().unstack(fill_value=0).rename(columns=RN)
ty.to_csv(RES / "old_yearly_by_kind.csv", encoding="utf-8-sig")
# 月ごとの遷移強度（株式会社）
N, ev, cif, atrisk, haz = old_curves(old[old.kindj == "株式会社"])
hz = haz.rename(columns=RN); hz.index = [str(pd.Period("2015-10", "M") + i) for i in hz.index]
hz.to_csv(RES / "old_kk_monthly_hazard.csv", encoding="utf-8-sig")
cif.rename(columns=RN).to_csv(RES / "old_kk_cif.csv", encoding="utf-8-sig")

# 地域（old の株式会社）
ra = []
for a, g in old[old.kindj == "株式会社"].groupby("area"):
    N, ev, cif, _, _ = old_curves(g); e = cif.iloc[-1]; tot = ev.sum()
    ra.append({"地域": a, "法人数": int(N), "清算の結了など": e[1], "合併": e[2], "登記官による閉鎖": e[3],
               "閉鎖のうち登記官による閉鎖の割合": tot[3] / tot.sum()})
pd.DataFrame(ra).to_csv(RES / "old_kk_by_area.csv", index=False, encoding="utf-8-sig")
print(pd.DataFrame(ra).round(4).to_string())

# ---- 2. new: Aalen–Johansen（指定からの月数） ----
from ms import aj_new

nr = []
for k, g in new.groupby("kindj"):
    cur, ar = aj_new(g); cur.insert(0, "種別", k); nr.append(cur)
    for y in (5, 10):
        r = cur[cur.age_m == 12 * y].iloc[0]
        out[f"new_{k}_{y}年"] = {c: float(r[c]) for c in ["清算の結了など", "合併", "登記官による閉鎖", "活動", "1-KM_清算だけ"]}
        out[f"new_{k}_{y}年"]["リスク集合"] = int(ar.iloc[12 * y])
newcif = pd.concat(nr); newcif.to_csv(RES / "new_cif_by_kind.csv", index=False, encoding="utf-8-sig")
# 年齢（年）ごとの登記官による閉鎖のハザード（new）
hy = []
for k, g in new.groupby("kindj"):
    ev = g[g.route == 3].assign(ay=lambda x: x.age // 12).groupby("ay").n.sum()
    _, ar = aj_new(g)
    for y in range(11):
        pm = ar.iloc[12 * y: 12 * y + 12].sum()  # 法人・月
        hy.append({"種別": k, "設立からの年": y, "登記官による閉鎖": int(ev.get(y, 0)), "法人年": pm / 12,
                   "1万法人年あたり": ev.get(y, 0) / (pm / 12) * 1e4 if pm > 0 else np.nan})
hy = pd.DataFrame(hy); hy.to_csv(RES / "new_route3_by_age.csv", index=False, encoding="utf-8-sig")
print(hy.pivot(index="設立からの年", columns="種別", values="1万法人年あたり").round(2))

# ---- 3. 復活を入れた多状態 Aalen–Johansen（old の株式会社） ----
def aj_revival(df, rv, mode="route3"):
    N = df.n.sum()
    ev = df[df.route > 0].groupby(["m", "route"]).n.sum().unstack(fill_value=0).reindex(range(M), fill_value=0)[[1, 2, 3]]
    rr = rv.groupby("m").n.sum().reindex(range(M), fill_value=0)
    P = np.array([1.0, 0, 0, 0]); n = np.array([N, 0, 0, 0], float); traj = []
    for m in range(M):
        T = np.eye(4)
        d = ev.iloc[m].values
        if n[0] > 0:
            T[0, 1:] = d / n[0]; T[0, 0] = 1 - d.sum() / n[0]
        r = rr.iloc[m]
        if mode == "route3" and n[3] > 0:
            q = min(r / n[3], 1); T[3, 0] = q; T[3, 3] = 1 - q
        elif mode == "all" and n[1:].sum() > 0:
            q = min(r / n[1:].sum(), 1)
            for s in (1, 2, 3): T[s, 0] = q; T[s, s] = 1 - q
        P = P @ T; n = n @ T * 1.0  # 数のほうも同じ遷移で更新（期待値）
        n = np.array([N * P[0], N * P[1], N * P[2], N * P[3]])
        traj.append([m, *P])
    return pd.DataFrame(traj, columns=["m", "活動", "清算の結了など", "合併", "登記官による閉鎖"])

kk = old[old.kindj == "株式会社"]; rk = rev[(rev.group == "old") & (rev.kindj == "株式会社")]
base = aj_revival(kk, rk.iloc[0:0]); withr = aj_revival(kk, rk, "route3"); allr = aj_revival(kk, rk, "all")
ms = pd.concat({"復活なし": base.iloc[-1], "復活は登記官閉鎖から": withr.iloc[-1], "復活はすべての閉鎖から": allr.iloc[-1]}, axis=1).T.drop(columns="m")
ms.to_csv(RES / "multistate_revival_kk.csv", encoding="utf-8-sig"); print(ms.round(5))
out["revival_old_kk_total"] = int(rk.n.sum())
out["revival_all_total"] = int(rev.n.sum())
out["revival_old_share"] = float(rev[rev.group == "old"].n.sum() / rev.n.sum())
r3 = old[(old.kindj == "株式会社") & (old.route == 3)].n.sum()
out["revival_per_route3_old_kk"] = float(rk.n.sum() / r3)
ry = rev.assign(y=lambda x: x.revive_ym.str[:4]).groupby("y").n.sum(); ry.to_csv(RES / "revival_by_year.csv", encoding="utf-8-sig")

# ---- 4. 登記が残っている法人の「変化の見えなさ」 ----
al = pd.read_csv(__import__("common").RAW / "alive_process_20261030.csv.gz", dtype=str, keep_default_na=False); al["n"] = al.n.astype(int)
al = al[al.kind.isin(["301", "302", "305", "399"])]
ap = al.groupby(["group", "kind"])[["process", "n"]].apply(lambda g: pd.Series({"法人数": g.n.sum(), "指定のあと変更なし": g[g.process == "01"].n.sum() / g.n.sum(),
                                                              "所在地の変更": g[g.process == "12"].n.sum() / g.n.sum(),
                                                              "商号の変更": g[g.process == "11"].n.sum() / g.n.sum()}))
ap.to_csv(RES / "alive_process.csv", encoding="utf-8-sig"); print(ap.round(3))
out["t1"] = t1.to_dict(orient="records")
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
