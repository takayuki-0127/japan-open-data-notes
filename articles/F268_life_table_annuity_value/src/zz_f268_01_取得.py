"""01 取得：元データの置き場所と確かめ。
このフォルダの data/raw/ にあるファイルは、次の場所から取った。
コンテナからは厚生労働省のサイトに直接つながらないため、手元の PC の curl で取得して写した。
--from-web を付けると、つながる環境ではもう一度取得する。
"""
import hashlib, sys, urllib.request
from common import RAW

FILES = {
    # 厚生労働省「簡易生命表」生命表のダウンロード（Excel）
    "mhlw_kani_2014.xls": ("https://www.mhlw.go.jp/toukei/saikin/hw/life/life14/dl/life14-12.xls", "eda0248dd333bd4218f30dd11da7eb53"),
    "mhlw_kani_2019.xlsx": ("https://www.mhlw.go.jp/toukei/saikin/hw/life/life19/xlsx/life19-12.xlsx", "4d4a07c0388413f549bb55493dc83be7"),
    "mhlw_kani_2024.xlsx": ("https://www.mhlw.go.jp/toukei/saikin/hw/life/life24/xls/life24-12.xlsx", "d204453fe1f0301149c01bdae48c4ff5"),
    # 日本版死亡データベース（JMD）の年齢別死亡率。F86 で取得・整形したものを写した
    # （F86_lee_carter_e0/data/mx_long.csv、取得元は F86 の README）
    "jmd_mx_long_from_F86.csv": (None, "cc1ccb6f2f7f8248495221ca80ef72ec"),
    "ipss_e0_from_F86.csv": (None, "40fd854dedf71dbc71aeead09ff23dd2"),
    "zaisei_kensho_r6_assumptions.csv": (None, "bf83079cefc0e05ea71fd3dd2458c425"),
}

def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()

if __name__ == "__main__":
    web = "--from-web" in sys.argv
    for name, (url, h) in FILES.items():
        p = RAW / name
        if web and url:
            urllib.request.urlretrieve(url, p)
        ok = p.exists() and (h is None or md5(p) == h)
        print(f"{name}: {'ok' if ok else 'NG'} {md5(p) if p.exists() else ''}")
        if not ok:
            raise SystemExit(f"{name} がないか、中身が違う")
