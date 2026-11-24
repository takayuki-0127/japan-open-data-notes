"""1132 背景の色と照明が違うと、同じ商品の写真の色の数値はどれだけ動くのか？（架空のデータ）

作成者が置いた架空の商品（色の板）40個を、5つの背景×3つの照明で写したときの、写真の上の商品の色の値（0〜255の赤・緑・青）を数える。
光は400〜700nmを10nmごとの31の波長に分けて扱う。商品・背景の「波長ごとの光の返しやすさ」、照明の「波長ごとの強さ」、
カメラの赤・緑・青の「波長ごとの感じやすさ」はすべて作成者が置いた。商品の返しやすさは乱数で作る。
商品には照明の光に加え、背景から返った光の一部（映りこみ）も当たる。
カメラの調整は3通り：①自動（画面全体の平均が灰色になるように色を合わせ、平均の明るさが一定になるように明るさを合わせる）、
②固定（昼の光・灰色の背景で合わせた設定のまま）、③灰色の板で合わせる（商品の横に置いた灰色の板が灰色に写るように毎回合わせる）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1132
SRC = "架空の商品・背景・照明・カメラ（作成者が置いた式と乱数で作成、seed 1132）"
WL = np.arange(400, 701, 10).astype(float)
N_PROD = 40
AREA = 0.25          # 写真の中で商品が占める割合（残りは背景）
SPILL = 0.10         # 背景から返った光が商品に当たる強さ（背景の返しやすさ×0.10）
GRID_AREA = [0.10, 0.25, 0.50]
GRID_SPILL = [0.0, 0.10, 0.20]
CARD = 0.40          # 灰色の板・灰色の背景の返しやすさ
LEVEL = 0.30         # 灰色の板を写す明るさ（直線の値）。自動の明るさ合わせも、測った明るさをこの値にする
CENTER = 2.0         # 自動の明るさ合わせは、真ん中（商品）を2倍重く見る
MODES = ["①自動", "②固定（基準で合わせたまま）", "③灰色の板で毎回合わせる"]


def bump(c, w):
    return np.exp(-0.5 * ((WL - c) / w) ** 2)


def step(c, w):
    return 1 / (1 + np.exp(-(WL - c) / w))


SENS = np.stack([bump(605, 35), bump(540, 35), bump(455, 28)])            # カメラの赤・緑・青
SENS = SENS / SENS.sum(1, keepdims=True)
LIGHTS = {"昼の光": np.ones_like(WL),
          "暖かい光": 0.35 + 1.3 * (WL - 400) / 300,
          "青白い光": 1.45 - 0.8 * (WL - 400) / 300}
BGS = {"灰色": np.full_like(WL, CARD),
       "白": np.full_like(WL, 0.85),
       "黒": np.full_like(WL, 0.04),
       "赤": 0.05 + 0.70 * step(590, 12),
       "青": 0.05 + 0.60 * bump(465, 30)}
REF_LIGHT, REF_BG = "昼の光", "灰色"


def r(x, d=2):
    return round(float(x), d)


def make_products(rng):
    out = []
    for _ in range(N_PROD):
        s = np.full_like(WL, rng.uniform(0.03, 0.25))
        for _ in range(rng.integers(1, 3)):
            s = s + rng.uniform(0.2, 0.7) * bump(rng.uniform(420, 690), rng.uniform(20, 70))
        if rng.random() < 0.4:
            s = s + rng.uniform(0.2, 0.6) * step(rng.uniform(480, 640), rng.uniform(8, 25))
        out.append(np.clip(s, 0.02, 0.92))
    return np.array(out)


def raw(refl, light):
    """返しやすさ×照明の強さを、カメラの3色の感じやすさで集めた値"""
    return (refl * light) @ SENS.T


def encode(lin):
    return 255 * np.clip(lin, 0, 1) ** (1 / 2.2)


def shoot(prod, bg, light, mode, area, spill, ref_gain):
    """1枚の写真での商品の色（0〜255）。ref_gain は②で使う基準の設定"""
    on_prod = light * (1 + spill * bg)                   # 商品と灰色の板に当たる光（映りこみ込み）
    p = raw(prod, on_prod)
    b = raw(bg, light)
    if mode == 0:
        mean = area * p + (1 - area) * b                 # 画面全体の平均
        gain = mean.mean() / mean                        # 平均が灰色になるように3色を合わせる
        wc = min(1.0, CENTER * area)
        meter = ((wc * p + (1 - wc) * b) * gain).mean()  # 真ん中を重く見た明るさ
        gain = gain * LEVEL / meter                      # 測った明るさを一定にする
    elif mode == 1:
        gain = ref_gain
    else:
        c = raw(np.full_like(WL, CARD), on_prod)         # 商品の横の灰色の板（商品と同じ光が当たる）
        gain = LEVEL / c                                 # 灰色の板が3色そろって決まった明るさになるように
    return encode(p * gain)


def reference_gain(spill):
    """基準（昼の光・灰色の背景）で灰色の板に合わせた設定"""
    light = LIGHTS[REF_LIGHT]
    c = raw(np.full_like(WL, CARD), light * (1 + spill * BGS[REF_BG]))
    return LEVEL / c


def dist_parts(v, ref):
    d = v - ref
    tot = np.sqrt((d ** 2).sum(-1))
    bright = d.mean(-1)                                  # 3色の平均の動き（明るさ）
    chrom = np.sqrt(((d - bright[..., None]) ** 2).sum(-1))  # 3色の平均を引いた残り（色合い）
    return tot, bright, chrom


def run(prods, area, spill):
    rg = reference_gain(spill)
    recs = []
    vals = {}
    for m in range(3):
        for ln, light in LIGHTS.items():
            for bn, bg in BGS.items():
                v = np.array([shoot(p, bg, light, m, area, spill, rg) for p in prods])
                vals[(m, ln, bn)] = v
    ref = np.array([shoot(p, BGS[REF_BG], LIGHTS[REF_LIGHT], 2, area, spill, rg) for p in prods])
    for (m, ln, bn), v in vals.items():
        tot, bri, chm = dist_parts(v, vals[(m, REF_LIGHT, REF_BG)])   # 同じ調整のしかたの、基準の条件（昼の光・灰色の背景）の写真から
        clipped = float(np.mean((v >= 254.5).any(-1) | (v <= 0.5).any(-1)))
        recs.append({"mode": MODES[m], "light": ln, "background": bn, "dist_mean": tot.mean(), "dist_max": tot.max(),
                     "bright_shift_mean": bri.mean(), "bright_shift_absmean": np.abs(bri).mean(), "chroma_dist_mean": chm.mean(),
                     "clipped_share": clipped})
    gap = dist_parts(vals[(0, REF_LIGHT, REF_BG)], ref)[0].mean()   # 基準の条件で、①自動と③灰色の板の写真の差
    return pd.DataFrame(recs), vals, ref, gap


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    prods = make_products(rng)
    base, vals, ref, gap = run(prods, AREA, SPILL)
    base_r = base.copy()
    for c in ["dist_mean", "dist_max", "bright_shift_mean", "bright_shift_absmean", "chroma_dist_mean"]:
        base_r[c] = base_r[c].round(2)
    base_r["clipped_share"] = base_r["clipped_share"].round(4)
    base_r.to_csv(RES / "conditions_base.csv", index=False)

    # まとめ：背景だけ替える（昼の光）・照明だけ替える（灰色の背景）・両方
    def summ(df):
        out = []
        for m in MODES:
            d = df[df["mode"] == m]
            bg_only = d[(d.light == REF_LIGHT) & (d.background != REF_BG)]
            lt_only = d[(d.background == REF_BG) & (d.light != REF_LIGHT)]
            both = d[(d.background != REF_BG) & (d.light != REF_LIGHT)]
            out.append({"mode": m,
                        "bg_only_dist": r(bg_only.dist_mean.mean()), "bg_only_dist_maxcond": r(bg_only.dist_mean.max()),
                        "bg_only_bright_abs": r(bg_only.bright_shift_absmean.mean()), "bg_only_chroma": r(bg_only.chroma_dist_mean.mean()),
                        "light_only_dist": r(lt_only.dist_mean.mean()), "light_only_dist_maxcond": r(lt_only.dist_mean.max()),
                        "light_only_bright_abs": r(lt_only.bright_shift_absmean.mean()), "light_only_chroma": r(lt_only.chroma_dist_mean.mean()),
                        "both_dist": r(both.dist_mean.mean()), "both_dist_maxcond": r(both.dist_mean.max()),
                        "all15_dist_max_product": r(d.dist_max.max())})
        return out
    summary = summ(base)
    pd.DataFrame(summary).to_csv(RES / "summary_base.csv", index=False)

    # 確かめ：商品の大きさ×映りこみ（9通り）
    grid_rows = []
    for a in GRID_AREA:
        for s in GRID_SPILL:
            df, _, _, _ = run(prods, a, s)
            for row in summ(df):
                grid_rows.append({"area": a, "spill": s, **row})
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)
    grng = []
    for m in MODES:
        g = grid[grid["mode"] == m]
        grng.append({"mode": m, "bg_only_min": r(g.bg_only_dist.min()), "bg_only_max": r(g.bg_only_dist.max()),
                     "light_only_min": r(g.light_only_dist.min()), "light_only_max": r(g.light_only_dist.max()),
                     "both_min": r(g.both_dist.min()), "both_max": r(g.both_dist.max())})
    no_spill = grid[grid.spill == 0.0]
    fixed_bg_nospill = r(no_spill[no_spill["mode"] == MODES[1]].bg_only_dist.max(), 4)
    card_bg_nospill = r(no_spill[no_spill["mode"] == MODES[2]].bg_only_dist.max(), 4)

    # 例の商品（ベージュに近いもの：赤・緑・青の差が小さく明るいもの）
    lum = ref.mean(1)
    sat = ref.max(1) - ref.min(1)
    ex = int(np.argmin(np.abs(lum - 170) + 2 * np.abs(sat - 40)))
    ex_rows = []
    for m in range(3):
        for ln in LIGHTS:
            for bn in BGS:
                v = vals[(m, ln, bn)][ex]
                ex_rows.append({"mode": MODES[m], "light": ln, "background": bn, "R": r(v[0], 1), "G": r(v[1], 1), "B": r(v[2], 1)})
    exdf = pd.DataFrame(ex_rows)
    exdf.to_csv(RES / "example_product.csv", index=False)

    # データ：商品・背景・照明・感じやすさ
    rows = [{"kind": "product", "name": f"商品{i + 1:02d}", **{f"w{int(w)}": round(float(x), 4) for w, x in zip(WL, p)}} for i, p in enumerate(prods)]
    rows += [{"kind": "background", "name": k, **{f"w{int(w)}": round(float(x), 4) for w, x in zip(WL, v)}} for k, v in BGS.items()]
    rows += [{"kind": "light", "name": k, **{f"w{int(w)}": round(float(x), 4) for w, x in zip(WL, v)}} for k, v in LIGHTS.items()]
    rows += [{"kind": "camera", "name": n, **{f"w{int(w)}": round(float(x), 5) for w, x in zip(WL, v)}} for n, v in zip(["赤", "緑", "青"], SENS)]
    pd.DataFrame(rows).to_csv(DATA / "spectra.csv", index=False)
    refdf = pd.DataFrame([{"product": f"商品{i + 1:02d}", "R": r(v[0], 1), "G": r(v[1], 1), "B": r(v[2], 1)} for i, v in enumerate(ref)])
    refdf.to_csv(DATA / "reference_colors.csv", index=False)

    main_json = {
        "settings": {"wavelengths": "400-700nm, 10nm", "products": N_PROD, "area": AREA, "spill": SPILL,
                     "lights": list(LIGHTS), "backgrounds": list(BGS), "modes": MODES, "reference": f"{REF_LIGHT}・{REF_BG}・③",
                     "card_and_auto_level_linear": LEVEL, "auto_center_weight": CENTER, "card_reflectance": CARD, "gamma": 2.2,
                     "grid_area": GRID_AREA, "grid_spill": GRID_SPILL},
        "summary_base": summary,
        "auto_vs_card_at_reference_condition": r(gap),
        "grid_range_9": grng,
        "no_spill_fixed_bg_only_max": fixed_bg_nospill,
        "no_spill_card_bg_only_max": card_bg_nospill,
        "example_product": f"商品{ex + 1:02d}",
        "example_reference_RGB": [r(x, 1) for x in ref[ex]],
        "auto_by_background_daylight": base_r[(base_r["mode"] == MODES[0]) & (base_r.light == REF_LIGHT)][["background", "dist_mean", "bright_shift_mean", "chroma_dist_mean", "clipped_share"]].to_dict("records"),
        "card_by_light_graybg": base_r[(base_r["mode"] == MODES[2]) & (base_r.background == REF_BG)][["light", "dist_mean", "dist_max", "chroma_dist_mean"]].to_dict("records"),
        "fixed_by_light_graybg": base_r[(base_r["mode"] == MODES[1]) & (base_r.background == REF_BG)][["light", "dist_mean", "bright_shift_mean", "chroma_dist_mean"]].to_dict("records"),
        "card_by_background_daylight": base_r[(base_r["mode"] == MODES[2]) & (base_r.light == REF_LIGHT)][["background", "dist_mean", "dist_max"]].to_dict("records"),
        "fixed_by_background_daylight": base_r[(base_r["mode"] == MODES[1]) & (base_r.light == REF_LIGHT)][["background", "dist_mean", "bright_shift_mean", "chroma_dist_mean"]].to_dict("records"),
    }
    with open(RES / "a1132_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # ---- 図1：例の商品の色の板（調整3通り×照明3×背景5） ----
    fig, axs = plt.subplots(3, 1, figsize=(8.2, 6.4))
    for m, ax in enumerate(axs):
        img = np.zeros((3, 5, 3))
        for i, ln in enumerate(LIGHTS):
            for j, bn in enumerate(BGS):
                img[i, j] = vals[(m, ln, bn)][ex] / 255
        ax.imshow(img, aspect="auto")
        ax.set_yticks(range(3)); ax.set_yticklabels(list(LIGHTS), fontsize=9)
        ax.set_xticks(range(5)); ax.set_xticklabels([f"背景：{b}" for b in BGS] if m == 2 else [""] * 5, fontsize=9)
        ax.set_title(MODES[m], fontsize=10, loc="left")
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(length=0)
        for i in range(3):
            for j in range(5):
                v = vals[(m, list(LIGHTS)[i], list(BGS)[j])][ex]
                ax.text(j, i, f"{v[0]:.0f}・{v[1]:.0f}・{v[2]:.0f}", ha="center", va="center", fontsize=7.5,
                        color="white" if v.mean() < 110 else INK)
    fig.suptitle(f"同じ商品（商品{ex + 1:02d}）の写真の上の色（数字は赤・緑・青の0〜255）", fontsize=11)
    fig.tight_layout()
    save(fig, "a1132_example.png", "出典：" + SRC)

    # ---- 図2：調整3通り×（背景だけ・照明だけ・両方）の平均の色の差 ----
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    keys = [("bg_only_dist", "背景だけ替える（昼の光）"), ("light_only_dist", "照明だけ替える（灰色の背景）"), ("both_dist", "両方替える")]
    xs = np.arange(3); w = 0.26
    for i, ((k, lab), c) in enumerate(zip(keys, [BLUE, ORANGE, GRAY])):
        v = [s[k] for s in summary]
        ax.bar(xs + (i - 1) * w, v, w, color=c, label=lab)
        for x, y in zip(xs + (i - 1) * w, v):
            ax.text(x, y + 0.4, f"{y:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels(MODES, fontsize=9)
    ax.set_ylim(0, None)
    ax.set_ylabel("色の差（0〜255、40個の平均）")
    ax.set_title("調整のしかたごとの商品の色の動き（基準の条件＝昼の光・灰色の背景）", fontsize=11.5)
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a1132_modes.png", "出典：" + SRC)

    # ---- 図3：自動のときの背景ごとの動き（明るさと色合いに分ける） ----
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    d = base_r[(base_r["mode"] == MODES[0]) & (base_r.light == REF_LIGHT)]
    xs = np.arange(len(d)); w = 0.36
    ax.bar(xs - w / 2, d.bright_shift_mean, w, color=BLUE, label="明るさの動き（3色の平均、＋は明るく）")
    ax.bar(xs + w / 2, d.chroma_dist_mean, w, color=ORANGE, label="色合いの動き（3色の平均を引いた残りの大きさ）")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels([f"背景：{b}" for b in d.background])
    ax.set_ylabel("灰色の背景との差（0〜255、40個の平均）")
    ax.set_title("①自動のまま背景だけ替えたとき（昼の光）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1132_auto_background.png", "出典：" + SRC)

    print(json.dumps({k: main_json[k] for k in ["summary_base", "auto_vs_card_at_reference_condition", "grid_range_9", "no_spill_fixed_bg_only_max", "no_spill_card_bg_only_max", "example_product", "example_reference_RGB", "auto_by_background_daylight", "card_by_light_graybg", "fixed_by_light_graybg", "card_by_background_daylight", "fixed_by_background_daylight"]}, ensure_ascii=False, indent=0))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
