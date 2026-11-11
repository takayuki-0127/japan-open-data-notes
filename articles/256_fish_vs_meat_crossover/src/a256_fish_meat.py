"""256 1人が食べる魚と肉は、いつ入れ替わったのか

農林水産省「食料需給表」（令和6年度、1960〜2024年度。2024年度は概算値）の
  ・国民1人・1年当たり供給純食料（kg、data/jukyu_r6_14.csv）
  ・国民1人・1日当たり供給熱量（kcal、data/jukyu_r6_16.csv）
で、肉類と魚介類の「重さ」と「熱量」がいつ入れ替わったのかを見る。
供給純食料は「国内に供給された食べられる部分の量」で、実際に食べた量ではない（食べ残し・廃棄を含む）。
"""
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()


def load(name):
    d = pd.read_csv(DATA / name, header=None)
    yrs = [int(re.match(r"(\d{4})", str(x)).group(1)) for x in d.iloc[11, 2:]]
    return pd.DataFrame({str(d.iloc[i, 1]): pd.to_numeric(pd.Series(d.iloc[i, 2:].values, index=yrs), errors="coerce")
                         for i in range(12, len(d))})


K = load("jukyu_r6_14.csv")
C = load("jukyu_r6_16.csv")


def crossings(a, b):
    """a が b を上回った年（前の年は a<=b）と、下回った年"""
    d = a - b
    up = [int(y) for y in d.index[1:] if d[y] > 0 and d[y - 1] <= 0]
    down = [int(y) for y in d.index[1:] if d[y] <= 0 and d[y - 1] > 0]
    return up, down


kg = pd.DataFrame({"肉類": K["肉類"], "魚介類": K["魚介類"], "牛肉": K["肉類_牛肉"], "豚肉": K["肉類_豚肉"],
                   "鶏肉": K["肉類_鶏肉"], "鯨": K["肉類_鯨"]})
kc = pd.DataFrame({"肉類": C["肉類"], "魚介類": C["魚介類"]})
kg.to_csv(RES / "a256_kg.csv"); kc.to_csv(RES / "a256_kcal.csv")

res = {}
res["重さ_肉が上回った年"], res["重さ_肉が下回った年"] = crossings(kg["肉類"], kg["魚介類"])
res["熱量_肉が上回った年"], res["熱量_肉が下回った年"] = crossings(kc["肉類"], kc["魚介類"])
ma_kg = kg[["肉類", "魚介類"]].rolling(3, center=True).mean()
res["頑健性_重さ3年移動平均_肉が上回った年"] = crossings(ma_kg["肉類"], ma_kg["魚介類"])[0]
ma_kc = kc.rolling(3, center=True).mean()
res["頑健性_熱量3年移動平均_肉が上回った年"] = crossings(ma_kc["肉類"], ma_kc["魚介類"])[0]
for y in [1960, 1980, 2001, 2010, 2011, 2024]:
    res[f"重さ_{y}年度"] = {"肉類": float(kg.loc[y, "肉類"]), "魚介類": float(kg.loc[y, "魚介類"])}
for y in [1960, 1979, 1987, 2024]:
    res[f"熱量_{y}年度"] = {"肉類": float(kc.loc[y, "肉類"]), "魚介類": float(kc.loc[y, "魚介類"])}
res["魚介類_最大"] = {"年度": int(kg["魚介類"].idxmax()), "kg": float(kg["魚介類"].max())}
res["魚介類_2001→2024_kg"] = round(float(kg.loc[2024, "魚介類"] - kg.loc[2001, "魚介類"]), 1)
res["魚介類_2001→2024_%"] = round(float((kg.loc[2024, "魚介類"] / kg.loc[2001, "魚介類"] - 1) * 100), 1)
res["肉類_2001→2024_kg"] = round(float(kg.loc[2024, "肉類"] - kg.loc[2001, "肉類"]), 1)
for c in ["牛肉", "豚肉", "鶏肉"]:
    res[f"{c}_2001→2024_kg"] = round(float(kg.loc[2024, c] - kg.loc[2001, c]), 1)
