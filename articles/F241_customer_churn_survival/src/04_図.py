"""図（Noto Sans CJK JP）とダッシュボードの HTML。"""
import pandas as pd, numpy as np, json, pathlib, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
B = pathlib.Path(__file__).resolve().parents[1]; R = B / "results"; F = B / "figures"; F.mkdir(exist_ok=True)
fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(fp); plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
o = json.load(open(R / "summary.json"))
C1, C2, C3, G = "#2b6cb0", "#dd6b20", "#2f855a", "#888"
# 図1 見かけの解約率とKM、月ごとのハザード
km = pd.read_csv(R / "A_km_overall.csv"); lt = pd.read_csv(R / "A_life_table.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
ax[0].step(km.month, km.S, where="post", color=C1, lw=2, label="Kaplan–Meier（打ち切りを考える）")
ax[0].axhline(1 - o["naive_churn_share"], color=C2, ls="--", label=f"「解約した人の割合」{o['naive_churn_share']:.1%} から見た残り")
for m in [12, 72]: ax[0].plot(m, o["km_S"][str(m)], "o", color=C1); ax[0].annotate(f"{m}か月 {o['km_S'][str(m)]:.0%}", (m, o["km_S"][str(m)]), (m - 14 if m == 72 else m + 2, o["km_S"][str(m)] - 0.08))
ax[0].set(xlabel="契約してからの月数", ylabel="まだ契約している割合", ylim=(0.4, 1.01), title="残っている人の割合（7,043人）"); ax[0].legend(fontsize=9, loc="lower left")
ax[1].bar(lt.month, lt.hazard * 100, color=C1, width=0.8)
ax[1].set(xlabel="契約してからの月数", ylabel="その月に解約する割合（%）", title="月ごとの解約の起こりやすさ"); ax[1].annotate(f"1か月目 {o['hazard_m1']:.1%}", (1, o['hazard_m1'] * 100), (8, o['hazard_m1'] * 100 - 0.3))
fig.tight_layout(); fig.savefig(F / "fig1_km_vs_naive.png", dpi=150); plt.close()
# 図2 契約の種類ごと
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for c, col, lab in [("Month_to_month", C2, "月ごと契約"), ("One_year", C1, "1年契約"), ("Two_year", C3, "2年契約")]:
    d = pd.read_csv(R / f"B_km_{c}.csv"); key = {"Month_to_month": "Month-to-month", "One_year": "One year", "Two_year": "Two year"}[c]
    ax.step(d.month, d.S, where="post", color=col, lw=2, label=f"{lab}（{o['contract'][key]['n']:,}人）72か月で{o['contract'][key]['S72']:.0%}")
ax.set(xlabel="契約してからの月数", ylabel="まだ契約している割合", ylim=(0, 1.02), title="契約の種類で、残り方はまったく違う"); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(F / "fig2_km_contract.png", dpi=150); plt.close()
# 図3 Cox
cx = pd.read_csv(R / "C_cox.csv", index_col=0).sort_values("exp(coef)")
fig, ax = plt.subplots(figsize=(7.5, 4.8)); y = np.arange(len(cx))
ax.errorbar(cx["exp(coef)"], y, xerr=[cx["exp(coef)"] - cx["exp(coef) lower 95%"], cx["exp(coef) upper 95%"] - cx["exp(coef)"]], fmt="o", color=C1, capsize=3)
ax.axvline(1, color=G, ls=":"); ax.set_xscale("log"); ax.set_yticks(y); ax.set_yticklabels(cx.index)
for i, v in enumerate(cx["exp(coef)"]): ax.text(v * 1.15, i + 0.15, f"{v:.2f}", fontsize=9)
ax.set(xlabel="ハザード比（1より大きいほど解約しやすい、対数目盛）", title="Cox モデル：ほかの条件をそろえたときの解約しやすさ")
fig.tight_layout(); fig.savefig(F / "fig3_cox.png", dpi=150); plt.close()
# 図4 コホート表（法人）
coh = pd.read_csv(R / "D_cohort_retention.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for j, k in enumerate(["株式会社", "合同会社"]):
    p = coh[coh.kind == k].pivot(index="cohort", columns="year", values="retention")
    im = ax[j].imshow(p.values, cmap="Blues", vmin=0.85, vmax=1.0, aspect="auto")
    for r_ in range(p.shape[0]):
        for c_ in range(p.shape[1]):
            v = p.values[r_, c_]
            if not np.isnan(v): ax[j].text(c_, r_, f"{v*100:.1f}", ha="center", va="center", fontsize=7.5, color="white" if v < 0.93 else "black")
    ax[j].set_xticks(range(p.shape[1])); ax[j].set_xticklabels([f"{c}年" for c in p.columns], fontsize=8); ax[j].set_yticks(range(p.shape[0])); ax[j].set_yticklabels(p.index)
    ax[j].set(title=f"{k}：設立年ごとの「まだ続いている割合」（%）", xlabel="設立からの年数", ylabel="設立年")
fig.tight_layout(); fig.savefig(F / "fig4_cohort_table.png", dpi=150); plt.close()
# 図5 LTV の外挿
ex = pd.read_csv(R / "E_extrapolation.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
ax[0].step(km.month, km.S, where="post", color="black", lw=2.5, label="実際（KM、72か月まで）")
for c, col, lab in [("sBG", C3, "sBG（人ごとに違う）"), ("LogNormal", C1, "対数正規"), ("Weibull", "#805ad5", "Weibull"), ("KM_then_const", C2, "最後の1年の解約率で一定"), ("Exponential", G, "指数（ずっと一定）")]:
    ax[0].plot(ex.month, ex[c], color=col, lw=1.5, label=lab)
ax[0].axvline(72, color=G, ls=":"); ax[0].set(xlim=(0, 360), ylim=(0, 1), xlabel="契約してからの月数", ylabel="まだ契約している割合", title="72か月より先は、仮定しだい"); ax[0].legend(fontsize=8.5)
L = o["ltv_30y"]; names = list(L.keys()); vals = [L[n] for n in names]
ax[1].barh(["72か月まで（実測）"] + names, [o["ltv_72_km"]] + vals, color=["black", C2, "#805ad5", G, C1, C3])
for i, v in enumerate([o["ltv_72_km"]] + vals): ax[1].text(v + 80, i, f"{v:,.0f}ドル", va="center", fontsize=9)
ax[1].set(xlabel="1人あたりの売上の見込み（30年、年5%で割り引き、ドル）", title="LTV は外挿の仕方で1.5倍変わる", xlim=(0, 9500))
fig.tight_layout(); fig.savefig(F / "fig5_ltv_extrapolation.png", dpi=150); plt.close()
# ダッシュボード HTML（架空の「さくら回線」の社内向け）
def path(df, w=420, h=200, xmax=72):
    pts = " ".join(f"{20 + m / xmax * w:.1f},{10 + (1 - s) * h:.1f}" for m, s in zip(df.month, df.S))
    return pts
curves = ""
for c, col, lab in [("Month_to_month", C2, "月ごと"), ("One_year", C1, "1年"), ("Two_year", C3, "2年")]:
    d = pd.read_csv(R / f"B_km_{c}.csv"); curves += f'<polyline fill="none" stroke="{col}" stroke-width="2.5" points="{path(d)}"/><text x="448" y="{10 + (1 - d.S.iloc[-1]) * 200:.0f}" fill="{col}" font-size="12">{lab}</text>'
p = coh[coh.kind == "株式会社"].pivot(index="cohort", columns="year", values="retention")
rows = "".join("<tr><th>" + str(i) + "</th>" + "".join(f'<td style="background:rgba(43,108,176,{max(0, (v - 0.88) / 0.12):.2f})">{v*100:.1f}</td>' if not np.isnan(v) else "<td></td>" for v in r) + "</tr>" for i, r in zip(p.index, p.values))
html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>解約と定着のダッシュボード（架空）</title>
<style>body{{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;background:#f7f8fa;color:#222}}.k{{display:inline-block;background:#fff;border-radius:8px;padding:12px 18px;margin:0 12px 12px 0;box-shadow:0 1px 3px #0002}}.k b{{display:block;font-size:26px}}.card{{background:#fff;border-radius:8px;padding:12px;margin-top:8px;box-shadow:0 1px 3px #0002;display:inline-block;vertical-align:top;margin-right:12px}}table{{border-collapse:collapse;font-size:12px}}td,th{{padding:3px 6px;text-align:center}}small{{color:#666}}</style></head><body>
<h2>解約と定着のダッシュボード（架空の通信サービス「さくら回線」・社内向けの例）</h2><small>データ：IBM の公開サンプル（架空の顧客 7,043人）。法人の表は F28 の公開データ。金額はドル、年5%で割り引き。</small><div style="margin-top:12px">
<div class="k">12か月後に残る割合<b>{o['km_S']['12']:.1%}</b></div><div class="k">1か月目の解約率<b>{o['hazard_m1']:.1%}</b></div><div class="k">2〜3年目の月の解約率<b>{o['hazard_m24_36']:.2%}</b></div><div class="k">LTV（72か月まで）<b>{o['ltv_72_km']:,.0f}ドル</b></div><div class="k">月ごと契約の LTV<b>{o['ltv72_contract']['Month-to-month']:,.0f}ドル</b></div></div>
<div class="card"><b>契約の種類ごとの残り方</b><br><svg width="480" height="240"><line x1="20" y1="210" x2="440" y2="210" stroke="#aaa"/><line x1="20" y1="10" x2="20" y2="210" stroke="#aaa"/>{curves}<text x="20" y="232" font-size="11">0</text><text x="420" y="232" font-size="11">72か月</text></svg></div>
<div class="card"><b>コホート表：設立年ごとの「続いている割合」（株式会社、%）</b><table><tr><th>設立年</th>{''.join(f'<th>{c}年</th>' for c in p.columns)}</tr>{rows}</table></div>
<p><small>読み方：1か月目の解約が多いので、最初の1か月の体験の改善を先に。月ごと契約の比率が上がると LTV は下がる。72か月より先の LTV は外挿の仕方で1.5倍変わるので、幅で見る。</small></p></body></html>"""
(B / "dashboard.html").write_text(html)
print("ok")
