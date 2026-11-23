"""1119 命中と会心が関係しているのに別々の確率と見て掛けると、ダメージの見込みはどれだけずれるのか？（架空のデータ）

架空のゲームの1回の攻撃。命中の判定と会心の判定があり、会心なら与えるダメージが倍率ぶん大きくなる。外れればダメージは0。
表に書いた命中率と会心率（どちらも攻撃1回ごとの判定の確率）を別々の確率と見て掛けた見込み
  見込み＝基本のダメージ×命中率×（1＋（倍率−1）×会心率）
と、作り方によって命中と会心が関係しているときの本当の1回あたりのダメージ
  本当＝基本のダメージ×（命中率＋（倍率−1）×命中して会心になる確率）
を比べる。命中と会心の決め方（作り方）を変え、乱数で攻撃を作って確かめる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1119
SRC = "架空のゲームの攻撃（作成者が置いた命中率・会心率・決め方からの乱数、seed 1119）"
BASE_DMG = 100.0
P_HIT, P_CRIT, MULT = 0.8, 0.2, 2.0
N_ATT = 1_000_000          # 作り方ごとの攻撃の回数
N_LOG, LOG_REPS = 1000, 2000   # 記録の長さと、記録を作り直す回数
# 敵の状態で命中と会心がそろって動く作り（状態の割合0.3、表の命中率・会心率は0.8・0.2のまま）
S_OPEN = 0.3
OPEN = {"hit": 0.98, "crit": 0.45}      # 敵の隙：当たりやすく会心も出やすい
FAR = {"hit": 0.50, "crit": 0.40}       # 遠い間合い：当たりにくいが会心は出やすい
GRID_PH = [0.6, 0.75, 0.9]
GRID_PC = [0.1, 0.25, 0.4]
GRID_M = [1.5, 2.5, 3.5]
GRID_LAM = [-1.0, -0.5, 0.0, 0.5, 1.0]  # 1つの乱数で決める攻撃の割合（＋は会心が命中の中、−は会心が外れの側から）
UP = 0.1                                # 強化：命中か会心を10ポイント上げる


def r(x, d=3):
    return round(float(x), d)


def joint_formula(ph, pc, lam):
    """命中して会心になる確率。lam の割合の攻撃は1つの乱数で決め、残りは別々の乱数で決める"""
    ind = ph * pc
    if lam >= 0:
        return ind + lam * (min(ph, pc) - ind)
    return ind + (-lam) * (max(0.0, ph + pc - 1.0) - ind)


def exp_true(ph, pc, m, lam, base=BASE_DMG):
    return base * (ph + (m - 1) * joint_formula(ph, pc, lam))


def exp_indep(ph, pc, m, base=BASE_DMG):
    return base * ph * (1 + (m - 1) * pc)


def latent_params(state, ph=P_HIT, pc=P_CRIT, s=S_OPEN):
    """状態の割合 s のとき、表の命中率・会心率（全体の割合）が ph・pc になるよう、残りの状態の値を決める"""
    h0 = (ph - s * state["hit"]) / (1 - s)
    c0 = (pc - s * state["crit"]) / (1 - s)
    return h0, c0


def simulate(rng, kind, n, ph=P_HIT, pc=P_CRIT, m=MULT):
    """攻撃 n 回を作る。命中（0/1）・会心（0/1、判定した結果）・ダメージを返す"""
    if kind == "indep":
        hit = rng.random(n) < ph
        crit = rng.random(n) < pc
    elif kind == "same_low":            # 1つの乱数の小さい側で命中も会心も決める（会心は必ず命中の中）
        u = rng.random(n)
        hit, crit = u < ph, u < pc
    elif kind == "same_high":           # 1つの乱数で、命中は小さい側・会心は大きい側（会心は外れと重なりやすい）
        u = rng.random(n)
        hit, crit = u < ph, u >= 1 - pc
    elif kind in ("open", "far"):
        st = OPEN if kind == "open" else FAR
        h0, c0 = latent_params(st, ph, pc)
        inst = rng.random(n) < S_OPEN
        hp = np.where(inst, st["hit"], h0)
        cp = np.where(inst, st["crit"], c0)
        hit = rng.random(n) < hp
        crit = rng.random(n) < cp
    else:
        raise ValueError(kind)
    dmg = np.where(hit, BASE_DMG * np.where(crit, m, 1.0), 0.0)
    return hit, crit, dmg


KINDS = [
    ("indep", "①命中と会心を別々の乱数で決める"),
    ("open", "②敵の隙で両方が上がる（3割の攻撃）"),
    ("far", "③遠い間合いで命中が下がり会心が上がる（3割）"),
    ("same_low", "④1つの乱数の同じ側で両方を決める"),
    ("same_high", "⑤1つの乱数の逆の側で会心を決める"),
]


def joint_of(kind, ph=P_HIT, pc=P_CRIT):
    if kind == "indep":
        return ph * pc
    if kind == "same_low":
        return min(ph, pc)
    if kind == "same_high":
        return max(0.0, ph + pc - 1)
    st = OPEN if kind == "open" else FAR
    h0, c0 = latent_params(st, ph, pc)
    return S_OPEN * st["hit"] * st["crit"] + (1 - S_OPEN) * h0 * c0


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ind = exp_indep(P_HIT, P_CRIT, MULT)

    # 1) 作り方ごと（基本の置き方）
    rows, samples = [], []
    for kind, label in KINDS:
        hit, crit, dmg = simulate(rng, kind, N_ATT)
        j = joint_of(kind)
        true_f = BASE_DMG * (P_HIT + (MULT - 1) * j)
        rows.append({
            "kind": kind, "label": label,
            "hit_rate_sim": r(hit.mean(), 4), "crit_rate_sim": r(crit.mean(), 4),
            "hit_and_crit_formula": r(j, 4), "hit_and_crit_sim": r((hit & crit).mean(), 4),
            "crit_given_hit_formula": r(j / P_HIT, 4), "crit_given_hit_sim": r((hit & crit).sum() / hit.sum(), 4),
            "expected_indep": r(ind, 2), "expected_true_formula": r(true_f, 2), "mean_damage_sim": r(dmg.mean(), 2),
            "gap_pct_formula": r((ind / true_f - 1) * 100, 2),
            "true_vs_indep_pct": r((true_f / ind - 1) * 100, 2),
        })
        d = pd.DataFrame({"kind": kind, "attack": np.arange(1, 501), "hit": hit[:500].astype(int),
                          "crit_roll": crit[:500].astype(int), "damage": dmg[:500]})
        samples.append(d)
    base = pd.DataFrame(rows)
    base.to_csv(RES / "kinds_base.csv", index=False)
    pd.concat(samples).to_csv(DATA / "attacks_sample.csv", index=False)

    # 2) 記録から見込む：当たった攻撃のうち会心だった割合×命中率、と、表の会心率で掛けた見込み
    log_rows = []
    for kind, label in KINDS:
        true_f = BASE_DMG * (P_HIT + (MULT - 1) * joint_of(kind))
        est = np.empty(LOG_REPS)
        for i in range(LOG_REPS):
            hit, crit, dmg = simulate(rng, kind, N_LOG)
            ph_hat = hit.mean()
            cgh = (hit & crit).sum() / max(hit.sum(), 1)       # 当たった攻撃のうち会心の割合（記録に出るのは命中した会心だけ）
            est[i] = BASE_DMG * ph_hat * (1 + (MULT - 1) * cgh)
        rel = (est / true_f - 1) * 100
        log_rows.append({"kind": kind, "label": label, "true": r(true_f, 2),
                         "est_mean": r(est.mean(), 2), "rel_err_p05": r(np.percentile(rel, 5), 2),
                         "rel_err_p95": r(np.percentile(rel, 95), 2),
                         "indep_rel_err": r((ind / true_f - 1) * 100, 2)})
    logs = pd.DataFrame(log_rows)
    logs.to_csv(RES / "log_estimate.csv", index=False)

    # 3) 置き方を変えると（27通り×1つの乱数で決める攻撃の割合5通り、式）と、強化の選び方
    grid = []
    for ph in GRID_PH:
        for pc in GRID_PC:
            for m in GRID_M:
                e_ind = exp_indep(ph, pc, m)
                gi_hit = exp_indep(min(ph + UP, 1.0), pc, m) - e_ind
                gi_crit = exp_indep(ph, pc + UP, m) - e_ind
                for lam in GRID_LAM:
                    e_tr = exp_true(ph, pc, m, lam)
                    gt_hit = exp_true(min(ph + UP, 1.0), pc, m, lam) - e_tr
                    gt_crit = exp_true(ph, pc + UP, m, lam) - e_tr
                    pick_ind = "hit" if gi_hit > gi_crit + 1e-9 else ("crit" if gi_crit > gi_hit + 1e-9 else "tie")
                    pick_tr = "hit" if gt_hit > gt_crit + 1e-9 else ("crit" if gt_crit > gt_hit + 1e-9 else "tie")
                    grid.append({"p_hit": ph, "p_crit": pc, "mult": m, "lam": lam,
                                 "expected_indep": r(e_ind, 3), "expected_true": r(e_tr, 3),
                                 "true_vs_indep_pct": r((e_tr / e_ind - 1) * 100, 2),
                                 "gain_hit_indep": r(gi_hit, 3), "gain_crit_indep": r(gi_crit, 3),
                                 "gain_hit_true": r(gt_hit, 3), "gain_crit_true": r(gt_crit, 3),
                                 "pick_indep": pick_ind, "pick_true": pick_tr,
                                 "pick_wrong": int(pick_ind != pick_tr),
                                 "loss_if_indep_pick": r(max(gt_hit, gt_crit) - (gt_hit if pick_ind == "hit" else gt_crit), 3)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # 乱数での確かめ（格子の中から、各 lam で1つ、10万回）
    chk = []
    for lam in GRID_LAM:
        ph, pc, m = 0.75, 0.25, 2.5
        n = 200_000
        same = rng.random(n) < abs(lam)
        u = rng.random(n)
        h_ind, c_ind = rng.random(n) < ph, rng.random(n) < pc
        if lam >= 0:
            h_s, c_s = u < ph, u < pc
        else:
            h_s, c_s = u < ph, u >= 1 - pc
        hit = np.where(same, h_s, h_ind)
        crit = np.where(same, c_s, c_ind)
        dmg = np.where(hit, BASE_DMG * np.where(crit, m, 1.0), 0.0)
        chk.append({"lam": lam, "formula": r(exp_true(ph, pc, m, lam), 2), "sim": r(dmg.mean(), 2)})
    chk_df = pd.DataFrame(chk)

    by_lam = g.groupby("lam").agg(gap_min=("true_vs_indep_pct", "min"), gap_max=("true_vs_indep_pct", "max"),
                                  wrong=("pick_wrong", "sum"), n=("pick_wrong", "size"),
                                  loss_max=("loss_if_indep_pick", "max")).reset_index()
    nz = g[g.lam != 0]
    main_json = {
        "settings": {"base_damage": BASE_DMG, "p_hit": P_HIT, "p_crit": P_CRIT, "mult": MULT, "n_attacks": N_ATT,
                     "state_share": S_OPEN, "open_state": OPEN, "far_state": FAR,
                     "open_other": [r(x, 4) for x in latent_params(OPEN)], "far_other": [r(x, 4) for x in latent_params(FAR)],
                     "log_len": N_LOG, "log_reps": LOG_REPS, "grid_p_hit": GRID_PH, "grid_p_crit": GRID_PC,
                     "grid_mult": GRID_M, "grid_lam": GRID_LAM, "upgrade": UP, "seed": SEED},
        "expected_indep": r(ind, 2),
        "kinds": rows,
        "kinds_sim_maxdiff": r((base.expected_true_formula - base.mean_damage_sim).abs().max(), 2),
        "log_estimate": log_rows,
        "grid_by_lam": [{k: (r(v, 3) if isinstance(v, float) else int(v)) for k, v in rec.items()} for rec in by_lam.to_dict("records")],
        "grid_nonzero_gap_min": r(nz.true_vs_indep_pct.min(), 2),
        "grid_nonzero_gap_max": r(nz.true_vs_indep_pct.max(), 2),
        "grid_nonzero_wrong": int(nz.pick_wrong.sum()), "grid_nonzero_n": int(len(nz)),
        "grid_lam0_wrong": int(g[g.lam == 0].pick_wrong.sum()),
        "grid_nonzero_flip": int(((nz.pick_indep != nz.pick_true) & (nz.pick_indep != "tie") & (nz.pick_true != "tie")).sum()),
        "grid_nonzero_tie_true": int(((nz.pick_true == "tie") & (nz.pick_indep != "tie")).sum()),
        "grid_nonzero_tie_indep": int(((nz.pick_indep == "tie") & (nz.pick_true != "tie")).sum()),
        "grid_flip_by_lam": {str(l): int(((d.pick_indep != d.pick_true) & (d.pick_indep != "tie") & (d.pick_true != "tie")).sum()) for l, d in g.groupby("lam")},
        "grid_nonzero_loss_max": r(nz.loss_if_indep_pick.max(), 2),
        "grid_flip_indep_hit_true_crit": int(((nz.pick_indep == "hit") & (nz.pick_true == "crit")).sum()),
        "grid_flip_indep_crit_true_hit": int(((nz.pick_indep == "crit") & (nz.pick_true == "hit")).sum()),
        "grid_sim_check": chk,
        "grid_sim_check_maxdiff": r((chk_df.formula - chk_df.sim).abs().max(), 2),
    }
    with open(RES / "a1119_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：作り方ごとの1回あたりのダメージ（掛けた見込み96と本当）
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    y = np.arange(len(KINDS))[::-1]
    ax.barh(y, base.expected_true_formula, color=[GRAY, BLUE, ORANGE, BLUE, ORANGE], height=0.6)
    ax.axvline(ind, color=INK, ls="--", lw=1.2)
    ax.text(ind, len(KINDS) - 0.35, f"  別々と見て掛けた見込み {ind:.0f}", fontsize=9, color=INK, va="bottom")
    for yy, v in zip(y, base.expected_true_formula):
        ax.text(max(v, ind) + 1.5, yy, f"{v:.2f}", va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(base.label, fontsize=9)
    ax.set_xlim(0, 120)
    ax.set_ylim(-0.6, len(KINDS) - 0.1)
    ax.set_xlabel("1回の攻撃あたりのダメージ（本当、式）")
    ax.set_title("命中80%・会心20%・会心2倍でも、決め方で1回あたりは80〜100")
    save(fig, "a1119_kinds.png", SRC)

    # 図2：置き方27通りで、本当÷見込み（1つの乱数で決める攻撃の割合ごと）
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for (ph, pc, m), d in g.groupby(["p_hit", "p_crit", "mult"]):
        ax.plot(d.lam, d.true_vs_indep_pct, color=LIGHT, lw=1, marker="o", ms=3)
    bl = g[(g.p_hit == 0.75) & (g.p_crit == 0.25) & (g.mult == 2.5)]
    ax.plot(bl.lam, bl.true_vs_indep_pct, color=BLUE, lw=2, marker="o", label="命中75%・会心25%・2.5倍")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(GRID_LAM)
    ax.set_xticklabels(["−1\n（全部が逆の側）", "−0.5", "0\n（別々）", "0.5", "1\n（全部が同じ側）"], fontsize=9)
    ax.set_xlabel("1つの乱数で決める攻撃の割合")
    ax.set_ylabel("本当が見込みより何%大きいか")
    ax.set_title("置き方27通り：逆の側では下に、同じ側では上にずれる")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1119_grid.png", SRC)

    # 図3：強化の選び方（命中+10ポイントと会心+10ポイントの伸びの差）
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    dx = nz.gain_hit_indep - nz.gain_crit_indep
    dy = nz.gain_hit_true - nz.gain_crit_true
    ok = nz.pick_wrong == 0
    ax.scatter(dx[ok], dy[ok], s=18, color=GRAY, label="選ぶ強化が同じ")
    ax.scatter(dx[~ok], dy[~ok], s=24, color=ORANGE, label="選ぶ強化が入れかわる・並ぶ")
    ax.axhline(0, color=INK, lw=0.8)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("掛けた見込みでの（命中+10の伸び）−（会心+10の伸び）\n（1回の攻撃あたりのダメージ）")
    ax.set_ylabel("本当の（命中+10の伸び）−（会心+10の伸び）")
    ax.set_title(f"強化の選び方：{int(nz.pick_wrong.sum())}/{len(nz)}通りで見込みと本当が食い違う")
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    save(fig, "a1119_upgrade.png", SRC)

    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
