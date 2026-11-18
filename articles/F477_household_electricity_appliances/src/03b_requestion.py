"""問い直し（結果を見てから足した）：照明の LED 化は、電気の減少を説明するか。
第6-2-2表「使用している照明の種類（住宅全体）別」の世帯数分布と電気の平均で、2017→2023年度を分解する。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
G = "使用している照明の種類（住宅全体）別"


def main():
    t = pd.read_csv(DATA / "t622_long.csv")
    s = t[(t.group == G) & (t.cat1 != "不明")]
    cats = list(s[s.fy == 2023].cat1)
    out = {"categories_2023": cats}
    piv = []
    for fy in range(2017, 2024):
        x = s[s.fy == fy].set_index("cat1")
        assert list(x.index) == cats, (fy, list(x.index))
        for c in cats:
            piv.append({"fy": fy, "cat": c, "share_pct": x.loc[c, "w"] / x.w.sum() * 100, "elec": x.loc[c, "mean"]})
    p = pd.DataFrame(piv)
    p.to_csv(RES / "requestion_led_by_fy.csv", index=False, float_format="%.3f")
    a = p[p.fy == 2017].set_index("cat").loc[cats]; b = p[p.fy == 2023].set_index("cat").loc[cats]
    s0, s1 = a.share_pct.values / 100, b.share_pct.values / 100
    comp = ((s1 - s0) * (a.elec.values + b.elec.values) / 2).sum()
    within = ((s0 + s1) / 2 * (b.elec.values - a.elec.values)).sum()
    m0, m1 = (s0 * a.elec.values).sum(), (s1 * b.elec.values).sum()
    out.update({"mean2017": round(m0, 4), "mean2023": round(m1, 4), "diff": round(m1 - m0, 4), "composition": round(comp, 4), "within": round(within, 4)})
    led_any = [c for c in cats if c.startswith("LED照明のみ") or c.startswith("LED照明と")]
    out["led_only_share"] = {"2017": round(float(a.loc[cats[0], "share_pct"]), 2), "2023": round(float(b.loc[cats[0], "share_pct"]), 2)}
    out["led_any_share"] = {"2017": round(float(a.loc[led_any, "share_pct"].sum()), 2), "2023": round(float(b.loc[led_any, "share_pct"].sum()), 2)}
    out["elec_2023"] = {c: round(float(b.loc[c, "elec"]), 2) for c in cats}
    out["elec_2017"] = {c: round(float(a.loc[c, "elec"]), 2) for c in cats}
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
