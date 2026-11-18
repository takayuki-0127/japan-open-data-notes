"""03b 問い直し（結果を見てから足した）：
頂点（日銀の割合が最も高かった期）から最新の期までの、部門ごとの残高の変化を、
取引（買い越し・売り越し）と調整（主に時価の変化）に分ける。取引と調整の系列がある6部門だけ。
あわせて、日銀の割合の低下を「日銀の残高の変化」と「発行残高の変化」に分ける。
出力：results/requestion_sector_decomp.csv、results/requestion.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
t = pd.read_csv(D / "ff_quarterly.csv", index_col="period")
nm = pd.read_csv(D / "series_names.csv").set_index("code")["name"]
m = json.load(open(R / "main.json", encoding="utf-8"))
pk, last = m["boj_share_peak_period"], m["last_period"]
idx = list(t.index)
after = idx[idx.index(pk) + 1:]


def main():
    rows = []
    for c in sorted(t.columns):
        if not (c.startswith("FOF_FFAF") and c.endswith("A311")):
            continue
        sec = nm[c].split("／")[1]
        s, a = c.replace("FFAF", "FFAS"), c.replace("FFAF", "FFAR")
        assert nm[s].split("／")[1] == sec and nm[a].split("／")[1] == sec
        dS = float(t.loc[last, s] - t.loc[pk, s])
        fl = float(t.loc[after, c].sum()); ad = float(t.loc[after, a].sum())
        rows.append({"sector": sec, "stock_peak_tn": round(float(t.loc[pk, s]) / 1e4, 1), "stock_last_tn": round(float(t.loc[last, s]) / 1e4, 1),
                     "change_tn": round(dS / 1e4, 1), "flow_tn": round(fl / 1e4, 1), "adjustment_tn": round(ad / 1e4, 1),
                     "gap_tn": round((dS - fl - ad) / 1e4, 2)})
    df = pd.DataFrame(rows)
    # 発行残高（一般政府＋財政融資資金）
    tot = t["FOF_FFAS420L311"] + t["FOF_FFAS181L311"]
    tfl = float(t.loc[after, "FOF_FFAF420L311"].sum() + t.loc[after, "FOF_FFAF181L311"].sum())
    tad = float(t.loc[after, "FOF_FFAR420L311"].sum() + t.loc[after, "FOF_FFAR181L311"].sum())
    df = pd.concat([df, pd.DataFrame([{"sector": "発行残高（一般政府＋財政融資資金）", "stock_peak_tn": round(float(tot[pk]) / 1e4, 1),
                                        "stock_last_tn": round(float(tot[last]) / 1e4, 1), "change_tn": round(float(tot[last] - tot[pk]) / 1e4, 1),
                                        "flow_tn": round(tfl / 1e4, 1), "adjustment_tn": round(tad / 1e4, 1),
                                        "gap_tn": round(float(tot[last] - tot[pk] - tfl - tad) / 1e4, 2)}])], ignore_index=True)
    df.to_csv(R / "requestion_sector_decomp.csv", index=False)

    # 割合の低下の分け方：日銀の残高だけ動いた場合と、発行残高だけ動いた場合
    bj = t["FOF_FFAS110A311"]
    s_pk = bj[pk] / tot[pk] * 100; s_last = bj[last] / tot[last] * 100
    only_num = bj[last] / tot[pk] * 100 - s_pk          # 発行残高を頂点の期のままにしたとき
    only_den = bj[pk] / tot[last] * 100 - s_pk          # 日銀の残高を頂点の期のままにしたとき
    # 時価の変化を除いた割合（頂点の期の残高に、その後の取引だけを足す）
    bj_fl = bj[pk] + t.loc[after, "FOF_FFAF110A311"].sum()
    tot_fl = tot[pk] + tfl
    q = {"peak": pk, "last": last, "share_peak": round(float(s_pk), 2), "share_last": round(float(s_last), 2),
         "change_if_only_boj_moved_pt": round(float(only_num), 2), "change_if_only_total_moved_pt": round(float(only_den), 2),
         "share_last_flows_only": round(float(bj_fl / tot_fl * 100), 2),
         "sectors": df.set_index("sector").to_dict(orient="index")}
    json.dump(q, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(df.to_string()); print({k: v for k, v in q.items() if k != "sectors"})


if __name__ == "__main__":
    main()
