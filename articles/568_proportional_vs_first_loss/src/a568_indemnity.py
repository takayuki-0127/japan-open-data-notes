"""568 保険金額が実際の価値より小さい契約で、比例てん補と実損てん補の支払と純保険料を比べる（架空のデータ）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の物件と損害（作成者が乱数で作成、seed 568）。記事568"
FREQ = 0.02                     # 1年に損害が起きる確率（架空）
KS = np.round(np.arange(0.3, 1.001, 0.1), 2)

def losses(rng, n=200_000):
    """損害1件ごとの物件の価値（万円）と損害率"""
    v = rng.lognormal(np.log(3000) - .5 * .5 ** 2, .5, n)
    kind = rng.choice(3, n, p=[.85, .12, .03])
    dr = np.where(kind == 0, rng.beta(1, 12, n), np.where(kind == 1, rng.beta(2, 4, n), 1.0))
    return pd.DataFrame(dict(value=v, damage_ratio=dr, loss=v * dr, kind=kind))

def pay(L, k):
    s = k * L.value
    prop = L.loss * np.minimum(1, k)                # 比例てん補
    first = np.minimum(L.loss, s)                    # 実損てん補（保険金額まで）
    return s, prop, first

def main():
    rng = np.random.default_rng(568)
    L = losses(rng)
    L.sample(2000, random_state=568).round(4).to_csv(RES / "loss_sample_2000.csv", index=False)
    rows = []
    for k in KS:
        s, prop, first = pay(L, k)
        # 純保険料＝年の損害の確率×1件の平均支払。保険金額100万円あたりで見る
        rows.append(dict(k=k,
                         pure_prop=FREQ * prop.mean(), pure_first=FREQ * first.mean(),
                         rate_prop=FREQ * prop.sum() / s.sum() * 100, rate_first=FREQ * first.sum() / s.sum() * 100,
                         paid_share_prop=prop.sum() / L.loss.sum(), paid_share_first=first.sum() / L.loss.sum(),
                         full_paid_prop=float((prop >= L.loss - 1e-9).mean()), full_paid_first=float((first >= L.loss - 1e-9).mean()),
                         short_mean_prop=(L.loss - prop).mean(), short_mean_first=(L.loss - first).mean()))
    T = pd.DataFrame(rows); T.to_csv(RES / "by_insured_ratio.csv", index=False)

    # 損害率ごとの「損害のうち支払われる割合」（k=0.6）
    bins = np.array([0, .02, .05, .1, .2, .4, .6, .8, .999, 1.001])
    L["bin"] = pd.cut(L.damage_ratio, bins, include_lowest=True)
    s, prop, first = pay(L, .6)
    B = L.assign(prop=prop, first=first).groupby("bin", observed=True).agg(n=("loss", "size"), loss=("loss", "sum"), prop=("prop", "sum"), first=("first", "sum"))
    B["share_prop"] = B["prop"] / B["loss"]; B["share_first"] = B["first"] / B["loss"]; B["n_share"] = B["n"] / B["n"].sum()
    B = B.reset_index(); B["bin"] = B.bin.astype(str); B.to_csv(RES / "by_damage_ratio_k06.csv", index=False)

    # SQL：同じ損害から、k=0.6 の2通りの支払の合計を DuckDB で計算
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("loss_events", L[["value", "damage_ratio", "loss"]])
    q = con.execute((SQL / "a568_indemnity.sql").read_text()).df()
    q.to_csv(RES / "sql_k06.csv", index=False)
    py = dict(prop=float(prop.sum()), first=float(first.sum()))
    match = bool(np.isclose(q.paid_prop.iloc[0], py["prop"], rtol=1e-12) and np.isclose(q.paid_first.iloc[0], py["first"], rtol=1e-12))

    J = dict(n_losses=len(L), mean_damage_ratio=float(L.damage_ratio.mean()), share_total_loss=float((L.kind == 2).mean()),
             mean_loss=float(L.loss.mean()), table=T.round(5).to_dict("records"),
             by_damage_ratio_k06=B.round(4).to_dict("records"),
             sql_check=dict(python=py, sql=dict(prop=float(q.paid_prop.iloc[0]), first=float(q.paid_first.iloc[0])), match=match))
    json.dump(J, open(RES / "a568_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：保険金額100万円あたりの純保険料
    fig, ax = plt.subplots(figsize=(8, 4.3))
    ax.plot(T.k * 100, T.rate_prop * 1e4, "o-", color=BLUE, label="比例てん補")
    ax.plot(T.k * 100, T.rate_first * 1e4, "o-", color=ORANGE, label="実損てん補（保険金額まで）")
    for _, w in T[T.k.isin([.3, .6, 1.0])].iterrows():
        ax.annotate(f"{w.rate_first*1e4:,.0f}円", (w.k * 100, w.rate_first * 1e4), textcoords="offset points", xytext=(4, 6), fontsize=9, color=ORANGE)
        ax.annotate(f"{w.rate_prop*1e4:,.0f}円", (w.k * 100, w.rate_prop * 1e4), textcoords="offset points", xytext=(4, -14), fontsize=9, color=BLUE)
    ax.set_xlabel("付保割合（保険金額 ÷ 物件の価値、%）"); ax.set_ylabel("保険金額100万円あたりの純保険料（円）")
    ax.set_ylim(1800, 7600); ax.set_title("付保割合が低いほど、実損てん補は保険金額あたりで高くなる"); ax.legend()
    save(fig, "a568_rate.png", SRC)

    # 図2：損害のうち支払われる割合
    fig, ax = plt.subplots(figsize=(8, 4.3))
    ax.plot(T.k * 100, T.paid_share_prop * 100, "o-", color=BLUE, label="比例てん補")
    ax.plot(T.k * 100, T.paid_share_first * 100, "o-", color=ORANGE, label="実損てん補（保険金額まで）")
    ax.plot(T.k * 100, T.full_paid_first * 100, "o--", color=ORANGE, alpha=.6, label="実損てん補：全額支払われた損害の件数の割合")
    ax.set_xlabel("付保割合（%）"); ax.set_ylabel("%"); ax.set_ylim(0, 105)
    ax.set_title("損害の額のうち支払われる割合"); ax.legend(fontsize=8.5, loc="lower right")
    save(fig, "a568_paid_share.png", SRC)

    # 図3：損害率ごと（k=0.6）
    fig, ax = plt.subplots(figsize=(8, 4.3)); xs = np.arange(len(B)); w = .38
    ax.bar(xs - w / 2, B.share_prop * 100, w, color=BLUE, label="比例てん補")
    ax.bar(xs + w / 2, B.share_first * 100, w, color=ORANGE, label="実損てん補")
    labs = ["〜2%", "2〜5%", "5〜10%", "10〜20%", "20〜40%", "40〜60%", "60〜80%", "80〜100%未満", "全損"]
    ax.set_xticks(xs, labs, rotation=30, fontsize=9); ax.set_xlabel("損害率（損害 ÷ 物件の価値）"); ax.set_ylabel("損害のうち支払われる割合（%）")
    ax.set_ylim(0, 120); ax.set_title("付保割合60%の場合：小さい損害ほど差が大きい"); ax.legend(loc="upper center", ncol=2)
    save(fig, "a568_by_damage.png", SRC)
    print(T.round(4).to_string()); print(B.round(3).to_string()); print(J["sql_check"], J["mean_damage_ratio"], J["mean_loss"])

if __name__ == "__main__":
    main()
