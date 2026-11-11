"""A285 輸入の半分は、何品目で占められているのか
統計品別表（輸入、9桁の統計品目番号）を金額の大きい順に並べ、累積の割合（パレート分析）を見る。
少額貨物などの特殊なコード（000000xxx）は品目でないので除いた（2025年の輸入額の約1.8%）。
品目の細かさの影響を見るため、6桁・4桁にまとめた場合も計算する。比べる相手として2015・2020年と、2025年の輸出も同じ計算をする。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, note

setup_font()
A = pd.read_csv(DATA / "hs9_values.csv", dtype={"HS": str})
MAP = pd.read_csv(DATA / "hs9_to_gaikyo_top_import2025.csv", dtype=str).fillna("").set_index("HS")["gaikyo_name"]
# 上位品目の短い名前（9桁の統計品目番号の内容。概況品の名前で足りないものだけ補った）
SHORT = {"270900900": "原油", "271111000": "液化天然ガス（LNG）", "851713000": "スマートフォン", "260300000": "銅鉱",
         "270112099": "一般炭（石炭）", "847130000": "ノートパソコンなど", "271012181": "揮発油", "260111000": "鉄鉱石",
         "847150000": "パソコンの処理装置", "841191000": "航空機用エンジンの部分品", "271112000": "液化石油ガス（LPG）",
         "854231010": "IC（集積回路）", "854239099": "IC（集積回路）", "854239010": "IC（集積回路）", "848620000": "半導体製造装置",
         "300215000": "医薬品（免疫製品）", "300490029": "医薬品（その他）", "854430010": "車両用の配線（ワイヤーハーネス）", "841112000": "航空機用ジェットエンジン",
         "240411200": "加熱式たばこ"}


def pareto(v):
    v = np.sort(v[v > 0])[::-1]; c = v.cumsum() / v.sum(); n = len(v)
    x = np.sort(v); gini = (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())
    return {"n_items": int(n), "n50": int(np.searchsorted(c, 0.5) + 1), "n80": int(np.searchsorted(c, 0.8) + 1),
            "n90": int(np.searchsorted(c, 0.9) + 1), "top1": float(c[0]), "top10": float(c[9]), "top100": float(c[99]),
            "gini": float(gini), "total_cho": float(v.sum() / 1e9)}, c


main = {}; curves = {}
for flow, y in [("import", 2015), ("import", 2020), ("import", 2025), ("export", 2025)]:
    d = A[(A.flow == flow) & (A.year == y)]
    sp = d.HS.str.startswith("00000")
    for k in (9, 6, 4):
        e = d[~sp].assign(HS=lambda x: x.HS.str[:k]).groupby("HS").value.sum()
        s, c = pareto(e.values); s["special_share"] = float(d.value[sp].sum() / d.value.sum())
        main[f"{flow}_{y}_hs{k}"] = s
        if k == 9:
            curves[(flow, y)] = c
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame(main).T.round(4).to_csv(RES / "pareto_summary.csv")

d = A[(A.flow == "import") & (A.year == 2025) & ~A.HS.str.startswith("00000")].nlargest(20, "value").copy()
tot = A[(A.flow == "import") & (A.year == 2025) & ~A.HS.str.startswith("00000")].value.sum()
d["name"] = [SHORT.get(h) or MAP.get(h, h) for h in d.HS]; d["share"] = d.value / tot; d["cum"] = d.share.cumsum()
d.round(5).to_csv(RES / "top20_import_2025.csv", index=False)
fuel = ["270900900", "271111000", "270112099", "271012181"]
main["fuel4_share"] = float(d[d.HS.isin(fuel)].share.sum())
v = np.sort(A[(A.flow == "import") & (A.year == 2025) & ~A.HS.str.startswith("00000") & (A.value > 0)].value.values)
main["bottom_half_items_share"] = float(v[: len(v) // 2].sum() / v.sum())
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# 図1：パレート曲線
fig, ax = plt.subplots(figsize=(8.2, 4.8))
for (fl, y), col, ls in [(("import", 2015), "#bdbdbd", "-"), (("import", 2020), "#7570b3", "-"), (("import", 2025), "#d95f02", "-"), (("export", 2025), "#1b9e77", "--")]:
    c = curves[(fl, y)]
    ax.plot(np.arange(1, len(c) + 1), c * 100, color=col, ls=ls, lw=1.8, label=f"{'輸入' if fl == 'import' else '輸出'} {y}年")
s = main["import_2025_hs9"]
for p, n in ((50, s["n50"]), (80, s["n80"])):
    ax.axhline(p, color="#999", lw=0.6, ls=":"); ax.plot(n, p, "o", color="#d95f02")
    ax.annotate(f"{n}品目で{p}%", (n, p), xytext=(8, -14), textcoords="offset points", fontsize=9, color="#d95f02")
ax.set_xscale("log"); ax.set_xlabel("金額の大きい順に並べた品目の数（対数目盛）"); ax.set_ylabel("累積の割合（%）")
ax.set_title(f"輸入の累積の割合：約{s['n_items']:,}品目のうち{s['n50']}品目で半分")
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.subplots_adjust(bottom=0.14); note(fig); fig.savefig(FIG / "a285_pareto.png"); plt.close(fig)

# 図2：上位20品目
t = d.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.4, 6.0))
ax.barh(range(len(t)), t.share * 100, color=["#d95f02" if h in fuel else "#7570b3" for h in t.HS])
for i, (_, r) in enumerate(t.iterrows()):
    ax.text(r.share * 100 + 0.1, i, f"{r.value/1e9:.2f}兆円（累計{r.cum*100:.0f}%）", va="center", fontsize=8)
ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{r['name']}（{r.HS}）" for _, r in t.iterrows()], fontsize=8.5)
ax.set_xlabel("2025年の輸入額に占める割合（%）"); ax.set_xlim(0, 11.5)
ax.set_title("上位20品目（橙＝燃料）：原油だけで8.6%")
fig.subplots_adjust(left=0.38, bottom=0.11); note(fig); fig.savefig(FIG / "a285_top20.png"); plt.close(fig)

# 図3：品目の細かさと、半分・8割に必要な数
fig, ax = plt.subplots(figsize=(8.2, 4.6))
labs = ["9桁", "6桁", "4桁"]; x = np.arange(3); w = 0.36
n50 = [main[f"import_2025_hs{k}"]["n50"] for k in (9, 6, 4)]; n80 = [main[f"import_2025_hs{k}"]["n80"] for k in (9, 6, 4)]
ni = [main[f"import_2025_hs{k}"]["n_items"] for k in (9, 6, 4)]
ax.bar(x - w / 2, [a / b * 100 for a, b in zip(n50, ni)], w, color="#d95f02", label="半分に必要な割合")
ax.bar(x + w / 2, [a / b * 100 for a, b in zip(n80, ni)], w, color="#7570b3", label="8割に必要な割合")
for i in range(3):
    ax.text(i - w / 2, n50[i] / ni[i] * 100 + 0.3, f"{n50[i]}/{ni[i]:,}", ha="center", fontsize=8.5)
    ax.text(i + w / 2, n80[i] / ni[i] * 100 + 0.3, f"{n80[i]}/{ni[i]:,}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"統計品目番号 {l}" for l in labs]); ax.set_ylabel("品目の数に対する割合（%）")
ax.set_title("品目をまとめても、半分は全品目の1〜2%、8割は7〜12%で占められる（2025年の輸入）", fontsize=10.5)
ax.legend(frameon=False, fontsize=9)
fig.subplots_adjust(bottom=0.12); note(fig); fig.savefig(FIG / "a285_levels.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=0)[:3000]); print(d[["HS", "name", "share", "cum"]].round(3).to_string())
