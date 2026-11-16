"""01 取得：総務省「人口推計」の都道府県別の表を e-Stat から取る（run_all.sh からは呼ばない）。
t5  ：第5表 都道府県、男女別人口－総人口、日本人人口（各年10月1日現在、千人）
ref6：参考表 都道府県、男女別出生児数及び死亡者数－日本人、外国人（前年10月〜当年9月、人）
ref7：参考表 都道府県、男女別都道府県間転出入者数－日本人、外国人（同）
ref8：参考表 都道府県、男女別出入国者数－日本人、外国人（同）
2015年・2020年は国勢調査の年で、同じ形の参考表が一覧にない（取らない）。"""
import pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
IDS = {
    2014: {"t5": ("000029026254", 0)},  # 2014年の参考表は県間移動・出入国が日本人だけなので使わない
    2016: {"ref6": ("000031560329", 0), "ref7": ("000031560330", 0), "ref8": ("000031560331", 0)},
    2017: {"ref6": ("000031690813", 0), "ref7": ("000031690814", 0), "ref8": ("000031690815", 0)},
    2018: {"ref6": ("000031807157", 0), "ref7": ("000031807158", 0), "ref8": ("000031807159", 0)},
    2019: {"t5": ("000031921674", 0), "ref6": ("000031921689", 0), "ref7": ("000031921690", 0), "ref8": ("000031921691", 0)},
    2021: {"ref6": ("000032191061", 4), "ref7": ("000032191062", 4), "ref8": ("000032191063", 4)},
    2022: {"ref6": ("000040045506", 4), "ref7": ("000040045507", 4), "ref8": ("000040045508", 4)},
    2023: {"ref6": ("000040166092", 4), "ref7": ("000040166093", 4), "ref8": ("000040166094", 4)},
    2024: {"t5": ("000040268859", 0), "ref6": ("000040269088", 4), "ref7": ("000040269089", 4), "ref8": ("000040269090", 4)},
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for y, d in IDS.items():
        for k, (sid, kind) in d.items():
            req = urllib.request.Request(URL.format(sid, kind), headers={"User-Agent": "Mozilla/5.0"})
            b = urllib.request.urlopen(req, timeout=60).read()
            ext = "xlsx" if b[:2] == b"PK" else ("xls" if b[:4] == b"\xd0\xcf\x11\xe0" else "bin")
            (RAW / f"suikei_{k}_{y}_{sid}.{ext}").write_bytes(b)
            print(y, k, sid, ext, len(b))
            time.sleep(0.7)

if __name__ == "__main__":
    main()
