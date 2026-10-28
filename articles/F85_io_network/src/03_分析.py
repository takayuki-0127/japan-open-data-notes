"""F85 分析：産業連関表を「産業のネットワーク」として読む。
python src/03_分析.py → results/*.csv, results/summary.json

1. 後方連関（Rasmussen：レオンチェフ逆行列の列和）と前方連関（Ghosh 逆行列の行和）、キーセクター
2. ネットワークの中心性（中間取引の流れを重みにした PageRank・固有ベクトル・強度・媒介中心性）
3. Domar ウエイト（国内生産額÷GDP）＝その産業の生産性ショックが GDP に効く大きさ（Hulten の定理）と集中度
4. 仮想的抽出法（その産業との取引を消すと、ほかの産業の生産がどれだけ減るか）
5. ショックの伝わり方（最終需要1兆円減の波及先、付加価値10%減の下流への波及＝Ghosh）
6. 頑健性：中心性の指標どうし、2015年表、2桁コードで統合した39部門、閉鎖型、帰属家賃・分類不明を除く
"""
import json
import numpy as np, pandas as pd, networkx as nx
from scipy.stats import spearmanr
from common import RES, load_table, matrices

SEED = 0
EXCL = ["553", "691"]  # 帰属家賃・分類不明（取引の実体が薄い）


def short(n):
    n = str(n)
    for a, b in [("（別掲を除く。）", ""), ("（石油化学系基礎製品・合成樹脂を除く。）", ""), ("（医薬品を除く。）", ""),
                 ("（自家輸送を除く。）", ""), ("（帰属家賃）", "（帰属）"), ("・同附属装置", ""), ("・同附属品", ""),
                 ("・同修理", ""), ("他に分類されない会員制団体", "会員制団体"), ("その他の対事業所サービス", "対事業所サービス他"),
                 ("その他の対個人サービス", "対個人サービス他"), ("非鉄金属製錬・精製", "非鉄製錬"), ("電子応用装置・電気計測器", "電子応用装置"),
                 ("インターネット附随サービス", "ネット附随サービス"), ("映像・音声・文字情報制作", "映像・文字情報制作")]:
        n = n.replace(a, b)
    return n


def domestic_Z(t, m=None):
    """中間取引のうち国内で生産された分（競争輸入型の表なので、行ごとに輸入係数の分を除く）。"""
    if m is None:
        m = matrices(t)
    return (1 - m["m"])[:, None] * t["Z"]


def linkages(t, model="comp"):
    m = matrices(t)
    B = m["B"] if model == "comp" else m["B0"]
    X = t["X"]; Z = domestic_Z(t, m)
    BL = B.sum(0); BL = BL / BL.mean()
    Bc = Z / np.where(X > 0, X, 1)[:, None]          # 配分係数（行ごと）
    G = np.linalg.inv(np.eye(len(X)) - Bc)            # Ghosh 逆行列
    FL = G.sum(1); FL = FL / FL.mean()
    return BL, FL, B, G, m


def centralities(t):
    Z = domestic_Z(t).copy(); np.fill_diagonal(Z, 0)
    n = len(Z)
    Gd = nx.DiGraph()
    for i in range(n):
        for j in range(n):
            if Z[i, j] > 0:
                Gd.add_edge(i, j, weight=Z[i, j], dist=1.0 / Z[i, j])
    # 供給者としての重要さ：買い手から売り手へ向かう流れで PageRank（よく買われる産業が高い）
    pr = nx.pagerank(Gd.reverse(copy=True), weight="weight", alpha=0.85)
    ev = nx.eigenvector_centrality_numpy(Gd.to_undirected(), weight="weight")
    btw = nx.betweenness_centrality(Gd, weight="dist", seed=SEED)
    out_s = Z.sum(1); in_s = Z.sum(0)
    return pd.DataFrame({"PageRank": [pr.get(i, 0) for i in range(n)],
                         "固有ベクトル": [ev.get(i, 0) for i in range(n)],
                         "媒介中心性": [btw.get(i, 0) for i in range(n)],
                         "販売の強度": out_s, "購入の強度": in_s})


