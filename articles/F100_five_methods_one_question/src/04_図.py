"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, DATA

R = json.load(open(RES / "results.json"))
S = pd.DataFrame(R["spec"])
V = json.load(open(RES / "variance_share.json"))
C_LV, C_CH = "#c4572a", "#2a6fb0"
METH = ["回帰", "固定効果", "マッチング", "DML（RF）", "DML（LightGBM）", "DML（Lasso）", "空間誤差モデル", "空間ラグモデル（直接効果）"]


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 図1 散布図：水準と変化
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
for a, k, xl, yl, col, ttl in [
    (ax[0], "q1_level", "保育所等に通う子ども（0〜5歳100人あたり、2015年）", "合計特殊出生率（2018〜22年）", C_LV, "水準：在所児が多い町ほど出生率が高い？"),
    (ax[1], "q1_change", "在所児の変化（2010→15年、100人あたり）", "出生率の変化（2013〜17年→2018〜22年）", C_CH, "変化：在所児が増えた町ほど出生率が上がった？")]:
    d = pd.read_csv(DATA / f"{k}.csv", dtype={"code": str})
    a.scatter(d.D, d.Y, s=5, alpha=0.25, color=col)
    b = pd.qcut(d.D, 20)
    g = d.groupby(b, observed=True)[["D", "Y"]].mean()
    a.plot(g.D, g.Y, "o-", color="black", ms=3.5, lw=1, label="20等分した平均")
    r = np.corrcoef(d.D, d.Y)[0, 1]
    a.set_title(f"{ttl}\n（{len(d):,}市区町村、相関 {r:+.2f}）", fontsize=10.5)
    a.set_xlabel(xl, fontsize=9); a.set_ylabel(yl, fontsize=9); a.legend(fontsize=8.5, loc="upper left")
    if k == "q1_change":
        a.set_xlim(-30, 50); a.set_ylim(-0.45, 0.25)
save(fig, "f100_1_散布図_水準と変化.png")

# 図2 5つの手法×2つの比べ方（問い1、県あり・全体）
fig, ax = plt.subplots(figsize=(9, 5.6))
m = S[(S.q == "q1") & (S.pref) & (S["sample"] == "all")]
y = 0; ticks = []
for meth in METH:
    for des, col, off in [("level", C_LV, 0.18), ("change", C_CH, -0.18)]:
        r = m[(m.method == meth) & (m.design == des)]
        if len(r):
            r = r.iloc[0]
            ax.errorbar(r.coef, y + off, xerr=[[r.coef - r.lo], [r.hi - r.coef]], fmt="o", color=col, ms=5, capsize=2.5,
                        label={"level": "水準の比較（2015年の在所児 → 2018〜22年の出生率）", "change": "変化の比較（2010→15年の在所児の増加 → 出生率の変化）"}[des] if y == 0 or (meth == "固定効果" and des == "change") else None)
    ticks.append(meth); y -= 1
nv = R["naive"]
ax.errorbar(nv["q1_level"]["coef"], y + 0.18, xerr=[[nv["q1_level"]["coef"] - nv["q1_level"]["lo"]], [nv["q1_level"]["hi"] - nv["q1_level"]["coef"]]], fmt="s", color=C_LV, mfc="white", ms=5, capsize=2.5)
ax.errorbar(nv["q1_change"]["coef"], y - 0.18, xerr=[[nv["q1_change"]["coef"] - nv["q1_change"]["lo"]], [nv["q1_change"]["hi"] - nv["q1_change"]["coef"]]], fmt="s", color=C_CH, mfc="white", ms=5, capsize=2.5)
ticks.append("（参考）条件を入れない単純な回帰")
ax.set_yticks(range(0, -len(ticks), -1)); ax.set_yticklabels(ticks, fontsize=9.5)
ax.axvline(0, color="gray", lw=0.8)
ax.set_xlabel("在所児が0〜5歳100人あたり10人多い（増えた）ときの、合計特殊出生率の差（95%区間）", fontsize=9)
ax.set_title("同じ問いを5つの手法で：答えを分けたのは手法より「何を比べるか」", fontsize=11)
h, l = ax.get_legend_handles_labels(); ax.legend(h[:2], l[:2], fontsize=8.5, loc="lower left")
save(fig, "f100_2_手法と比べ方の推定値.png")

# 図3 条件を1段ずつ足す（回帰）
fig, ax = plt.subplots(figsize=(9, 4.6))
for des, col, off, lab in [("level", C_LV, 0.12, "水準の比較"), ("change", C_CH, -0.12, "変化の比較")]:
    st = R["steps"][des]
    names = [s["step"] for s in st]
    xs = np.arange(len(st))
    if des == "change":
        xs = np.array([0, 1, 2, 3, 4, 5, 6, 7])[:len(st)]
    else:
        xs = np.array([0, 1, 2, 3, 4, 6, 7])
    c = np.array([s["coef"] for s in st]); lo = np.array([s["lo"] for s in st]); hi = np.array([s["hi"] for s in st])
    ax.errorbar(xs + off, c, yerr=[c - lo, hi - c], fmt="o-", color=col, ms=5, capsize=2.5, lw=1, label=lab)
