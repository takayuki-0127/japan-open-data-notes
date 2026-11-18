"""問い直し（結果を見てから足した）：集積回路の生産の伸びは、どの品目が押し上げたのか。
集積回路（業種別の指数）の2019年→直近12か月の増加（ポイント）を、品目の指数 × 付加生産ウエイト の割合で分ける。
マイコンと「その他のモス型」は2020年途中から秘匿（X）なので、2つをまとめて「秘匿の2品目など（差し引き）」とする。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
LAST12 = (202510, 202609)
LAB = {"ic_memory": "メモリ", "ic_logic": "ロジック", "ic_linear": "線形IC", "ic_hybrid": "混成IC"}


def avg(s, lo, hi):
    return float(s[(s.index >= lo) & (s.index <= hi)].mean())


def main():
    it = pd.read_csv(D / "iip_items_prod.csv")
    w = it.groupby("series")["weight"].first()
    P = it.pivot(index="ym", columns="series", values="value")
    L = pd.read_csv(R / "iip_linked_monthly.csv").set_index("ym")
    W = float(w[["ic_linear", "ic_mcu", "ic_logic", "ic_memory", "ic_mos_other", "ic_hybrid"]].sum())
    g19, gl = avg(L["ic_prod"], 201901, 201912), avg(L["ic_prod"], *LAST12)
    rows, known = [], 0.0
    for s in ["ic_memory", "ic_logic", "ic_linear", "ic_hybrid"]:
        a, b = avg(P[s], 201901, 201912), avg(P[s], *LAST12)
        c = w[s] / W * (b - a)
        known += c
        rows.append({"item": s, "label": LAB[s], "weight": float(w[s]), "weight_share_pct": round(w[s] / W * 100, 2),
                     "idx_2019": round(a, 2), "idx_last12": round(b, 2), "item_change_pct": round((b / a - 1) * 100, 2),
                     "contrib_pt": round(c, 3)})
    resid = (gl - g19) - known
    rows.append({"item": "secret_and_residual", "label": "秘匿の2品目など（差し引き）", "weight": float(w["ic_mcu"] + w["ic_mos_other"]),
                 "weight_share_pct": round((w["ic_mcu"] + w["ic_mos_other"]) / W * 100, 2), "idx_2019": None, "idx_last12": None,
                 "item_change_pct": None, "contrib_pt": round(resid, 3)})
    df = pd.DataFrame(rows)
    df["contrib_share_pct"] = (df["contrib_pt"] / (gl - g19) * 100).round(1)
    df.to_csv(R / "requestion_items.csv", index=False)
    q = {"ic_change_pt": round(gl - g19, 3), "memory_contrib_pt": float(df.loc[0, "contrib_pt"]), "memory_share_pct": float(df.loc[0, "contrib_share_pct"]),
         "memory_weight_share_pct": float(df.loc[0, "weight_share_pct"]), "memory_change_pct": float(df.loc[0, "item_change_pct"]),
         "logic_change_pct": float(df.loc[1, "item_change_pct"]), "linear_change_pct": float(df.loc[2, "item_change_pct"]),
         "hybrid_change_pct": float(df.loc[3, "item_change_pct"]), "secret_contrib_pt": float(df.loc[4, "contrib_pt"]),
         "secret_share_pct": float(df.loc[4, "contrib_share_pct"]), "secret_weight_share_pct": float(df.loc[4, "weight_share_pct"])}
    # 半導体製造装置（品目）も参考に
    q["equip_semi_item_change_pct"] = round((avg(P["equip_semi"], *LAST12) / avg(P["equip_semi"], 201901, 201912) - 1) * 100, 2)
    (R / "requestion.json").write_text(json.dumps(q, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(df.to_string()); print(q)


if __name__ == "__main__":
    main()
