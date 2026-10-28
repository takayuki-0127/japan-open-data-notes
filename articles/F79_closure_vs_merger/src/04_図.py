import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, FixedLocator, FixedFormatter
from common import RES, FIG
C1, C2, C3 = "#c0504d", "#4f81bd", "#9bbb59"
cif = pd.read_csv(RES / "cif_by_kind.csv")
kinds = ["株式会社", "合同会社", "その他（一般社団・NPOなど）"]

# 1. 種別ごとの CIF（閉鎖と合併を積み上げ）
fig, ax = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
for a, k in zip(ax, kinds):
    c = cif[(cif.kind == k) & (cif.year <= 10)]
    a.fill_between(c.year, 0, c.F1 * 100, color=C1, alpha=.8, label="閉鎖（清算結了・登記官）")
    a.fill_between(c.year, c.F1 * 100, (c.F1 + c.F2) * 100, color=C2, alpha=.8, label="合併による解散")
    c10 = c[np.isclose(c.year, 10)].iloc[0]; f1, f2 = c10.F1 * 100, c10.F2 * 100
    a.set_title(f"{k}\n10年後：閉鎖 {f1:.1f}%・合併 {f2:.1f}%", fontsize=10)
    a.set_xlabel("法人番号の指定からの年数"); a.grid(alpha=.3)
ax[0].set_ylabel("累積発生割合（%）"); ax[0].legend(loc="upper left", fontsize=8)
fig.suptitle("登記がなくなる2つの道：閉鎖と合併（Aalen–Johansen の累積発生関数）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f79_cif_kind.png"); plt.close()

# 2. 1−KM と CIF の差
kv = pd.read_csv(RES / "km_vs_cif.csv")
fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
x = np.arange(len(kv)); w = .38
for a, (cif_c, km_c, ttl) in zip(ax, [("close_CIF10", "close_1mKM10", "閉鎖（10年）"), ("merge_CIF10", "merge_1mKM10", "合併（10年）")]):
    a.bar(x - w / 2, kv[km_c] * 100, w, color="#999", label="競合を打ち切り扱い（1−KM）")
    a.bar(x + w / 2, kv[cif_c] * 100, w, color=C1 if "close" in cif_c else C2, label="累積発生関数（CIF）")
    for i in x:
        a.text(i, max(kv[km_c][i], kv[cif_c][i]) * 100 * 1.02, f"+{(kv[km_c][i] - kv[cif_c][i]) * 100:.2f}pt", ha="center", fontsize=8)
    a.set_xticks(x); a.set_xticklabels([g.replace("その他の市町村の", "その他の市町村の\n").replace("東京23区の", "東京23区の\n") for g in kv.group], fontsize=8)
    a.set_title(ttl); a.set_ylabel("%"); a.grid(axis="y", alpha=.3)
ax[0].legend(fontsize=8, loc="lower left")
fig.suptitle("競合リスクを無視すると、どれだけ多く見積もるか（差は「1−KM − CIF」）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f79_km_vs_cif.png"); plt.close()

# 3. 原因別 Cox と Fine–Gray
hr = pd.read_csv(RES / "hr_cs_fg.csv")
lab = {"kindj_合同会社": "合同会社（対 株式会社）", "kindj_その他（一般社団・NPOなど）": "一般社団・NPOなど", "area_東京23区": "東京23区（対 その他の市町村）",
       "area_政令市": "政令市", "cohort_c": "設立が5年新しい"}
fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.9), sharey=True)
for a, ev in zip(ax, ["閉鎖", "合併"]):
    pass
for a, ev in zip(ax, ["閉鎖", "合併"]):
    for j, (m, col, off) in enumerate([(f"原因別Cox_{ev}", "#555", -.13), (f"FineGray_{ev}", C1 if ev == "閉鎖" else C2, .13)]):
        t = hr[(hr.model == m) & (hr["var"].isin(lab))].set_index("var").loc[list(lab)]
        y = np.arange(len(t))[::-1] + off
        a.errorbar(t.HR, y, xerr=[t.HR - t.lo, t.hi - t.HR], fmt="o", color=col, ms=5, capsize=2,
                   label="原因別ハザード（Cox）" if j == 0 else "部分分布ハザード（Fine–Gray）")
    a.axvline(1, color="k", lw=.8); a.set_xscale("log"); a.set_title(ev); a.grid(alpha=.3)
    tk = [1, 1.2, 1.4, 1.6, 1.8] if ev == "閉鎖" else [0.2, 0.5, 1, 2, 4]
    a.xaxis.set_minor_formatter(NullFormatter()); a.xaxis.set_major_locator(FixedLocator(tk)); a.xaxis.set_major_formatter(FixedFormatter([str(t) for t in tk]))
