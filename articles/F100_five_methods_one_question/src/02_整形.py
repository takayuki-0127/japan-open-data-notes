"""02 整形：市区町村×年の表、出生率、隣接の表を作り、2つの問い×2つの比べ方の分析用の表を書き出す。

単位：市区町村（政令市は市全体、東京23区は区ごと）。F16 と同じ。
"""
import json
import numpy as np, pandas as pd
from common import RAW, DATA, MIN_CHILD, wide, lfpr, enroll, facilities, base_covariates


# ---------- 1. 社会・人口統計体系（F16 で取得した表）を市区町村×年にする ----------
def tidy(rows, y):
    h = rows[0]; out = []
    for r in rows[1:]:
        code, name = r[0].split("_", 1)
        rec = {"code": code, "name": name, "year": y}
        for c, v in zip(h[1:], r[1:]):
            k = c.split("_")[0]; v = v.replace(",", "")
            try: rec[k] = float(v)
            except ValueError: rec[k] = np.nan
        out.append(rec)
    return pd.DataFrame(out)


def is_ward(code):
    # 政令指定都市の区（例 01101）は除き、市全体（例 01100）を残す。東京23区は残す
    return code[2] == "1" and code[4] != "0" and code[:2] != "13"


def panel():
    d = json.load(open(RAW / "f16_ssds_municipal.json", encoding="utf-8"))
    frames = {}
    for k, rows in d.items():
        frames.setdefault(int(k[:4]), []).append(tidy(rows, int(k[:4])))
    out = []
    for y, fs in frames.items():
        m = fs[0]
        for f in fs[1:]:
            add = f.drop(columns=["name", "year"])
            add = add[[c for c in add.columns if c == "code" or c not in m.columns]]
            m = m.merge(add, on="code", how="outer")
        out.append(m)
    p = pd.concat(out, ignore_index=True)
    return p[~p.code.apply(is_ward) & (p.code != "13100")]


# ---------- 2. 合計特殊出生率（ベイズ推定値、F20 で取得） ----------
def tfr():
    d = json.load(open(RAW / "f20_raw.json", encoding="utf-8"))
    s = {}
    for key in ["tfr_2013_17", "tfr_2018_22"]:
        s[key] = pd.Series({r[0]: (r[2] if isinstance(r[2], (int, float)) else np.nan) for r in d[key]})
    return pd.DataFrame(s)


# ---------- 3. 隣接（境界の弧を共有する区域。政令市の区は市にまとめる） ----------
def adjacency(codes):
    topo = json.load(open(RAW / "N03-21_210101.json", encoding="utf-8"))
    geoms = list(topo["objects"].values())[0]["geometries"]
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        a = np.cumsum(np.array(arc, dtype=float), axis=0)
        arcs.append(np.c_[a[:, 0] * sc[0] + tr[0], a[:, 1] * sc[1] + tr[1]])

    def unit(c):
        return c[:4] + "0" if is_ward(c) else c
    used, pts = {}, {}
    for g in geoms:
        c = g["properties"].get("N03_007")
        if not c:
            continue
        u = unit(c)
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        for poly in polys:
            for r in poly:
                for i in r:
                    j = i if i >= 0 else ~i
                    used.setdefault(u, set()).add(j)
                    pts.setdefault(u, []).append(arcs[j])
    codes = [c for c in codes if c in used]
    owner = {}
    for u in codes:
        for j in used[u]:
            owner.setdefault(j, set()).add(u)
    nb = {u: set() for u in codes}
    for j, us in owner.items():
        for u in us:
            nb[u] |= us - {u}
    cen = {u: np.vstack(pts[u]).mean(0) for u in codes}
    xy = np.array([cen[u] for u in codes])
    xy_km = np.c_[(xy[:, 0] - 137) * 111.32 * np.cos(np.radians(36)), (xy[:, 1] - 36) * 110.57]
    iso = 0
    for k, u in enumerate(codes):
        if not nb[u]:  # 島などで隣がない区域は、いちばん近い1区域を隣とする
            d = np.hypot(*(xy_km - xy_km[k]).T); d[k] = np.inf
            v = codes[int(np.argmin(d))]
            nb[u].add(v); nb[v].add(u); iso += 1
    rows = [(u, v) for u in codes for v in sorted(nb[u])]
    cen_df = pd.DataFrame(xy_km, index=codes, columns=["x_km", "y_km"])
    return pd.DataFrame(rows, columns=["code", "neighbor"]), cen_df, iso