def extraction(t, B, m):
    """仮想的抽出法：産業 j の中間取引（行と列）を国内から消したとき、j 以外の生産の減少率。"""
    A = m["A"]; M = m["M"]; I = m["I"]
    Ad = (I - M) @ A
    f = t["X"] - Ad @ t["X"]                         # 競争輸入型の最終需要（国内生産で満たす分）
    X0 = B @ f
    out = []
    for j in range(len(f)):
        Aj = Ad.copy(); Aj[j, :] = 0; Aj[:, j] = 0
        Xj = np.linalg.solve(I - Aj, f)
        mask = np.ones(len(f), bool); mask[j] = False
        bk = Ad.copy(); bk[:, j] = 0; Xb = np.linalg.solve(I - bk, f)
        fw = Ad.copy(); fw[j, :] = 0; Xf = np.linalg.solve(I - fw, f)
        out.append(((X0 - Xj)[mask].sum() / X0[mask].sum(),
                    (X0 - Xb)[mask].sum() / X0[mask].sum(),
                    (X0 - Xf)[mask].sum() / X0[mask].sum()))
    return np.array(out)


def analyze(t, model="comp", excl=()):
    keep = [i for i, s in enumerate(t["sec"]) if s not in excl]
    if excl:
        t = dict(t); idx = np.array(keep)
        for k in ["Z"]:
            t[k] = t[k][np.ix_(idx, idx)]
        for k in ["X", "W", "VA", "hh", "dom", "imp", "exp"]:
            t[k] = t[k][idx]
        t["sec"] = [t["sec"][i] for i in keep]; t["name"] = [t["name"][i] for i in keep]
    BL, FL, B, G, m = linkages(t, model)
    c = centralities(t)
    gdp = t["VA"].sum()
    dom = t["X"] / gdp; vas = t["VA"] / gdp
    df = pd.DataFrame({"部門コード": t["sec"], "部門": [short(n) for n in t["name"]],
                       "国内生産額_十億円": t["X"], "付加価値_十億円": t["VA"],
                       "後方連関": BL, "前方連関": FL, "Domar": dom, "付加価値シェア": vas})
    df = pd.concat([df, c], axis=1)
    df["キーセクター"] = (df["後方連関"] > 1) & (df["前方連関"] > 1)
    return df, B, G, m, t


def aggregate39(t):
    g = sorted(set(s[:2] for s in t["sec"]))
    P = np.array([[1.0 if s[:2] == k else 0.0 for s in t["sec"]] for k in g])
    t2 = dict(t)
    t2["Z"] = P @ t["Z"] @ P.T
    for k in ["X", "W", "VA", "hh", "dom", "imp", "exp"]:
        t2[k] = P @ t[k]
    big = {}
    for s, n, x in zip(t["sec"], t["name"], t["X"]):
        if s[:2] not in big or x > big[s[:2]][1]:
            big[s[:2]] = (n, x)
    t2["sec"] = [k + "0" for k in g]
    t2["name"] = [(short(big[k][0]).rstrip("他") + ("など" if sum(1 for s in t["sec"] if s[:2] == k) > 1 else "")) for k in g]
    return t2, P


