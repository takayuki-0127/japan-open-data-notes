"""クラスタ数ごとのブートストラップ安定性（再標本で作った k-means と全体の k-means の一致度 ARI）。"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from common import DATA, RES, SEED

P = pd.read_csv(DATA / "pcs.csv").values
rng = np.random.default_rng(SEED)
B = 50
rows = []
for k in range(2, 11):
    base = KMeans(k, n_init=20, random_state=SEED).fit(P).labels_
    aris = []
    for b in range(B):
        idx = rng.integers(0, len(P), len(P))
        km = KMeans(k, n_init=5, random_state=b).fit(P[idx])
        aris.append(adjusted_rand_score(base, km.predict(P)))
    rows.append({"k": k, "ari_mean": np.mean(aris), "ari_p10": np.percentile(aris, 10), "ari_p90": np.percentile(aris, 90)})
    print(rows[-1])
pd.DataFrame(rows).to_csv(RES / "k_stability.csv", index=False)