ax[0].set_yticks(np.arange(len(lab))[::-1]); ax[0].set_yticklabels(list(lab.values()), fontsize=9)
ax[1].legend(fontsize=8, loc="lower left"); ax[0].set_xlabel("ハザード比（対数目盛）"); ax[1].set_xlabel("ハザード比（対数目盛）")
fig.suptitle("閉鎖しやすい法人と、合併しやすい法人は違う（30万法人、95%区間）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f79_hr.png"); plt.close()

# 4. 地域別の合併・閉鎖（5年）
gp = pd.read_csv(RES / "cif_by_group.csv")
a_ = gp[gp.by == "area"].set_index("value").loc[["東京23区", "政令市", "その他の市町村"]]
r_ = gp[gp.by == "region"].sort_values("merge5", ascending=False).set_index("value")
fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.9))
for a, t, ttl in [(ax[0], a_, "本店の場所"), (ax[1], r_, "地方")]:
    x = np.arange(len(t))
    a.bar(x - .2, t.close5 * 100, .4, color=C1, label="閉鎖")
    a.bar(x + .2, t.merge5 * 100, .4, color=C2, label="合併")
    for i in x:
        a.text(i + .2, t.merge5.iloc[i] * 100 + .1, f"{t.merge5.iloc[i] / t.close5.iloc[i] * 100:.0f}%", ha="center", fontsize=8, color=C2)
    a.set_xticks(x); a.set_xticklabels(t.index, fontsize=9); a.set_title(f"{ttl}（5年以内）"); a.set_ylabel("%"); a.grid(axis="y", alpha=.3)
ax[0].legend(fontsize=8)
fig.suptitle("合併は東京23区に集中（青の数字は「閉鎖を100としたときの合併」）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f79_area.png"); plt.close()

# 5. 全法人の年別
yy = pd.read_csv(RES / "yearly_all_corps.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 3.9)); ax2 = ax.twinx()
ax.bar(yy.index - .2, yy["清算の結了等"] / 1e4, .4, color=C1, label="清算の結了等")
ax.bar(yy.index + .2, yy["合併による解散"] / 1e4, .4, color=C2, label="合併による解散")
sh = yy["合併による解散"] / (yy["清算の結了等"] + yy["合併による解散"]) * 100
ax2.plot(yy.index, sh, "k-o", ms=4, label="合併の割合（右軸）"); ax2.set_ylim(0, 20); ax2.set_ylabel("合併÷（清算＋合併）（%）")
ax.set_ylabel("件数（万件）"); ax.set_xticks(yy.index); ax.grid(axis="y", alpha=.3)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
ax.set_title("すべての会社（株式・有限・合同）の年別：清算と合併（登記官による閉鎖は除く）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f79_yearly.png"); plt.close()

# 6. 頑健性
rb = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8))
for a, ev, col in [(ax[0], "close", C1), (ax[1], "merge", C2)]:
    t = rb[rb.event == ev].reset_index(drop=True)
    for i, r in t.iterrows():
        for k, (c, mk, off) in enumerate([("LLC_HR", "o", -.12), ("23ku_HR", "s", .12)]):
            v = eval(r[c]) if isinstance(r[c], str) else r[c]
            a.errorbar(v[0], i + off, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt=mk, color=col if k == 0 else "#333", ms=5, capsize=2,
                       label=("合同会社" if k == 0 else "東京23区") if i == 0 else None)
    a.set_yticks(range(len(t))); a.set_yticklabels(t.setting, fontsize=8); a.invert_yaxis()
    a.axvline(1, color="k", lw=.8); a.set_xscale("log"); a.grid(alpha=.3); a.set_title("閉鎖" if ev == "close" else "合併")
    a.xaxis.set_minor_formatter(NullFormatter())
    tk = [1, 1.2, 1.4, 1.6, 1.8] if ev == "close" else [0.4, 0.6, 1, 2, 3, 4]
    a.xaxis.set_major_locator(FixedLocator(tk)); a.xaxis.set_major_formatter(FixedFormatter([str(t) for t in tk]))
    a.legend(fontsize=8)
fig.suptitle("頑健性（Fine–Gray のハザード比、95%区間）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f79_robust.png"); plt.close()
print("ok")
