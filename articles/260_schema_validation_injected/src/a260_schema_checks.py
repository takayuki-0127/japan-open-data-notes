"""260 取り込む前に、壊れたファイルを止めるチェックはどこまで効くか

SSDSE-B 2026年版（47都道府県×12年度×109項目）に、正解の分かる「壊れ」を10種類×200回ずつ入れて、
4段のチェック（下の段を含む）がそれぞれ何割を止めるかを数える。壊していないファイルで鳴る割合（空振り）も数える。
  L1 型と空欄　　：数値に読めるか、空欄がないか
  L2 ＋キー　　　：年度×地域コードが重複・欠けなし、地域コードが決まった47個か
  L3 ＋範囲　　　：負になりえない項目が負でないか、前年度からの変化が項目ごとの上限以内か
                   （上限は2025年版の2011〜2022年度で見た最大の変化×係数。2026年版の値は使わない）
  L4 ＋列どうし　：総数＝男＋女（丸めで±1,000まで）、うち数≦総数 など
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, read_raw, save, plt

SEED, N = 260, 200
codes, names, body = read_raw(DATA / "SSDSE-B-2026.csv")
body.columns = ["year"] + codes[1:]
pcodes, _, prev = read_raw(DATA / "SSDSE-B-2025.csv")
prev.columns = ["year"] + pcodes[1:]
ITEMS = codes[3:]
NAME = dict(zip(codes, names))
NEG_OK = {"B4101", "B4102", "B4103"}  # 気温は負になりうる
CODES47 = sorted(prev["Code"].unique())

# --- 範囲の上限：2025年版（2011〜2022年度）の前年度比の最大 ---
pv = prev.copy(); pv[ITEMS] = pv[ITEMS].apply(pd.to_numeric); pv["y"] = pv["year"].astype(int)
pv = pv.sort_values(["Code", "y"])
YOY_MAX = {}
for c in ITEMS:
    a = pv.groupby("Code")[c].shift(1); b = pv[c]
    if c in NEG_OK:  # 気温は差で見る
        YOY_MAX[c] = float((b - a).abs().max())
    else:
        r = (b / a - 1).replace([np.inf, -np.inf], np.nan).abs()
        YOY_MAX[c] = float(r.max())

RULES_L4 = [("A1101", ["A110101", "A110102"]), ("A1102", ["A110201", "A110202"]), ("A1301", ["A130101", "A130102"]),
            ("A1302", ["A130201", "A130202"]), ("A1303", ["A130301", "A130302"]), ("A4101", ["A410101", "A410102"]),
            ("A4200", ["A420001", "A420002"]), ("A5101", ["A510101", "A510102"]), ("A5102", ["A510201", "A510202"])]
LE_L4 = [("A1102", "A1101"), ("E3702", "E3701"), ("E4602", "E4601"), ("E650110", "E6501"), ("E650210", "E6502"),
         ("G7102", "G7101"), ("F3104", "F3103"), ("J250502", "J2505")]


def validate(df, mult=1.5):
    """4段のチェックを順に当て、段ごとに鳴った件数を返す（下の段を含む累積で使う）"""
    out = {}
    num = df[ITEMS].apply(pd.to_numeric, errors="coerce")
    out["L1"] = int(num.isna().sum().sum() + (df[ITEMS] == "").sum().sum())
    k = df[["year", "Code"]]
    yrs = df["year"].unique()
    out["L2"] = int(k.duplicated().sum() + abs(len(yrs) * 47 - len(df)) + (~df["Code"].isin(CODES47)).sum()
                    + (df.groupby("year").size() != 47).sum())
    n = num.copy(); n["Code"] = df["Code"].values; n["y"] = pd.to_numeric(df["year"], errors="coerce").values
    n = n.sort_values(["Code", "y"])
    bad = 0
    for c in ITEMS:
        v = n[c]
        if c not in NEG_OK:
            bad += int((v < 0).sum())
        a = n.groupby("Code")[c].shift(1)
        d = (v - a).abs() if c in NEG_OK else (v / a - 1).replace([np.inf, -np.inf], np.nan).abs()
        bad += int((d > YOY_MAX[c] * mult).sum())
    out["L3"] = bad
    bad = 0
    for tot, parts in RULES_L4:
        bad += int(((num[tot] - num[parts].sum(axis=1)).abs() > 1000).sum())
    for small, big in LE_L4:
        bad += int((num[small] > num[big]).sum())
    out["L4"] = bad
    return out


def corrupt(df, kind, rng):
    d = df.copy()
    i = int(rng.integers(0, len(d)))
    num_items = [c for c in ITEMS if c not in NEG_OK]
    c = num_items[int(rng.integers(0, len(num_items)))]
    if kind == "K1 空欄":
        d.loc[i, c] = ""
    elif kind == "K2 数字の代わりに記号":
        d.loc[i, c] = ["-", "…", "x", "***"][int(rng.integers(0, 4))]
    elif kind == "K3 行が二重に入る":
        d = pd.concat([d, d.iloc[[i]]], ignore_index=True)
    elif kind == "K4 行が抜ける":
        d = d.drop(index=i).reset_index(drop=True)
    elif kind == "K5 地域コードの打ち間違い":
        d.loc[i, "Code"] = d.loc[i, "Code"][:-1]
    elif kind == "K6 1つの値が10倍（桁ずれ）":
        d.loc[i, c] = f"{float(d.loc[i, c]) * 10:g}"
    elif kind == "K7 1つの値が5%ずれる":
        d.loc[i, c] = f"{round(float(d.loc[i, c]) * 1.05, 3):g}"
    elif kind == "K8 1年度分の1列が千分の1（単位）":
        y = d.loc[i, "year"]; m = d["year"] == y
        d.loc[m, c] = (pd.to_numeric(d.loc[m, c]) / 1000).map(lambda v: f"{v:g}")
    elif kind == "K9 1年度分の男女の列が入れ替わる":
        y = d.loc[i, "year"]; m = d["year"] == y
        tot, (a, b) = RULES_L4[int(rng.integers(0, len(RULES_L4)))]
        d.loc[m, [a, b]] = d.loc[m, [b, a]].to_numpy()
    elif kind == "K10 1つの値の符号が逆":
        d.loc[i, c] = f"{-float(d.loc[i, c]):g}"
    return d


KINDS = ["K1 空欄", "K2 数字の代わりに記号", "K3 行が二重に入る", "K4 行が抜ける", "K5 地域コードの打ち間違い",
         "K6 1つの値が10倍（桁ずれ）", "K7 1つの値が5%ずれる", "K8 1年度分の1列が千分の1（単位）",
         "K9 1年度分の男女の列が入れ替わる", "K10 1つの値の符号が逆"]
LV = ["L1", "L2", "L3", "L4"]
clean = validate(body)


def clean_l3_detail(df, mult=1.5):
    """壊していないファイルで範囲チェック（L3）が鳴った所の一覧"""
    num = df[ITEMS].apply(pd.to_numeric); num["Code"] = df["Code"].values; num["y"] = df["year"].astype(int).values
    num = num.sort_values(["Code", "y"]); out = []
    for c in ITEMS:
        a = num.groupby("Code")[c].shift(1); v = num[c]
        d = (v - a).abs() if c in NEG_OK else (v / a - 1).replace([np.inf, -np.inf], np.nan).abs()
        for i in d[d > YOY_MAX[c] * mult].index:
            out.append({"item": c, "name": NAME[c], "Code": num.loc[i, "Code"], "year": int(num.loc[i, "y"]),
                        "prev": float(a[i]), "value": float(v[i]), "limit": YOY_MAX[c] * mult})
    return out


CLEAN_L3 = clean_l3_detail(body)
rng = np.random.default_rng(SEED)
rows = []
for kd in KINDS:
    for t in range(N):
        r = validate(corrupt(body, kd, rng))
        cum = 0
        rec = {"kind": kd, "trial": t}
        for L in LV:
            cum += r[L] - clean[L] if r[L] > clean[L] else 0  # 壊していないファイルでも鳴る分は差し引いて「増えたか」で見る
            rec[L] = cum > 0
        rows.append(rec)
R = pd.DataFrame(rows)
R.to_csv(RES / "trials.csv", index=False)
rate = R.groupby("kind", sort=False)[LV].mean()
rate.to_csv(RES / "detection_rate.csv")

# 壊していないファイルで、それぞれの段が何件鳴るか（空振り）。係数を変えて L3 の空振りと K7 の見つかり方を比べる
trade = []
for mult in [1.0, 1.2, 1.5, 2.0, 3.0]:
    cl = validate(body, mult)
    rng2 = np.random.default_rng(SEED + 1)
    hits7 = hits6 = 0
    for t in range(N):
        d7 = corrupt(body, "K7 1つの値が5%ずれる", rng2); r7 = validate(d7, mult)
        hits7 += r7["L3"] > cl["L3"]
        d6 = corrupt(body, "K6 1つの値が10倍（桁ずれ）", rng2); r6 = validate(d6, mult)
        hits6 += r6["L3"] > cl["L3"]
    trade.append({"mult": mult, "clean_L3_alarms": cl["L3"], "K7_rate": hits7 / N, "K6_rate": hits6 / N})
T = pd.DataFrame(trade); T.to_csv(RES / "l3_threshold_tradeoff.csv", index=False)
summary = {"clean_alarms": clean, "clean_L3_detail": CLEAN_L3, "detection_rate": rate.round(3).to_dict("index"), "tradeoff": T.to_dict("records"),
           "n_trials": N, "seed": SEED, "n_cells": int(len(body) * len(ITEMS))}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)

# --- 図1：壊れの種類×段の見つかった割合 ---
fig, ax = plt.subplots(figsize=(10.5, 5.6))
for i, kd in enumerate(KINDS):
    for j, L in enumerate(LV):
        v = rate.loc[kd, L]
        col = BLUE if v >= 0.95 else (LIGHT if v >= 0.3 else ("#f2d4c8" if v > 0 else "#f4f4f2"))
        ax.add_patch(plt.Rectangle((j, -i), 0.96, -0.9, color=col))
        ax.text(j + 0.48, -i - 0.45, f"{v*100:.0f}%", ha="center", va="center", fontsize=10, color="white" if v >= 0.95 else INK)
    ax.text(-0.1, -i - 0.45, kd, ha="right", va="center", fontsize=10)
for j, t in enumerate(["L1 型と空欄", "＋L2 キー", "＋L3 範囲", "＋L4 列どうし"]):
    ax.text(j + 0.48, 0.2, t, ha="center", va="bottom", fontsize=10)
ax.set_xlim(-3.1, 4); ax.set_ylim(-len(KINDS) - 0.1, 0.9); ax.axis("off")
ax.set_title(f"壊れの種類ごとに、チェックを足していくと何割止まったか（各{N}回）", loc="left", fontsize=12)
save(fig, "a260_detection.png")

# --- 図2：どの段で初めて止まったか（壊れの種類ごとの積み上げ）---
first = pd.DataFrame({L: rate[L] - (rate[LV[k - 1]] if k else 0) for k, L in enumerate(LV)})
first["止まらない"] = 1 - rate["L4"]
fig, ax = plt.subplots(figsize=(10.5, 4.8))
left = np.zeros(len(KINDS)); cols = [GRAY, BLUE, ORANGE, GREEN, "#e9e8e4"]
labs = ["L1 で止まる", "L2 で初めて", "L3 で初めて", "L4 で初めて", "止まらない"]
for col, L, lb in zip(cols, list(first.columns), labs):
    ax.barh(KINDS[::-1], first[L].values[::-1] * 100, left=left[::-1] * 100, color=col, label=lb)
    left = left + first[L].values
ax.set_xlabel("%"); ax.set_xlim(0, 100)
ax.legend(ncol=5, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=9, frameon=False)
ax.set_title("どの段のチェックで初めて止まったか", loc="left", fontsize=12, pad=28)
save(fig, "a260_first_stage.png")

# --- 図3：範囲チェックの上限の係数と、空振り・見つかる割合 ---
fig, ax1 = plt.subplots(figsize=(10.5, 3.9))
ax1.plot(T["mult"], T["K6_rate"] * 100, "o-", color=BLUE, label="10倍の桁ずれを止めた割合")
ax1.plot(T["mult"], T["K7_rate"] * 100, "o-", color=ORANGE, label="5%のずれを止めた割合")
ax1.set_xlabel("上限の係数（2025年版で見た前年度比の最大×係数）"); ax1.set_ylabel("%"); ax1.set_ylim(0, 105)
ax2 = ax1.twinx(); ax1.set_zorder(ax2.get_zorder() + 1); ax1.patch.set_visible(False); ax2.bar(T["mult"], T["clean_L3_alarms"], width=0.12, color=GRAY, alpha=0.6, label="壊していないファイルで鳴った件数")
ax2.set_ylabel("件"); ax2.spines["right"].set_visible(True)
for x, v in zip(T["mult"], T["clean_L3_alarms"]):
    ax2.text(x, v, f"{v}", ha="center", va="bottom", fontsize=9, color=INK)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="center right", fontsize=9, frameon=True, facecolor="white", edgecolor="none")
ax1.set_title("範囲チェック（L3）の上限をゆるめると、空振りは減るが小さなずれは止まらない", loc="left", fontsize=12)
save(fig, "a260_threshold.png")
print(json.dumps({"clean": clean, "clean_L3_detail": CLEAN_L3}, ensure_ascii=False)); print((rate * 100).round(1).to_string()); print(T.to_string())
