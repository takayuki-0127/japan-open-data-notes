"""04 図（オフライン）：PNG 4枚。日付が入らないよう metadata を消す。"""
import csv, json, math, pathlib
from collections import defaultdict
import figstyle
from figstyle import plt, C, INK2, style, save

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準（全国、年平均）をもとに作成者が加工して作成"
SRC3 = "出典：総務省「消費者物価指数」2025年基準（全国、年平均）、財務省「貿易統計」（輸入、主要商品別）をもとに作成者が加工して作成"
SRC4 = "出典：総務省「消費者物価指数」2015年・2020年基準（全国、年平均）、財務省「貿易統計」をもとに作成者が加工して作成"


def load():
    d = defaultdict(dict); names = {}
    with open(DATA / "cpi_items_annual.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["basis"] == "2025":
                d[r["code"]][int(r["period"])] = float(r["value"]); names[r["code"]] = r["name"]
    return d, names


def fig1(d):
    fig, ax = plt.subplots(figsize=(8, 5))
    lines = [("9079", "パソコン（ノート型）", C[0], "-"), ("9078", "パソコン（デスクトップ型）", C[0], "--"), ("9013", "テレビ", C[1], "-"),
             ("9043", "カメラ", C[2], "-"), ("4021", "冷蔵庫", C[5], "-"), ("0001", "総合", "#0b0b0b", "-")]
    for code, lab, col, ls in lines:
        ys = [y for y in range(2000, 2026) if y in d[code]]
        ax.plot(ys, [d[code][y] for y in ys], color=col, ls=ls, lw=2, label=lab)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.set_yscale("log")
    ax.set_yticks([50, 100, 200, 500, 1000, 2000, 5000]); ax.set_yticklabels(["50", "100", "200", "500", "1,000", "2,000", "5,000"])
    ax.set_xlim(2000, 2025.5); ax.set_xticks(range(2000, 2026, 5))
    ax.set_ylabel("指数（2025年＝100、対数目盛）")
    ax.set_title("品質を差し引いた指数は、2010年代の前半までに大きく下がり、その後は横ばい", loc="left", fontsize=12)
    style(ax)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.13)
    save(fig, FIG / "fig1_index_log.png", SRC, "注：2025年に100になるようにそろえた長期の系列。テレビは2005年から")


def fig2(m):
    items = ["テレビ", "パソコン（デスクトップ型）", "パソコン（ノート型）", "カメラ", "ビデオレコーダー", "プリンタ",
             "冷蔵庫", "洗濯機（全自動洗濯機）", "掃除機", "電子レンジ", "ルームエアコン", "携帯電話機", "総合"]
    ir = m["item_rates"]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    y = list(range(len(items)))[::-1]
    h = 0.38
    a = [ir[i]["r2005_2015"] for i in items]; b = [ir[i]["r2015_2025"] for i in items]
    ax.barh([v + h / 2 for v in y], a, height=h, color=C[0], label="2005→2015年")
    ax.barh([v - h / 2 for v in y], b, height=h, color=C[1], label="2015→2025年")
    for v, x1, x2 in zip(y, a, b):
        ax.text(min(x1, 0) - 0.4, v + h / 2, f"{x1:.1f}", ha="right", va="center", fontsize=7.5, color=INK2)
        ax.text((x2 + 0.4) if x2 >= 0 else (x2 - 0.4), v - h / 2, f"{x2:+.1f}", ha="left" if x2 >= 0 else "right", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(items, fontsize=9)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.axhline(6.5, color="#e4e3df", lw=1)
    ax.set_xlim(-30, 9)
    ax.set_xlabel("年平均の変化率（%、対数の差÷年数）")
    ax.set_title("2015年からは、ほとんど下がっていない", loc="left", fontsize=12)
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.grid(axis="x", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.92, bottom=0.14)
    save(fig, FIG / "fig2_period_rates.png", SRC, "注：上の6品目は POS 情報で作る品目（テレビ・パソコン2品目・カメラはヘドニック法）")


def fig3():
    rows = list(csv.DictReader(open(RES / "unit_value_vs_cpi.csv", encoding="utf-8")))
    ys = [int(r["year"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    uv = [float(r["unit_value_idx2005"]) for r in rows]; cp = [float(r["cpi_pc_idx2005"]) for r in rows]
    ax.plot(ys, uv, color=C[1], lw=2); ax.plot(ys, cp, color=C[0], lw=2)
    ax.text(2025.3, uv[-1], f"1台あたりの輸入額\n（電算機類）{uv[-1]:.2f}", fontsize=8.5, va="center", color=INK2)
    ax.text(2025.3, cp[-1], f"CPI パソコン\n（2品目）{cp[-1]:.2f}", fontsize=8.5, va="center", color=INK2)
    ax.fill_between(ys, cp, uv, where=[y >= 2005 for y in ys], color=C[0], alpha=0.08, lw=0)
    ax.set_yscale("log"); ax.set_yticks([0.1, 0.2, 0.5, 1, 2, 5]); ax.set_yticklabels(["0.1", "0.2", "0.5", "1", "2", "5"])
    ax.axhline(1, color=INK2, lw=0.6)
    ax.set_xlim(2000, 2031); ax.set_xticks(range(2000, 2026, 5))
    ax.set_ylabel("2005年＝1（対数目盛）")
    ax.set_title("1台あたりの金額は上がり、品質を差し引いた指数は10分の1に", loc="left", fontsize=12)
    style(ax)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
    save(fig, FIG / "fig3_unit_value_gap.png", SRC3, "注：輸入額は周辺機器を含む「電算機類」の金額÷台数で、店の値段ではない。CPI パソコンはデスクトップ型とノート型のウエイトでの幾何平均")


def fig4():
    rows = list(csv.DictReader(open(RES / "requestion_counterfactual.csv", encoding="utf-8")))
    ys = [int(r["year"]) for r in rows]
    act = [float(r["c_pc_actual"]) for r in rows]; cf = [float(r["c_pc_if_unit_value"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    w = 0.38
    ax.bar([y - w / 2 for y in ys], act, width=w, color=C[0], label="実際の指数（品質を差し引く）")
    ax.bar([y + w / 2 for y in ys], cf, width=w, color=C[1], label="1台あたりの輸入額で動かした場合")
    ax.axvspan(2005.5, 2015.5, color="#efeeea", zorder=0)
    ax.text(2010.5, 0.075, "2006〜2015年は近似\n（2015年基準のウエイトの割合を使用）", ha="center", fontsize=8, color=INK2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(2006, 2026, 2))
    ax.set_ylim(-0.12, 0.11)
    ax.set_ylabel("総合の前年比への寄与（ポイント）")
    ax.set_title("1台あたりの輸入額で動かしても、総合の前年比の違いは年に0.1ポイント未満", loc="left", fontsize=12)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    style(ax)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.9, bottom=0.13)
    save(fig, FIG / "fig4_counterfactual_pc.png", SRC4, "注：パソコン2品目だけの寄与。2016年以降はその時期の基準（2015年・2020年）のウエイトで計算")


def main():
    d, names = load()
    m = json.load(open(RES / "main.json", encoding="utf-8"))
    fig1(d); fig2(m); fig3(); fig4()


if __name__ == "__main__":
    main()
