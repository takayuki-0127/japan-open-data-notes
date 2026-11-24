"""1145 録音全体の音量を上げると、声と雑音の差は広がるのか？（架空のデータ）

作成者が式と乱数で作った架空の録音（20秒）。声は音程のある音に音節ごとの強弱と息つぎの間を付けたもの、
雑音は録音に入った一定の雑音。声と雑音を別々に作っているので、本当の「声と雑音の差」（強さの比を dB にしたもの）が分かる。
録音全体の音量を 0〜30 dB 上げたとき、声と雑音の差がどう動くかを、雑音が入る場所の3通りで数える。
 A 録音の中の雑音（上げる前に入っている）
 B 保存の段の粗さ（8ビットで保存してから上げるか、上げてから保存するか）
 C 聞く場所の雑音（上げたあとに、決まった大きさで加わる）
上限（振れ幅1.0）を超えた分は切れる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1145
SRC = "架空の録音の波形（作成者が式と乱数で作成、seed 1145）"
SR = 8000
DUR = 20
N = SR * DUR
GAINS = np.round(np.arange(0, 30.01, 0.5), 2)
ROOM_DB = -45.0


def db(p):
    return 10 * np.log10(np.maximum(p, 1e-30))


def make_voice(rng, spread):
    """声に見立てた音。spread は音節ごとの強さの散らばり（dB）"""
    t = np.arange(N) / SR
    f0 = 150 + 25 * np.sin(2 * np.pi * 0.3 * t + rng.uniform(0, 6.3)) + 10 * np.sin(2 * np.pi * 1.7 * t)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    s = sum(np.sin(k * ph + rng.uniform(0, 6.3)) / k for k in range(1, 11))
    env = np.zeros(N); pos = 0
    while pos < N:
        if rng.uniform() < 0.18:      # 息つぎの間
            pos += int(rng.uniform(0.3, 1.0) * SR); continue
        L = int(rng.uniform(0.15, 0.3) * SR)
        a = 10 ** (rng.normal(0, spread) / 20)
        w = np.sin(np.pi * np.arange(L) / L) ** 2 * a
        e = min(N, pos + L); env[pos:e] = w[:e - pos]; pos += L
    v = s * env
    return v


def setup(rng, peak_db, snr_db, spread):
    v = make_voice(rng, spread)
    v = v / np.abs(v).max() * 10 ** (peak_db / 20)
    n = rng.standard_normal(N)
    n = n / np.sqrt(np.mean(n ** 2)) * np.sqrt(np.mean(v ** 2) / 10 ** (snr_db / 10))
    room = rng.standard_normal(N)
    room = room / np.sqrt(np.mean(room ** 2)) * 10 ** (ROOM_DB / 20)
    return v, n, room


def quant(x, bits):
    m = 2 ** (bits - 1) - 1
    return np.clip(np.round(x * m), -m, m) / m


def snr(sig, y):
    return float(db(np.mean(sig ** 2)) - db(np.mean((y - sig) ** 2)))


def est_snr(y):
    """録音だけから見積もる差：0.1秒ごとの強さの、大きい半分の平均と小さい1割の平均から"""
    p = np.sort((y.reshape(-1, int(0.1 * SR)) ** 2).mean(1))
    noise = p[:len(p) // 10].mean(); loud = p[len(p) // 2:].mean()
    return float(db(max(loud - noise, 1e-30)) - db(noise))


def sweep(v, n, room, bits=8):
    rows = []
    for g in GAINS:
        k = 10 ** (g / 20); gv = k * v
        ya = np.clip(k * (v + n), -1, 1)
        yb1 = np.clip(k * quant(v + n, bits), -1, 1)          # 保存してから上げる
        yb2 = quant(np.clip(k * (v + n), -1, 1), bits)          # 上げてから保存
        yc = ya + room
        rows.append({"gain_db": float(g),
                     "A_in_recording": snr(gv, ya), "B1_save_then_gain": snr(gv, yb1), "B2_gain_then_save": snr(gv, yb2),
                     "C_room_after": snr(gv, yc),
                     "A_estimated_from_recording": est_snr(ya), "C_estimated_from_recording": est_snr(yc),
                     "clipped_pct": float(np.mean(np.abs(k * (v + n)) > 1) * 100)})
    return pd.DataFrame(rows)


def key_numbers(sw, peak_db, vn_peak_db=None):
    a0 = sw.A_in_recording.iloc[0]
    drop1 = sw[sw.A_in_recording < a0 - 1.0]
    c0 = sw.C_room_after.iloc[0]; ib = int(sw.C_room_after.idxmax())
    return {"A_at_0": round(a0, 2), "A_change_before_clip_maxabs": round(float((sw[sw.clipped_pct == 0].A_in_recording - a0).abs().max()), 3),
            "first_clip_gain": float(sw[sw.clipped_pct > 0].gain_db.min()) if (sw.clipped_pct > 0).any() else None,
            "voice_peak_db": peak_db,
            "formula_first_clip_gain": round(-vn_peak_db, 2) if vn_peak_db is not None else None,
            "A_gain_drop_1db": float(drop1.gain_db.min()) if len(drop1) else None,
            "A_at_30": round(float(sw.A_in_recording.iloc[-1]), 2),
            "A_change_at_30": round(float(sw.A_in_recording.iloc[-1] - a0), 2) + 0.0,
            "C_at_0": round(c0, 2), "C_best": round(float(sw.C_room_after.max()), 2),
            "C_best_gain": float(sw.gain_db[ib]), "C_best_improve": round(float(sw.C_room_after.max() - c0), 2),
            "C_at_30": round(float(sw.C_room_after.iloc[-1]), 2),
            "B1_at_0": round(float(sw.B1_save_then_gain.iloc[0]), 2),
            "B1_best": round(float(sw.B1_save_then_gain.max()), 2),
            "B2_best": round(float(sw.B2_gain_then_save.max()), 2),
            "B2_best_gain": float(sw.gain_db[int(sw.B2_gain_then_save.idxmax())]),
            "Aest_at_0": round(float(sw.A_estimated_from_recording.iloc[0]), 2),
            "Aest_change_before_clip_maxabs": round(float((sw[sw.clipped_pct == 0].A_estimated_from_recording - sw.A_estimated_from_recording.iloc[0]).abs().max()), 3),
            "Aest_at_30": round(float(sw.A_estimated_from_recording.iloc[-1]), 2),
            "Aest_change_at_30": round(float(sw.A_estimated_from_recording.iloc[-1] - sw.A_estimated_from_recording.iloc[0]), 2)}


def main():
    t0 = time.time()
    PEAK, SNR0, SPREAD = -20.0, 20.0, 4.0
    v, n, room = setup(np.random.default_rng(SEED), PEAK, SNR0, SPREAD)
    pd.DataFrame({"t_sec": np.arange(0, N, 8) / SR, "voice": np.round(v[::8], 6), "noise": np.round(n[::8], 6)}).to_csv(
        DATA / "recording_every8th_point.csv", index=False)
    sw = sweep(v, n, room)
    sw.round(4).to_csv(RES / "gain_sweep.csv", index=False)
    kn = key_numbers(sw, PEAK, float(db(np.abs(v + n).max() ** 2)))
    kn["voice_rms_db"] = round(float(db(np.mean(v ** 2))), 2)
    kn["noise_rms_db"] = round(float(db(np.mean(n ** 2))), 2)
    kn["room_rms_db"] = ROOM_DB
    kn["quant8_rms_db"] = round(float(db(np.mean((quant(v + n, 8) - (v + n)) ** 2))), 2)
    pv, pn, pr = np.mean(v ** 2), np.mean(n ** 2), np.mean(room ** 2)
    nc = sw[sw.clipped_pct == 0]
    c_form = db(pv * 10 ** (nc.gain_db / 10)) - db(pn * 10 ** (nc.gain_db / 10) + pr)
    kn["C_formula_before_clip_maxabs"] = round(float(np.abs(nc.C_room_after - c_form).max()), 3)
    kn["Aest_minus_true_at_0"] = round(kn["Aest_at_0"] - kn["A_at_0"], 2)
    kn["last_gain_without_clip"] = float(sw[sw.clipped_pct == 0].gain_db.max())
    kn["C_formula_limit_db"] = round(float(db(pv) - db(pn)), 2)
    sel = sw[sw.gain_db.isin([0, 10, 15, 20, 25, 30])].round(2)

    # 保存の段の細かさ（8・12・16ビット）
    bits_rows = []
    for b in [8, 12, 16]:
        s2 = sweep(v, n, room, bits=b)
        bits_rows.append({"bits": b, "B1_at_0": round(float(s2.B1_save_then_gain.iloc[0]), 2),
                          "B1_best": round(float(s2.B1_save_then_gain.max()), 2),
                          "B2_best": round(float(s2.B2_gain_then_save.max()), 2),
                          "B2_best_gain": float(s2.gain_db[int(s2.B2_gain_then_save.idxmax())]),
                          "true_snr": round(float(s2.A_in_recording.iloc[0]), 2)})
    bits = pd.DataFrame(bits_rows)
    bits.to_csv(RES / "by_bits.csv", index=False)

    # 置き方を変えた27通り（声のいちばん大きい点×本当の差×音節の強さの散らばり）
    grid = []
    for pk in [-30.0, -20.0, -10.0]:
        for s0 in [10.0, 20.0, 30.0]:
            for spd in [2.0, 4.0, 8.0]:
                vv, nn, rr = setup(np.random.default_rng(SEED * 10 + int(-pk) * 100 + int(s0) * 10 + int(spd)), pk, s0, spd)
                k2 = key_numbers(sweep(vv, nn, rr), pk, float(db(np.abs(vv + nn).max() ** 2)))
                grid.append({"voice_peak_db": pk, "true_snr_db": s0, "syllable_spread_db": spd,
                             "first_clip_gain": k2["first_clip_gain"], "A_change_before_clip_maxabs": k2["A_change_before_clip_maxabs"],
                             "A_gain_drop_1db": k2["A_gain_drop_1db"], "A_drop1_over_first_clip": (k2["A_gain_drop_1db"] - k2["first_clip_gain"]) if k2["A_gain_drop_1db"] is not None else None,
                             "formula_first_clip_gain": k2["formula_first_clip_gain"],
                             "A_change_at_30": k2["A_change_at_30"], "Aest_change_at_30": k2["Aest_change_at_30"],
                             "C_best_improve": k2["C_best_improve"], "C_best_gain": k2["C_best_gain"],
                             "B2_minus_B1_best": round(k2["B2_best"] - k2["B1_best"], 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gd = grid.dropna(subset=["A_drop1_over_first_clip"])
    gsum = {"grid_n": len(grid),
            "grid_A_before_clip_maxabs": float(grid.A_change_before_clip_maxabs.max()),
            "grid_A_change30_min": float(grid.A_change_at_30.min()), "grid_A_change30_max": float(grid.A_change_at_30.max()),
            "grid_drop1_n": len(gd),
            "grid_clip_vs_formula_maxabs": float((grid.dropna(subset=["first_clip_gain"]).first_clip_gain - grid.dropna(subset=["first_clip_gain"]).formula_first_clip_gain).abs().max()),
            "grid_Aest_change30_min": float(gd.Aest_change_at_30.min()), "grid_Aest_change30_max": float(gd.Aest_change_at_30.max()),
            "grid_est_smaller_drop_n": int((gd.Aest_change_at_30 > gd.A_change_at_30).sum()),
            "grid_est_drop_share_of_true_min": round(float((gd.Aest_change_at_30 / gd.A_change_at_30).min()), 3),
            "grid_est_drop_share_of_true_max": round(float((gd.Aest_change_at_30 / gd.A_change_at_30).max()), 3),
            "grid_A_change30_clipped_min": float(gd.A_change_at_30.min()), "grid_A_change30_clipped_max": float(gd.A_change_at_30.max()),
            "grid_drop1_over_clip_min": float(gd.A_drop1_over_first_clip.min()), "grid_drop1_over_clip_max": float(gd.A_drop1_over_first_clip.max()),
            "grid_C_improve_min": float(grid.C_best_improve.min()), "grid_C_improve_max": float(grid.C_best_improve.max()),
            "grid_C_bestgain_min": float(grid.C_best_gain.min()), "grid_C_bestgain_max": float(grid.C_best_gain.max()),
            "grid_B_diff_min": float(grid.B2_minus_B1_best.min()), "grid_B_diff_max": float(grid.B2_minus_B1_best.max())}

    out = {"headline": {**kn, **gsum}, "selected_gains": sel.to_dict("records"), "by_bits": bits.to_dict("records")}
    json.dump(out, open(RES / "a1145_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：録音の例（声と雑音）
    fig, ax = plt.subplots(figsize=(9, 3.6))
    tt = np.arange(N) / SR; m = tt < 5
    ax.plot(tt[m], (v + n)[m], color=BLUE, lw=0.4, label="録音（声＋雑音）")
    ax.plot(tt[m], n[m], color=ORANGE, lw=0.4, label="雑音だけ")
    ax.axhline(10 ** (PEAK / 20), color=GRAY, ls=":", lw=1); ax.axhline(-10 ** (PEAK / 20), color=GRAY, ls=":", lw=1)
    ax.set_xlabel("時刻（秒、はじめの5秒）"); ax.set_ylabel("振れ幅（上限1.0）")
    ax.set_title(f"架空の録音（声のいちばん大きい点 {PEAK:.0f} dB、声と雑音の差 {kn['A_at_0']:.2f} dB）")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    save(fig, "a1145_recording.png", SRC)

    # 図2：音量を上げたときの声と雑音の差
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(sw.gain_db, sw.A_in_recording, color=BLUE, lw=2, label="A 録音の中の雑音")
    ax.plot(sw.gain_db, sw.B1_save_then_gain, color=GREEN, lw=1.6, label="B 8ビットで保存してから上げる")
    ax.plot(sw.gain_db, sw.B2_gain_then_save, color=GREEN, lw=1.6, ls="--", label="B 上げてから8ビットで保存")
    ax.plot(sw.gain_db, sw.C_room_after, color=ORANGE, lw=2, label=f"C 聞く場所の雑音（{ROOM_DB:.0f} dB）")
    ax.axvline(kn["first_clip_gain"], color=GRAY, ls=":", lw=1)
    ax.text(kn["first_clip_gain"] + 0.3, ax.get_ylim()[0] + 1, "ここから上限で切れ始める", fontsize=8, color=INK)
    ax.set_xlabel("録音全体の音量を上げた量（dB）"); ax.set_ylabel("声と雑音の差（dB）"); ax.set_xlim(0, 30)
    ax.set_title("差が広がるかは、雑音が上げる前に入るか後に入るかで決まる")
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    save(fig, "a1145_gain.png", SRC)

    # 図3：27通りの、切れ始めから差が1 dB 縮むまでの余裕と、聞く場所の雑音での伸び
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    lab = [f"{int(r.voice_peak_db)}/{int(r.true_snr_db)}/{int(r.syllable_spread_db)}" for r in grid.itertuples()]
    xi = np.arange(len(grid))
    axs[0].bar(xi, grid.A_drop1_over_first_clip.fillna(0), color=BLUE)
    axs[0].set_xticks(xi); axs[0].set_xticklabels(lab, rotation=90, fontsize=6)
    axs[0].set_ylabel("切れ始めから、差が1 dB 縮むまでに上げた量（dB）"); axs[0].set_ylim(0, None)
    axs[0].set_title("A：切れ始めてから差が縮むまで", fontsize=11)
    axs[0].text(4, 0.5, "左の9通りは、30 dB 上げても\n差が1 dB 縮まなかった", ha="center", fontsize=8, color=INK)
    axs[0].set_xlabel("声のいちばん大きい点/本当の差/音節の散らばり（dB）", fontsize=8)
    axs[1].bar(xi, grid.C_best_improve, color=ORANGE)
    axs[1].set_xticks(xi); axs[1].set_xticklabels(lab, rotation=90, fontsize=6)
    axs[1].set_ylabel("差がいちばん広がった量（dB）"); axs[1].set_ylim(0, None)
    axs[1].set_title("C：聞く場所の雑音に対して広がった量", fontsize=11)
    axs[1].set_xlabel("声のいちばん大きい点/本当の差/音節の散らばり（dB）", fontsize=8)
    fig.tight_layout()
    save(fig, "a1145_grid.png", SRC)

    head = {**kn, **gsum, "run_sec": round(time.time() - t0, 1)}
    print(json.dumps(head, ensure_ascii=False, indent=1)); print(sel.to_string()); print(bits); print(grid.to_string())


if __name__ == "__main__":
    main()
