"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
環境省「家庭部門のCO2排出実態統計調査」（e-Stat、統計コード 00650408）の Excel。
- 時系列第2表（2017〜2023年度）
- 令和7年度速報 図1-3（全国の推移）
- 各年度（2017〜2023）の全国の第6-2-2表・第7-1-1表"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "ts2_energy_by_attr_2017_2023.xlsx": ("000031913551", 4, "時系列第2表 基本項目別 年間エネルギー種別エネルギー消費量（2017〜2023年度）"),
    "r7_sokuhou_fig1_3.xlsx": ("000040519206", 4, "令和7年度速報 図1-3・表1 世帯当たり年間エネルギー種別消費量の推移（全国）"),
}
YEARS = {  # 年度: (第6-2-2表, 第7-1-1表, fileKind)
    2017: ("000031788042", "000031788069", 0), 2018: ("000031912836", "000031912863", 0),
    2019: ("000032051954", "000032051981", 4), 2020: ("000032171000", "000032171027", 4),
    2021: ("000040033346", "000040033373", 4), 2022: ("000040161446", "000040161473", 4),
    2023: ("000040277733", "000040277760", 4),
}
for y, (a, b, k) in YEARS.items():
    FILES[f"t6_2_2_{y}.xlsx"] = (a, k, f"{y}年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量")
    FILES[f"t7_1_1_{y}.xlsx"] = (b, k, f"{y}年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, kind, desc) in FILES.items():
        url = E.format(sid, kind)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "- 調査の e-Stat ページ：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00650408",
              "- 環境省の調査のページ：https://www.env.go.jp/earth/ondanka/ghg/kateiCO2tokei.html",
              "- 値は年度（4月〜翌3月）。2024年度は調査がなく、2025年度は速報値。各年度の表の1〜3行目（年度・表題・「全国」）を 02_build.py で確かめる。",
              "", "出典：環境省「家庭部門のCO2排出実態統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
