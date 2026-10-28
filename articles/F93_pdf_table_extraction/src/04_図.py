"""図を作る（figures/）。"""
from common import *
import textwrap
acc = pd.read_csv(RES / "accuracy_by_tool_table.csv")
tot = pd.read_csv(RES / "accuracy_by_tool.csv", index_col=0)
order = tot.sort_values("correct_rate", ascending=False).index.tolist()

# 図1 ツール×表の正読率
m = acc.pivot(index="tool", columns="table", values="correct_rate").loc[order]
fig, ax = plt.subplots(figsize=(8.4, 6.2))
im = ax.imshow(m.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
for i in range(m.shape[0]):
    for j in range(m.shape[1]):
        v = m.values[i, j]; ax.text(j, i, f"{v*100:.1f}%" if v < 0.9995 else "100%", ha="center", va="center", fontsize=10, color="white" if v > 0.6 else INK)
ax.set_xticks(range(4)); ax.set_xticklabels([SHORT[t] for t in m.columns]); ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
ax.set_title("正解と同じ値・同じ順で読めたセルの割合（4つの表、計4,757セル）", loc="left")
ax.spines[:].set_visible(False)
note(fig); fig.savefig(FIG / "fig1_accuracy_heatmap.png"); plt.close(fig)

# 図2 誤りの内訳
t = tot.loc[order]
fig, ax = plt.subplots(figsize=(8.6, 6.0))
y = np.arange(len(t))[::-1]
left = np.zeros(len(t))
for col, lab, c in [("correct_rate", "正しく読めた", BLUE), ("misread_rate", "違う値で読んだ（誤読）", RED), ("missing_rate", "読み落とした・順番が崩れた", GRAY)]:
    ax.barh(y, t[col], left=left, color=c, label=lab, height=0.65); left += t[col].values
for yi, (_, r) in zip(y, t.iterrows()):
    ax.text(1.01, yi, f"行として再現 {r.row_rate*100:.0f}%", va="center", fontsize=9, color=INK)
ax.set_yticks(y); ax.set_yticklabels(t.index); ax.set_xlim(0, 1.25); ax.set_xticks([0, .25, .5, .75, 1]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.07), ncol=3, frameon=False, fontsize=9)
ax.set_title("読み方ごとの誤りの内訳（4つの表の合計）", loc="left")
fig.text(0.01, -0.07, SOURCE, fontsize=8, color=GRAY, ha="left", va="top"); fig.savefig(FIG / "fig2_error_breakdown.png"); plt.close(fig)

# 図3 よくある崩れ方の実例（同じ行が、読み方によってどうなったか）
def first(tool, tid, p, pred):
    x = json.load(open(EXT / f"{tool}.json", encoding="utf-8"))[tid][str(p)]
    for r in x:
        s = " | ".join(str(c).replace("\n", "⏎") for c in r)
        if pred(s): return s
    return "（該当する行なし）"
ex = [
    ("T4 符号つき：1982年1月の切替（正解：－4 －3 0 －1 0.0）", [
        ("pdfplumber_文字", first("pdfplumber_文字", "T4", 2, lambda s: "－ 4" in s or "- 4" in s), "◯ 符号と数のあいだの空白を詰めれば正しく読める"),
        ("pdfplumber_表（罫線）", first("pdfplumber_表（罫線）", "T4", 2, lambda s: "4" in s and "3" in s and "1" in s and "－" in s), "× 罫線のない最後の列（失業率）が消える"),
        ("tabula_stream", first("tabula_stream", "T4", 2, lambda s: "1980" in s), "△ 値はそろうが、失業率が行の見出しの側に入り込む"),
        ("PyMuPDF_表", first("PyMuPDF_表", "T4", 2, lambda s: "1982" in s), "× 符号が数の後ろの改行に回り、0.0 が「0 0 .」に割れる")]),
    ("T1 学歴別：中学・1999年3月卒（正解：4,479 3,066 2,032 641 393 …）", [
        ("pdfplumber_文字", first("pdfplumber_文字", "T1", 0, lambda s: "4,479" in s), "◯ そのまま読める"),
        ("PyMuPDF_表", first("PyMuPDF_表", "T1", 0, lambda s: "4 479" in s), "× カンマと小数点が別の行に分かれ、4,479 が「4」と「479」になる")]),
    ("T3 規模別：2004年3月卒・1年目まで（正解：363,522 54,941 15.1 2,392 32.4 …）", [
        ("camelot_stream", first("camelot_stream", "T3", 0, lambda s: "363,522" in s), "◯ 1行ずつ読める"),
        ("camelot_lattice", first("camelot_lattice", "T3", 0, lambda s: "363,522" in s), "× 横の罫線がない3行が1つのセルにまとまり、縦に並ぶ"),
        ("OCR英語_150dpi", first("OCR英語_150dpi", "T3", 0, lambda s: "363,522" in s), "△ 数は読めるが「:」「.」などのごみが付き、見出しが化ける")]),
]
fig, ax = plt.subplots(figsize=(11, 8.2)); ax.axis("off")
yy = 0.99
for title, items in ex:
    ax.text(0, yy, title, fontsize=11.5, weight="bold", va="top", transform=ax.transAxes); yy -= 0.05
    for tool, s, cm in items:
        s = s if len(s) < 230 else s[:230] + " …"
        lines = textwrap.wrap(s, 86) or [""]
        ax.text(0.01, yy, tool, fontsize=9.5, color=BLUE, va="top", transform=ax.transAxes)
        ax.text(0.22, yy, "\n".join(lines[:3]), fontsize=8.8, va="top", transform=ax.transAxes, color=INK)
        yy -= 0.032 * min(len(lines), 3)
        ax.text(0.22, yy, cm, fontsize=8.8, va="top", transform=ax.transAxes, color=RED if cm.startswith("×") else (ORANGE if cm.startswith("△") else GREEN))
        yy -= 0.045
    yy -= 0.012
