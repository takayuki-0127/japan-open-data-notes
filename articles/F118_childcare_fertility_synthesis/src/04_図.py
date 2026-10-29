"""04 図"""
from common import *

R = jload(RES / "results.json")
E = pd.read_csv(RES / "estimates_common_unit.csv")
COL = {"プラス": BLUE, "マイナス": ORANGE, "0をまたぐ": GRAY}
ORDER = ["県どうしの差（水準）", "県の中の年ごとの動き", "県の変化どうし", "町どうしの差（水準）", "町の変化どうし"]

# ---------- 図1：すべての推定を同じ単位で ----------
F = E[~E.method.str.contains("就業を通る|通らない")].copy()
F["design"] = pd.Categorical(F.design, ORDER, ordered=True)
F = F.sort_values(["design", "study", "coef"])
fig, ax = plt.subplots(figsize=(9.5, 8.6))
y = 0; ticks = []; labs = []; gy = []
for dz, g in F.groupby("design", observed=True):
    gy.append((y, dz))
    y -= 1
    for _, r in g.iterrows():
        ax.hlines(y, r.lo, r.hi, color=COL[r.sig], lw=2.2); ax.scatter(r.coef, y, color=COL[r.sig], zorder=3, s=22)
        ticks.append(y); labs.append(f"{r.study}｜{r.method.replace('（県ダミーあり）', '')}")
        y -= 1
    y -= 0.6
for yy, dz in gy:
    ax.text(-0.125, yy, dz, fontsize=10.5, fontweight="bold", color=INK, va="center")
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(ticks, labs, fontsize=8.5); ax.set_xlim(-0.125, 0.115)
ax.set_xlabel(UNIT + "（95%区間）")
ax.set_title(f"同じ問いへの{len(F)}の答え：県どうしはプラス、県の中と町の比較ではマイナスか0", loc="left", fontsize=12)
ax.text(0.99, 0.01, "青：プラス　橙：マイナス　灰：0をまたぐ\n市区町村（F100）は県ダミーあり・全体の推定", transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color="#52514e")
fig.text(0.01, -0.02, SRC, fontsize=7, color="#8a8984")
fig.savefig(FIG / "f118_1_all_estimates.png"); plt.close(fig)

# ---------- 図2：何をそろえると向きが変わるか ----------
pm = R["pref_main"]
stepsP = [("県どうし\n（2022年）", pm["県どうし（2022年の断面）"]), ("県×年を\nプール", pm["そのまま（県×年をプール）"]), ("＋県の\n固定効果", pm["＋県の固定効果"]),
          ("＋年の\n固定効果", pm["＋県と年の固定効果（二方向）"]), ("長い差\n2012→22", pm["長い差 2012→2022"])]
f100 = jload(PRIOR / "F100_results.json")["steps"]
SHORT = {"条件なし": "条件\nなし", "人口・密度": "＋人口\n密度", "＋年齢・世帯": "＋年齢\n世帯", "＋産業・通勤・所得": "＋産業\n通勤\n所得", "＋財政・学歴・雇用": "＋財政\n学歴\n雇用",
         "＋前の出生率・在所児": "＋前の\n出生率\n在所児", "＋県": "＋県", "＋隣との似かた（空間誤差）": "＋隣と\nの似方"}
fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), gridspec_kw={"width_ratios": [5, 7, 8]})
for ax, (ttl, st) in zip(axes, [("都道府県（022 を再推定、47県×11年）", stepsP),
                                ("市区町村・水準の比較（F100）", [(SHORT.get(s["step"], s["step"]), s) for s in f100["level"]]),
                                ("市区町村・変化の比較（F100）", [(SHORT.get(s["step"], s["step"]), s) for s in f100["change"]])]):
    for i, (lab, s) in enumerate(st):
        sig = "プラス" if s["lo"] > 0 else ("マイナス" if s["hi"] < 0 else "0をまたぐ")
        ax.vlines(i, s["lo"], s["hi"], color=COL[sig], lw=2.4); ax.scatter(i, s["coef"], color=COL[sig], zorder=3)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(len(st)), [l for l, _ in st], fontsize=8)
    ax.set_title(ttl, fontsize=10.5, loc="left"); ax.set_ylim(-0.09, 0.115)
axes[0].set_ylabel("在所児＋10人あたりの出生率の差")
fig.suptitle("何をそろえるかで向きが変わる：県どうしはプラス、県の違いを除くとマイナス、町の変化どうしは0の近く", x=0.01, ha="left", fontsize=12.5, fontweight="bold")
fig.text(0.01, -0.06, SRC, fontsize=7, color="#8a8984"); fig.tight_layout()
fig.savefig(FIG / "f118_2_what_is_held_fixed.png"); plt.close(fig)

