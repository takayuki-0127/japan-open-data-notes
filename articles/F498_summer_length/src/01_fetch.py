"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
1. 気象庁「過去の気象データ・ダウンロード」から、地点ごとの日平均気温（日別値、1901〜2025年）を CSV で取り、gzip で保存する。
   本線：気象庁が都市化の影響が比較的小さいとする15地点。比べ用：大都市11地点。
2. 照合用に、同じ15地点の「過去の気象データ検索」年ごとの値（詳細：気温、view=a2。日平均気温25℃以上の日数を含む）を HTML のまま gzip で保存する。
"""
import pathlib, urllib.request, urllib.parse, hashlib, datetime, time, gzip

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
OBSDL = "https://www.data.jma.go.jp/risk/obsdl/show/table"
A2 = "https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no={}&block_no={}&year=&month=&day=&view=a2"
# 名前: (prec_no, block_no, 区分)  北から南の順
STATIONS = {
    "網走": ("17", "47409", "rural"), "根室": ("18", "47420", "rural"), "寿都": ("16", "47421", "rural"),
    "札幌": ("14", "47412", "city"), "山形": ("35", "47588", "rural"), "石巻": ("34", "47592", "rural"),
    "仙台": ("34", "47590", "city"), "伏木": ("55", "47606", "rural"), "銚子": ("45", "47648", "rural"),
    "東京": ("44", "47662", "city"), "横浜": ("46", "47670", "city"), "飯田": ("48", "47637", "rural"),
    "名古屋": ("51", "47636", "city"), "彦根": ("60", "47761", "rural"), "京都": ("61", "47759", "city"),
    "大阪": ("62", "47772", "city"), "神戸": ("63", "47770", "city"), "境": ("69", "47742", "rural"),
    "浜田": ("68", "47755", "rural"), "広島": ("67", "47765", "city"), "多度津": ("72", "47890", "rural"),
    "福岡": ("82", "47807", "city"), "宮崎": ("87", "47830", "rural"), "鹿児島": ("88", "47827", "city"),
    "名瀬": ("88", "47909", "rural"), "石垣島": ("91", "47918", "rural"),
}


def post(block):
    d = {"stationNumList": f'["s{block}"]', "aggrgPeriod": "1", "elementNumList": '[["201",""]]', "interAnnualType": "1",
         "ymdList": '["1901","2025","1","12","1","31"]', "option": '{"list":["obs"],"nyear":0}', "downloadFlag": "true",
         "rmkFlag": "1", "disconnectFlag": "1", "youbiFlag": "0", "fukenFlag": "0", "kijiFlag": "0", "csvFlag": "1",
         "jikantaiFlag": "0", "jikantaiList": "[]", "ymdLiteral": "1"}
    req = urllib.request.Request(OBSDL, data=urllib.parse.urlencode(d).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | 取得元 | sha256 の先頭12字（gzip を解いた中身） |", "|---|---|---|---|"]
    meta = ["station,prec_no,block_no,group,order"]
    for i, (name, (prec, block, grp)) in enumerate(STATIONS.items()):
        b = post(block)
        fn = f"jma_daily_tmean_{block}.csv.gz"
        (RAW / fn).write_bytes(gzip.compress(b, mtime=0))
        lines.append(f"| {fn} | {name}：日平均気温の日別値 1901〜2025年（品質情報・均質番号つき、Shift_JIS） | {OBSDL}（POST。地点 s{block}、要素 201＝平均気温、日別値） | {hashlib.sha256(b).hexdigest()[:12]} |")
        meta.append(f"{name},{prec},{block},{grp},{i}")
        time.sleep(1.0)
        if grp == "rural":
            url = A2.format(prec, block)
            h = get(url)
            fn2 = f"jma_a2_{block}.html.gz"
            (RAW / fn2).write_bytes(gzip.compress(h, mtime=0))
            lines.append(f"| {fn2} | {name}：年ごとの値（気温。照合用） | {url} | {hashlib.sha256(h).hexdigest()[:12]} |")
            time.sleep(1.0)
    (RAW / "stations.csv").write_text("\n".join(meta) + "\n", encoding="utf-8")
    lines += ["", "出典：気象庁「過去の気象データ・ダウンロード」（https://www.data.jma.go.jp/risk/obsdl/index.php）、",
              "気象庁「過去の気象データ検索」年ごとの値（https://www.data.jma.go.jp/stats/etrn/index.php）。",
              "区分 rural は、気象庁が日本の平均気温の変化を求めるのに使う、都市化の影響が比較的小さい15地点。city は大都市（比べ用）。",
              "日別値の CSV の1行目にはダウンロードした時刻が入るため、取り直すと sha256 は変わる（02 以降は同梱のファイルだけを使う）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
