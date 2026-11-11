"""F264 01 取得：元データを data/raw に置く。

警察庁（e-Stat）と損害保険料率算出機構の表は、ブラウザ（Chrome）で取得して
data/raw/f264_estat_bundle.json・f264_giroj_bundle.json にまとめた（取得日 2026-11-11）。
このスクリプトは、その2つから表ごとの CSV を書き出す。
e-Stat の表は下の URL から直接も取れる（fileKind=1 は CSV、Shift_JIS）。
"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
ESTAT = {  # 名前: statInfId
    "rate_all_2025ed": "000040418703",   # 交通事故の発生状況 2025年 表3-1-1
    "cnt_all_2025ed": "000040418704",    # 同 表3-1-2
    "rate_all_2019ed": "000031911596",   # 交通事故の発生状況 2019年 表3-1-1
    "cnt_all_2019ed": "000031911597",    # 同 表3-1-2
    "rate_fatal_2025ed": "000040418634", # 交通死亡事故の発生状況 2025年 表3-1-1
    "cnt_fatal_2025ed": "000040418635",  # 同 表3-1-2
    "rate_fatal_2019ed": "000031910541", # 交通死亡事故の発生状況 2019年 表3-1-1
    "cnt_fatal_2019ed": "000031910542",  # 同 表3-1-2
}


def from_bundle():
    b = json.load(open(RAW / "f264_estat_bundle.json", encoding="utf-8"))
    for k, v in b["tables"].items():
        (RAW / f"{k}.csv").write_text(v["text"], encoding="utf-8")
    g = json.load(open(RAW / "f264_giroj_bundle.json", encoding="utf-8"))
    (RAW / "giroj_jibaiseki_t1.csv").write_text(g["jibai_t1"]["csv"], encoding="utf-8")
    json.dump(g["nini_t17_totals"], open(RAW / "giroj_nini_t17_totals.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def from_web():  # 参考：e-Stat から直接取る場合
    for k, sid in ESTAT.items():
        url = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={sid}&fileKind=1"
        txt = urllib.request.urlopen(url, timeout=60).read().decode("cp932")
        (RAW / f"{k}.csv").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    from_bundle()
    print("ok", sorted(p.name for p in RAW.glob("*.csv")))
