"""e-Stat から都道府県別生命表（平成12年〜令和2年、5回分）の CSV を取得する。

表の一覧（statInfId）は data/raw/f49_lifetables.json の "ids" に入っている。
- 2020年：令和２年都道府県別生命表（tclass2=000001172687）
- 2015年：平成27年（000001109755）、2010年：平成22年（000001060867）
- 2005年：平成17年（000001060978）、2000年：平成12年（000001060930）
取るのは、都道府県（01〜47）と全国（00）の「男」「女」の生命表、2000年と2020年の死因別死亡確率、
付録80000「都道府県別平均寿命の年次推移」。CSV は Shift_JIS。

e-Stat はアクセスの環境によっては取れないことがあるので、記事ではブラウザの中で同じ URL を取り、
1つの JSON（data/raw/f49_lifetables.json）にまとめたものを使った。
"""
import json, time
import requests
from common import RAW

URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"


def main():
    meta = json.load(open(RAW / "f49_lifetables.json", encoding="utf-8"))
    ids = meta["ids"]
    out = {}
    for y, m in ids.items():
        for k, (lab, sid, *_rest) in m.items():
            keep = lab.endswith(" 男") or lab.endswith(" 女") or (k == "80000" and y == "2020") \
                or ("死因別死亡確率" in lab and y in ("2000", "2020"))
            if not keep:
                continue
            r = requests.get(URL.format(sid), timeout=60)
            r.raise_for_status()
            out[f"{y}_{k}"] = {"lab": lab, "id": sid, "csv": r.content.decode("shift_jis")}
            time.sleep(1)
    json.dump({"ids": ids, "lt": out}, open(RAW / "f49_lifetables_refetch.json", "w", encoding="utf-8"),
              ensure_ascii=False)
    print(len(out))


if __name__ == "__main__":
    main()