labels = ["条件なし", "人口・密度", "＋年齢・世帯", "＋産業・通勤・所得", "＋財政・学歴・雇用", "＋前の出生率・在所児\n（変化の比較だけ）", "＋県", "＋隣との似かた\n（空間誤差モデル）"]
ax.set_xticks(range(8)); ax.set_xticklabels(labels, fontsize=8, rotation=20, ha="right")
ax.axhline(0, color="gray", lw=0.8)
ax.set_ylabel("出生率の差（在所児+10人あたり）", fontsize=9)
ax.set_title("条件を足すと：水準の比較は向きが変わり、変化の比較はほぼ0のまま", fontsize=11)
ax.legend(fontsize=9)
save(fig, "f100_3_条件を足すと.png")

# 図4 すべての組み合わせ（仕様の曲線、問い1）
s = S[S.q == "q1"].sort_values("coef").reset_index(drop=True)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.2), gridspec_kw={"height_ratios": [2.2, 1.6]}, sharex=True)
for i, r in s.iterrows():
    col = C_LV if r.design == "level" else C_CH
    sig = (r.lo > 0) or (r.hi < 0)
    a1.plot([i, i], [r.lo, r.hi], color=col, alpha=0.35, lw=1)
    a1.plot(i, r.coef, "o", color=col, mfc=col if sig else "white", ms=4)
a1.axhline(0, color="gray", lw=0.8)
a1.set_ylabel("出生率の差（在所児+10人あたり）", fontsize=9)
a1.set_title(f"手法×比べ方×県の扱い×対象の{len(s)}通り（塗りつぶし＝区間が0をまたがない）", fontsize=10.5)
a1.plot([], [], "o", color=C_LV, label="水準の比較"); a1.plot([], [], "o", color=C_CH, label="変化の比較"); a1.legend(fontsize=8.5, loc="upper left")
rows = [("比べ方：変化", s.design == "change"), ("県の違いを除く", s.pref), ("人口1万人以上だけ", s["sample"] == "pop1man")] + \
       [(f"手法：{mm}", s.method.str.startswith(mm)) for mm in ["回帰", "固定効果", "マッチング", "DML", "空間"]]
for j, (lab, mask) in enumerate(rows):
    a2.scatter(np.where(mask)[0], [-j] * int(mask.sum()), s=9, marker="s", color="#444")
a2.set_yticks([-j for j in range(len(rows))]); a2.set_yticklabels([r[0] for r in rows], fontsize=8.5)
a2.set_xlabel("推定値の小さい順", fontsize=9)
v = V["q1"]
a2.set_title(f"ばらつきのうち説明できる割合：比べ方 {v['比べ方（水準か変化か）']:.0%}、手法 {v['手法']:.0%}、県の扱い {v['県の違いを除くか']:.0%}、比べ方×県の扱い {v['比べ方×県の扱い']:.0%}", fontsize=9)
save(fig, "f100_4_すべての組み合わせ.png")

# 図5 問い2（女性の労働力率）でも同じことが起きるか
fig, ax = plt.subplots(figsize=(9, 5.2))
m = S[(S.q == "q2") & (S.pref) & (S["sample"] == "all")]
y = 0; ticks = []
for meth in METH:
    for des, col, off in [("level", C_LV, 0.18), ("change", C_CH, -0.18)]:
        r = m[(m.method == meth) & (m.design == des)]
        if len(r):
            r = r.iloc[0]
            ax.errorbar(r.coef, y + off, xerr=[[r.coef - r.lo], [r.hi - r.coef]], fmt="o", color=col, ms=5, capsize=2.5)
    ticks.append(meth); y -= 1
ax.plot([], [], "o", color=C_LV, label="水準の比較（2015年）"); ax.plot([], [], "o", color=C_CH, label="変化の比較（2010→15年、F16 と同じ）")
ax.set_yticks(range(0, -len(ticks), -1)); ax.set_yticklabels(ticks, fontsize=9.5)
ax.axvline(0, color="gray", lw=0.8)
ax.set_xlabel("在所児が100人あたり10人多い（増えた）ときの、女性の労働力率の差（ポイント、95%区間）", fontsize=9)
ax.set_title("問い2（保育所と女性の働き方）：どの手法でもプラス、大きさは比べ方で約3倍違う", fontsize=11)
ax.legend(fontsize=8.5, loc="upper right")
save(fig, "f100_5_問い2_女性の労働力率.png")
print("ok")
