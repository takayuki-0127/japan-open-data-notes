"""S9：人口が2倍の街には、飲食店や医師は2倍あるのか。市区町村の「スケーリング則」（両対数の回帰の傾き）"""
from common import *
import statsmodels.api as sm
h = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, nrows=3)
d = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, skiprows=3); d.columns = list(h.iloc[0])
lab = dict(zip(h.iloc[0], h.iloc[2]))
d = d.rename(columns={"SSDSE-A-2026": "code", "Prefecture": "pref", "Municipality": "muni"})
code = {v: k for k, v in lab.items()}
ITEMS = {"従業者数（民営）（情報通信業）": "情報通信業で働く人", "従業者数（民営）（学術研究、専門・技術サービス業）": "専門・技術サービスで働く人",
         "従業者数（民営）（金融業、保険業）": "金融・保険業で働く人", "医師数": "医師", "飲食店数": "飲食店", "従業者数（民営）": "民営事業所で働く人（全体）",
         "大型小売店数": "大型小売店", "一般診療所数": "診療所", "薬剤師数": "薬剤師", "小売店数": "小売店", "一般病院数": "病院", "歯科診療所数": "歯科診療所",
         "一般行政部門職員数（市区町村）": "役所の職員（一般行政）", "図書館数": "図書館", "小学校数": "小学校", "公民館数": "公民館"}
d["pop"] = pd.to_numeric(d[code["総人口"]])
rows = []
for k, nm in ITEMS.items():
    y = pd.to_numeric(d[code[k]], errors="coerce"); m = (y > 0) & d["pop"].gt(0)
    X = sm.add_constant(np.log(d.loc[m, "pop"])); r = sm.OLS(np.log(y[m]), X).fit(cov_type="HC3")
    b = r.params.iloc[1]; lo, hi = r.conf_int().iloc[1]
    rows.append({"item": nm, "beta": b, "lo": lo, "hi": hi, "r2": r.rsquared, "n": int(m.sum()), "n_zero": int((y == 0).sum()), "x2": 2 ** b})
t = pd.DataFrame(rows).sort_values("beta", ascending=False); t.round(3).to_csv(RES / "s9_scaling.csv", index=False, encoding="utf-8-sig"); print(t.round(3).to_string())

# 例：飲食店（両対数の散布図）と、「人口の割に多い・少ない」街
y = pd.to_numeric(d[code["飲食店数"]]); m = y > 0
X = sm.add_constant(np.log(d.loc[m, "pop"])); r = sm.OLS(np.log(y[m]), X).fit()
d.loc[m, "rest_resid"] = r.resid; d["rest_ratio"] = np.exp(d.rest_resid)
big = d[d["pop"] >= 50000].sort_values("rest_resid")
print(big[["pref", "muni", "pop", code["飲食店数"], "rest_ratio"]].head(5)); print(big[["pref", "muni", "pop", code["飲食店数"], "rest_ratio"]].tail(8))
big[["pref", "muni", "pop", code["飲食店数"], "rest_ratio"]].rename(columns={code["飲食店数"]: "restaurants"}).round(3).to_csv(RES / "s9_restaurant_resid_pop50k.csv", index=False, encoding="utf-8-sig")
s = {"n_muni": len(d), "beta_rest": t.set_index("item").loc["飲食店", "beta"], "beta_ict": t.set_index("item").loc["情報通信業で働く人", "beta"],
     "beta_doctor": t.set_index("item").loc["医師", "beta"], "beta_staff": t.set_index("item").loc["役所の職員（一般行政）", "beta"],
     "beta_school": t.set_index("item").loc["小学校", "beta"], "beta_workers": t.set_index("item").loc["民営事業所で働く人（全体）", "beta"],
     "doctor_zero": t.set_index("item").loc["医師", "n_zero"]}
pd.Series(s).to_csv(RES / "s9_summary.csv", header=["value"]); print(pd.Series(s))

SRC = source("SSDSE-市区町村（SSDSE-A-2026）")
fig, ax = plt.subplots(figsize=(8.5, 5.6)); yy = np.arange(len(t))
col = [ORANGE if b_ > 1 else (BLUE if h_ < 1 else GRAY) for b_, h_ in zip(t.beta, t.hi)]
ax.errorbar(t.beta, yy, xerr=[t.beta - t.lo, t.hi - t.beta], fmt="none", ecolor="#c9c7c0", capsize=2)
ax.scatter(t.beta, yy, color=col, zorder=3); ax.axvline(1, color=INK, lw=0.8)
for i, (b_, x_) in enumerate(zip(t.beta, t.x2)): ax.text(max(t.hi.max(), 1.6) + 0.02, i, f"{x_:.2f}倍", va="center", fontsize=8.5, color="#52514e")
ax.set_yticks(yy, t.item); ax.invert_yaxis(); ax.set_xlabel("傾き β（人口が1%多いと何%多いか）")
ax.text(1.01, len(t) - 0.4, "← 人口の割に少なくてすむ ｜ 人口以上に増える →", fontsize=8.5, ha="center", color="#52514e")
ax.set_title("人口が2倍の街では、情報通信業で働く人は2倍以上、公民館は1.3倍", loc="left")
fig.text(0.01, -0.05, SRC + "\n（両対数の回帰、0の市区町村は除く。線は95%区間、右の数字は人口2倍のときの倍率＝2^β）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s9_beta.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.scatter(d.loc[m, "pop"], y[m], s=6, color=LIGHT, edgecolor=BLUE, lw=0.3, alpha=0.8)
xx = np.logspace(np.log10(d["pop"].min()), np.log10(d["pop"].max()), 50)
ax.plot(xx, np.exp(r.params.iloc[0]) * xx ** r.params.iloc[1], color=ORANGE, label=f"傾き {r.params.iloc[1]:.2f}")
ax.plot(xx, y[m].sum() / d.loc[m, "pop"].sum() * xx, color=GRAY, ls="--", label="傾き 1（人口に比例）")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("人口（対数目盛）"); ax.set_ylabel("飲食店の数（対数目盛）"); ax.legend(frameon=False, loc="upper left")
for _, rr in d[d.muni.isin(["札幌市", "渋谷区", "千代田区", "中央区", "大阪市", "那覇市", "熱海市", "軽井沢町"]) & (d.pref.isin(["北海道", "東京都", "大阪府", "沖縄県", "静岡県", "長野県"]))].iterrows():
    ax.annotate(rr.muni, (rr["pop"], rr[code["飲食店数"]]), xytext=(4, -3), textcoords="offset points", fontsize=8)
ax.set_title("飲食店は、人口にほぼ比例して増える（傾き1に近い）", loc="left")
fig.text(0.01, -0.04, SRC, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s9_restaurant.png"); plt.close(fig)
