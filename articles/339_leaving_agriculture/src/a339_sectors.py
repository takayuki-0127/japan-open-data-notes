"""339：働く人の半分が農業（第1次産業）を離れたのは、いつだったのか。
国勢調査の産業3部門別の就業者数（1920〜2020年）。割合は「分類不能の産業」を除いて計算する。
"""
import json
import numpy as np, pandas as pd, openpyxl
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省統計局「国勢調査」時系列データ（産業4・同【参考】）をもとに作成者が加工して作成"
def read(f, sheet=0):
    ws = openpyxl.load_workbook(DATA / "raw" / f, data_only=True).worksheets[sheet]
    return [[("" if v is None else v) for v in r] for r in ws.iter_rows(values_only=True)]
def table(rows, years, ncol):
    rec = []
    for r in rows:
        if r[0] in ("総数", "男", "女") and isinstance(r[4], (int, float)):
            for j, y in enumerate(years):
                v = r[4 + j]
                rec.append((r[0], str(r[1]), str(r[3]), y, float(v) if isinstance(v, (int, float)) else (float(v) if str(v).replace(".", "").isdigit() else np.nan)))
    return pd.DataFrame(rec, columns=["sex", "sector", "industry", "year", "workers"])
old = read("kokusei_jikeiretsu_sangyo_1920_2000.xlsx")
i0 = next(i for i, r in enumerate(old) if str(r[0]).startswith("その1"))
i1 = next((i for i, r in enumerate(old) if i > i0 + 3 and str(r[0]).startswith("その")), len(old))
O = table(old[i0:i1], [1920, 1930, 1940, 1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000], 14)
Nw = table(read("kokusei_jikeiretsu_sangyo_1995_2020.xlsx"), [1995, 2000, 2005, 2010, 2015, 2020], 6)
def three(D, src):
    g = {}
    for sx in ("総数", "男", "女"):
        d = D[D.sex == sx]
        for y in sorted(d.year.unique()):
            e = d[d.year == y]; get = lambda k: float(e[e.industry.str.contains(k)].workers.sum())
            tot = float(e[(e.sector == "-") & (e.industry == "総数")].workers.iloc[0]); unk = get("分類不能")
            g[(sx, y)] = {"total": tot, "unknown": unk, "p1": get("（再掲）第1次"), "p2": get("（再掲）第2次"), "p3": get("（再掲）第3次"),
                          "agri": float(e[e.industry.isin(["農業", "農業，林業"])].workers.sum()), "source": src}
    return g
G = three(O, "旧分類（1920〜2000年）"); G2 = three(Nw, "新分類（1995〜2020年）")
rows = []
for (sx, y), v in sorted(G.items()): rows.append({"sex": sx, "year": y, **v})
for (sx, y), v in sorted(G2.items()):
    if y >= 2005: rows.append({"sex": sx, "year": y, **v})
S = pd.DataFrame(rows)
for k in ("p1", "p2", "p3"): S["s" + k[1]] = S[k] / (S.total - S.unknown) * 100          # 分類不能を除く割合
S["unknown_pct"] = S.unknown / S.total * 100
S = S.sort_values(["sex", "year"]); S.to_csv(DATA / "sectors_1920_2020.csv", index=False)
T = S[S.sex == "総数"].set_index("year")

def cross(series, level, down=True):
    """割合が level を最後にまたいだ年を、調査と調査のあいだを直線でつないで求める"""
    ys = list(series.index); hit = None
    for a, b in zip(ys[:-1], ys[1:]):
        va, vb = series[a], series[b]
        if (down and va >= level > vb) or (not down and va < level <= vb):
            hit = (a, b, round(a + (va - level) / (va - vb) * (b - a), 1))
    return hit
out = {"share": {int(y): {k: round(float(T.loc[y, k]), 1) for k in ("s1", "s2", "s3", "unknown_pct")} for y in T.index},
       "workers_man": {int(y): {k: round(float(T.loc[y, k]) / 1e4) for k in ("p1", "p2", "p3", "total", "agri")} for y in T.index}}
out["agri_share"] = {int(y): round(float(T.agri[y] / (T.total[y] - T.unknown[y]) * 100), 1) for y in T.index}
out["primary_below"] = {str(l): cross(T.s1, l) for l in (50, 40, 30, 20, 10, 5)}
out["tertiary_above"] = {str(l): cross(T.s3, l, False) for l in (30, 40, 50, 60, 70)}
out["secondary_peak"] = [int(T.s2.idxmax()), round(float(T.s2.max()), 1)]
out["primary_peak_workers"] = [int(T.p1.idxmax()), round(float(T.p1.max()) / 1e4)]
out["tertiary_overtakes_primary"] = cross(T.s1 - T.s3, 0)
out["secondary_overtakes_primary"] = cross(T.s1 - T.s2, 0)
# 5年あたりの下がり方（ポイント）
ys = list(T.index); out["primary_drop_pt_per_5yr"] = {f"{a}-{b}": round(float((T.s1[b] - T.s1[a]) / (b - a) * 5), 1) for a, b in zip(ys[:-1], ys[1:])}
# 1950→1970：割合の下がりを「第1次が減った分」と「ほかが増えた分」に分ける
a, b = T.loc[1950], T.loc[1970]; na, nb = a.total - a.unknown, b.total - b.unknown
only_others = a.p1 / (a.p1 + (nb - b.p1)) * 100          # 第1次の人数は1950年のまま、ほかだけ増えたとき
out["decomp_1950_1970"] = {"from": round(float(a.s1), 1), "to": round(float(b.s1), 1), "if_primary_unchanged": round(float(only_others), 1),
                           "primary_change_man": round(float(b.p1 - a.p1) / 1e4), "others_change_man": round(float((nb - b.p1) - (na - a.p1)) / 1e4)}
