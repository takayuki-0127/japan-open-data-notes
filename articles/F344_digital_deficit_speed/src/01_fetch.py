"""元データを日本銀行の API から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
財務省・日本銀行「国際収支統計」（BP01）のサービス収支の項目別（月次・四半期の地域別）と、ドル円（FM08）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
M_ITEMS = ["9072", "9073", "9071", "9062", "9061", "9082", "9081", "907", "906"]
M_CODES = [f"BPBP6JYN{t}{i}" for i in M_ITEMS for t in ("SC", "SD", "SN")] + ["BPBP6JYNSN", "BPBP6JYNTS"]
Q_REG = ["", "US", "NA", "EP", "EU", "AS"]
Q_CODES = [f"BPBP6Q{t}{r}{i}" for r in Q_REG for i in ("95", "96") for t in ("SC", "SD")]
REQ = {
    "bop_services_monthly_1996_2026.json": ("BP01", M_CODES, "199601", "202609", "国際収支統計 サービス収支の項目別 月次（受取・支払・ネット、億円）"),
    "bop_digital_by_region_quarterly_2014_2026.json": ("BP01", Q_CODES, "201401", "202602", "国際収支統計 知的財産権等使用料・通信・コンピュータ・情報サービスの地域別 四半期（億円）"),
    "boj_usdjpy_monthly.json": ("FM08", ["FXERM07"], "199601", "202609", "ドル・円 東京市場17時 月中平均"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (db, codes, s, e, desc) in REQ.items():
        url = API.format(db=db, codes=",".join(codes), s=s, e=e)
        with urllib.request.urlopen(url, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256((RAW / name).read_bytes()).hexdigest()[:12]} |")
        print(name, (RAW / name).stat().st_size)
    lines += ["", "出典：財務省・日本銀行「国際収支統計」、日本銀行「外国為替市況」（日本銀行 時系列統計データ検索サイトの API）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
