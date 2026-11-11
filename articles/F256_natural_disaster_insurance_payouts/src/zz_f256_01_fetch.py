"""01 取得：元データの一覧（ファイルはブラウザで取得して data/raw/ に置いた）。

日本損害保険協会のサイトはプログラムからの直接取得が通らない環境があったため、
ブラウザで開いて保存した。以下のURLから同じファイルを取れる。
"""
GIAJ_ATT = "https://www.sonpo.or.jp/report/statistics/disaster/ctuevu000000j470-att/"
SOURCES = {
    "giaj_fusuigai_top10.pdf": "https://www.sonpo.or.jp/report/statistics/disaster/ctuevu000000530r-att/c_fusuigai.pdf",
    "giaj_events/<FY>_<nn>.pdf": GIAJ_ATT + "<FY>_<nn>.pdf （一覧：https://www.sonpo.or.jp/report/statistics/disaster/weather.html）",
    "mlit_deflator_nendo.xlsx": "https://www.mlit.go.jp/statistics/details/content/defnendo_261030.xlsx （国土交通省 建設工事費デフレーター 年度・2020年度基準）",
    "cpi_monthly_from_F101.csv": "総務省 消費者物価指数（e-Stat）。F101 で取得した月次系列を流用",
    "hlts_timeseries_from_F127.json": "総務省 住宅・土地統計調査 第3表（住宅数及び世帯数、1958〜2023年）。F127 で取得した表を流用",
}
if __name__ == "__main__":
    import pathlib
    raw = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
    for k, v in SOURCES.items():
        print(k, "<-", v)
    print(len(list((raw / "giaj_events").glob("*.pdf"))), "event PDFs in data/raw/giaj_events")