ax.set_title("同じ行が、読み方によってどう出てくるか（| はセルの区切り、⏎ はセル内の改行）", loc="left", fontsize=12)
note(fig); fig.savefig(FIG / "fig3_examples.png"); plt.close(fig)

# 図4 わざと入れた読み間違いを検算で見つけられた割合
det = pd.read_csv(RES / "rules_simulation_detect_rate.csv")
kinds = ["桁の落ち（1桁消える）", "数字の入れ替え（隣の2桁）", "似た字の誤認（3↔8・1↔7・0↔6）", "小数点・符号の落ち", "列ずれ（隣と入れ替え）", "列の抜け（1つ落ちて左に詰まる）"]
d = det.pivot(index="kind", columns="table", values="any").reindex(kinds)
fig, ax = plt.subplots(figsize=(8.6, 5.4))
ax.imshow(d.values, cmap="Greens", vmin=0, vmax=1, aspect="auto")
for i in range(d.shape[0]):
    for j in range(d.shape[1]):
        v = d.values[i, j]
        ax.text(j, i, "—" if np.isnan(v) else f"{v*100:.0f}%", ha="center", va="center", color="white" if (not np.isnan(v) and v > 0.6) else INK)
ax.set_xticks(range(4)); ax.set_xticklabels([SHORT[t] for t in d.columns]); ax.set_yticks(range(len(kinds))); ax.set_yticklabels(kinds)
ax.spines[:].set_visible(False)
ax.set_title("わざと1か所だけ読み間違えたとき、検算で気づける割合（各1,000回）", loc="left")
note(fig, SOURCE + "\n— は該当する値がない（T2 は小数・符号がない）"); fig.savefig(FIG / "fig4_detection_by_error.png"); plt.close(fig)

# 図5 ルールを足していくと、どこまで気づけるか
sim = pd.read_csv(RES / "rules_simulation_raw.csv.gz")
steps = [("列の数", ["R0"]), ("＋足し算", ["R0", "R1"]), ("＋割り算（率）", ["R0", "R1", "R2"]), ("＋大小・範囲", ["R0", "R1", "R2", "R3"]), ("＋行どうし", ["R0", "R1", "R2", "R3", "R4"])]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
cols = {"T1": BLUE, "T2": ORANGE, "T3": GREEN, "T4": PURPLE}
for tid, g in sim.groupby("table"):
    vals = [g[ks].fillna(False).astype(bool).any(axis=1).mean() for _, ks in steps]
    ax.plot(range(len(steps)), vals, marker="o", color=cols[tid], label=SHORT[tid], lw=2)
allv = [sim[ks].fillna(False).astype(bool).any(axis=1).mean() for _, ks in steps]
ax.plot(range(len(steps)), allv, marker="s", color=INK, ls="--", label="全体", lw=1.5)
for i, v in enumerate(allv): ax.text(i + 0.12, v - 0.05, f"{v*100:.0f}%", ha="center", fontsize=9, color=INK)
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s for s, _ in steps]); ax.set_ylim(0, 1.05)
ax.set_yticks([0, .25, .5, .75, 1]); ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.grid(axis="y", color="#e6e6e6")
ax.set_title("検算のルールを足していくと、読み間違いに気づける割合はどう増えるか", loc="left")
note(fig); fig.savefig(FIG / "fig5_rules_cumulative.png"); plt.close(fig)
print([p.name for p in sorted(FIG.glob("*.png"))])
