"""05 図：results/ から figures/fig1〜6 を作る（Noto Sans CJK JP）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False})
C_OK, C_NG, C_MID, C_GREY, C_BLUE = "#2e8b57", "#c0392b", "#e6a23c", "#b0b0b0", "#2e86c1"


def box(ax, x, y, w, h, text, fc="#f4f6f8", ec="#888", fs=10, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight, linespacing=1.45)


# ---------- 図1 引き継ぎ前と後 ----------
A = pd.read_csv(RES / "A_audit_by_article.csv")
Bs = json.load(open(RES / "B_dryrun_samever.json", encoding="utf-8"))
C1 = json.load(open(RES / "C_after_local1.json", encoding="utf-8"))
nsteps = sum(len(a["steps"]) for a in Bs)
fig, ax = plt.subplots(figsize=(13, 6.4)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 6.6)
ax.text(0.1, 6.3, "引き継ぎ前：README が6つ", fontsize=13, weight="bold")
for i, a in A.iterrows():
    y = 5.3 - i * 0.82
    dep = a["前の回への依存"] if isinstance(a["前の回への依存"], str) else "—"
    box(ax, 0.1, y, 5.6, 0.68, f"{a['回']}　手順 {a['README の手順']}　前の回：{dep}"
        + ("　ブラウザ" if a["ブラウザ（playwright）"] else "") + ("　GitHub から取る" if a["ネットワーク"] else ""), fs=9.5)
ax.text(0.1, 0.25, f"pip install を6回、python を {nsteps} 回、順番と前提は自分で読み取る", fontsize=10, color="#555")
ax.annotate("", xy=(7.0, 3.3), xytext=(6.0, 3.3), arrowprops=dict(arrowstyle="-|>", lw=2, color="#555"))
ax.text(7.2, 6.3, "引き継ぎ後：入口が1つ", fontsize=13, weight="bold")
box(ax, 7.2, 4.9, 5.6, 1.0, "pip install -r requirements.lock\n（版を固定。各回の requirements.txt は下限だけ）", fc="#eaf2fb", ec=C_BLUE, fs=10)
box(ax, 7.2, 3.3, 5.6, 1.3, "python run_all.py\nコミットを決めて取る → F246 → F247 → F248\n（前の回は隣で作り直したものを使う。DuckDB は1本で足す）", fc="#eaf2fb", ec=C_BLUE, fs=10)
box(ax, 7.2, 1.9, 5.6, 1.1, "照合：数字のファイル 88 個を基準の md5 と比べる\n＋ 記事に載った元のファイルとの差を書く", fc="#eaf7ef", ec=C_OK, fs=10)
box(ax, 7.2, 0.7, 5.6, 0.9, "python tests/test_rules.py\n既存店の判定（4か所に書かれている）が同じ答えか", fc="#eaf7ef", ec=C_OK, fs=10)
fig.suptitle("図1　引き継ぎ資料で変えたこと：6つの README を読んで33回流す形から、決めた版で1回流して照合する形へ",
             x=0.01, ha="left", fontsize=13, weight="bold")
fig.savefig(FIG / "fig1_before_after.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図2 監査（コードを読んで数えたこと） ----------
cols = [("前の回への依存", "前の回に頼る"), ("ネットワーク", "GitHub から取る"), ("ブラウザ（playwright）", "ブラウザが要る"),
        ("版の下限だけ（>=）", "版が下限だけ"), ("逃げ道なしで隣を読む", "隣のフォルダを\n逃げ道なしで読む")]
R = pd.read_csv(RES / "A_rule_copies.csv")
M = pd.DataFrame(index=A["回"])
for c, lab in cols:
    v = A.set_index("回")[c]
    M[lab] = [(1 if isinstance(x, str) and x.strip() else 0) if c in ("前の回への依存", "逃げ道なしで隣を読む") else int(x > 0) for x in v]
M["既存店の判定を\n自分で書いている"] = [int(a in set(R["回"])) for a in M.index]
fig, ax = plt.subplots(figsize=(11.5, 4.6))
ax.imshow(M.values, cmap=matplotlib.colors.ListedColormap(["#f2f2f2", "#f0b27a"]), aspect="auto", vmin=0, vmax=1)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, "●" if M.values[i, j] else "", ha="center", va="center", color="#a04000", fontsize=13)
ax.set_xticks(range(M.shape[1]), M.columns, fontsize=10); ax.set_yticks(range(M.shape[0]), M.index)
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
ax.set_xticks([x - 0.5 for x in range(1, M.shape[1])], minor=True); ax.set_yticks([y - 0.5 for y in range(1, M.shape[0])], minor=True)
ax.grid(which="minor", color="white", lw=3)
kinds = R["書き方"].value_counts()
ax.set_title(f"版を固定した行（==）は 0／30。既存店の判定は {len(R)} か所に書かれ、書き方は2通り"
             f"（暦の月の差 {kinds.get('暦の月の差（開店月を1か月目と数える）', 0)}・日付で13か月後 {kinds.get('日付で13か月後（開店日から数える）', 0)}）",
             fontsize=10.5, loc="left")
fig.suptitle("図2　コードを読んで数えた「引き継ぐ人がつまずきそうなところ」（F246〜F251）", x=0.01, ha="left", fontsize=13, weight="bold")
fig.savefig(FIG / "fig2_audit.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図3 引き継ぎ前の試走 ----------
def reason(err):
    if "non-existent directory" in err or ("No such file" in err and ("results" in err or "dashboard" in err)):
        return "フォルダが無い"
    if "═" in err or "Executable" in err:
        return "ブラウザが無い"
    return "その他"


fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
for ax, (nm, lab) in zip(axes, [("samever", "同じ版（記事を作ったときのライブラリ）"), ("latest", "最新版（requirements.txt のとおり今入れた）")]):
    r = json.load(open(RES / f"B_dryrun_{nm}.json", encoding="utf-8"))
    for i, a in enumerate(r):
        for j, s in enumerate(a["steps"]):
            col = C_OK if s["rc"] == 0 else C_NG
            ax.add_patch(plt.Rectangle((j, i), 0.92, 0.8, color=col))
            ax.text(j + 0.46, i + 0.4, s["script"][4:6] if s["rc"] == 0 else reason(s["err"]).replace("が無い", "\nが無い"),
                    ha="center", va="center", color="white", fontsize=8.5 if s["rc"] else 10, weight="bold")
    nf = sum(s["rc"] != 0 for a in r for s in a["steps"])
    ax.set_xlim(-0.1, 6.1); ax.set_ylim(6, -0.2); ax.set_yticks([i + 0.4 for i in range(6)], [a["article"][:4] for a in r])
    ax.set_xticks([]); [s.set_visible(False) for s in ax.spines.values()]
    ax.set_title(f"{lab}\n33手順のうち止まったのは {nf}", fontsize=11, loc="left")
fig.text(0.01, -0.02, "緑：最後まで流れた（数字は src のスクリプトの番号）。赤：止まった（理由）。生成物（results/ など）を消し、README の python の行を上から流した。"
         "止まっても次の手順へ進んだ。", fontsize=9.5, color="#555")
fig.suptitle("図3　新しい人の役で、README だけを見て流すと：版の違いでは止まらず、止まったのは「フォルダが無い」と「ブラウザが無い」",
             x=0.01, y=1.06, ha="left", fontsize=13, weight="bold")
fig.savefig(FIG / "fig3_dryrun_before.png", dpi=150, bbox_inches="tight"); plt.close(fig)


# ---------- 図4 照合：数字のファイルは元と同じか ----------
def cat(s):
    if s == "同じ":
        return "バイトまで同じ"
    if s.startswith("同じ（中身"):
        return "gz の中身は同じ"
    if s.startswith("同じ（丸め"):
        return "丸めの差（相対1e-9か、書いた桁の1単位）"
    if s.startswith("近い"):
        return "JSON の数が少し違う"
    if s.startswith("違う"):
        return "違う"
    return "作られなかった"


order = ["バイトまで同じ", "gz の中身は同じ", "丸めの差（相対1e-9か、書いた桁の1単位）", "JSON の数が少し違う", "違う", "作られなかった"]
colors = [C_OK, "#7dcea0", "#f7dc6f", C_MID, C_NG, C_GREY]
rows = {}
for nm, lab in [("samever", "引き継ぎ前・同じ版\n（6回・コミットの全部）"), ("latest", "引き継ぎ前・最新版\n（6回・コミットの全部）")]:
    b = pd.read_csv(RES / f"B_files_{nm}.csv"); b = b[(b.種類 == "数字") & ~b.結果.str.startswith("手書き")]
    rows[lab] = b.結果.map(cat).value_counts()
c = pd.read_csv(RES / "C_verify_local1.csv"); c = c[(c.種類 == "数字") & (c.元のファイルと != "元に無い")]
rows["引き継ぎ後・run_all.py\n（F246〜F248 の段で作るもの）"] = c.元のファイルと.map(cat).value_counts()
T = pd.DataFrame(rows).T.reindex(columns=order).fillna(0)
T.to_csv(RES / "E_fig4_table.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(13, 4.6))
left = pd.Series(0.0, index=T.index)
for k, col in zip(order, colors):
    v = T[k] / T.sum(axis=1) * 100
    ax.barh(T.index, v, left=left, color=col, label=k, height=0.6)
    for y, (l, w, n) in enumerate(zip(left, v, T[k])):
        if n:
            ax.text(l + w / 2, y, f"{int(n)}", ha="center", va="center", fontsize=9.5, color="black")
    left += v
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("数字のファイル（csv・json・md・sql など）に占める割合（%）。数字は個数")
ax.legend(ncol=6, loc="upper left", bbox_to_anchor=(0, -0.18), frameon=False, fontsize=9.5)
fig.suptitle("図4　作り直した数字のファイルを、記事に載った元のファイルと比べる：バイトで比べると「違う」に見えるものの多くは、gz の時刻と丸めの差",
             x=0.01, ha="left", fontsize=12.5, weight="bold")
fig.savefig(FIG / "fig4_verify.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図5 DuckDB の並列と、版の固定 ----------
D = pd.read_csv(RES / "D_duckdb_threads.csv")
L = json.load(open(RES / "D_latest_vs_baseline.json", encoding="utf-8"))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
for k, (mode, col) in enumerate([("そのまま（並列）", C_NG), ("1本で足す（launch.py）", C_OK)]):
    d = D[D.流し方 == mode]
    a1.plot(d.回目, d["元のファイルと違うセル"], "o-", color=col, lw=2, label=f"{mode}：元のファイルと")
    a1.plot(d.回目, d["1回目と違うセル"], "s--", color=col, lw=1.2, alpha=0.7, label=f"{mode}：1回目と")
a1.set_xticks(range(1, 6)); a1.set_xlabel("同じコード・同じデータで流した回"); a1.set_ylabel("0.1 ずれたセルの数（mart の店×月）")
a1.legend(fontsize=8.8, frameon=False); a1.set_title("F247 の mart（store_month.csv、1,062行）", fontsize=11, loc="left")
vals = [L["same_as_baseline"], L["diff_from_baseline"]]
a2.bar(["基準と同じ", "基準と違う"], vals, color=[C_OK, C_NG], width=0.55)
for x, v in enumerate(vals):
    a2.text(x, v + 0.8, str(v), ha="center", fontsize=11)
a2.set_title(f"最新版（pandas {L['versions'].split()[0]}・DuckDB {L['versions'].split()[2]} ほか）で run_all.py\n数字のファイル {L['baseline_files']} 個を基準の md5 と", fontsize=11, loc="left")
fig.suptitle("図5　同じ数字に戻すのに効いたもの：DuckDB を1本で足すと実行ごとの揺れが消える。版を固定しないと md5 は合わない",
             x=0.01, y=1.07, ha="left", fontsize=12.5, weight="bold")
fig.savefig(FIG / "fig5_determinism.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図6 既存店の判定のテスト ----------
t = pd.read_csv(ROOT / "results" / "F_test_rules.csv")
e = t[(t.store_id == 91) & t.ym.between("2025-09", "2026-01")]
cols6 = ["設定書", "F246", "F247", "F248", "F250"]
fig, ax = plt.subplots(figsize=(11, 3.6))
for i, c in enumerate(cols6):
    for j, (ym, v) in enumerate(zip(e.ym, e[c])):
        ax.add_patch(plt.Rectangle((j, i), 0.94, 0.86, color=C_OK if v else "#e5e7e9"))
        ax.text(j + 0.47, i + 0.43, "既存店" if v else "—", ha="center", va="center", fontsize=10, color="white" if v else "#555")
ax.set_xlim(0, len(e)); ax.set_ylim(len(cols6), -0.1)
ax.set_xticks([j + 0.47 for j in range(len(e))], e.ym); ax.set_yticks([i + 0.43 for i in range(len(cols6))],
    ["会社設定書の文の読み方", "F246（暦の月の差）", "F247（暦の月の差）", "F248（暦の月の差）", "F250（日付で13か月後）"])
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title("テスト用の架空の店（2024-10-15 開店）。実際の24店×48か月では、5つとも同じ答え", fontsize=10.5, loc="left")
fig.suptitle("図6　同じ「既存店」の決めごとが4か所に書かれていた：月の途中に開店する店が来ると、2025-11 だけ答えが割れる",
             x=0.01, y=1.06, ha="left", fontsize=12.5, weight="bold")
fig.savefig(FIG / "fig6_rule_test.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("ok")
