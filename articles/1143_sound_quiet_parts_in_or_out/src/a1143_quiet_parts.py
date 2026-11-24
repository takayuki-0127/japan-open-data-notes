"""1143 静かな部分を含めて測るか除いて測るかで、1曲の大きさの数字はどれだけ変わるのか？（架空のデータ）

作成者が式と乱数で作った架空の曲（波形）。曲ごとに、大きい部分・静かに弾く部分・音のない部分（無音）の
長さと大きさを置く。大きさは「上限の振れ幅を0 dBとした、強さ（振れ幅の2乗）の平均を dB にした値」で数える。
①全部含める、②とても小さい区間（−70 dB 未満）だけ除く、③①〜②で出した値より10 dB 以上小さい区間も除く（2段）、
の3つの測り方で、1曲の大きさの数字がどれだけ変わるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1143
SRC = "架空の曲の波形（作成者が式と乱数で作成、seed 1143）"
SR = 4000            # 1秒あたりの点の数
DUR = 60             # 1曲の長さ（秒）
SUB = 0.1            # 強さを数える最小の区間（秒）
NSUB = int(DUR / SUB)
N_SONG = 300
ABS_GATE = -70.0


def db(p):
    return 10 * np.log10(np.maximum(p, 1e-30))


def carrier(rng, n):
    """強さの平均が1になる音のもと（3つの音程＋雑音）"""
    t = np.arange(n) / SR
    f = rng.uniform(110, 440)
    s = (np.sin(2 * np.pi * f * t + rng.uniform(0, 6.3)) + 0.5 * np.sin(2 * np.pi * 2 * f * t + rng.uniform(0, 6.3))
         + 0.3 * np.sin(2 * np.pi * 3.01 * f * t + rng.uniform(0, 6.3)))
    s = s / np.sqrt(np.mean(s ** 2))
    x = 0.6 * s + 0.8 * rng.standard_normal(n)
    return x / np.sqrt(np.mean(x ** 2))


def layout(rng, q, s):
    """0.1秒ごとのラベル（0=無音、1=静かに弾く、2=大きい）。無音は頭・終わり・途中の切れ目に分ける"""
    n_q = int(round(q * NSUB)); n_s = int(round(s * NSUB)); n_l = NSUB - n_q - n_s
    # 無音：頭・終わり・途中の0〜3か所
    k_gap = rng.integers(0, 4)
    cuts = np.sort(rng.uniform(0, 1, k_gap + 1)); parts_q = np.diff(np.r_[0, cuts, 1])
    q_sizes = np.floor(parts_q * n_q).astype(int); q_sizes[0] += n_q - q_sizes.sum()
    head, tail, gaps = q_sizes[0], q_sizes[1] if k_gap >= 0 and len(q_sizes) > 1 else 0, list(q_sizes[2:])
    # 静かに弾く部分：1〜3か所
    k_s = rng.integers(1, 4)
    ps = rng.dirichlet(np.ones(k_s)); s_sizes = np.floor(ps * n_s).astype(int); s_sizes[0] += n_s - s_sizes.sum()
    # 大きい部分を区切りの数で分ける
    k_l = k_s + len(gaps) + 1
    pl = rng.dirichlet(np.ones(k_l) * 2); l_sizes = np.floor(pl * n_l).astype(int); l_sizes[0] += n_l - l_sizes.sum()
    mids = [(1, v) for v in s_sizes] + [(0, v) for v in gaps]
    order = rng.permutation(len(mids))
    seq = [(0, head)]
    for i, j in enumerate(order):
        seq.append((2, l_sizes[i])); seq.append(mids[j])
    seq.append((2, l_sizes[-1])); seq.append((0, tail))
    lab = np.concatenate([np.full(v, c, dtype=int) for c, v in seq if v > 0])
    return lab, len([1 for c, v in seq if c == 2 and v > 0])


def make_song(rng, q, s, loud, depth, floor_db):
    """0.1秒ごとの強さ（実際に波形を作って数える）と、ラベル"""
    lab, n_loud_sec = layout(rng, q, s)
    lvl = np.full(NSUB, -300.0)
    # 大きい部分は区切りごとに ±1.5 dB 振る
    sec_id = np.cumsum(np.r_[1, (np.diff(lab) != 0).astype(int)])
    for sid in np.unique(sec_id):
        m = sec_id == sid
        c = lab[m][0]
        if c == 2:
            lvl[m] = loud + rng.uniform(-1.5, 1.5)
        elif c == 1:
            lvl[m] = loud - depth + rng.uniform(-1.0, 1.0)
    n = NSUB * int(SR * SUB)
    amp = np.repeat(np.where(lab > 0, 10 ** (lvl / 20), 0.0), int(SR * SUB))
    x = amp * carrier(rng, n)
    if floor_db is not None:
        x = x + 10 ** (floor_db / 20) * rng.standard_normal(n)
    p_sub = (x.reshape(NSUB, -1) ** 2).mean(1)
    # 作成者の置いた「鳴っている部分」の本当の強さ（波形を作る前の値）
    true_p = 10 ** (lvl / 10)
    return p_sub, lab, true_p, x


def measure(p_sub, block=0.4, rel=-10.0):
    """①全部、②−70 dB 未満の区間を除く、③さらに②の値より rel dB 小さい区間を除く"""
    k = int(round(block / SUB))
    nb = len(p_sub) // k
    pb = p_sub[:nb * k].reshape(nb, k).mean(1)
    m1 = db(pb.mean())
    keep2 = db(pb) >= ABS_GATE
    m2 = db(pb[keep2].mean()) if keep2.any() else -300.0
    keep3 = keep2 & (db(pb) >= m2 + rel)
    m3 = db(pb[keep3].mean()) if keep3.any() else -300.0
    return m1, m2, m3, pb, keep2, keep3


def gen_songs(seed, n=N_SONG, floor_db=None):
    """曲を作って、0.1秒ごとの強さ・ラベル・本当の強さを返す（測り方を変えても作り直さない）"""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        q = rng.uniform(0, 0.4); s = rng.uniform(0, 0.4)
        loud = rng.uniform(-20, -10); depth = rng.uniform(4, 24)
        p_sub, lab, true_p, x = make_song(rng, q, s, loud, depth, floor_db)
        out.append((i + 1, q, loud, depth, p_sub, lab, true_p))
    return out


def songs(gen, block=0.4, rel=-10.0, keep_example=False):
    rows, ex = [], None
    for sid, q, loud, depth, p_sub, lab, true_p in gen:
        s = float((lab == 1).mean())
        m1, m2, m3, pb, k2, k3 = measure(p_sub, block, rel)
        r_sound = db(true_p[lab > 0].mean()); r_loud = db(true_p[lab == 2].mean())
        rows.append({"song_id": sid, "quiet_share": q, "soft_share": s,
                     "silence_share": float((lab == 0).mean()), "loud_db": loud, "soft_depth_db": depth,
                     "m1_all": m1, "m2_abs_gate": m2, "m3_two_step": m3,
                     "true_sounding": r_sound, "true_loud_only": r_loud})
        if keep_example and ex is None and 0.2 < q < 0.35 and 0.2 < s < 0.35 and 9 < depth < 16:
            ex = {"p_sub": p_sub, "lab": lab, "pb": pb, "k2": k2, "k3": k3, "m": (m1, m2, m3), "song_id": sid}
    return pd.DataFrame(rows), ex


def reversed_pairs(a, b):
    a = np.asarray(a); b = np.asarray(b)
    da = np.sign(a[:, None] - a[None, :]); dbb = np.sign(b[:, None] - b[None, :])
    iu = np.triu_indices(len(a), 1)
    return float(np.mean(da[iu] * dbb[iu] < 0))


def rank_move(a, b):
    ra = pd.Series(a).rank(ascending=False); rb = pd.Series(b).rank(ascending=False)
    return np.abs(ra - rb)


def summarize(df):
    d31 = df.m3_two_step - df.m1_all
    return {
        "diff_3_minus_1_median": round(float(d31.median()), 2),
        "diff_3_minus_1_p5": round(float(d31.quantile(0.05)), 2),
        "diff_3_minus_1_p95": round(float(d31.quantile(0.95)), 2),
        "diff_3_minus_1_max": round(float(d31.max()), 2),
        "diff_3_minus_1_min": round(float(d31.min()), 2),
        "m3_minus_true_sounding_median": round(float((df.m3_two_step - df.true_sounding).median()), 2),
        "m3_minus_true_sounding_p5": round(float((df.m3_two_step - df.true_sounding).quantile(0.05)), 2),
        "m3_minus_true_sounding_p95": round(float((df.m3_two_step - df.true_sounding).quantile(0.95)), 2),
        "m3_within_05_of_sounding_pct": round(float(((df.m3_two_step - df.true_sounding).abs() <= 0.5).mean() * 100), 1),
        "m3_within_05_of_loud_only_pct": round(float(((df.m3_two_step - df.true_loud_only).abs() <= 0.5).mean() * 100), 1),
        "m2_minus_m1_median": round(float((df.m2_abs_gate - df.m1_all).median()), 2),
        "reversed_pairs_1_vs_3_pct": round(reversed_pairs(df.m1_all, df.m3_two_step) * 100, 2),
        "n_pairs": int(len(df) * (len(df) - 1) // 2),
        "rank_moved_30_or_more_pct": round(float((rank_move(df.m1_all, df.m3_two_step) >= 30).mean() * 100), 1),
    }


def jump_sweep(seed):
    """大きい部分60%・静かに弾く部分40%・無音なしの曲で、静かに弾く部分の深さを4〜20 dB に動かす"""
    rows = []
    lab = np.r_[np.full(120, 2), np.full(120, 1), np.full(120, 2), np.full(120, 1), np.full(120, 2)]
    for d in np.round(np.arange(4, 20.01, 0.25), 2):
        rng = np.random.default_rng(seed)
        loud = -14.0
        lvl = np.where(lab == 2, loud, loud - d)
        n = NSUB * int(SR * SUB)
        x = np.repeat(10 ** (lvl / 20), int(SR * SUB)) * carrier(rng, n)
        p_sub = (x.reshape(NSUB, -1) ** 2).mean(1)
        m1, m2, m3, pb, k2, k3 = measure(p_sub)
        incl = db(0.6 * 10 ** (loud / 10) + 0.4 * 10 ** ((loud - d) / 10))
        rows.append({"soft_depth_db": d, "m1_all": round(m1, 3), "m3_two_step": round(m3, 3),
                     "formula_with_soft": round(float(incl), 3), "formula_loud_only": loud,
                     "soft_blocks_kept_pct": round(float(k3[np.repeat(lab, 1)[:len(k3) * 4].reshape(-1, 4)[:, 0] == 1].mean() * 100), 1)})
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    df, ex = songs(gen_songs(SEED), keep_example=True)
    df.round(4).to_csv(DATA / "songs.csv", index=False)
    base = summarize(df)

    # 無音だけのときの式：①は鳴っている部分より 10*log10(1-無音の割合) 低い
    formula = db(1 - df.silence_share)
    gap = (df.m1_all - df.true_sounding) - formula
    base["m1_minus_sounding_vs_formula_maxabs"] = round(float(gap.abs().max()), 3)
    base["formula_q30_db"] = round(float(db(1 - 0.3)), 3)
    base["formula_q40_db"] = round(float(db(1 - 0.4)), 3)
    base["m1_minus_true_sounding_median"] = round(float((df.m1_all - df.true_sounding).median()), 2)
    base["m1_minus_true_sounding_min"] = round(float((df.m1_all - df.true_sounding).min()), 2)

    # 鳴っている部分が同じで、無音の割合だけ違う2曲
    pair = []
    for q in [0.0, 0.4]:
        rng = np.random.default_rng(SEED + 7)
        lab = np.full(NSUB, 2); lab[:int(q * NSUB / 2)] = 0; lab[NSUB - int(q * NSUB / 2):] = 0
        lvl = np.where(lab == 2, -14.0, -300.0)
        n = NSUB * int(SR * SUB)
        x = np.repeat(np.where(lab > 0, 10 ** (lvl / 20), 0.0), int(SR * SUB)) * carrier(rng, n)
        m1, m2, m3, *_ = measure((x.reshape(NSUB, -1) ** 2).mean(1))
        pair.append({"silence_share": q, "m1_all": round(m1, 2), "m2_abs_gate": round(m2, 2), "m3_two_step": round(m3, 2)})
    pair = pd.DataFrame(pair)
    pair.to_csv(RES / "pair_same_music.csv", index=False)

    jump = jump_sweep(SEED + 1)
    jump.to_csv(RES / "jump_sweep.csv", index=False)
    j = jump.m3_two_step.values
    k = int(np.argmax(np.abs(np.diff(j))))
    # 静かに弾く部分が入るかどうかで変わる幅（0.25 dB 刻みで最も大きく動いたところ）
    jj = jump.set_index("soft_depth_db")
    jump_info2 = {f"m3_at_depth_{d:g}": round(float(jj.m3_two_step[d]), 2) for d in [10.0, 11.0, 12.0, 13.0, 14.0]}
    jump_info2.update({f"soft_kept_pct_at_depth_{d:g}": float(jj.soft_blocks_kept_pct[d]) for d in [10.0, 11.0, 12.0, 13.0, 14.0]})
    jump_info2["formula_with_soft_at_11"] = float(jj.formula_with_soft[11.0])
    jump_info2["m3_change_11_to_13"] = round(float(jj.m3_two_step[13.0] - jj.m3_two_step[11.0]), 2)
    jump_info2["m1_change_11_to_13"] = round(float(jj.m1_all[13.0] - jj.m1_all[11.0]), 2)
    jump_info = {"jump_at_depth_from": float(jump.soft_depth_db[k]), "jump_at_depth_to": float(jump.soft_depth_db[k + 1]),
                 "jump_db": round(float(j[k + 1] - j[k]), 2),
                 "m3_at_depth_from": round(float(j[k]), 2), "m3_at_depth_to": round(float(j[k + 1]), 2),
                 "m1_at_depth_from": round(float(jump.m1_all[k]), 2), "m1_at_depth_to": round(float(jump.m1_all[k + 1]), 2), **jump_info2}

    # 置き方を変えた27通り（境目の深さ×区間の長さ×無音に入る雑音）
    grid = []
    for fl_name, fl in [("なし", None), ("−60 dB", -60.0), ("−45 dB", -45.0)]:
        gen = gen_songs(SEED * 10 + 1, n=150, floor_db=fl)
        for block in [0.1, 0.4, 1.0]:
            for rel in [-8.0, -10.0, -15.0]:
                g, _ = songs(gen, block=block, rel=rel)
                sm = summarize(g)
                grid.append({"noise_in_silence": fl_name, "block_sec": block, "rel_gate_db": rel,
                             "diff_3_minus_1_median": sm["diff_3_minus_1_median"],
                             "diff_3_minus_1_max": sm["diff_3_minus_1_max"],
                             "m2_minus_m1_median": sm["m2_minus_m1_median"],
                             "m3_minus_true_sounding_median": sm["m3_minus_true_sounding_median"],
                             "m3_within_05_of_sounding_pct": sm["m3_within_05_of_sounding_pct"],
                             "reversed_pairs_1_vs_3_pct": sm["reversed_pairs_1_vs_3_pct"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = {"grid_n": len(grid),
            "grid_diff_median_min": float(grid.diff_3_minus_1_median.min()),
            "grid_diff_median_max": float(grid.diff_3_minus_1_median.max()),
            "grid_diff_max_min": float(grid.diff_3_minus_1_max.min()),
            "grid_diff_max_max": float(grid.diff_3_minus_1_max.max()),
            "grid_reversed_min": float(grid.reversed_pairs_1_vs_3_pct.min()),
            "grid_reversed_max": float(grid.reversed_pairs_1_vs_3_pct.max()),
            "grid_within05_min": float(grid.m3_within_05_of_sounding_pct.min()),
            "grid_within05_max": float(grid.m3_within_05_of_sounding_pct.max()),
            "grid_m2_minus_m1_noise45_min": float(grid[grid.noise_in_silence == "−45 dB"].m2_minus_m1_median.min()),
            "grid_m2_minus_m1_noise45_max": float(grid[grid.noise_in_silence == "−45 dB"].m2_minus_m1_median.max()),
            "grid_m2_minus_m1_none_min": float(grid[grid.noise_in_silence == "なし"].m2_minus_m1_median.min()),
            "grid_m2_minus_m1_none_max": float(grid[grid.noise_in_silence == "なし"].m2_minus_m1_median.max())}

    # 例の曲の区間
    exb = pd.DataFrame({"block_start_sec": np.arange(len(ex["pb"])) * 0.4, "block_db": np.round(db(ex["pb"]), 3),
                        "kept_abs_gate": ex["k2"], "kept_two_step": ex["k3"]})
    exb.to_csv(DATA / "example_song_blocks.csv", index=False)
    ex_info = {"song_id": int(ex["song_id"]), "m1_all": round(ex["m"][0], 2), "m2_abs_gate": round(ex["m"][1], 2),
               "m3_two_step": round(ex["m"][2], 2),
               "silence_share": round(float(df.loc[ex["song_id"] - 1, "silence_share"]), 3),
               "soft_share": round(float(df.loc[ex["song_id"] - 1, "soft_share"]), 3),
               "soft_depth_db": round(float(df.loc[ex["song_id"] - 1, "soft_depth_db"]), 2),
               "true_sounding": round(float(df.loc[ex["song_id"] - 1, "true_sounding"]), 2),
               "true_loud_only": round(float(df.loc[ex["song_id"] - 1, "true_loud_only"]), 2)}

    # 静かに弾く部分の深さで、③が「鳴っている部分」と「大きい部分だけ」のどちらに近いか
    bands = []
    for lo, hi in [(4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]:
        g = df[(df.soft_depth_db >= lo) & (df.soft_depth_db < hi) & (df.soft_share > 0.1)]
        bands.append({"soft_depth_band": f"{lo}〜{hi} dB", "n": len(g),
                      "m3_minus_sounding_median": round(float((g.m3_two_step - g.true_sounding).median()), 2),
                      "m3_minus_loud_only_median": round(float((g.m3_two_step - g.true_loud_only).median()), 2),
                      "m3_minus_m1_median": round(float((g.m3_two_step - g.m1_all).median()), 2)})
    bands = pd.DataFrame(bands)
    bands.to_csv(RES / "by_soft_depth.csv", index=False)

    out = {"headline": {**base, **jump_info, **gsum}, "example_song": ex_info,
           "pair_same_music": pair.to_dict("records"), "by_soft_depth": bands.to_dict("records")}
    json.dump(out, open(RES / "a1143_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の曲の区間ごとの大きさと、除かれた区間
    fig, ax = plt.subplots(figsize=(9, 4))
    t = exb.block_start_sec.values; v = exb.block_db.values
    vv = np.where(v < -88, -87.0, v)
    col = np.where(exb.kept_two_step, BLUE, np.where(exb.kept_abs_gate, ORANGE, GRAY))
    ax.bar(t, vv + 90, bottom=-90, width=0.4, color=col, align="edge")
    for val, name, c, va in [(ex_info["m1_all"], "①全部含める", INK, "top"), (ex_info["m3_two_step"], "③2段で除く", BLUE, "bottom")]:
        ax.axhline(val, color=c, lw=1.2, ls="--")
        ax.text(60.5, val, f"{name} {val:.2f} dB", color=c, va=va, fontsize=9)
    ax.axhline(ex_info["m2_abs_gate"] - 10, color=ORANGE, lw=0.8, ls=":")
    ax.text(60.5, ex_info["m2_abs_gate"] - 10, "③の境目（②の値−10 dB）", color=ORANGE, va="center", fontsize=8)
    ax.set_xlim(0, 60); ax.set_ylim(-90, 0)
    ax.set_xlabel("曲の中の時刻（秒）"); ax.set_ylabel("0.4秒ごとの大きさ（dB）")
    ax.set_title(f"例の曲（無音{ex_info['silence_share']*100:.0f}%・静かに弾く部分{ex_info['soft_share']*100:.0f}%）")
    ax.text(0.5, -5, "青：③でも数える区間　橙：③で除かれた区間　灰：無音（②でも除く。図の下端に短く描いた）", fontsize=8, color=INK)
    save(fig, "a1143_example.png", SRC)

    # 図2：①−③ と無音の割合
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sc = ax.scatter(df.silence_share * 100, df.m3_two_step - df.m1_all, c=df.soft_depth_db, cmap="viridis", s=14)
    xs = np.linspace(0, 0.42, 50)
    ax.plot(xs * 100, -db(1 - xs), color=ORANGE, lw=1.5, label="無音だけを除いたときの式 −10×log10(1−無音の割合)")
    ax.set_xlabel("無音の割合（%）"); ax.set_ylabel("③2段で除く − ①全部含める（dB）")
    ax.set_ylim(0, None)
    ax.set_title("無音が多い曲ほど、除いた数字との差が大きい（300曲）")
    cb = fig.colorbar(sc, ax=ax); cb.set_label("静かに弾く部分の深さ（dB）")
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    save(fig, "a1143_scatter.png", SRC)

    # 図3：静かに弾く部分の深さを動かすと、③が跳ぶ
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(jump.soft_depth_db, jump.m1_all, color=INK, lw=1.4, label="①全部含める")
    ax.plot(jump.soft_depth_db, jump.m3_two_step, color=BLUE, lw=1.8, label="③2段で除く")
    ax.plot(jump.soft_depth_db, jump.formula_with_soft, color=GRAY, lw=1, ls="--", label="式：静かに弾く部分も含めた値")
    ax.axhline(-14.0, color=ORANGE, lw=1, ls=":", label="式：大きい部分だけの値（−14 dB）")
    ax.set_xlabel("静かに弾く部分が大きい部分より小さい量（dB）"); ax.set_ylabel("1曲の大きさ（dB）")
    ax.set_title("静かに弾く部分（40%）が境目をまたぐと、③の数字が跳ぶ")
    ax.legend(fontsize=8, frameon=False)
    save(fig, "a1143_jump.png", SRC)

    head = {**base, **jump_info, **gsum, "run_sec": round(time.time() - t0, 1)}
    print(json.dumps(head, ensure_ascii=False, indent=1))
    print(json.dumps(ex_info, ensure_ascii=False)); print(pair); print(bands)


if __name__ == "__main__":
    main()
