"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#888888", "axes.grid": True,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.8})
BLUE, ORANGE, GRAY, GREEN, LIGHT = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9"
SRC = ("出典：厚生労働省「毎月勤労統計調査」季節調整済指数、内閣府「景気動向指数」個別系列（生産指数（鉱工業））・"
       "「景気基準日付」をもとに作成者が加工して作成")
META = {"Software": None}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=6.6, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def ts(ym):
    return pd.to_datetime(pd.Series(ym).astype(str), format="%Y%m")


def recessions():
    c = pd.read_csv(ROOT / "data" / "cycle_dates.csv", dtype={"ym": str})
    c = c[c["ym"] >= "199701"].sort_values("ym").reset_index(drop=True)
    out = []
    for i, r in c.iterrows():
        if r["kind"] == "山":
            nxt = c[(c.index > i) & (c["kind"] == "谷")]
            if len(nxt):
                out.append((ts([r["ym"]])[0], ts([nxt.iloc[0]["ym"]])[0]))
    return out


def fig1():
    d = pd.read_csv(ROOT / "data" / "monthly.csv", dtype={"ym": str})
    t = ts(d["ym"])
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for a, b in recessions():
        ax.axvspan(a, b, color="#eeeeee", lw=0)
    ax.plot(t, d["ot_mfg5"], color=ORANGE, lw=1.5, label="所定外労働時間指数（製造業、5人以上）")
    ax.plot(t, d["iip"], color=BLUE, lw=1.5, label="生産指数（鉱工業）")
    ax.set_ylabel("指数（2020年=100、季節調整済）")
    ax.set_title("所定外の時間と生産は、ほぼ同じ形で上下する\n（灰色は景気の後退期：山から谷まで）", fontsize=12)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.set_ylim(50, 160)
    ax.set_xlim(t.iloc[0] - pd.DateOffset(months=3), t.iloc[-1] + pd.DateOffset(months=3))
    save(fig, "fig1_overtime_and_production.png")


def fig2():
    x = pd.read_csv(RES / "xcorr.csv")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.4), sharey=True)
    for ax, s, ttl in [(axes[0], "ot5_m1", "前月からの変化率"), (axes[1], "ot5_m3", "3か月前からの変化率")]:
        q = x[x.series == s]
        cols = [ORANGE if k == 0 else LIGHT for k in q.lag]
        ax.bar(q.lag, q["corr"], color=cols, width=0.75)
        for k, v in zip(q.lag, q["corr"]):
            if k in (-1, 0, 1):
                ax.text(k, v + 0.02, f"{v:.2f}", ha="center", fontsize=8.5)
        ax.set_title(ttl, fontsize=11)
        ax.set_xticks(range(-6, 7))
        ax.set_xlabel("← 生産が先　　時差（か月）　　所定外が先 →", fontsize=9)
        ax.axhline(0, color="#999999", lw=0.8)
    axes[0].set_ylabel("相関係数")
    axes[0].set_ylim(-0.2, 1.0)
    fig.suptitle("相関がいちばん高いのは同じ月（時差0）", fontsize=12)
    save(fig, "fig2_cross_correlation.png")


def fig3():
    t = pd.read_csv(RES / "turning_points.csv", dtype={"ref": str})
    t = t.sort_values(["kind", "ref"], ascending=[False, True]).reset_index(drop=True)
    labs = [f"{'山' if k == '山' else '谷'} {r[:4]}年{int(r[4:])}月" for k, r in zip(t.kind, t.ref)]
    y = np.arange(len(t))[::-1]
    fig, ax = plt.subplots(figsize=(8.2, 4.9))
    ax.axvline(0, color="#999999", lw=0.8)
    ax.scatter(t.months_from_ref_iip, y + 0.12, color=BLUE, s=48, label="生産指数の山・谷", zorder=3)
    ax.scatter(t.months_from_ref_ot, y - 0.12, color=ORANGE, s=48, marker="D", label="所定外の山・谷", zorder=3)
    for yy, a, b in zip(y, t.months_from_ref_ot, t.months_from_ref_iip):
        if a != b:
            ax.plot([a, b], [yy - 0.12, yy + 0.12], color="#bbbbbb", lw=1, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(labs)
    ax.set_xlim(-9, 4)
    ax.set_xlabel("景気の山・谷の月からのずれ（か月、3か月移動平均の最大・最小）")
    ax.set_title("向きを変えた月は、ほぼ同じ。2018年の山だけ所定外が7か月早い", fontsize=12)
    ax.legend(loc="lower left", fontsize=9, frameon=True)
    save(fig, "fig3_turning_points.png")


def fig4():
    r = pd.read_csv(RES / "annual_ratio.csv", dtype={"year": int})
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.plot(r.year, r.ot_per_iip, color=ORANGE, lw=2, marker="o", ms=3.5, label="1人あたり所定外 ÷ 生産")
    ax.plot(r.year, r.ot_total_per_iip, color=GREEN, lw=2, marker="s", ms=3.5,
            label="（1人あたり所定外×常用雇用）÷ 生産")
    ax.axhline(100, color="#999999", lw=0.8)
    for col, c in [("ot_per_iip", ORANGE), ("ot_total_per_iip", GREEN)]:
        for yy in (1998, 2025):
            v = float(r.loc[r.year == yy, col].iloc[0])
            ax.text(yy, v + 2.2, f"{v:.0f}", ha="center", fontsize=8.5, color=c)
    ax.set_ylabel("比（2020年=100）")
    ax.set_ylim(80, 135)
    ax.set_title("生産あたりの1人の残業は増えたが、人が減ったぶんを掛けると増えていない\n（年平均、製造業）", fontsize=12)
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    save(fig, "fig4_overtime_per_production.png")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    print(json.dumps(sorted(p.name for p in FIG.glob("*.png")), ensure_ascii=False))


if __name__ == "__main__":
    main()
