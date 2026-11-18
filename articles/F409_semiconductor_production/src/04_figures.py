"""図を4枚つくる（PNG、日付などのメタデータを入れない）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
matplotlib.rcParams["svg.hashsalt"] = "f409"
ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
S_IIP = "経済産業省「鉱工業指数」（e-Stat）"
C1, C2, C3, C4, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#9b5fa5", "#8c8c8c"


def save(fig, name, src):
    fig.text(0.01, 0.01, "出典：" + src + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def to_date(idx):
    return pd.to_datetime(pd.Series(idx).astype(str), format="%Y%m").values


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    q = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
    L = pd.read_csv(R / "iip_linked_monthly.csv").set_index("ym")
    b19 = L[(L.index >= 201901) & (L.index <= 201912)].mean()

    # fig1 生産指数（2019年平均=100）
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.16)
    x = to_date(L.index)
    for c, col, lab in [("equip_prod", C2, "半導体・FPD製造装置"), ("ic_prod", C1, "集積回路（IC）"),
                        ("ecd_prod", C3, "電子部品・デバイス工業"), ("mining_mfg_prod", GR, "鉱工業全体")]:
        ax.plot(x, L[c] / b19[c] * 100, color=col, lw=2.0 if c in ("ic_prod", "equip_prod") else 1.5, label=lab)
    ax.axhline(100, color="#444444", lw=0.8, ls=":")
    ax.set_ylabel("生産指数（季節調整済、2019年平均＝100）"); ax.set_xlabel("年")
    ax.grid(axis="y", color="#dddddd"); ax.legend(loc="upper left", fontsize=9, frameon=False)
    fig.suptitle(f"集積回路の生産は2019年より{m['ic_prod_last12_vs_2019_pct']:.0f}%多い。鉱工業全体は{abs(m['mining_mfg_prod_last12_vs_2019_pct']):.0f}%少ない", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"直近12か月（2025年10月〜2026年9月）の平均で比べた。製造装置は+{m['equip_prod_last12_vs_2019_pct']:.0f}%。2013〜17年は2015年基準の指数をつないだ", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_production_index.png", S_IIP)

    # fig2 集積回路の出荷と在庫（前年同期比、四半期）
    cy = pd.read_csv(R / "ic_inventory_cycle_q.csv")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.2)
    xs = range(len(cy))
    ax.bar(xs, cy["inv_yoy"], color=C2, alpha=0.55, width=0.8, label="在庫の前年同期比")
    ax.plot(xs, cy["ship_yoy"], color=C1, lw=2.2, marker="o", ms=3, label="出荷の前年同期比")
    ax.axhline(0, color="#444444", lw=0.8)
    ticks = [i for i, s in enumerate(cy["q"]) if s.endswith("Q1")]
    ax.set_xticks(ticks); ax.set_xticklabels([cy["q"][i][:4] for i in ticks], fontsize=9)
    ax.set_ylabel("前年の同じ四半期との比（%）"); ax.set_xlabel("年（各年の第1四半期の位置）")
    ax.grid(axis="y", color="#dddddd"); ax.legend(loc="upper left", fontsize=9, frameon=False)
    fig.suptitle(f"集積回路の在庫は、出荷の波から{m['inv_ship_best_lag_q']}四半期ほど遅れて増減してきた（相関{m['inv_ship_best_corr']:.2f}）", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"在庫は直近12か月の平均で2019年より{abs(m['ic_inv_last12_vs_2019_pct']):.0f}%少ない。出荷は+{m['ic_ship_last12_vs_2019_pct']:.0f}%（季節調整済の指数の四半期平均）", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_ship_inventory.png", S_IIP)

    # fig3 IC の輸出入（名目・実質、12か月移動平均、2019年=100）
    t = pd.read_csv(R / "trade_real_monthly.csv").set_index("ym")
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.2), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.78, bottom=0.17, wspace=0.08)
    for ax, (nom, real, ttl) in zip(axes, [("ex_ic", "ex_ic_real", "IC の輸出"), ("im_ic", "im_ic_real", "IC の輸入")]):
        sub = t[[nom, real]].rolling(12).mean()
        base = sub[(sub.index >= 201912) & (sub.index <= 201912)].iloc[0]
        sub = sub[sub.index >= 201612]
        xx = to_date(sub.index)
        ax.plot(xx, sub[nom] / t.loc[201901:201912, nom].mean() * 100, color=C2, lw=2, label="金額（名目）")
        ax.plot(xx, sub[real] / t.loc[201901:201912, real].mean() * 100, color=C1, lw=2, label="量の目安（実質）")
        ax.axhline(100, color="#444444", lw=0.8, ls=":")
        ax.set_title(ttl, fontsize=11); ax.grid(axis="y", color="#dddddd"); ax.set_xlabel("年")
    axes[0].set_ylabel("12か月の移動平均（2019年平均＝100）")
    axes[0].legend(loc="upper left", fontsize=9, frameon=False)
    fig.suptitle(f"IC の輸出の金額は2019年の{m['ex_ic_last12_vs_2019_pct']/100+1:.1f}倍。輸出物価で割った実質は+{m['ex_ic_real_last12_vs_2019_pct']:.0f}%（割る物価で大きく変わる）", fontsize=13, x=0.02, ha="left")
    fig.text(0.02, 0.905, f"実質＝金額 ÷ 日銀の集積回路の輸出物価・輸入物価（円ベース）。物価は2019年から輸出で+{m['px_ic_yen_last12_vs_2019_pct']:.0f}%、輸入で+{m['pm_ic_yen_last12_vs_2019_pct']:.0f}%（直近12か月）。\n国内企業物価の集積回路で割ると、実質の輸出は+{m['ex_ic_real_ppi_last12_vs_2019_pct']:.0f}%", fontsize=9.5, color="#444444", va="top")
    save(fig, "fig3_trade_real.png", "財務省「貿易統計」、日本銀行「企業物価指数」")

    # fig4 品目の寄与（問い直し）
    it = pd.read_csv(R / "requestion_items.csv")
    it = it.iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.0))
    fig.subplots_adjust(left=0.27, right=0.95, top=0.76, bottom=0.18)
    cols = [C4 if s == "secret_and_residual" else (C1 if v >= 0 else C2) for s, v in zip(it["item"], it["contrib_pt"])]
    ax.barh(it["label"], it["contrib_pt"], color=cols)
    for yv, (v, sh, ws) in enumerate(zip(it["contrib_pt"], it["contrib_share_pct"], it["weight_share_pct"])):
        ax.text(max(v, 0) + 0.6, yv, f"{v:+.1f}（重み{ws:.0f}%）", va="center", ha="left", fontsize=9)
    ax.axvline(0, color="#444444", lw=0.8)
    ax.set_xlim(-6, 38)
    ax.set_xlabel("集積回路の生産指数の増加への寄与（ポイント）")
    fig.suptitle(f"集積回路の生産の増加{q['ic_change_pt']:.0f}ポイントのうち、メモリが{q['memory_contrib_pt']:.0f}、秘匿の品目などが{q['secret_contrib_pt']:.0f}", fontsize=13, x=0.02, ha="left")
    fig.text(0.02, 0.86, "2019年平均→直近12か月の平均。寄与＝品目の重みの割合 × 品目の指数の増加。\n秘匿の2品目（マイコン、その他のモス型）は、集積回路全体から4品目を差し引いて出した", fontsize=9, color="#444444", va="top")
    save(fig, "fig4_items_contrib.png", S_IIP + "（品目別・業種別）")


if __name__ == "__main__":
    main()
