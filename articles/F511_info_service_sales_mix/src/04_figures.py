"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「特定サービス産業動態統計調査」長期データ（情報サービス業）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.76, top=0.89, bottom=0.15)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def endlabel(ax, x, y, text, ty=None):
    ax.annotate(text, (x, y), xytext=(x + 0.4, y if ty is None else ty), textcoords="data", va="center", fontsize=9, color=INK,
                annotation_clip=False)


def spread(vals, gap):
    """右端のラベルの縦の位置が重ならないようにずらす（上から順に gap 以上あける）。"""
    order = sorted(vals, key=lambda k: -vals[k])
    out, prev = {}, None
    for k in order:
        y = vals[k] if prev is None else min(vals[k], prev - gap)
        out[k] = y
        prev = y
    return out


main = json.load(open(R / "main.json", encoding="utf-8"))
sh = pd.read_csv(R / "share_by_year.csv", index_col=0).loc[2000:]
idx = pd.read_csv(R / "index_2000_100.csv", index_col=0)
rq = pd.read_csv(R / "requestion_table.csv", index_col=0)
L = int(sh.index.max())

# ---- 図1：割合 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
items = [("custom", "受注ソフトウェア"), ("sys_mgmt", "システム等管理運営受託"), ("products", "ソフトウェアプロダクツ"), ("processing", "計算事務等情報処理")]
pos = spread({k: sh[k][L] for k, _ in items}, 2.6)
for (k, lab), c in zip(items, C):
    ax.plot(sh.index, sh[k], color=c, lw=2.2, label=lab)
    endlabel(ax, L, sh[k][L], f"{lab} {sh[k][L]:.1f}%", pos[k])
ax.set_ylim(0, 70)
ax.set_xlabel("年")
ax.set_ylabel("売上高合計に占める割合（%）")
finish(fig, ax, "受注ソフトウェアは売上の6割前後のまま。伸びたのは運用の受託")
save(fig, "fig1_share_by_kind.png")

# ---- 図2：指数 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
items2 = [("total", "売上高合計"), ("custom", "受注ソフトウェア"), ("sys_mgmt", "システム等管理運営受託"), ("products", "ソフトウェアプロダクツ"), ("processing", "計算事務等情報処理")]
cols2 = [INK2, C[0], C[1], C[2], C[3]]
pos = spread({k: idx[k][L] for k, _ in items2}, 11)
for (k, lab), c in zip(items2, cols2):
    ax.plot(idx.index, idx[k], color=c, lw=2.4 if k == "total" else 2.0, ls="--" if k == "total" else "-", label=lab)
    endlabel(ax, L, idx[k][L], f"{lab} {idx[k][L]:.0f}", pos[k])
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlabel("年")
ax.set_ylabel("指数（2000年＝100）")
finish(fig, ax, "不連続を調整した伸びでつなぐと、2000→2024年で売上は1.6倍、運用の受託は3.3倍")
save(fig, "fig2_index.png")

# ---- 図3：受注の中身 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(rq.index, rq.si_in_custom_pct, color=C[0], lw=2.2, label="実数の比")
ax.plot(rq.index, rq.si_in_custom_from_index_pct, color=C[0], lw=2.0, ls="--", label="調整済みの伸びでつないだ値")
for col in ["si_in_custom_pct", "si_in_custom_from_index_pct"]:
    endlabel(ax, L, rq[col][L], f"{rq[col][L]:.1f}%")
ax.annotate(f"{rq.si_in_custom_pct[2000]:.1f}%", (2000, rq.si_in_custom_pct[2000]), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 80)
ax.set_xlabel("年")
ax.set_ylabel("受注ソフトウェアに占めるSIの割合（%）")
ax.legend(frameon=False, loc="lower right")
finish(fig, ax, "受注ソフトウェアの中で、SI（システムをまとめて作る仕事）が増えた")
save(fig, "fig3_si_within_custom.png")

# ---- 図4：プロダクツとゲーム ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(rq.index, rq.products_share, color=C[2], lw=2.2, label="ソフトウェアプロダクツ")
ax.plot(rq.index, rq.products_ex_game_share, color=C[2], lw=2.0, ls="--", label="うちゲームソフトを除く")
ax.plot(rq.index, rq.game_share, color=C[4], lw=2.0, label="うちゲームソフト")
for col in ["products_share", "products_ex_game_share", "game_share"]:
    endlabel(ax, L, rq[col][L], f"{rq[col][L]:.1f}%")
pk = int(rq.products_share.idxmax())
ax.annotate(f"{pk}年 {rq.products_share[pk]:.1f}%", (pk, rq.products_share[pk]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 16)
ax.set_xlabel("年")
ax.set_ylabel("売上高合計に占める割合（%）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "パッケージの割合が上がった年は、ゲームソフトの山。ゲームを除くと6%前後")
save(fig, "fig4_products_game.png")
