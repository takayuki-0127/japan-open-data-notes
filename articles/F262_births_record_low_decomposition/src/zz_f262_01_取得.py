"""01 取得：元データの確認（取得はブラウザで行った。ここでは置き場所・大きさ・md5 を確かめて記録する）

取得元（2026-11-11 取得）
- 国立社会保障・人口問題研究所「人口統計資料集（2026年版）」表4-7・4-8・4-1・4-2
  https://www.ipss.go.jp/syoushika/tohkei/Popular/Popular2026.asp?chap=4
  （Excel から HTML に書き出された各シートの表を、タブ区切りの文字にして1つのファイル ipss_2026_T04.txt に保存）
- 総務省統計局「人口推計」長期時系列データ（平成12年～令和2年）第3表（statInfId=000013168603）
  各年10月1日現在人口 第10表 都道府県、年齢（5歳階級）、男女別人口（2021: 000032191051, 2022: 000040045496,
  2023: 000040166082, 2024: 000040268918） https://www.e-stat.go.jp/
- 厚生労働省「令和7年(2025)人口動態統計（確定数）の概況」統計表 06_hyoR07.xlsx・結果の概要 02_kek.pdf（2026-09-30 公表）
  https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/kakutei25/index.html
"""
import hashlib, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
files = ["ipss_2026_T04.txt", "estat_pop_t3_2000_2020.xlsx", "estat_pop_y2021.xlsx", "estat_pop_y2022.xlsx",
         "estat_pop_y2023.xlsx", "estat_pop_y2024.xlsx", "mhlw_kakutei25_06_hyoR07.xlsx", "mhlw_kakutei25_02_kek.pdf"]
out = {}
for f in files:
    p = R / f
    assert p.exists(), f"missing {p}"
    out[f] = {"bytes": p.stat().st_size, "md5": hashlib.md5(p.read_bytes()).hexdigest()}
(R / "MANIFEST.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