# 男女
out["by_sex"] = {sx: {int(y): round(float(v), 1) for y, v in S[S.sex == sx].set_index("year").s1.items()} for sx in ("男", "女")}
out["by_sex_below_50"] = {sx: cross(S[S.sex == sx].set_index("year").s1, 50) for sx in ("男", "女")}
out["women_share_in_primary"] = {int(y): round(float(S[(S.sex == "女") & (S.year == y)].p1.iloc[0] / T.p1[y] * 100), 1) for y in T.index}
# 確かめ：分類不能を含めた分母、旧分類と新分類の重なる年
out["check_incl_unknown"] = {int(y): round(float(T.p1[y] / T.total[y] * 100), 1) for y in T.index}
out["check_overlap_old_new"] = {y: [round(G[("総数", y)]["p1"] / (G[("総数", y)]["total"] - G[("総数", y)]["unknown"]) * 100, 1), round(G2[("総数", y)]["p1"] / (G2[("総数", y)]["total"] - G2[("総数", y)]["unknown"]) * 100, 1)] for y in (1995, 2000)}
json.dump(out, open(RES / "a339_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(8.8, 4.4))
for k, c, lab in (("s1", GREEN, "第1次産業（農林漁業）"), ("s2", ORANGE, "第2次産業（鉱業・建設・製造）"), ("s3", BLUE, "第3次産業（サービスなど）")):
    ax.plot(T.index, T[k], "-o", color=c, ms=4, lw=2); ax.annotate(f"{lab} {T[k].iloc[-1]:.1f}%", (2020, T[k].iloc[-1]), xytext=(-4, {"s1": 9, "s2": -16, "s3": 8}[k]), textcoords="offset points", ha="right", fontsize=9, color=c)
ax.axhline(50, color=GRAY, lw=0.8, ls="--"); ax.axvspan(1940, 1950, color="#f1f0ec", zorder=0); ax.text(1945, 3, "調査なし\n(1945年)", ha="center", fontsize=8, color=GRAY)
ax.annotate(f"1920年 {T.s1[1920]:.1f}%", (1920, T.s1[1920]), xytext=(6, 4), textcoords="offset points", fontsize=9); ax.annotate(f"1950年 {T.s1[1950]:.1f}%", (1950, T.s1[1950]), xytext=(4, 6), textcoords="offset points", fontsize=9)
ax.set_ylabel("就業者に占める割合（%）"); ax.set_xlabel("年"); ax.set_ylim(0, 80)
ax.set_title("第1次産業は1930年に5割を切り、戦後に戻ったあと、1955〜70年に一気に下がった")
save(fig, "a339_shares.png", SRC + "。割合は「分類不能の産業」を除く。2000年までは旧分類、2005年からは新分類")

fig, ax = plt.subplots(figsize=(8.8, 4.2))
ax.stackplot(T.index, T.p1 / 1e4, T.p2 / 1e4, T.p3 / 1e4, colors=[GREEN, ORANGE, BLUE], labels=["第1次", "第2次", "第3次"], alpha=0.85)
pk = out["primary_peak_workers"]; ax.annotate(f"第1次のピーク {pk[0]}年 {pk[1]:,}万人", (pk[0], pk[1]), xytext=(-10, -22), textcoords="offset points", fontsize=9, color="white", ha="center")
ax.annotate(f"2020年 {T.p1[2020] / 1e4:.0f}万人", (2020, T.p1[2020] / 1e4), xytext=(-6, 12), textcoords="offset points", fontsize=9, ha="right", color=INK)
ax.set_ylabel("就業者数（万人）"); ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_xlim(1920, 2020)
ax.set_title("第1次産業の人数は1950年の1,748万人が最多。1970年までの20年で約730万人減った")
save(fig, "a339_workers.png", SRC + "。分類不能の産業は図に入れていない")

fig, ax = plt.subplots(figsize=(8.8, 4.2))
for sx, c in (("男", BLUE), ("女", ORANGE)):
    d = S[S.sex == sx].set_index("year").s1; ax.plot(d.index, d, "-o", color=c, ms=4, lw=2, label=sx)
    for y in (1920, 1950, 1970): ax.annotate(f"{d[y]:.0f}%", (y, d[y]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9, color=c)
ax.axhline(50, color=GRAY, lw=0.8, ls="--"); ax.set_ylabel("就業者のうち第1次産業の割合（%）"); ax.set_xlabel("年"); ax.legend(frameon=False); ax.set_ylim(0, 75)
ax.set_title("女性は1955年まで働く人の半分以上が第1次産業。男性は1920年の時点で5割を下回っていた")
save(fig, "a339_by_sex.png", SRC)
print(out["agri_share"])