# 1970〜1990年代：重さでは魚が上なのに熱量で肉が上（1kg当たりの熱量の違い）
res["1kg当たり熱量_2024年度_肉類"] = round(float(kc.loc[2024, "肉類"] * 365 / kg.loc[2024, "肉類"]), 0)
res["1kg当たり熱量_2024年度_魚介類"] = round(float(kc.loc[2024, "魚介類"] * 365 / kg.loc[2024, "魚介類"]), 0)
res["1kg当たり熱量_1980年度_肉類"] = round(float(kc.loc[1980, "肉類"] * 365 / kg.loc[1980, "肉類"]), 0)
res["1kg当たり熱量_1980年度_魚介類"] = round(float(kc.loc[1980, "魚介類"] * 365 / kg.loc[1980, "魚介類"]), 0)
# 鶏肉が魚を上回るか
res["鶏肉と豚肉の合計が魚介類を上回った年"] = crossings(kg["鶏肉"] + kg["豚肉"], kg["魚介類"])[0]
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# 図1：重さ
fig, ax = plt.subplots(figsize=(8.2, 4.3))
ax.plot(kg.index, kg["魚介類"], color="#2b6cb0", lw=2, label="魚介類")
ax.plot(kg.index, kg["肉類"], color="#c05621", lw=2, label="肉類")
x = res["重さ_肉が上回った年"][-1]
ax.axvline(x, color="#888", lw=0.8, ls="--")
ax.annotate(f"{x}年度に入れ替わり\n肉 {kg.loc[x,'肉類']}kg・魚 {kg.loc[x,'魚介類']}kg", (x, kg.loc[x, "肉類"]), xytext=(x - 26, 12), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="#555"))
ax.annotate(f"魚の最大 2001年度 {kg.loc[2001,'魚介類']}kg", (2001, kg.loc[2001, "魚介類"]), xytext=(1975, 42), fontsize=8.5,
            arrowprops=dict(arrowstyle="->", color="#555"))
ax.set_ylim(0, 45)
ax.set_ylabel("国民1人・1年当たり供給純食料（kg）")
ax.set_title("重さで見ると、肉が魚を上回ったのは2011年度", fontsize=11)
ax.legend(frameon=False, loc="lower right")
ax.text(0, -0.13, "2024年度は概算値。出典：農林水産省「食料需給表」", transform=ax.transAxes, fontsize=7.5, color="#555")
fig.tight_layout(); fig.savefig(FIG / "a256_kg.png", dpi=150); plt.close(fig)

# 図2：熱量
fig, ax = plt.subplots(figsize=(8.2, 4.3))
ax.plot(kc.index, kc["魚介類"], color="#2b6cb0", lw=2, label="魚介類")
ax.plot(kc.index, kc["肉類"], color="#c05621", lw=2, label="肉類")
for x in res["熱量_肉が上回った年"]:
    ax.axvline(x, color="#888", lw=0.8, ls="--")
    ax.text(x + 0.5, 20, f"{x}年度", fontsize=8.5)
ax.set_ylabel("国民1人・1日当たり供給熱量（kcal）")
ax.set_title("熱量で見ると、肉が上回ったのは1979年度（定着は1987年度）", fontsize=11)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "a256_kcal.png", dpi=150); plt.close(fig)

# 図3：肉の内訳と魚
fig, ax = plt.subplots(figsize=(8.2, 4.3))
ax.stackplot(kg.index, kg["鶏肉"], kg["豚肉"], kg["牛肉"], kg["鯨"], labels=["鶏肉", "豚肉", "牛肉", "鯨"],
             colors=["#f6ad55", "#ed8936", "#9c4221", "#cbd5e0"], alpha=0.9)
ax.plot(kg.index, kg["魚介類"], color="#2b6cb0", lw=2.2, label="魚介類（線）")
ax.set_ylabel("1人・1年当たり供給純食料（kg）")
ax.set_title("増えたのは鶏肉と豚肉。魚は2001年度から半分近くに", fontsize=11)
ax.legend(frameon=False, loc="upper left", fontsize=8.5, ncol=2)
fig.tight_layout(); fig.savefig(FIG / "a256_breakdown.png", dpi=150); plt.close(fig)
print(json.dumps(res, ensure_ascii=False, indent=1))
