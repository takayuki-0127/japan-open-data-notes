"""作り直しの決まりを3つ比べる：作り直さない／13週ごとに作り直す／管理図が鳴ったら作り直す（直近8週の曜日平均）。
80週目から需要が +10% 変わる場合と、変わらない場合（作り直しの空振りの損）を 1,000回ずつ。seed 296"""
import json, numpy as np
from common import RES
from a296_sim import demand, fit, W_TRAIN, W_BASE, W_BREAK, W_END

def run(rng, shift, strategy, refit_weeks=8):
    y = demand(rng, shift); wk = y.reshape(-1, 7)
    m = fit(y, 1, W_TRAIN)
    base = (wk[W_TRAIN:W_BASE].sum(1) - m.sum()) / m.sum(); mu, sd = base.mean(), base.std(ddof=1)
    zs, errs, refits, last = [], [], [], W_BASE
    for w in range(W_BASE, W_END):  # w は0始まりの週番号
        b = (wk[w].sum() - m.sum()) / m.sum(); errs.append(abs(b)); z = (b - mu) / sd; zs.append(z)
        h = np.array(zs[-4:])
        alarm = abs(z) > 3 or (len(h) >= 3 and ((h[-3:] > 2).sum() >= 2 or (h[-3:] < -2).sum() >= 2)) or (len(h) >= 4 and ((h > 1).all() or (h < -1).all()))
        due = (strategy == "13週ごと" and (w + 1 - last) >= 13) or (strategy == "鳴ったら" and alarm)
        if due and w + 1 - refit_weeks >= 0:
            m = wk[w + 1 - refit_weeks:w + 1].mean(0); refits.append(w + 1); last = w + 1; zs = []
            mu = 0.0  # 作り直した後は誤差の中心を0とみなす（ばらつきは元の幅を使う）
    errs = np.array(errs); idx = np.arange(W_BASE + 1, W_END + 1)
    return {"mape_after": float(errs[idx >= W_BREAK].mean()), "mape_first8": float(errs[(idx >= W_BREAK) & (idx < W_BREAK + 8)].mean()), "refits": len(refits)}

out = {}
for shift in [0.10, 0.0]:
    for strat in ["作り直さない", "13週ごと", "鳴ったら"]:
        rng = np.random.default_rng(2960 + int(shift * 100))
        r = [run(rng, shift, strat) for _ in range(1000)]
        out[f"{shift:+.0%} {strat}"] = {"weekly_abs_error_after_break_pct": round(100 * np.mean([x["mape_after"] for x in r]), 2),
                                       "first8_weeks_pct": round(100 * np.mean([x["mape_first8"] for x in r]), 2),
                                       "refits_per_run": round(float(np.mean([x["refits"] for x in r])), 2)}
json.dump(out, open(RES / "retrain.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
