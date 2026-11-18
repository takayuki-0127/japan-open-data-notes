"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」（e-Stat の Excel）、高等教育機関の各年度の
「関係学科別 入学者数（大学入学状況）」と「専攻分野別 大学院入学状況」、2000〜2025年度。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
# (調査年度, 中身, statInfId, 表の題)
FILES = [
    (2000, "grad_entrants", "000015170578", "表22 専攻分野別 大学院入学状況"),
    (2000, "ug_entrants", "000015170574", "表18 関係学科別 入学者数"),
    (2001, "grad_entrants", "000012663129", "表22 専攻分野別 大学院入学状況"),
    (2001, "ug_entrants", "000012663125", "表18 関係学科別 入学者数"),
    (2002, "grad_entrants", "000012459909", "表22 専攻分野別 大学院入学状況"),
    (2002, "ug_entrants", "000012459905", "表18 関係学科別 入学者数"),
    (2003, "grad_entrants", "000006499300", "表22 専攻分野別 大学院入学状況"),
    (2003, "ug_entrants", "000006499296", "表18 関係学科別 入学者数"),
    (2004, "grad_entrants", "000002947524", "表22 専攻分野別 大学院入学状況"),
    (2004, "ug_entrants", "000002947520", "表18 関係学科別 入学者数"),
    (2005, "grad_entrants", "000002947037", "表22 専攻分野別 大学院入学状況"),
    (2005, "ug_entrants", "000002947033", "表18 関係学科別 入学者数"),
    (2006, "grad_entrants", "000001226017", "表22 専攻分野別 大学院入学状況"),
    (2006, "ug_entrants", "000001226013", "表18 関係学科別 入学者数"),
    (2007, "grad_entrants", "000001211199", "表22 専攻分野別 大学院入学状況"),
    (2007, "ug_entrants", "000001211195", "表18 関係学科別 入学者数"),
    (2008, "grad_entrants", "000002031011", "表22 専攻分野別 大学院入学状況"),
    (2008, "ug_entrants", "000002031007", "表18 関係学科別 入学者数"),
    (2009, "grad_entrants", "000006196996", "表22 専攻分野別 大学院入学状況"),
    (2009, "ug_entrants", "000006196992", "表18 関係学科別 入学者数"),
    (2010, "grad_entrants", "000008349977", "表22 専攻分野別 大学院入学状況"),
    (2010, "ug_entrants", "000008349973", "表18 関係学科別 入学者数"),
    (2011, "grad_entrants", "000012683853", "表22 専攻分野別 大学院入学状況"),
    (2011, "ug_entrants", "000012683849", "表18 関係学科別 入学者数"),
    (2012, "grad_entrants", "000018428750", "表19 専攻分野別 大学院入学状況"),
    (2012, "ug_entrants", "000018428747", "表16 関係学科別 入学者数"),
    (2013, "grad_entrants", "000023610155", "表19 専攻分野別 大学院入学状況"),
    (2013, "ug_entrants", "000023610152", "表16 関係学科別 入学者数"),
    (2014, "grad_entrants", "000027597245", "表19 専攻分野別 大学院入学状況"),
    (2014, "ug_entrants", "000027597242", "表16 関係学科別 入学者数"),
    (2015, "grad_entrants", "000031358101", "表18 専攻分野別 大学院入学状況"),
    (2015, "ug_entrants", "000031358098", "表15 関係学科別 大学入学状況"),
    (2016, "grad_entrants", "000031504870", "表18 専攻分野別 大学院入学状況"),
    (2016, "ug_entrants", "000031504867", "表15 関係学科別 大学入学状況"),
    (2017, "grad_entrants", "000031656043", "表18 専攻分野別 大学院入学状況"),
    (2017, "ug_entrants", "000031656040", "表15 関係学科別 大学入学状況"),
    (2018, "grad_entrants", "000031776665", "表18 専攻分野別 大学院入学状況"),
    (2018, "ug_entrants", "000031776662", "表15 関係学科別 大学入学状況"),
    (2019, "grad_entrants", "000031894025", "表18 専攻分野別 大学院入学状況"),
    (2019, "ug_entrants", "000031894022", "表15 関係学科別 大学入学状況"),
    (2020, "grad_entrants", "000032040276", "表18 専攻分野別 大学院入学状況"),
    (2020, "ug_entrants", "000032040273", "表15 関係学科別 大学入学状況"),
    (2021, "grad_entrants", "000032155540", "表18 専攻分野別 大学院入学状況"),
    (2021, "ug_entrants", "000032155537", "表15 関係学科別 大学入学状況"),
    (2022, "grad_entrants", "000032265035", "表18 専攻分野別 大学院入学状況"),
    (2022, "ug_entrants", "000032265032", "表15 関係学科別 大学入学状況"),
    (2023, "grad_entrants", "000040128623", "表18 専攻分野別 大学院入学状況"),
    (2023, "ug_entrants", "000040128620", "表15 関係学科別 大学入学状況"),
    (2024, "grad_entrants", "000040230326", "表18 専攻分野別 大学院入学状況"),
    (2024, "ug_entrants", "000040230323", "表15 関係学科別 大学入学状況"),
    (2025, "grad_entrants", "000040392737", "表18 専攻分野別 大学院入学状況"),
    (2025, "ug_entrants", "000040392734", "表15 関係学科別 大学入学状況"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    out = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
           "| ファイル | 調査年度 | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|---|"]
    for y, key, sid, title in FILES:
        req = urllib.request.Request(BASE.format(sid), headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        name = f"{key}_{y}{ext}"
        (RAW / name).write_bytes(b)
        out.append(f"| {name} | {y} | {title} | {BASE.format(sid)} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    out += ["", "出典：文部科学省「学校基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001&tstat=000001011528）。",
            "各年度5月1日時点。ug_entrants＝関係学科別の大学（学部）入学者、grad_entrants＝専攻分野別の大学院入学状況。"]
    (RAW / "SOURCES.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
