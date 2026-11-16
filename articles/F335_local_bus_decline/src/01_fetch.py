"""01 取得（run_all.sh からは呼ばない）
国土交通省「旅客地域流動調査」府県相互間旅客輸送人員表（e-Stat のファイル、2000〜2024年度）
e-Stat の検索結果で各年度に2つずつ出るファイルのうち、「乗合バス」のシートがある方を残す。
"""
import pathlib, time, urllib.request, zipfile, io

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
CAND = {
    2024: ["000040442733", "000040442734"], 2023: ["000040269187", "000040269188"], 2022: ["000040169489", "000040169490"],
    2021: ["000040041762", "000040041763"], 2020: ["000032187226", "000032187227"], 2019: ["000032088731", "000032088732"],
    2018: ["000032021233", "000032021234"], 2017: ["000031817433", "000031817434"], 2016: ["000031682658", "000031682659"],
    2015: ["000031605975", "000031605976"], 2014: ["000031524092", "000031524093"], 2013: ["000031355337", "000031355338"],
    2012: ["000027644747", "000027644748"], 2011: ["000027669598", "000027669878"], 2010: ["000027670520", "000027669870"],
    2009: ["000027671349", "000027671736"], 2008: ["000027672116", "000027672232"], 2007: ["000027672792", "000027672556"],
    2006: ["000027672804", "000027672940"], 2005: ["000027673272", "000027672945"], 2004: ["000027673688", "000027673664"],
    2003: ["000027673912", "000027673909"], 2002: ["000027674352", "000027673929"], 2001: ["000027674726", "000027675276"],
    2000: ["000027676322", "000027676321"],
}


def sheets(b):
    if b[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(b))
        return z.read("xl/workbook.xml").decode("utf-8", "replace"), "xlsx"
    import xlrd
    return " ".join(xlrd.open_workbook(file_contents=b, on_demand=True).sheet_names()), "xls"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for y, ids in sorted(CAND.items()):
        for i in ids:
            time.sleep(1.0)
            b = urllib.request.urlopen(urllib.request.Request(URL.format(i), headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
            names, ext = sheets(b)
            if "乗合バス" in names:
                (RAW / f"ryokaku_{y}_{i}.{ext}").write_bytes(b)
                print(y, i, ext, len(b))
                break
        else:
            print(y, "見つからない")


if __name__ == "__main__":
    main()
