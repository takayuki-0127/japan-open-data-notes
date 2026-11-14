"""799 季節の波を月のダミー変数で表すか、フーリエ項で表すかで、予測の誤差はどれだけ違うのか

架空の月次の系列：水準＋ゆるい伸び＋季節の波＋ばらつき（sd 1）。季節の波は2種類。
  なめらか：振幅3の正弦波　　とがった：12月だけ＋8（ほかの月は少しずつ下げて平均0）
系列の長さを2・3・5・10年に変え、各300回、
  月のダミー（11個）／フーリエ項 K＝1・2・3（sin と cos を K 組）
を伸びと一緒に最小二乗で当てはめ、次の12か月を予測して、本当の値（ばらつきなし）との誤差を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 799）"
rng = np.random.default_rng(799)
R = 300
YEARS = [2, 3, 5, 10]
m = np.arange(12)
SEAS = {"smooth": 3 * np.sin(2 * np.pi * (m - 2) / 12),
        "spike": np.where(m == 11, 8.0, -8.0 / 11)}


def design(t, kind):
    X = [np.ones_like(t, dtype=float), t / 12.0]
    mo = t % 12
    if kind == "dummy":
        X += [(mo == j).astype(float) for j in range(1, 12)]
    else:
        for k in range(1, kind + 1):
            X += [np.sin(2 * np.pi * k * mo / 12), np.cos(2 * np.pi * k * mo / 12)]
    return np.column_stack(X)


KINDS = ["dummy", 1, 2, 3]
rows = []
for sname, s in SEAS.items():
    for yrs in YEARS:
        T = 12 * yrs; t = np.arange(T); tf = np.arange(T, T + 12)
        truth_f = 50 + .5 * tf / 12 + s[tf % 12]
        errs = {k: [] for k in KINDS}
        for _ in range(R):
            y = 50 + .5 * t / 12 + s[t % 12] + rng.normal(0, 1, T)
            for k in KINDS:
                b = np.linalg.lstsq(design(t, k), y, rcond=None)[0]
                errs[k].append(np.sqrt(np.mean((design(tf, k) @ b - truth_f) ** 2)))
        for k in KINDS:
            rows.append(dict(season=sname, years=yrs, model=str(k), params=design(t, k).shape[1], rmse=float(np.mean(errs[k]))))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
g = lambda s, y, k: float(S[(S.season == s) & (S.years == y) & (S.model == str(k))].rmse.iloc[0])
out = {"reps": R, "noise_sd": 1.0, "by": {f"{s}_{y}y": {str(k): round(g(s, y, k), 3) for k in KINDS} for s in SEAS for y in YEARS},
       "smooth_2y_dummy": g("smooth", 2, "dummy"), "smooth_2y_k1": g("smooth", 2, 1), "smooth_10y_dummy": g("smooth", 10, "dummy"), "smooth_10y_k1": g("smooth", 10, 1),
       "spike_2y_dummy": g("spike", 2, "dummy"), "spike_2y_k2": g("spike", 2, 2), "spike_10y_dummy": g("spike", 10, "dummy"), "spike_10y_k3": g("spike", 10, 3),
       "spike_10y_k1": g("spike", 10, 1)}
json.dump(out, open(RES / "a799_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：季節の形とフーリエ項での近さ
fig, axs = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
mm = np.arange(12); fine = np.linspace(0, 12, 200)
for ax, (sname, t_) in zip(axs, [("smooth", "なめらかな季節の波"), ("spike", "12月だけとがった季節の波")]):
    s = SEAS[sname]; ax.bar(mm + 1, s, color=LIGHT, label="本当の季節の波")
    for k, c in zip([1, 3], [ORANGE, GREEN]):
        X = np.column_stack([np.ones(12)] + [f(2 * np.pi * j * mm / 12) for j in range(1, k + 1) for f in (np.sin, np.cos)])
        b = np.linalg.lstsq(X, s, rcond=None)[0]
        Xf = np.column_stack([np.ones(200)] + [f(2 * np.pi * j * (fine - 1) / 12) for j in range(1, k + 1) for f in (np.sin, np.cos)])
        ax.plot(fine, Xf @ b, color=c, label=f"フーリエ項 K＝{k}")
    ax.set_xticks(mm + 1); ax.set_xlabel("月"); ax.set_title(t_, fontsize=11)
axs[0].set_ylabel("季節の波"); axs[1].legend(frameon=False, fontsize=9)
fig.suptitle("フーリエ項は少ない数でなめらかな波を表せるが、とがった月は表しきれない", y=1.03)
save(fig, "a799_shapes.png", SRC, y=-0.06)

# 図2・3：系列の長さと予測の誤差
for sname, fn, t_ in [("smooth", "a799_smooth.png", "なめらかな波：短い系列ではフーリエ項（K＝1）がダミーより当たる"),
                      ("spike", "a799_spike.png", "とがった波：フーリエ項の数が少ないと外れ、ダミーが当たる")]:
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for k, c in zip(KINDS, [BLUE, ORANGE, GRAY, GREEN]):
        s = S[(S.season == sname) & (S.model == str(k))]
        ax.plot(s.years, s.rmse, "o-", color=c, label="月のダミー（11個）" if k == "dummy" else f"フーリエ項 K＝{k}（{2*k}個）")
    ax.set_xticks(YEARS); ax.set_xlabel("学習に使った系列の長さ（年）"); ax.set_ylabel("次の12か月の誤差（RMSE）")
    ax.legend(frameon=False); ax.set_title(t_)
    save(fig, fn, SRC)
print(S.pivot_table(index=["season", "years"], columns="model", values="rmse").round(3))
