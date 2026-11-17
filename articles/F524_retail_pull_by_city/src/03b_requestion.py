"""問い直し：県庁所在市の指数が下がったのは、販売額の全国シェアが落ちたからか、人口の全国シェアが上がったからか。
指数＝販売額のシェア÷人口のシェア なので、log(指数)の変化＝log(販売額シェア)の変化−log(人口シェア)の変化。店舗の販売額だけでも見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
c = pd.read_csv(R / "capitals.csv", dtype={"code": str})
d = pd.read_csv(R / "index_by_municipality.csv", dtype={"code": str})
ok14, ok21 = d.sales2014.notna(), d.sales2021.notna()
S14, S21 = d.loc[ok14, "sales2014"].sum(), d.loc[ok21, "sales2021"].sum()
P14, P21 = d.loc[ok14, "pop2015"].sum(), d.loc[ok21, "pop2020"].sum()
c["sales_share_chg_pct"] = 100 * ((c.sales2021 / S21) / (c.sales2014 / S14) - 1)
c["pop_share_chg_pct"] = 100 * ((c.pop2020 / P21) / (c.pop2015 / P14) - 1)
c["dlog_idx"] = np.log(c.idx2021 / c.idx2014)
c["dlog_sales"] = np.log((c.sales2021 / S21) / (c.sales2014 / S14))
c["dlog_pop"] = np.log((c.pop2020 / P21) / (c.pop2015 / P14))
assert (abs(c.dlog_idx - (c.dlog_sales - c.dlog_pop)) < 1e-3).all()
out_cols = ["code", "pref", "name", "idx2014", "idx2021", "idx_store2014", "idx_store2021", "sales_share_chg_pct", "pop_share_chg_pct"]
c[out_cols].to_csv(R / "requestion_capitals.csv", index=False, float_format="%.4f")
down = c[c.idx2021 < c.idx2014]
out = {"question": "県庁所在市の指数の低下は、販売額のシェアの低下か、人口のシェアの上昇か",
       "n_down": int(len(down)),
       "n_down_with_pop_share_up": int((down.pop_share_chg_pct > 0).sum()),
       "n_down_with_sales_share_down": int((down.sales_share_chg_pct < 0).sum()),
       "median_pop_share_chg_pct_all": round(float(c.pop_share_chg_pct.median()), 2),
       "median_sales_share_chg_pct_all": round(float(c.sales_share_chg_pct.median()), 2),
       "n_pop_share_up_all": int((c.pop_share_chg_pct > 0).sum()),
       "n_store_down": int((c.idx_store2021 < c.idx_store2014).sum())}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out); print(c[["name", "sales_share_chg_pct", "pop_share_chg_pct"]].round(1).to_string())