if __name__ == "__main__":
    p = panel()
    p.to_csv(DATA / "panel_long.csv", index=False, encoding="utf-8")
    w = wide()
    T = tfr()
    g10, g15, g17, g05 = w[2010], w[2015], w[2017], w[2005]
    X = base_covariates(w)
    idx = X.index[(g10.A1405.reindex(X.index) >= MIN_CHILD)]
    T = T.reindex(idx)
    D10, D15, D05 = enroll(g10), enroll(g15), enroll(g05)
    F10, F15 = facilities(g10, g10.A1405), facilities(g15, g15.A1405)
    name = g15.name

    def chg(a, b):
        C = pd.DataFrame(index=a.index)
        C["女性65歳以上の割合の変化"] = 100 * (b.A130302 / b.A110102 - a.A130302 / a.A110102)
        C["女性15〜64歳の割合の変化"] = 100 * (b.A130202 / b.A110102 - a.A130202 / a.A110102)
        C["人口増減率"] = 100 * (b.A1101 / a.A1101 - 1)
        return C
    C = chg(g10, g15)
    common_extra = pd.DataFrame({
        "保育所等に通う子ども（2010）": D10,
        "前の5年の在所児の変化": D10 - D05,
    })
    # 問い1：保育所と出生率
    q1L = pd.concat([T.tfr_2018_22.rename("Y"), D15.rename("D"), F15.rename("D_fac"), X], axis=1)
    q1C = pd.concat([(T.tfr_2018_22 - T.tfr_2013_17).rename("Y"), (D15 - D10).rename("D"), (F15 - F10).rename("D_fac"),
                     X, common_extra, C,
                     T.tfr_2013_17.rename("出生率（2013〜17年）"),
                     (1000 * g10.A4101 / g10.A1101).rename("人口千人あたり出生数（2010）"),
                     lfpr(g10).rename("女性の労働力率（2010）"),
                     (lfpr(g10) - lfpr(g05)).rename("前の5年の労働力率の変化")], axis=1)
    # 問い2：保育所と女性の労働力率（F16 と同じ問い）
    q2L = pd.concat([lfpr(g15).rename("Y"), D15.rename("D"), F15.rename("D_fac"), X], axis=1)
    q2C = pd.concat([(lfpr(g15) - lfpr(g10)).rename("Y"), (D15 - D10).rename("D"), (F15 - F10).rename("D_fac"),
                     X, common_extra, C,
                     lfpr(g10).rename("女性の労働力率（2010）"),
                     (lfpr(g10) - lfpr(g05)).rename("前の5年の労働力率の変化"),
                     (100 * (g15.A1405 / g15.A1101 - g10.A1405 / g10.A1101)).rename("0〜5歳の割合の変化")], axis=1)
    out = {}
    for k, df in {"q1_level": q1L, "q1_change": q1C, "q2_level": q2L, "q2_change": q2C}.items():
        df = df.reindex(idx).replace([np.inf, -np.inf], np.nan).dropna()
        df.insert(0, "name", name.reindex(df.index))
        df.index.name = "code"
        df.to_csv(DATA / f"{k}.csv", encoding="utf-8")
        out[k] = df
        print(k, len(df), "Y", round(df.Y.mean(), 3), round(df.Y.std(), 3), "D", round(df.D.mean(), 2), round(df.D.std(), 2))
    codes = sorted(set().union(*[set(d.index) for d in out.values()]))
    A, cen, iso = adjacency(codes)
    A.to_csv(DATA / "adjacency.csv", index=False)
    cen.to_csv(DATA / "centroids_km.csv", index_label="code")
    print("隣接", A.code.nunique(), "区域、組", len(A) // 2, "、隣がなく最寄りを隣とした", iso, "、境界にない", len(codes) - A.code.nunique())
