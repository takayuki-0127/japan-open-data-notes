"""01 取得：元データの確認（ネットワークは使わない）。
data/raw の各ファイルは次から取った（README の「データ」参照）。
- jma_amedas_extreme_counts.csv：気象庁「大雨や猛暑日など（極端現象）のこれまでの変化」の数値ファイル
  https://www.data.jma.go.jp/cpdinfo/extreme/csv/{amdhour50mm,amdhour80mm,amdhour100mm,amd3hour100mm,amd3hour150mm,amdday200mm,amdday300mm}_p.csv
  （2026-11-11 取得、1976〜2025年の年間回数、アメダス1,300地点あたり）。値だけを1行ずつ並べ直した
- giroj_revisions.csv：損害保険料率算出機構「火災保険参考純率改定のご案内」5回分の PDF から手で転記（PDF の md5 を併記）
- giaj_events_from_F256.csv / deflator_from_F256.csv：F256 で整理した日本損害保険協会の支払保険金調査と建設工事費デフレーター
- giroj_fire_pref_from_F272.csv：F272 で整理した「火災保険・地震保険の概況」第2表（住宅物件・都道府県別）
"""
import hashlib, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
man = {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(R.glob("*.csv"))}
(R.parent / "MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
print(json.dumps(man, ensure_ascii=False, indent=1))
