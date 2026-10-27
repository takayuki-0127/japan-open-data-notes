"""04 図：6枚（note には f61_robust 以外の5枚を使う）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

S = json.load(open(RES / "summary.json", encoding="utf-8"))
SIZES = ["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]
MS = ["100人未満", "100〜300人", "300〜1,000人", "1,000人以上"]
COL = ["#d1495b", "#edae49", "#66a182", "#2e4057"]


def funnel():
    m = pd.read_csv(RES / "_smr_all_eb.csv")
    f = pd.read_csv(RES / "_funnel_2023.csv")
    mu = S["smr"]["all"]["mean_ratio"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    # 左：死亡（SMR）
    E = np.logspace(np.log10(m.E_all.min() * 0.9), np.log10(m.E_all.max() * 1.1), 200)
    a = ax[0]
    a.scatter(m.E_all, m.raw, s=6, alpha=0.5, color="#2e4057", lw=0)
    for z, ls in ((1.96, "--"), (3.09, "-")):
        a.plot(E, 100 * mu * (1 + z / np.sqrt(E * mu)), color="#d1495b", ls=ls, lw=1)
        a.plot(E, 100 * mu * (1 - z / np.sqrt(E * mu)), color="#d1495b", ls=ls, lw=1)
    a.axhline(100 * mu, color="gray", lw=0.8)
    a.set_xscale("log"); a.set_ylim(30, 190)
    a.set_xlabel("期待死亡数（5年間、対数目盛）"); a.set_ylabel("標準化死亡比（全国＝100）")
    a.set_title("死亡（全死因、2018〜22年、1,887地域）")
    a.text(0.98, 0.95, f"99.8%の線の外：{S['smr']['all']['share_out998']*100:.0f}%", transform=a.transAxes, ha="right", va="top", fontsize=9)
    # 右：検診
    b = ax[1]
    p0 = S["funnel_2023"]["p0"]
    n = np.logspace(np.log10(f.n_colon.min() * 0.9), np.log10(f.n_colon.max() * 1.1), 200)
    b.scatter(f.n_colon, 100 * f.p_raw, s=6, alpha=0.5, color="#2e4057", lw=0)
    for z, ls in ((1.96, "--"), (3.09, "-")):
        b.plot(n, 100 * (p0 + z * np.sqrt(p0 * (1 - p0) / n)), color="#d1495b", ls=ls, lw=1)
        b.plot(n, 100 * np.clip(p0 - z * np.sqrt(p0 * (1 - p0) / n), 0, 1), color="#d1495b", ls=ls, lw=1)
    b.axhline(100 * p0, color="gray", lw=0.8)
    b.set_xscale("log"); b.set_ylim(-2, 100)
    b.set_xlabel("対象者数（対数目盛）"); b.set_ylabel("受診率（%）")
    b.set_title("大腸がん検診（国保40〜69歳、2023年度、1,656団体）")
    b.text(0.98, 0.95, f"99.8%の線の外：{S['funnel_2023']['share_out998']*100:.0f}%", transform=b.transAxes, ha="right", va="top", fontsize=9)
    fig.suptitle("ファンネルプロット：赤線は「本当の値がみな全国と同じでも、偶然だけで出る範囲」（点線95%・実線99.8%）", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "f61_funnel.png", dpi=150); plt.close(fig)


def sim():
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    share = S["share_units_by_size"]
    sv = S["simulation_same_rate"]
    x = np.arange(4); w = 0.27
    a = ax[0]
    a.bar(x - w, [share[c] * 100 for c in SIZES], w, label="団体の数の割合", color="#bbbbbb")
    a.bar(x, [sv["top1_size_share"][c] * 100 for c in SIZES], w, label="1位になる確率", color="#d1495b")
    a.bar(x + w, [sv["top50_avg"][c] / 50 * 100 for c in SIZES], w, label="上位50に入る割合", color="#edae49")
    a.set_xticks(x); a.set_xticklabels(SIZES); a.set_ylabel("%")
    a.set_title("検診：全団体の本当の受診率が同じ（16.8%）とした2,000回")
    a.legend(fontsize=8)
    b = ax[1]
    sm = S["smr"]["all"]["sim_same_smr"]
    cnt = pd.read_csv(RES / "_smr_all_eb.csv")["size"].value_counts(normalize=True).reindex(MS)
    b.bar(x - w, cnt.values * 100, w, label="地域の数の割合", color="#bbbbbb")
    b.bar(x, [sm["top1_size_share"][c] * 100 for c in MS], w, label="いちばん高くなる確率", color="#d1495b")
    b.bar(x + w, [sm["high50_avg"][c] / 50 * 100 for c in MS], w, label="高い50に入る割合", color="#edae49")
    b.set_xticks(x); b.set_xticklabels([c.replace("人", "") for c in MS]); b.set_xlabel("期待死亡数（人）")
    b.set_title("死亡：全地域の本当の死亡比が同じとした2,000回")
    b.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f61_sim.png", dpi=150); plt.close(fig)


def composition():
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    tb = S["smr"]["all"]["top_bottom50_size"]
    labels = ["高い50（生）", "高い50（EB）", "低い50（生）", "低い50（EB）"]
    keys = ["raw|高い50", "eb|高い50", "raw|低い50", "eb|低い50"]
    a = ax[0]; bottom = np.zeros(4)
    for c, col in zip(MS, COL):
        v = np.array([tb[k][c] for k in keys]); a.bar(labels, v, bottom=bottom, color=col, label=c); bottom += v
    a.set_title("死亡（全死因）：高い・低い50地域の規模"); a.set_ylabel("地域の数"); a.legend(title="期待死亡数", fontsize=8)
    b = ax[1]; tk = S["topk_avg_composition"]; bottom = np.zeros(4)
    keys2 = ["生の率|上位|50", "経験ベイズ|上位|50", "生の率|下位|50", "経験ベイズ|下位|50"]
    labels2 = ["上位50（生）", "上位50（EB）", "下位50（生）", "下位50（EB）"]
    for c, col in zip(SIZES, COL):
        v = np.array([tk[k][c] for k in keys2]); b.bar(labels2, v, bottom=bottom, color=col, label=c); bottom += v
    b.set_title("検診：上位・下位50団体の規模（4年度の平均）"); b.legend(title="対象者数", fontsize=8)
    fig.suptitle("経験ベイズ（EB）で縮めると、端に並ぶ小さい地域が減る。減り方は死亡のほうがずっと大きい", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "f61_composition.png", dpi=150); plt.close(fig)


def shrink():
    m = pd.read_csv(RES / "_smr_all_eb.csv")
    s = pd.read_csv(RES / "_screening_with_eb.csv")
    s = s[s.year == 2023]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    a = ax[0]
    for c, col in zip(MS, COL):
        d = m[m["size"] == c]; a.scatter(d.raw, d.eb, s=7, alpha=0.6, color=col, label=c, lw=0)
    a.plot([40, 180], [40, 180], color="gray", lw=0.8)
    a.set_xlabel("そのままの標準化死亡比"); a.set_ylabel("経験ベイズで縮めた値"); a.set_title("死亡：小さい地域ほど全国の値に寄る")
    a.legend(title="期待死亡数", fontsize=8)
    b = ax[1]
    for c, col in zip(SIZES, COL):
        d = s[s["size"] == c]; b.scatter(100 * d.p_raw, 100 * d.p_eb, s=7, alpha=0.6, color=col, label=c, lw=0)
    b.plot([0, 100], [0, 100], color="gray", lw=0.8)
    b.set_xlabel("そのままの受診率（%）"); b.set_ylabel("経験ベイズで縮めた値（%）"); b.set_title("検診（2023年度）：ほとんど動かない")
    b.legend(title="対象者数", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f61_shrink.png", dpi=150); plt.close(fig)


def turnover():
    rr = S["rank_range_median_by_size"]
    ret = S["retention_next_year"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    a = ax[0]; x = np.arange(4); w = 0.38
    a.bar(x - w / 2, [rr["raw"][c] for c in SIZES], w, label="そのままの受診率", color="#2e4057")
    a.bar(x + w / 2, [rr["eb"][c] for c in SIZES], w, label="経験ベイズ", color="#edae49")
    a.set_xticks(x); a.set_xticklabels(SIZES); a.set_ylabel("4年度の順位の幅（中央値、1,656団体中）")
    a.set_title("検診：小さい町ほど順位が大きく動く"); a.legend(fontsize=8)
    b = ax[1]
    ks = ["上位1", "上位10", "上位50", "下位10", "下位50"]
    b.bar(np.arange(5) - w / 2, [ret[k]["生の率"] * 100 for k in ks], w, label="そのままの受診率", color="#2e4057")
    b.bar(np.arange(5) + w / 2, [ret[k]["経験ベイズ"] * 100 for k in ks], w, label="経験ベイズ", color="#edae49")
    b.set_xticks(np.arange(5)); b.set_xticklabels(ks); b.set_ylabel("翌年度も同じ範囲に残る割合（%）")
    b.set_title("検診：1位は4年度とも別の町。上位10は4〜5割が入れ替わる"); b.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f61_turnover.png", dpi=150); plt.close(fig)


def robust():
    r = pd.read_csv(RES / "robustness.csv").iloc[:5]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    y = np.arange(len(r))
    ax.barh(y + 0.2, r["上位50の500人未満_生"], 0.4, label="そのまま", color="#2e4057")
    ax.barh(y - 0.2, r["上位50の500人未満_EB"], 0.4, label="経験ベイズ", color="#edae49")
    ax.set_yticks(y); ax.set_yticklabels(r["設定"]); ax.invert_yaxis()
    ax.set_xlabel("上位50団体に入る対象者500人未満の町（4年度の平均）")
    ax.set_title("頑健性：設定を変えても、検診では縮めた後も小さい町が上位に残る")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f61_robust.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    funnel(); sim(); composition(); shrink(); turnover(); robust()
    print(sorted(p.name for p in FIG.glob("*.png")))
