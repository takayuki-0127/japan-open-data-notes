"""標準化 → PCA → クラスタ数の検討（k-means のシルエット、ガウス混合の BIC）。"""
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from common import DATA, RES, SEED

d = pd.read_csv(DATA / "indicators.csv")
X = d.iloc[:, 4:]
lo, hi = X.quantile(0.01), X.quantile(0.99)
Xw = X.clip(lo, hi, axis=1)
Z = StandardScaler().fit_transform(Xw)
pd.DataFrame(Z, columns=X.columns).to_csv(DATA / "z.csv", index=False, encoding="utf-8-sig")

pca = PCA(random_state=SEED).fit(Z)
ev = pca.explained_variance_ratio_
cum = ev.cumsum()
npc = int(np.searchsorted(cum, 0.80) + 1)
S = pca.transform(Z)
pd.DataFrame(S[:, :npc], columns=[f"PC{i+1}" for i in range(npc)]).to_csv(DATA / "pcs.csv", index=False)
load = pd.DataFrame(pca.components_[:5].T, index=X.columns, columns=[f"PC{i+1}" for i in range(5)])
load.to_csv(RES / "pca_loadings.csv", encoding="utf-8-sig")
pd.DataFrame({"pc": np.arange(1, len(ev) + 1), "ratio": ev, "cum": cum}).to_csv(RES / "pca_variance.csv", index=False)
print("PC数(80%)", npc, "PC1-3", ev[:3].round(3))
for k in range(3):
    s = load[f"PC{k+1}"].sort_values()
    print(f"PC{k+1} -:", list(s.index[:5]), "\n      +:", list(s.index[-5:]))

P = S[:, :npc]
rows = []
for k in range(2, 13):
    km = KMeans(k, n_init=20, random_state=SEED).fit(P)
    sil = silhouette_score(P, km.labels_)
    gm = GaussianMixture(k, covariance_type="full", n_init=3, random_state=SEED).fit(P)
    rows.append({"k": k, "silhouette": sil, "inertia": km.inertia_, "gmm_bic": gm.bic(P)})
r = pd.DataFrame(rows)
r.to_csv(RES / "k_selection.csv", index=False)
print(r.round(3).to_string())
json.dump({"n_pc": npc, "pc_var": ev[:npc].round(4).tolist(), "n_ind": X.shape[1], "n_muni": len(d)}, open(RES / "pca_summary.json", "w"), ensure_ascii=False)
