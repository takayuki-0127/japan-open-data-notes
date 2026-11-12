"""480 ヒストグラムは、幅と始点の取り方で、山の数がどれだけ変わるのか（架空のデータ＋市区町村の65歳以上の割合、seed 480）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from scipy.signal import find_peaks
from common import *

SEED = 480
SRC = "架空のデータ（作成者が乱数で作成、seed 480）"
SRC2 = "統計センター「SSDSE-A-2026（市区町村）」の65歳以上人口の割合を加工して作成"
PROM = 0.10          # 「はっきりした山」：いちばん高い棒の1割以上、まわりより高い山


def draw(kind, n, rng):
    if kind == "山が1つ（左右対称）": return rng.normal(0, 1, n)
    if kind == "山が1つ（右に長い）": return rng.lognormal(0, 0.6, n)
    k = rng.random(n) < (0.5 if "大きさが違う" not in kind else 0.75)
    sep = {"山が2つ（離れている）": 4.0, "山が2つ（近い）": 2.6, "山が2つ（大きさが違う）": 3.6}[kind]
    return np.where(k, rng.normal(0, 1, n), rng.normal(sep, 1, n))


KINDS = ["山が1つ（左右対称）", "山が1つ（右に長い）", "山が2つ（離れている）", "山が2つ（近い）", "山が2つ（大きさが違う）"]
TRUE = {k: (1 if "1つ" in k else 2) for k in KINDS}
NS = [50, 200, 1000, 5000]
RULES = ["スタージェス", "スコット", "フリードマン＝ディアコニス", "10本に決め打ち", "30本に決め打ち", "60本に決め打ち"]
NP_RULE = {"スタージェス": "sturges", "スコット": "scott", "フリードマン＝ディアコニス": "fd"}


def peaks(h, prom=PROM):
    h = np.asarray(h, float)
    if h.max() <= 0: return 0
    p, _ = find_peaks(np.r_[0, h, 0], prominence=prom * h.max() if prom else None)
    return len(p)


def edges(x, rule):
    if rule in NP_RULE: return np.histogram_bin_edges(x, bins=NP_RULE[rule])
    return np.histogram_bin_edges(x, bins=int(rule[:2]))


def kde_peaks(x):
    g = np.linspace(x.min(), x.max(), 400); d = stats.gaussian_kde(x)(g)
    return peaks(d)


def shifted_counts(x, w, steps=10):
    out = []
    for s in range(steps):
        lo = x.min() - w * s / steps
        e = np.arange(lo, x.max() + w, w)
        out.append(peaks(np.histogram(x, bins=e)[0]))
    return out


# ---- 0. 置いた分布そのものの山の数（確かめ）----
g = np.linspace(-5, 12, 20001)
dens = {"山が1つ（左右対称）": stats.norm.pdf(g), "山が1つ（右に長い）": stats.lognorm.pdf(g.clip(1e-9), 0.6),
        "山が2つ（離れている）": 0.5 * stats.norm.pdf(g) + 0.5 * stats.norm.pdf(g, 4.0), "山が2つ（近い）": 0.5 * stats.norm.pdf(g) + 0.5 * stats.norm.pdf(g, 2.6),
        "山が2つ（大きさが違う）": 0.75 * stats.norm.pdf(g) + 0.25 * stats.norm.pdf(g, 3.6)}
truth = pd.DataFrame([dict(分布=k, 置いた山の数=TRUE[k], 密度から数えた山の数=peaks(dens[k]),
                           谷の深さ=round((1 - dens[k][(g > 0.5) & (g < (3.5 if "2つ" in k else 0.6))].min() / np.sort(dens[k][find_peaks(dens[k])[0]])[0]) * 100, 1) if "2つ" in k else np.nan) for k in KINDS])
truth.to_csv(RES / "true_modes.csv", index=False)

# ---- 1. 幅の決まりごとに、本当の山の数と合う割合 ----
rng = np.random.default_rng(SEED)
REP = 500
rows, rows_shift = [], []
for kind in KINDS:
    for n in NS:
        cnt = {r: [] for r in RULES + ["核密度推定"]}; allp = {r: [] for r in RULES}; nb = {r: [] for r in RULES}; ch = []; chm = []
        for _ in range(REP):
            x = draw(kind, n, rng)
            for r in RULES:
                h = np.histogram(x, bins=edges(x, r))[0]
                cnt[r].append(peaks(h)); allp[r].append(peaks(h, None)); nb[r].append(len(h))
            cnt["核密度推定"].append(kde_peaks(x))
            e = edges(x, "スコット"); c = shifted_counts(x, e[1] - e[0]); ch.append(c)
        for r in RULES + ["核密度推定"]:
            c = np.array(cnt[r])
            rows.append(dict(分布=kind, 件数=n, 決まり=r, 本当の山の数=TRUE[kind], 合った割合=round((c == TRUE[kind]).mean() * 100, 1), 多く出た割合=round((c > TRUE[kind]).mean() * 100, 1),
                             少なく出た割合=round((c < TRUE[kind]).mean() * 100, 1), 山の数の平均=round(c.mean(), 2),
                             小さな山も数えた平均=round(np.mean(allp[r]), 2) if r in allp else np.nan, 棒の本数の中央値=float(np.median(nb[r])) if r in nb else np.nan))
        ch = np.array(ch)
        rows_shift.append(dict(分布=kind, 件数=n, 始点で山の数が変わった割合=round((ch.max(1) != ch.min(1)).mean() * 100, 1),
                               本当の数と合う始点と合わない始点が両方あった割合=round((((ch == TRUE[kind]).any(1)) & ((ch != TRUE[kind]).any(1))).mean() * 100, 1),
                               山の数の幅の平均=round((ch.max(1) - ch.min(1)).mean(), 2)))
rule = pd.DataFrame(rows); rule.to_csv(RES / "modes_by_rule.csv", index=False)
shift = pd.DataFrame(rows_shift); shift.to_csv(RES / "modes_by_origin_shift.csv", index=False)

# ---- 2. きりのよい数字に丸めた値が作る見かけの山 ----
def heaped(n, share, rng):
    """架空の「1回の利用時間（分）」。対数正規。share の人は10分単位に丸めて答える"""
    t = rng.lognormal(np.log(45), 0.5, n)
    r = rng.random(n) < share
    return np.where(r, np.round(t / 10) * 10, np.round(t)).clip(1, None)

rows = []
for share in [0.0, 0.2, 0.4]:
    for w, lo in [(1, 0.5), (2, 0.5), (5, 0.0), (5, 2.5), (10, 0.0), (10, 5.0)]:
        c = []
        for _ in range(REP):
            x = heaped(2000, share, rng); e = np.arange(lo, x.max() + w, w); c.append(peaks(np.histogram(x, bins=e)[0]))
        c = np.array(c)
        rows.append(dict(丸めて答える人の割合=int(share * 100), 幅=w, 始点=lo, 山の数の平均=round(c.mean(), 2), 山が1つだった割合=round((c == 1).mean() * 100, 1), 山が3つ以上だった割合=round((c >= 3).mean() * 100, 1)))
heap = pd.DataFrame(rows); heap.to_csv(RES / "heaping_modes.csv", index=False)
xh = heaped(2000, 0.4, np.random.default_rng(SEED + 1)); pd.DataFrame({"利用時間_分": xh.astype(int)}).to_csv(DATA / "example_heaped_minutes.csv", index=False)

# ---- 3. 公的統計の分布：市区町村の65歳以上の割合（1,740市区町村）----
a = pd.read_csv(DATA / "municipal_aged_share_values.csv").iloc[:, 0].values
rows = []
for r in RULES:
    e = edges(a, r); h = np.histogram(a, bins=e)[0]
    c = shifted_counts(a, e[1] - e[0])
    rows.append(dict(決まり=r, 棒の本数=len(h), 幅=round(e[1] - e[0], 2), 山の数=peaks(h), 小さな山も数えた数=peaks(h, None), 始点を10通りずらした山の数=f"{min(c)}〜{max(c)}"))
for w in [0.5, 1, 2, 2.5, 5]:
    c = [peaks(np.histogram(a, bins=np.arange(lo, a.max() + w, w))[0]) for lo in np.arange(10 - w, 10, w / 10)]
    c0 = peaks(np.histogram(a, bins=np.arange(10, a.max() + w, w))[0]); ca = peaks(np.histogram(a, bins=np.arange(10, a.max() + w, w))[0], None)
    rows.append(dict(決まり=f"幅{w}ポイント（始点10%）", 棒の本数=len(np.arange(10, a.max() + w, w)) - 1, 幅=w, 山の数=c0, 小さな山も数えた数=ca, 始点を10通りずらした山の数=f"{min(c)}〜{max(c)}"))
rows.append(dict(決まり="核密度推定", 棒の本数=np.nan, 幅=np.nan, 山の数=kde_peaks(a), 小さな山も数えた数=np.nan, 始点を10通りずらした山の数=""))
pub = pd.DataFrame(rows); pub.to_csv(RES / "public_data_modes.csv", index=False)

# ---- 図 ----
rg = np.random.default_rng(SEED + 2)
for _ in range(200):                         # 幅と始点で山の数が 1・2・たくさん と変わる例を探す（種は固定）
    x = draw("山が2つ（近い）", 200, rg); e = edges(x, "スコット"); w = e[1] - e[0]; c = shifted_counts(x, w)
    if 1 in c and 2 in c: break
pd.DataFrame({"x": x.round(4)}).to_csv(DATA / "example_bimodal_200.csv", index=False)
s1, s2 = c.index(2), c.index(1); w_ex, c_ex = float(w), list(c)
fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.7), sharey=False)
for ax, (ttl, e_, col) in zip(axs, [(f"幅{w:.2f}・始点A", np.arange(x.min() - w * s1 / 10, x.max() + w, w), BLUE), (f"幅は同じ・始点だけ{abs(s2 - s1) / 10 * w:.2f}ずらす", np.arange(x.min() - w * s2 / 10, x.max() + w, w), ORANGE),
                               ("幅を4分の1に", np.arange(x.min(), x.max() + w / 4, w / 4), GRAY)]):
    h = np.histogram(x, bins=e_)[0]; ax.bar(e_[:-1], h, width=np.diff(e_), align="edge", color=col, edgecolor="white", lw=0.5)
    ax.set_title(f"{ttl}\n→ はっきりした山 {peaks(h)}つ", fontsize=10.5, loc="left"); ax.set_xlabel("値")
axs[0].set_ylabel("件数"); fig.suptitle("同じ200件のデータ。幅と始点だけを変えた", x=0.01, ha="left", fontsize=13)
fig.tight_layout(); save(fig, "a480_same_data_three_histograms.png", f"出典：{SRC}。山が2つ（近い）の分布から200件")

fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.3), sharey=True)
cols = dict(zip(RULES + ["核密度推定"], [BLUE, "#14427a", LIGHT, GREEN, ORANGE, "#8f3210", INK]))
for ax, kind in zip(axs, ["山が1つ（左右対称）", "山が2つ（近い）"]):
    for r in RULES + ["核密度推定"]:
        s = rule[(rule.分布 == kind) & (rule.決まり == r)]
        ax.plot(np.arange(4), s.合った割合, marker="o", ms=4, lw=2, color=cols[r], label=r, ls="--" if r == "核密度推定" else "-")
    ax.set_xticks(np.arange(4)); ax.set_xticklabels(["50件", "200件", "1,000件", "5,000件"]); ax.set_title(kind, loc="left", fontsize=11); ax.set_ylim(-3, 103)
axs[0].set_ylabel("山の数が本当の数と合った割合（%）"); hd, lb = axs[1].get_legend_handles_labels()
fig.tight_layout(); fig.legend(hd, lb, fontsize=8.5, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.1))
save(fig, "a480_correct_rate_by_rule.png", f"出典：{SRC}。件数ごとに500回。「山」はいちばん高い棒の1割以上まわりより高いもの", y=-0.12)

fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.7))
for ax, (w, lo, ttl) in zip(axs, [(1, 0.5, "幅1分"), (5, 0.0, "幅5分（始点0）"), (10, 5.0, "幅10分（始点5）")]):
    e_ = np.arange(lo, 151, w); h = np.histogram(xh, bins=e_)[0]
    ax.bar(e_[:-1], h, width=w, align="edge", color=BLUE if w == 10 else ORANGE, edgecolor="white", lw=0.3)
    ax.set_title(f"{ttl}\n→ はっきりした山 {peaks(h)}つ", fontsize=10.5, loc="left"); ax.set_xlabel("利用時間（分）"); ax.set_xlim(0, 150)
axs[0].set_ylabel("件数"); fig.suptitle("4割の人が10分単位に丸めて答えたデータ（本当の山は1つ）", x=0.01, ha="left", fontsize=13)
fig.tight_layout(); save(fig, "a480_heaping.png", f"出典：{SRC}。架空の利用時間2,000件")

main = dict(seed=SEED, 山の決め方="いちばん高い棒の1割以上、まわりより高い山", 例の幅=round(w_ex, 3), 例の始点ごとの山の数=c_ex,
            市区町村の数=int(len(a)))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(truth.to_string()); print(rule.pivot_table(index=["分布", "件数"], columns="決まり", values="合った割合")[RULES + ["核密度推定"]].to_string())
print(rule.pivot_table(index=["分布", "件数"], columns="決まり", values="棒の本数の中央値")[RULES].to_string()); print(rule.pivot_table(index=["分布", "件数"], columns="決まり", values="小さな山も数えた平均")[RULES].to_string())
print(shift.to_string()); print(heap.to_string()); print(pub.to_string()); print(main)
