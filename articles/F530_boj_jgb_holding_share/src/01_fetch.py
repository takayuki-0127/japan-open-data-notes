"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
日本銀行「資金循環統計」（時系列統計データ検索サイトの API、db=FF）と
「日本銀行勘定」（db=BS01）の長期国債の残高を JSON で保存する。"""
import gzip, json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}"
HDR = {"User-Agent": "japan-open-data-notes research script (python urllib)", "Accept-Encoding": "gzip"}

# 保有部門のコード（資金循環統計の部門）
SECTORS = ["110", "120", "126", "121", "122", "124", "125", "130", "132", "134", "140", "160", "190",
           "410", "420", "423", "424", "430", "440", "500", "150", "170", "180", "300"]
FF = []
for s in SECTORS:
    FF += [f"FOF_FFAS{s}A311"] + ([] if s == "430" else [f"FOF_FFAS{s}A310"])  # 残高（国債・財投債、国庫短期証券。家計の国庫短期証券は系列なし）
for s in ["110", "120", "121", "130", "500", "423", "430"]:
    FF += [f"FOF_FFAF{s}A311", f"FOF_FFAR{s}A311"]          # 取引（フロー）と調整（主に時価の変化）
FF += ["FOF_FFAS420L311", "FOF_FFAS181L311", "FOF_FFAS420L310", "FOF_FFAS181L310",   # 発行残高（時価）
       "FOF_FFAF420L311", "FOF_FFAF181L311", "FOF_FFAR420L311", "FOF_FFAR181L311",
       "FOF_FFAB420L311", "FOF_FFAB420L310"]                        # 額面
BS = ["MABJMA5", "MABJMA5A", "MABJMA5B"]  # 日本銀行勘定の国債（簿価、月末）


def get(db, codes):
    out = []
    for i in range(0, len(codes), 20):
        u = API.format(db=db, codes=",".join(codes[i:i + 20]))
        b = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=120).read()
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        d = json.loads(b)
        assert d["STATUS"] == 200, d
        out += d["RESULTSET"]
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, db, codes in [("boj_ff_jgb.json", "FF", FF), ("boj_bs01_jgb.json", "BS01", BS)]:
        res = get(db, codes)
        (RAW / name).write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
        print(name, len(res))
    # 照らし合わせ用：日銀の参考図表（時系列、Excel）。最近の10期の保有者別残高がある
    u = "https://www.boj.or.jp/statistics/sj/sjlong.xlsx"
    (RAW / "sjlong.xlsx").write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=120).read())


if __name__ == "__main__":
    main()
