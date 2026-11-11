# 02 整形：シミュレーションに使う「公開データのばらつき」を作る
# - 割合の指標の基準値：家計消費状況調査「ネットショッピング利用世帯の割合」（2024年平均）
# - 金額の指標の形：国民生活基礎調査「所得金額階級別の世帯の割合」（2024年）を階級内一様＋パレートでつなぎ、
#   家計消費状況調査の「ネットショッピングの支出額」（2024年平均、利用世帯あたり）に平均を合わせる
import json, numpy as np, pandas as pd
from pathlib import Path
D = Path(__file__).resolve().parents[1] / "data"

net = pd.read_csv(D / "f185_net_shopping_2023_2025.csv")
share24 = float(net.query("year==2024 and series=='share'")["annual"].iloc[0]) / 10000      # 1万分比 → 割合
spend24 = float(net.query("year==2024 and series=='spend22'")["annual"].iloc[0])           # 円／月（全世帯平均）
spend_user = spend24 / share24                                                              # 利用世帯あたり

b = pd.read_csv(D / "f173_income_bins.csv").query("year==2024").copy()
b["share"] = b["share"] / b["share"].sum()
# パレートの α：1,500万円と2,000万円の生存割合から
s1500 = b.loc[b.lo >= 1500, "share"].sum(); s2000 = b.loc[b.lo >= 2000, "share"].sum()
alpha = float(np.log(s1500 / s2000) / np.log(2000 / 1500))

def sampler(rng, n):
    """所得の形の分布から n 個引く（万円）"""
    k = rng.choice(len(b), size=n, p=b["share"].values)
    lo = b["lo"].values[k]; hi = b["hi"].values[k]
    u = rng.random(n)
    x = lo + u * (np.where(np.isinf(hi), lo + 1, hi) - lo)
    top = np.isinf(hi)
    x[top] = 2000 * (1 - u[top]) ** (-1 / alpha)   # パレート
    return x

rng = np.random.default_rng(20261111)
x = sampler(rng, 2_000_000)
scale = spend_user / x.mean()
meta = {"share_2024": share24, "spend_all_2024": spend24, "spend_user_2024": spend_user,
        "pareto_alpha": alpha, "scale": scale,
        "user_mean": float((x * scale).mean()), "user_sd": float((x * scale).std()),
        "user_cv": float(x.std() / x.mean()),
        "p50_user": float(np.median(x * scale)), "p99_user": float(np.quantile(x * scale, .99))}
z = np.where(rng.random(len(x)) < share24, x * scale, 0.0)
meta.update({"all_mean": float(z.mean()), "all_sd": float(z.std()), "all_cv": float(z.std() / z.mean())})
json.dump(meta, open(D / "metric_params.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False, indent=1))