# ---------- 図3：実際に増えた分に当てはめると ----------
I = pd.read_csv(RES / "estimates_implied_2012_22.csv")
I = I[~I.method.str.contains("就業を通る|通らない")]
sc = R["scale"]
fig, ax = plt.subplots(figsize=(9, 4.6))
for i, dz in enumerate(ORDER):
    g = I[I.design == dz]
    ax.add_patch(plt.Rectangle((i - 0.3, g.implied_lo.min()), 0.6, g.implied_hi.max() - g.implied_lo.min(), color="#e8e6e1", zorder=0))
    ax.scatter(np.full(len(g), i) + np.linspace(-0.18, 0.18, len(g)), g.implied, color=[COL[s] for s in g.sig], zorder=3, s=26)
ax.axhline(sc["tfr_change"], color=PURPLE, lw=1.5, ls="--"); ax.text(4.45, sc["tfr_change"] - 0.006, f"実際の出生率の変化（47県の平均）{sc['tfr_change']:+.2f}", color=PURPLE, ha="right", va="top", fontsize=9)
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(range(len(ORDER)), [o.replace("（水準）", "\n（水準）") for o in ORDER], fontsize=9)
ax.set_ylabel("出生率の差（2012→22年の増加分を当てはめた値）")
ax.set_title(f"在所児が実際に増えた分（0〜5歳100人あたり +{sc['D_change']:.1f}人）を当てはめると", loc="left")
ax.text(0.01, 0.98, "灰色の帯：その比べ方の推定の95%区間の端から端まで", transform=ax.transAxes, fontsize=8.5, color="#52514e", va="top")
fig.text(0.01, -0.04, SRC, fontsize=7, color="#8a8984")
fig.savefig(FIG / "f118_3_implied_size.png"); plt.close(fig)

# ---------- 図4：都道府県の二方向固定効果の頑健性 ----------
rb = R["pref_robust"]
labs = list(rb.keys())
fig, ax = plt.subplots(figsize=(9, 4.8))
for i, k in enumerate(labs[::-1]):
    s = rb[k]; sig = "プラス" if s["lo"] > 0 else ("マイナス" if s["hi"] < 0 else "0をまたぐ")
    ax.hlines(i, s["lo"], s["hi"], color=COL[sig], lw=2.4); ax.scatter(s["coef"], i, color=COL[sig], zorder=3)
    ax.text(0.042, i, f"{s['coef']:+.3f}", fontsize=8.5, va="center")
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(range(len(labs)), labs[::-1], fontsize=8.5); ax.set_xlim(-0.06, 0.05)
ax.set_xlabel(UNIT)
ax.set_title("都道府県の二方向固定効果は、処置を定員にする・コロナ前だけにすると0をまたぐ", loc="left", fontsize=11.5)
fig.text(0.01, -0.03, "県を1つずつ抜く：線は47回の推定値の最小〜最大。出典：統計センター SSDSE-B-2026（022 と同じデータ）、0〜5歳の割合は社会・人口統計体系（国勢調査）から補間して作成", fontsize=7, color="#8a8984")
fig.savefig(FIG / "f118_4_pref_robustness.png"); plt.close(fig)

# ---------- 図5：女性の就業（問い2）の答え ----------
Q = pd.read_csv(RES / "estimates_q2_labor.csv")
Q["design"] = pd.Categorical(Q.design, ["町どうしの差（水準）", "町の変化どうし"], ordered=True)
Q = Q.sort_values(["design", "study", "coef"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 5.4))
for i, r in Q.iloc[::-1].reset_index(drop=True).iterrows():
    sig = "プラス" if r.lo > 0 else ("マイナス" if r.hi < 0 else "0をまたぐ")
    ax.hlines(i, r.lo, r.hi, color=COL[sig], lw=2.2); ax.scatter(r.coef, i, color=COL[sig], zorder=3, s=20)
ax.set_yticks(range(len(Q)), [f"{r.study}｜{('水準' if '水準' in r.design else '変化')}｜{r.method}" for _, r in Q.iloc[::-1].iterrows()], fontsize=8)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("在所児＋10人（0〜5歳100人あたり）で、女性の労働力率が何ポイント違うか（95%区間）")
ax.set_title("女性の就業への答えは、どの記事・手法でも向きはプラス。大きさは比べ方で約3倍違う", loc="left", fontsize=11.5)
fig.text(0.01, -0.03, SRC, fontsize=7, color="#8a8984")
fig.savefig(FIG / "f118_5_labor_answers.png"); plt.close(fig)
print("ok")
