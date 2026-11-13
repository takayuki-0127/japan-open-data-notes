"""A500 抜けた値を「前の値」で埋めると、平均と傾きはどれだけずれるのか（架空の日次データ、seed 500）"""
import json
import numpy as np
import pandas as pd
from common import plt, save, DATA, RES, BLUE, ORANGE, GRAY, GREEN, INK

SRC = "架空の日次データ（作成者が乱数で作成、seed 500）"
rng = np.random.default_rng(500)
T, REPS = 365, 2000
t = np.arange(T)
SLOPE = 0.05                       # 1日あたり +0.05（1年で約+18）
SEAS = 8 * np.sin(2 * np.pi * t / 7) + 0 * t   # 曜日の波


def series():
    e = np.zeros(T); u = rng.standard_normal(T) * 4
    for i in range(1, T):
        e[i] = 0.6 * e[i - 1] + u[i]           # 前の日に似た揺れ
    return 100 + SLOPE * t + SEAS + e


def mask(y, kind, share):
    """抜ける日を決める（True が抜け）"""
    m = np.zeros(T, bool)
    if kind == "ばらばらに抜ける":
        m = rng.random(T) < share
    elif kind == "7日まとめて抜ける":
        while m.mean() < share:
            s = rng.integers(0, T - 7); m[s:s + 7] = True
    elif kind == "後ろほど抜ける":
        p = share * 2 * t / (T - 1); m = rng.random(T) < p
    elif kind == "最後の60日が抜ける":
        m[-60:] = True
    elif kind == "大きい値ほど抜ける":
        r = (y - y.mean()) / y.std(); p = 1 / (1 + np.exp(-(r * 2 + np.log(share / (1 - share)))))
        m = rng.random(T) < p
    m[0] = False                                # 最初の日はある（前の値で埋められるように）
    return m


def fill(y, m, how):
    s = pd.Series(np.where(m, np.nan, y))
    if how == "前の値で埋める":
        return s.ffill().to_numpy()
    if how == "直線で埋める":
        return s.interpolate(limit_direction="both").to_numpy()
    if how == "曜日の平均で埋める":
        dow = t % 7; v = s.copy()
        for d in range(7):
            v[(dow == d) & s.isna()] = s[dow == d].mean()
        return v.to_numpy()
    return s.to_numpy()                          # 抜いたまま


def slope(y):
    ok = ~np.isnan(y)
    return np.polyfit(t[ok], y[ok], 1)[0]


KINDS = ("ばらばらに抜ける", "7日まとめて抜ける", "後ろほど抜ける", "大きい値ほど抜ける", "最後の60日が抜ける")
HOWS = ("抜いたまま", "前の値で埋める", "直線で埋める", "曜日の平均で埋める")
rows = []
for kind in KINDS:
    for share in ((0.164,) if kind == "最後の60日が抜ける" else (0.1, 0.3)):
        err = {h: {"mean": [], "slope": [], "sd": [], "acf1": []} for h in HOWS}
        for _ in range(REPS):
            y = series(); m = mask(y, kind, share)
            tm, ts, tsd = y.mean(), slope(y), np.std(np.diff(y))
            for h in HOWS:
                z = fill(y, m, h); zz = z[~np.isnan(z)]
                err[h]["mean"].append(np.nanmean(z) - tm)
                err[h]["slope"].append((slope(z) - ts) / SLOPE * 100)
                d = np.diff(z); d = d[~np.isnan(d)]
                err[h]["sd"].append(np.std(d) / tsd - 1)
        for h in HOWS:
            e = err[h]
            rows.append(dict(kind=kind, share=share, how=h, mean_bias=np.mean(e["mean"]), mean_rmse=np.sqrt(np.mean(np.square(e["mean"]))),
                             slope_bias_pct=np.mean(e["slope"]), slope_rmse_pct=np.sqrt(np.mean(np.square(e["slope"]))),
                             daychange_sd_ratio=np.mean(e["sd"]) * 100))
df = pd.DataFrame(rows); df.to_csv(RES / "errors_by_pattern.csv", index=False, float_format="%.4f")

# 例：後ろほど抜ける 30%
y = series(); m = mask(y, "後ろほど抜ける", 0.3)
ex = pd.DataFrame({"day": t, "true": y, "missing": m.astype(int), **{h: fill(y, m, h) for h in HOWS[1:]}})
ex.to_csv(DATA / "example_later_missing_30pct.csv", index=False, float_format="%.3f")

col = {"抜いたまま": GRAY, "前の値で埋める": ORANGE, "直線で埋める": BLUE, "曜日の平均で埋める": GREEN}
# --- 図1：抜け方ごとの平均のずれ（30%）
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
s = df[(df.share == 0.3) | (df.kind == "最後の60日が抜ける")]; x = np.arange(5); w = 0.2
for i, h in enumerate(HOWS):
    q = s[s.how == h]
    ax[0].bar(x + (i - 1.5) * w, q.mean_bias, w, color=col[h], label=h)
    ax[1].bar(x + (i - 1.5) * w, q.slope_rmse_pct, w, color=col[h])
for a in ax:
    a.set_xticks(x); a.set_xticklabels([k.replace("抜ける", "\n抜ける") for k in KINDS], fontsize=9); a.axhline(0, color="k", lw=0.6)
ax[0].set_title("平均のずれ（本当の平均との差、平均は約109）"); ax[1].set_title("傾きの誤差の大きさ（RMSE、%、本当は1日+0.05）")
ax[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("365日のうち30%が抜けたとき（最後の60日は16%、2,000回の平均）", y=1.02)
save(fig, "a500_bias_by_pattern.png", "出典：" + SRC)

# --- 図2：例
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(t, y, color=GRAY, lw=0.8, label="本当の値")
ax.plot(t, ex["前の値で埋める"], color=ORANGE, lw=0.9, label="前の値で埋める")
ax.scatter(t[m], y[m], s=6, color="k", zorder=3, label="抜けた日の本当の値")
ax.set_xlabel("日"); ax.set_ylabel("値"); ax.legend(frameon=False, fontsize=9, ncol=3)
ax.set_title("後ろほど抜ける（全体の30%）例：前の値で埋めると平らな段ができる")
save(fig, "a500_example.png", "出典：" + SRC)

# --- 図3：日ごとの変化の大きさ（ばらばら 10% と 30%）
fig, ax = plt.subplots(figsize=(8, 4.2))
s = df[df.kind == "ばらばらに抜ける"]; x = np.arange(2)
for i, h in enumerate(HOWS[1:]):
    q = s[s.how == h]; ax.bar(x + (i - 1) * 0.26, q.daychange_sd_ratio, 0.26, color=col[h], label=h)
ax.set_xticks(x); ax.set_xticklabels(["10%抜ける", "30%抜ける"]); ax.axhline(0, color="k", lw=0.6)
ax.set_ylabel("日ごとの変化の標準偏差のずれ（%）"); ax.legend(frameon=False); ax.set_title("ばらばらに抜けたとき、日ごとの変化の大きさ")
save(fig, "a500_daychange_sd.png", "出典：" + SRC)

g = lambda k, s, h: df[(df.kind == k) & (df.share == s) & (df.how == h)].iloc[0].to_dict()
main = {f"{k}_{int(s*100)}": {h: g(k, s, h) for h in HOWS} for k in KINDS[:4] for s in (0.1, 0.3)}
main["最後の60日が抜ける"] = {h: g("最後の60日が抜ける", 0.164, h) for h in HOWS}
main["true_mean_typical"] = float(np.mean([series().mean() for _ in range(200)]))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(df.round(3).to_string())