def main():
    np.random.seed(SEED)
    t = load_table("2020")
    df, B, G, m, _ = analyze(t)
    ext = extraction(t, B, m)
    df["抽出_全体"] = ext[:, 0]; df["抽出_後方"] = ext[:, 1]; df["抽出_前方"] = ext[:, 2]
    df.to_csv(RES / "sectors_2020.csv", index=False, encoding="utf-8-sig")

    # 取引の集中：中間取引の上位何本で全体の8割か
    Zd = domestic_Z(t, m)
    Z = Zd.copy(); np.fill_diagonal(Z, 0)
    w = np.sort(Z[Z > 0])[::-1]
    cum = np.cumsum(w) / w.sum()
    n80 = int(np.searchsorted(cum, 0.8) + 1)
    selfshare = float(np.trace(Zd) / Zd.sum())

    # Domar と Hulten、集中度（Gabaix）
    gdp = t["VA"].sum()
    dom = t["X"] / gdp; vas = t["VA"] / gdp
    H_dom = float(np.sqrt((dom ** 2).sum())); H_va = float(np.sqrt((vas ** 2).sum()))
    H_eq = float(1 / np.sqrt(len(dom)))

    # ショック1：最終需要が1兆円減ったときの国内生産の減少（競争輸入型）と、その行き先
    I = m["I"]; M = m["M"]
    shocks = {}
    for s in ["351", "353", "321", "411", "511", "641", "672", "461"]:
        j = t["sec"].index(s)
        e = np.zeros(len(t["X"])); e[j] = 1000.0                 # 十億円
        dX = B @ ((I - M) @ e)
        own = dX[j]; tot = dX.sum()
        top = np.argsort(-np.where(np.arange(len(dX)) == j, 0, dX))[:3]
        shocks[s] = dict(部門=short(t["name"][j]), 生産減_十億円=round(float(tot), 1), 自部門=round(float(own), 1),
                         他部門の割合=round(float((tot - own) / tot), 3),
                         波及先上位=[(short(t["name"][k]), round(float(dX[k]), 1)) for k in top])
    # ショック2：付加価値（供給）が10%減ったとき、下流の生産の減少（Ghosh、相対価格は固定という強い仮定）
    supply = {}
    for s in ["321", "353", "461", "211", "262", "511", "593"]:
        j = t["sec"].index(s)
        dv = np.zeros(len(t["X"])); dv[j] = 0.10 * t["VA"][j]
        dX = dv @ G
        supply[s] = dict(部門=short(t["name"][j]), 付加価値減_十億円=round(float(dv[j]), 1),
                         生産減_十億円=round(float(dX.sum()), 1), 倍率=round(float(dX.sum() / dv[j]), 2),
                         他部門の割合=round(float((dX.sum() - dX[j]) / dX.sum()), 3))

    # 頑健性
    rob = {}
    cols = ["後方連関", "前方連関", "Domar", "PageRank", "固有ベクトル", "媒介中心性", "販売の強度", "抽出_全体"]
    cm = df[cols].corr(method="spearman")
    cm.to_csv(RES / "rank_corr_measures.csv", encoding="utf-8-sig")
    # 2015年表
    t5 = load_table("2015")
    d5, *_ = analyze(t5)
    mg = df.merge(d5[["部門コード", "後方連関", "前方連関", "Domar", "PageRank", "キーセクター"]], on="部門コード", suffixes=("", "_2015"))
    rob["2015年表との順位相関"] = {k: round(float(spearmanr(mg[k], mg[k + "_2015"])[0]), 3) for k in ["後方連関", "前方連関", "Domar", "PageRank"]}
    rob["キーセクターの一致"] = {"両年": int((mg["キーセクター"] & mg["キーセクター_2015"]).sum()),
                                "2020のみ": int((mg["キーセクター"] & ~mg["キーセクター_2015"]).sum()),
                                "2015のみ": int((~mg["キーセクター"] & mg["キーセクター_2015"]).sum())}
    # 閉鎖型
    dc, *_ = analyze(t, model="closed")
    rob["閉鎖型との順位相関_後方連関"] = round(float(spearmanr(df["後方連関"], dc["後方連関"])[0]), 3)
    rob["閉鎖型のキーセクター数"] = int(dc["キーセクター"].sum())
    # 帰属家賃・分類不明を除く
    de, *_ = analyze(t, excl=EXCL)
    me = df.merge(de[["部門コード", "後方連関", "前方連関", "PageRank", "キーセクター"]], on="部門コード", suffixes=("", "_除"))
    rob["除外との順位相関"] = {k: round(float(spearmanr(me[k], me[k + "_除"])[0]), 3) for k in ["後方連関", "前方連関", "PageRank"]}
    rob["除外のキーセクター数"] = int(de["キーセクター"].sum())
    # 39部門に統合
    t39, P = aggregate39(t)
    d39, *_ = analyze(t39)
    agg = pd.DataFrame(P @ df[["Domar", "販売の強度"]].values, columns=["Domar_108合計", "販売_108合計"])
    d39 = pd.concat([d39, agg], axis=1)
    d39.to_csv(RES / "sectors_39.csv", index=False, encoding="utf-8-sig")
    rob["39部門_PageRank上位5"] = d39.nlargest(5, "PageRank")["部門"].tolist()
    rob["39部門_キーセクター数"] = int(d39["キーセクター"].sum())
    # 108部門の PageRank 上位10が、39部門でどの順位のグループに入るか
    top10 = df.nlargest(10, "PageRank")["部門コード"].str[:2]
    rk39 = d39.assign(g=d39["部門コード"].str[:2]).set_index("g")["PageRank"].rank(ascending=False)
    rob["108上位10の39部門での順位"] = [int(rk39[g]) for g in top10]
    # PageRank の減衰率
    Zr = domestic_Z(t, m).copy(); np.fill_diagonal(Zr, 0)
    Gd = nx.DiGraph()
    for i in range(len(Zr)):
        for j in range(len(Zr)):
            if Zr[i, j] > 0:
                Gd.add_edge(j, i, weight=Zr[i, j])
    rob["PageRank_alpha"] = {}
    for a in [0.5, 0.95]:
        p = nx.pagerank(Gd, weight="weight", alpha=a)
        rob["PageRank_alpha"][str(a)] = round(float(spearmanr(df["PageRank"], [p.get(i, 0) for i in range(len(Zr))])[0]), 3)
    pd.DataFrame([dict(項目=k, 値=json.dumps(v, ensure_ascii=False)) for k, v in rob.items()]).to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")

    key = df[df["キーセクター"]].sort_values("後方連関", ascending=False)
    summ = dict(
        部門数=len(df), 国内生産額_兆円=round(float(t["X"].sum() / 1000), 1), GDP_兆円=round(float(gdp / 1000), 1),
        中間取引の本数=int((Z > 0).sum()), 上位で8割の本数=n80, 自部門内取引の割合=round(selfshare, 3),
        キーセクター=key["部門"].tolist(), キーセクター数=int(len(key)),
        後方連関_上位5=df.nlargest(5, "後方連関")[["部門", "後方連関"]].round(3).values.tolist(),
        前方連関_上位5=df.nlargest(5, "前方連関")[["部門", "前方連関"]].round(3).values.tolist(),
        PageRank_上位10=df.nlargest(10, "PageRank")[["部門", "PageRank"]].round(4).values.tolist(),
        Domar_上位5=df.nlargest(5, "Domar")[["部門", "Domar"]].round(3).values.tolist(),
        Domar合計=round(float(dom.sum()), 3),
        Domar_付加価値シェア比_上位5=df.assign(r=df["Domar"] / df["付加価値シェア"]).query("付加価値シェア>0.002").nlargest(5, "r")[["部門", "r"]].round(2).values.tolist(),
        集中度_Domar=round(H_dom, 3), 集中度_付加価値=round(H_va, 3), 集中度_均等=round(H_eq, 3),
        抽出_上位8=df.nlargest(8, "抽出_全体")[["部門", "抽出_全体"]].round(4).values.tolist(),
        抽出と最終需要の順位相関=round(float(spearmanr(df["抽出_全体"], df["国内生産額_十億円"] - (domestic_Z(t, m).sum(1)))[0]), 3),
        需要ショック=shocks, 供給ショック=supply, 頑健性=rob,
        指標の順位相関_PageRank_Domar=round(float(cm.loc["PageRank", "Domar"]), 3),
        指標の順位相関_後方_前方=round(float(cm.loc["後方連関", "前方連関"]), 3),
        指標の順位相関_PageRank_媒介=round(float(cm.loc["PageRank", "媒介中心性"]), 3),
        指標の順位相関_PageRank_抽出=round(float(cm.loc["PageRank", "抽出_全体"]), 3),
    )
    json.dump(summ, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
