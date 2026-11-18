"""元データを日本銀行「時系列統計データ検索サイト」の API から取り、data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
このスクリプトは、日本銀行時系列統計データ検索サイトの API 機能を使用しています。内容は日本銀行によって保証されたものではありません。"""
import datetime, json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BOJ = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}"
# 頻度ごとに分けて取る（API は1回に同じ頻度の系列を渡す）
SETS = {
    "boj_FM02_call_rate_monthly.json": ("FM02", ["STRACLUCON", "STRECLUCON"]),
    # 店頭表示金利：2022年4月以降（月次）
    "boj_IR02_posted_monthly.json": ("IR02", ["DLDR121N", "DLDR43TL61YN", "DLDR43TL63MN", "DLDR43TL65YN", "DLDR43TL41YN"]),
    # 店頭表示金利：2007年10月〜2022年3月（週次・月曜）
    "boj_IR02_posted_weekly_2007.json": ("IR02", ["DLDR120N", "DLDR43TL31YN", "DLDR43TL33MN", "DLDR43TL35YN", "DLDR43TL11YN"]),
    # 店頭表示金利：普通預金 1994年10月〜2007年9月（週次・月曜）
    "boj_IR02_posted_weekly_1994_ordinary.json": ("IR02", ["DLDR120"]),
    # 店頭表示金利：定期預金 1991年10月〜2007年9月（週次・木曜）
    "boj_IR02_posted_weekly_1991_time.json": ("IR02", ["DLDR43TL31Y", "DLDR43TL33M", "DLDR43TL35Y", "DLDR43TL11Y"]),
    # 定期預金の新規受入分の平均金利（実際に約定した金利、月次）
    "boj_IR03_new_time_deposits.json": ("IR03", ["DLDRK_DLDR442DB", "DLDRK_DLDR442DBKT", "DLDRK_DLDR442DBFT", "DLDRK_DLDR442DBKT5"]),
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "research-script"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, (db, codes) in SETS.items():
        url = BOJ.format(db=db, codes=",".join(codes))
        b = get(url)
        j = json.loads(b)
        assert j.get("STATUS") == 200, j.get("MESSAGE")
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 日本銀行 時系列統計データ（{db}：{', '.join(codes)}） | {url} | {today} |")
        print("saved", name, len(j.get("RESULTSET", [])))
    lines += ["", "- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/ （API 利用）",
              "- FM02：コールレート、IR02：預金種類別店頭表示金利の平均年利率等、IR03：定期預金の預入期間別平均金利（新規受入分）",
              "- 出典を示して加工して使う（日本銀行の利用規約）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
