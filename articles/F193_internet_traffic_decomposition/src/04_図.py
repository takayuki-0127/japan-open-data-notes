import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3, CG = "#2b6cb0", "#dd6b20", "#2f855a", "#888888"
S = json.load(open(RES / "summary.json")); semi = pd.read_csv(RES / "semiannual_spliced.csv"); semi["t"] = pd.to_datetime(semi.date)
# 1 長期
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(semi.t, semi.down / 1000, "o-", c=C1, ms=4, label="ダウンロード（つないだ全国推計）")
ax.plot(semi.t, semi.up / 1000, "o-", c=C2, ms=4, label="アップロード（つないだ全国推計）")
ax.plot(semi.t, semi.isp5_down / 1000, ":", c=C1, alpha=.6, label="協力ISP5社による推計（つなぐ前）")
ax.plot(semi.t, semi.isp5_up / 1000, ":", c=C2, alpha=.6)
ax.set_yscale("log"); ax.axvline(pd.Timestamp("2020-03-01"), c=CG, ls="--", lw=1); ax.text(pd.Timestamp("2020-04-01"), 0.2, "2020年春", color=CG)
ax.set_ylabel("Tbps（対数目盛）"); ax.set_title("固定ブロードバンド契約者の通信量（全国推計、5月・11月）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.text(0.99, 0.02, "2004年9月〜2018年11月は協力ISP5社の推計を、重なる4時点の比（下り0.82・上り0.78）で9社の水準にそろえた", transform=ax.transAxes, ha="right", fontsize=8, color=CG)
fig.tight_layout(); fig.savefig(FIG / "f193_longrun.png", dpi=150); plt.close()
# 2 トレンドの延長との比
fig, ax = plt.subplots(figsize=(9, 5))
for key, lab, c, ls in [("cf_down_2017", "ダウンロード（2017〜19年の伸びをのばした線と比べる）", C1, "-"), ("cf_down", "ダウンロード（2015〜19年の伸びをのばした線と比べる）", C1, ":"),
                        ("cf_up_2017", "アップロード（2017〜19年の伸び）", C2, "-")]:
    d = S[key]; x = pd.to_datetime(list(d.keys())); ax.plot(x, list(d.values()), "o" + ls, c=c, ms=4, label=lab)
ax.axhline(1, c="k", lw=.8); ax.axvline(pd.Timestamp("2020-03-01"), c=CG, ls="--", lw=1)
ax.set_ylabel("実際 ÷ コロナ前の伸びをのばした値"); ax.set_title("コロナ前の伸び方をのばした線と比べると"); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f193_counterfactual.png", dpi=150); plt.close()
# 3 IX 月次 STL
st = pd.read_csv(RES / "ix_stl.csv"); st["t"] = pd.to_datetime(st.date)
fig, axs = plt.subplots(3, 1, figsize=(9, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1, 1]})
axs[0].plot(st.t, np.exp(st.log) / 1000, c=C3, lw=1.2, label="実際"); axs[0].plot(st.t, np.exp(st.trend) / 1000, c="k", lw=1, ls="--", label="トレンド")
axs[0].set_yscale("log"); axs[0].set_ylabel("Tbps"); axs[0].legend(frameon=False, fontsize=9); axs[0].set_title("国内主要IXの1日平均トラヒック（月次）をトレンド・季節・残りに分ける")
axs[1].plot(st.t, (np.exp(st.seasonal) - 1) * 100, c=C1, lw=1); axs[1].set_ylabel("季節（%）")
axs[2].bar(st.t, (np.exp(st.resid) - 1) * 100, width=25, color=np.where(st.date.str[:4] == "2020", C2, CG)); axs[2].set_ylabel("残り（%）")
for a in axs: a.axvline(pd.Timestamp("2020-03-01"), c=CG, ls=":", lw=1)
fig.tight_layout(); fig.savefig(FIG / "f193_ix_stl.png", dpi=150); plt.close()
# 4 時間帯の形
di = pd.read_csv(DATA / "diurnal.csv"); di["wk"] = np.where(di.day.str[0].isin(["土", "日"]), "週末", "平日"); di["hour"] = di.start.str[:2].astype(int)
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
for a, wk in zip(axs, ["平日", "週末"]):
    for p, c in [("2020-11", CG), ("2023-05", C3), ("2026-05", C1)]:
        x = di[(di.period == p) & (di.wk == wk)].groupby("hour").down.mean() / 1000
        a.plot(x.index, x.values, "o-", c=c, ms=4, label=p.replace("-", "年") + "月")
    a.set_xticks(range(1, 24, 2)); a.set_xticklabels([f"{h}時" for h in range(1, 24, 2)], fontsize=8); a.set_title(f"{wk}（2時間ごとの平均）")
