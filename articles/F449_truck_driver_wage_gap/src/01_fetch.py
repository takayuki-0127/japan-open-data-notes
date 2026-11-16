"""元データを e-Stat から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
旧形式の .xls は大きいので、取得したバイト列をそのまま gzip（mtime=0）で圧縮して保存する（中身は同じ）。"""
import datetime, gzip, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
# 賃金構造基本統計調査 一般労働者。occ2=職種別第2表（2019年まで、職種・性×年齢）、
# occ1=職種第1表（2020年から、職種小分類×性）、occ5=職種第5表（2020年から、職種小分類×年齢）、ind1=産業計の第1表（年齢階級別）
FILES = {
    2009: {"occ2": ("000007368421", 0), "ind1": ("000007214289", 0)},
    2010: {"occ2": ("000009544207", 0), "ind1": ("000008278863", 0)},
    2011: {"occ2": ("000012743014", 0), "ind1": ("000012740223", 0)},
    2012: {"occ2": ("000016347005", 0), "ind1": ("000015981178", 0)},
    2013: {"occ2": ("000023602573", 0), "ind1": ("000023602360", 0)},
    2014: {"occ2": ("000026308729", 0), "ind1": ("000026308307", 0)},
    2015: {"occ2": ("000028996525", 0), "ind1": ("000028996409", 0)},
    2016: {"occ2": ("000031227941", 0), "ind1": ("000031226663", 0)},
    2017: {"occ2": ("000031559737", 0), "ind1": ("000031559750", 0)},
    2018: {"occ2": ("000031683129", 0), "ind1": ("000031683036", 0)},
    2019: {"occ2": ("000031919844", 0), "ind1": ("000031919751", 0)},
    2020: {"occ1": ("000032069431", 0), "occ5": ("000032069435", 0), "ind1": ("000032069350", 0)},
    2021: {"occ1": ("000032182952", 4), "occ5": ("000032182956", 4), "ind1": ("000032182871", 4)},
    2022: {"occ1": ("000040029181", 4), "occ5": ("000040029185", 4), "ind1": ("000040029100", 4)},
    2023: {"occ1": ("000040163741", 4), "occ5": ("000040163745", 4), "ind1": ("000040163660", 4)},
    2024: {"occ1": ("000040247854", 4), "occ5": ("000040247858", 4), "ind1": ("000040247773", 4)},
    2025: {"occ1": ("000040421116", 4), "occ5": ("000040421120", 4), "ind1": ("000040420843", 4)},
}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    desc = {"occ2": "職種別第2表 職種・性、年齢階級別", "occ1": "職種第1表 職種（小分類）、性別",
            "occ5": "職種第5表 職種（小分類）、年齢階級別", "ind1": "第1表 年齢階級別（産業計・産業別）"}
    for y, d in FILES.items():
        for k, (sid, kind) in d.items():
            url = BASE.format(sid, kind)
            b = get(url)
            xlsx = b[:2] == b"PK"
            name = f"wage_{y}_{k}.xlsx" if xlsx else f"wage_{y}_{k}.xls.gz"
            if xlsx:
                (RAW / name).write_bytes(b)
            else:
                with gzip.GzipFile(RAW / name, "wb", mtime=0) as f:
                    f.write(b)
            lines.append(f"| {name} | {y}年 賃金構造基本統計調査 一般労働者 {desc[k]} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
            print("saved", name, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450091&tstat=000001011429",
              "- 出典：厚生労働省「賃金構造基本統計調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- .xls.gz は取得した .xls をそのまま gzip で圧縮したもの（`gunzip -k` で元のファイルに戻る）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
