"""W2：コロナ後、宿泊者数が戻るのが早かった県・遅かった県（2019年同月比、日本人・外国人別、月次）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_monthly, note, PREFS, METRO, FIG, RES, BLUE, ORANGE, GRAY, INK

m = load_monthly()
base = m[m.year == 2019].set_index(["pref", "month"])[["japanese", "foreign", "total"]]
post = m[m.year >= 2020].copy()
for c in ("japanese", "foreign", "total"):
    post[f"{c}_idx"] = post[c].values / base.loc[list(zip(post.pref, post.month)), c].values * 100

# 1. 全国の月次（2019年同月＝100）
nat = m.groupby(["year", "month"])[["japanese", "foreign", "total"]].sum().reset_index()
nb = nat[nat.year == 2019].set_index("month")
for c in ("japanese", "foreign", "total"):
    nat[f"{c}_idx"] = nat[c] / nat.month.map(nb[c]) * 100
nat = nat[nat.year >= 2019]
nat.to_csv(RES / "w2_national_monthly.csv", index=False, float_format="%.1f")


# 2. 都道府県：年ごとの回復率と、12か月移動合計が2019年の同じ12か月を初めて上回った月
def first_back(d, col):
    """2022年1月以降、直近12か月の合計が2019年の同じ12か月の合計以上になった最初の月"""
    d = d.sort_values(["year", "month"])
    r = d[col].rolling(12).sum() / d[f"b_{col}"].rolling(12).sum()
    ok = d.loc[(r >= 1) & (d.year >= 2022)]
    return f"{ok.year.iloc[0]}-{ok.month.iloc[0]:02d}" if len(ok) else "未回復"


mm = m[m.year >= 2019].copy()
for c in ("japanese", "foreign"):
    mm[f"b_{c}"] = base.loc[list(zip(mm.pref, mm.month)), c].values
rows = []
for p, d in mm.groupby("pref"):
    a = d.groupby("year")[["japanese", "foreign", "total"]].sum()
    r = {"pref": p, "metro8": p in METRO}
    for c in ("japanese", "foreign", "total"):
        for y in (2021, 2022, 2023, 2024, 2025):
            r[f"{c}_{y}"] = a.loc[y, c] / a.loc[2019, c] * 100
    r["japanese_back"] = first_back(d, "japanese"); r["foreign_back"] = first_back(d, "foreign")
    r["foreign_share_2019"] = a.loc[2019, "foreign"] / a.loc[2019, "total"] * 100
    rows.append(r)
pr = pd.DataFrame(rows).set_index("pref").loc[PREFS]
pr.to_csv(RES / "w2_pref_recovery.csv", float_format="%.1f")
post[["year", "month", "pref", "japanese_idx", "foreign_idx", "total_idx"]].to_csv(RES / "w2_pref_monthly_index.csv", index=False, float_format="%.1f")

# 相関など
c1 = np.corrcoef(pr.japanese_2025, pr.foreign_2025)[0, 1]
c2 = np.corrcoef(pr.foreign_share_2019, pr.total_2025)[0, 1]
c3 = np.corrcoef(np.log(pr.foreign_2025), pr.foreign_share_2019)[0, 1]
pd.DataFrame({"stat": ["corr_jp2025_fo2025", "corr_foshare2019_total2025", "corr_logfo2025_foshare2019",
                       "jp2025_metro_median", "jp2025_other_median", "fo2025_metro_median", "fo2025_other_median",
                       "n_pref_jp2025_ge100", "n_pref_fo2025_ge100", "n_pref_total2025_ge100"],
              "value": [c1, c2, c3, pr[pr.metro8].japanese_2025.median(), pr[~pr.metro8].japanese_2025.median(),
                        pr[pr.metro8].foreign_2025.median(), pr[~pr.metro8].foreign_2025.median(),
                        (pr.japanese_2025 >= 100).sum(), (pr.foreign_2025 >= 100).sum(), (pr.total_2025 >= 100).sum()]}
             ).to_csv(RES / "w2_summary.csv", index=False, float_format="%.3f")

# --- 図1：全国の月次 ---
t = nat[nat.year >= 2020].reset_index(drop=True)
x = np.arange(len(t))
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.plot(x, t.japanese_idx, color=ORANGE, label="日本人")
ax.plot(x, t.foreign_idx, color=BLUE, label="外国人")
ax.axhline(100, color=GRAY, lw=1, ls=":")
ticks = [i for i in range(len(t)) if t.month[i] == 1]
ax.set_xticks(ticks, [f"{t.year[i]}年" for i in ticks])
ax.set_ylabel("2019年の同じ月＝100"); ax.set_ylim(0, 190)
ax.set_title("延べ宿泊者数の回復（全国、2020年1月〜2025年12月）")
ax.legend(frameon=False, loc="upper left")
note(ax)
fig.savefig(FIG / "w2_national.png"); plt.close(fig)

# --- 図2：都道府県別 日本人の回復率（2025年） ---
s = pr.japanese_2025.sort_values()
fig, ax = plt.subplots(figsize=(7.5, 9.5))
cols = [BLUE if p in METRO else GRAY for p in s.index]
ax.barh(range(len(s)), s.values, color=cols)
ax.axvline(100, color=INK, lw=0.8)
ax.set_yticks(range(len(s)), s.index, fontsize=8.5)
ax.set_xlim(70, s.max() + 5); ax.set_ylim(-0.7, len(s) - 0.3)
for i, v in enumerate(s.values):
    ax.text(v + 0.5, i, f"{v:.0f}", va="center", fontsize=7.5)
ax.set_xlabel("2025年の日本人延べ宿泊者数（2019年＝100）")
ax.set_title("日本人の宿泊の回復（2025年、青＝三大都市圏8都府県）", fontsize=12)
note(ax, y=-0.07)
fig.savefig(FIG / "w2_pref_japanese.png"); plt.close(fig)

# --- 図3：日本人と外国人の回復（2025年） ---
fig, ax = plt.subplots(figsize=(8, 6))
cc = [BLUE if p in METRO else GRAY for p in pr.index]
ax.scatter(pr.japanese_2025, pr.foreign_2025, c=cc, s=25)
ax.axvline(100, color=GRAY, lw=0.8, ls=":"); ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_yscale("log"); ax.set_yticks([50, 70, 100, 150, 200, 300], ["50", "70", "100", "150", "200", "300"]); ax.yaxis.set_minor_formatter(plt.NullFormatter())
lab = set(pr.foreign_2025.nlargest(5).index) | set(pr.foreign_2025.nsmallest(5).index) | set(pr.japanese_2025.nlargest(3).index) \
    | set(pr.japanese_2025.nsmallest(3).index) | {"東京都", "大阪府", "京都府", "北海道", "沖縄県"}
for p in lab:
    ax.annotate(p, (pr.japanese_2025[p], pr.foreign_2025[p]), fontsize=8, xytext=(3, 2), textcoords="offset points")
ax.set_xlabel("日本人（2019年＝100）"); ax.set_ylabel("外国人（2019年＝100、対数目盛）")
ax.set_title("2025年の延べ宿泊者数：日本人と外国人の回復（青＝三大都市圏8都府県）", fontsize=12)
note(ax, y=-0.11)
fig.savefig(FIG / "w2_scatter.png"); plt.close(fig)

# 要約
print(nat[["year", "month", "japanese_idx", "foreign_idx", "total_idx"]].round(1).to_string(index=False))
print(nat.groupby("year")[["japanese", "foreign", "total"]].sum().pipe(lambda d: d / d.loc[2019] * 100).round(1))
print(pr[["japanese_2022", "japanese_2023", "japanese_2025", "foreign_2023", "foreign_2025", "total_2025", "japanese_back", "foreign_back", "foreign_share_2019"]]
      .sort_values("japanese_2025").round(1).to_string())
print(pd.read_csv(RES / "w2_summary.csv").to_string(index=False))
print(pr.japanese_back.value_counts().sort_index().to_string())
print(pr.foreign_back.value_counts().sort_index().to_string())