axs[0].set_ylabel("ダウンロード Tbps（協力ISP9社の契約者）"); axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("1日の中の通信量の形（開始時刻で表示）"); fig.tight_layout(); fig.savefig(FIG / "f193_diurnal.png", dpi=150); plt.close()
# 5 時間帯ごとの伸び
hr = pd.read_csv(RES / "hour_rates.csv"); hr["wk"] = hr.key.str[:2]; hr["h"] = hr.key.str[2:].astype(int)
fig, ax = plt.subplots(figsize=(9, 4.6))
for wk, c, dx in [("平日", C1, -0.3), ("週末", C2, 0.3)]:
    x = hr[hr.wk == wk]; ax.errorbar(x.h + dx, x.rate * 100, yerr=[(x.rate - x.lo) * 100, (x.hi - x.rate) * 100], fmt="o", c=c, capsize=3, label=wk)
ax.axhline(np.mean(hr.rate) * 100, c=CG, ls="--", lw=1)
ax.set_xticks(range(1, 24, 2)); ax.set_xticklabels([f"{h}時" for h in range(1, 24, 2)]); ax.set_ylabel("年あたりの伸び（%、95%区間）")
ax.set_title("時間帯ごとのダウンロードの伸び（2020年11月〜2026年5月の12時点）"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "f193_hour_growth.png", dpi=150); plt.close()
# 6 頑健性（段差の大きさ）
rb = pd.read_csv(RES / "robustness_step.csv")
def jl(r):
    p = r.spec.split("|"); f = lambda d: f"{int(d[:4])}年{int(d[5:])}月〜"
    if r.kind == "semi":
        return f"半年ごと｜{'下り' if p[0]=='down' else '上り'}｜{f(p[1])}｜{'段差＋傾き' if p[2]=='step+slope' else '段差のみ'}｜{'2020年の2点除く' if p[3]=='drop2020' else '全点'}"
    return f"IX月次｜{f(p[0])}｜{'段差＋傾き' if p[1]=='step+slope' else '段差のみ'}｜段差を{int(p[2][5:])}月から"
rb["lab"] = rb.apply(jl, axis=1)
rb = rb.sort_values(["kind", "spec"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 9))
y = np.arange(len(rb))[::-1]
cols = [C1 if s.startswith("down") else (C2 if s.startswith("up") else C3) for s in rb.spec]
for yi, r, c in zip(y, rb.itertuples(), cols): ax.plot([r.lo * 100, r.hi * 100], [yi, yi], c=c, lw=1.2)
ax.scatter(rb.step * 100, y, c=cols, s=18, zorder=3)
ax.set_yticks(y); ax.set_yticklabels(rb.lab, fontsize=7); ax.axvline(0, c="k", lw=.8)
ax.set_xlabel("2020年春の段差（%、95%区間）"); ax.set_title("段差の大きさは、期間・指標・段差の置き方でどれだけ動くか\n（青＝下り、橙＝上り、緑＝IX。段差＋傾き＝2020年以降の伸びの変化も入れたモデル）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f193_robustness.png", dpi=150); plt.close()
print("ok")
