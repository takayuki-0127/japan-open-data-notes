"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
気象庁「過去の気象データ検索」の年ごとの値（詳細：気温・蒸気圧・湿度、view=a2）のページを、地点ごとに HTML のまま保存する。
大都市11地点と、気象庁が「都市化の影響が比較的小さい」とする15地点。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
U = "https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no={}&block_no={}&year=&month=&day=&view=a2"
STATIONS = {
    "札幌": ("14", "47412", "city"), "仙台": ("34", "47590", "city"), "東京": ("44", "47662", "city"), "横浜": ("46", "47670", "city"),
    "名古屋": ("51", "47636", "city"), "京都": ("61", "47759", "city"), "大阪": ("62", "47772", "city"), "神戸": ("63", "47770", "city"),
    "広島": ("67", "47765", "city"), "福岡": ("82", "47807", "city"), "鹿児島": ("88", "47827", "city"),
    "網走": ("17", "47409", "rural"), "根室": ("18", "47420", "rural"), "寿都": ("16", "47421", "rural"), "山形": ("35", "47588", "rural"),
    "石巻": ("34", "47592", "rural"), "伏木": ("55", "47606", "rural"), "飯田": ("48", "47637", "rural"), "銚子": ("45", "47648", "rural"),
    "境": ("69", "47742", "rural"), "浜田": ("68", "47755", "rural"), "彦根": ("60", "47761", "rural"), "宮崎": ("87", "47830", "rural"),
    "多度津": ("72", "47890", "rural"), "名瀬": ("88", "47909", "rural"), "石垣島": ("91", "47918", "rural"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 地点（区分） | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    meta = ["station,prec_no,block_no,group"]
    for name, (prec, block, grp) in STATIONS.items():
        url = U.format(prec, block)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"}), timeout=60) as r:
            b = r.read()
        fn = f"jma_a2_{block}.html"
        (RAW / fn).write_bytes(b)
        lines.append(f"| {fn} | {name}（{'大都市' if grp == 'city' else '都市化の影響が小さい地点'}） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        meta.append(f"{name},{prec},{block},{grp}")
        time.sleep(0.4)
    (RAW / "stations.csv").write_text("\n".join(meta) + "\n", encoding="utf-8")
    lines += ["", "出典：気象庁「過去の気象データ検索」年ごとの値（https://www.data.jma.go.jp/stats/etrn/index.php）。",
              "都市化の影響が比較的小さい15地点は、気象庁「気候変動監視レポート」などで日本の平均気温の変化を求めるのに使われている地点。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
