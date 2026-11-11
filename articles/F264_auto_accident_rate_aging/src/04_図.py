"""F264 04 図"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = BASE / "results", BASE / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
M = json.load(open(RES / "main.json", encoding="utf-8"))
C1, C2, C3, GR = "#2b6cb0", "#c05621", "#2f855a", "#718096"
NOTE = "出典：警察庁「交通事故の発生状況」「交通死亡事故の発生状況」（e-Stat）から作成。原付以上運転者（第1当事者）"

# 図1 そのままの率と年齢をそろえた率（2009年=100）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, kind, ttl in zip(axs, ["all", "fatal"], ["人身事故", "死亡事故"]):
    d = pd.DataFrame(M[f"{kind}_std"]).set_index("year")
    for col, c, lab in [("raw", C1, "そのままの率"), ("std2009", C2, "年齢構成を2009年に固定した率")]:
        ax.plot(d.index, d[col] / d[col].iloc[0] * 100, color=c, lw=2.2, label=lab, marker="o", ms=3)
    ax.set_title(f"{ttl}：免許保有者10万人当たり（2009年=100）")
    ax.set_ylim(0, 105); ax.grid(axis="y", alpha=.3)
    last = d.iloc[-1]
    ax.annotate(f"{last['raw']/d['raw'].iloc[0]*100:.0f}", (2025, last["raw"] / d["raw"].iloc[0] * 100), xytext=(4, 4), textcoords="offset points", color=C1)
    ax.annotate(f"{last['std2009']/d['std2009'].iloc[0]*100:.0f}", (2025, last["std2009"] / d["std2009"].iloc[0] * 100), xytext=(4, -12), textcoords="offset points", color=C2)
axs[0].legend(loc="lower left", frameon=False)
fig.text(0.01, 0.01, NOTE, fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_1_rate_vs_standardized.png", dpi=150); plt.close(fig)

# 図2 年齢層ごとの率 2009 と 2025
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, kind, ttl in zip(axs, ["all", "fatal"], ["人身事故", "死亡事故"]):
    d = pd.DataFrame(M[f"{kind}_age_rate_change"])
    x = np.arange(len(d))
    ax.plot(x, d.r2009, color=GR, marker="o", lw=1.8, label="2009年")
    ax.plot(x, d.r2025, color=C1, marker="o", lw=2.2, label="2025年")
    tot = {r["year"]: r["R_reconstructed"] for r in M[f"{kind}_series"]}
    ax.axhline(tot[2009], color=GR, ls=":", lw=1); ax.axhline(tot[2025], color=C1, ls=":", lw=1)
    ax.set_xticks(x); ax.set_xticklabels([a.replace("歳", "").replace("以上", "+") for a in d.g], rotation=60, fontsize=9)
    ax.set_title(f"{ttl}：年齢層別 免許保有者10万人当たり（点線は全体）"); ax.grid(axis="y", alpha=.3)
axs[0].legend(frameon=False)
fig.text(0.01, 0.01, NOTE, fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_2_age_rates.png", dpi=150); plt.close(fig)

# 図3 分解（変化を始点の率に対する%で）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, kind, ttl in zip(axs, ["all", "fatal"], ["人身事故", "死亡事故"]):
    per = [(2009, 2025), (2009, 2019), (2019, 2025)]
    mix = [M[f"{kind}_kit_{s}_{t}"]["mid"]["mix"] / M[f"{kind}_kit_{s}_{t}"]["mid"]["R_s"] * 100 for s, t in per]
    rate = [M[f"{kind}_kit_{s}_{t}"]["mid"]["rate"] / M[f"{kind}_kit_{s}_{t}"]["mid"]["R_s"] * 100 for s, t in per]
    x = np.arange(len(per)); w = .36
    b1 = ax.bar(x - w / 2, rate, w, color=C1, label="年齢ごとの率の変化")
    b2 = ax.bar(x + w / 2, mix, w, color=C2, label="年齢構成の変化")
    for xi, v in zip(x + w / 2, mix):
        ax.annotate(f"{v:+.1f}%", (xi, v), xytext=(0, 3 if v >= 0 else -12), textcoords="offset points", ha="center", fontsize=9, color=C2)
    for xi, v in zip(x - w / 2, rate):
        ax.annotate(f"{v:+.0f}%", (xi, v), xytext=(0, -12), textcoords="offset points", ha="center", fontsize=9, color=C1)
    ax.axhline(0, color="k", lw=.8); ax.set_ylim(min(rate) * 1.12, max(max(mix), 0) + 3)
    ax.set_xticks(x); ax.set_xticklabels([f"{s}→{t}" for s, t in per])
    ax.set_title(f"{ttl}：率の変化の分け方（始めの年の率に対する%）"); ax.grid(axis="y", alpha=.3)
axs[0].legend(frameon=False, loc="lower right")
fig.text(0.01, 0.01, NOTE + "。北川の分解（中点の重み）", fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_3_decomposition.png", dpi=150); plt.close(fig)

# 図4 年齢層ごとの寄与（平均からの差で表した年齢構成の効果）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, kind, ttl in zip(axs, ["all", "fatal"], ["人身事故", "死亡事故"]):
    c = M["mix_contrib_centered_2009_2025"][kind]
    s = pd.Series(c["by_age"]); tot = abs(c["total_change"])
    v = s / tot * 100
    cols = [C2 if x > 0 else C1 for x in v]
    ax.bar(range(len(v)), v, color=cols)
    ax.set_xticks(range(len(v))); ax.set_xticklabels([a.replace("歳", "").replace("以上", "+") for a in v.index], rotation=60, fontsize=9)
    ax.axhline(0, color="k", lw=.8); ax.grid(axis="y", alpha=.3)
    ax.set_title(f"{ttl}：年齢構成の効果の内訳（下がった幅に対する%）", fontsize=11)
    ax.text(0.02, 0.95, f"65歳以上 {c['share65plus']*100:+.1f}%／65歳未満 {c['share_under65']*100:+.1f}%", transform=ax.transAxes, va="top", fontsize=10)
fig.text(0.01, 0.01, NOTE + "。2009→2025年。各年齢層の割合の変化×（その層の率−全体の率）", fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_4_mix_by_age.png", dpi=150); plt.close(fig)

# 図5 保険の頻度と警察の率
ins = pd.DataFrame(M["insurance"]["levels"]).set_index("year")
fig, ax = plt.subplots(figsize=(9, 4.4))
for col, c, lab, base in [("police", C1, "警察：免許保有者10万人当たり人身事故（暦年）", 2009), ("jibai", C2, "自賠責：支払件数÷契約台数（年度）", 2009), ("nini", C3, "任意保険：支払件数÷契約台数（年度、全種目）", 2017)]:
    s = ins[col].dropna()
    if col == "nini": s = s.loc[2017:]  # 2016年度は契約台数の数え方が他の年と合わない（約6,170万台→6,660万台）ので除く
    ref = ins["police"].loc[base] / ins["police"].loc[2009] * 100 if col == "nini" else 100
    ax.plot(s.index, s / s.loc[base] * ref, color=c, lw=2.2, marker="o", ms=3, label=lab)
ax.set_ylim(0, 115); ax.grid(axis="y", alpha=.3); ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("保険の事故の頻度と警察の事故率（2009年=100、任意保険は2017年を警察の線に合わせた）", fontsize=11)
fig.text(0.01, 0.01, "出典：警察庁（e-Stat）、損害保険料率算出機構「自動車保険の概況」各年度版", fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_5_insurance.png", dpi=150); plt.close(fig)

# 図6 問い直し：年齢構成だけで10年後どうなるか
P = pd.DataFrame(M["reask"]["projection"]); B = pd.DataFrame(M["reask"]["backtest"]).set_index("kind")
fig, ax = plt.subplots(figsize=(9, 4.4))
labs = ["人身事故", "死亡事故"]
for i, kind in enumerate(["all", "fatal"]):
    p = P[P.kind == kind].set_index("youth_scale")
    ax.bar(i - .18, p.loc[1.0, "pct"], .34, color=C2, label="2025→2035 の見込み（年齢構成だけ）" if i == 0 else None)
    ax.errorbar(i - .18, p.loc[1.0, "pct"], yerr=[[p.loc[1.0, "pct"] - p.pct.min()], [p.pct.max() - p.loc[1.0, "pct"]]], color="k", capsize=4)
    ax.annotate(f"{p.loc[1.0,'pct']:+.1f}%", (i - .18, p.pct.max()), xytext=(0, 4), textcoords="offset points", ha="center")
    ax.bar(i + .18, B.loc[kind, "mix_only_actual_pct"], .34, color=GR, label="2015→2025 の実際（年齢構成だけ）" if i == 0 else None)
    ax.scatter(i + .18, B.loc[kind, "mix_only_proj_pct"], color="k", marker="D", zorder=3, label="同じ方法で2015年から出した見込み" if i == 0 else None)
    ax.annotate(f"実際 {B.loc[kind,'mix_only_actual_pct']:+.1f}%／見込み {B.loc[kind,'mix_only_proj_pct']:+.1f}%", (i + .18, max(B.loc[kind, 'mix_only_actual_pct'], B.loc[kind, 'mix_only_proj_pct'], 0)), xytext=(0, 10), textcoords="offset points", ha="center", color="#4a5568", fontsize=9)
ax.axhline(0, color="k", lw=.8); ax.set_xticks([0, 1]); ax.set_xticklabels(labs); ax.grid(axis="y", alpha=.3)
ax.set_ylabel("率の変化（%）"); ax.set_ylim(-1, 7.5); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("年齢ごとの率を2025年のままとし、年齢構成だけを10年進めると", fontsize=11)
fig.text(0.01, 0.01, "免許保有者の各年齢層が前の10年と同じ割合で残り、16〜24歳は今と同じ人数（幅は0.85〜1.15倍）とおいた投影。推測を含む", fontsize=8, color=GR)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "f264_6_projection.png", dpi=150); plt.close(fig)
print(sorted(p.name for p in FIG.glob("*.png")))
