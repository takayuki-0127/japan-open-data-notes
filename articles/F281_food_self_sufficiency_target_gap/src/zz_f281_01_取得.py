"""F281 01 取得：使った元データの一覧と、手元のファイルの確かめ（md5）。

政府のサイトはこの環境のスクリプトから直接つながらないことがあるため、取得は手元のパソコン（curl）で行い、
data/raw に置いた。ここでは置いたファイルがそろっているかを確かめ、data/raw/MANIFEST.json に md5 を書く。

取得元（2026-11-11 取得）
- 令和7年度食料需給表（概算、2026-08-07公表）Excel：https://www.maff.go.jp/j/zyukyu/fbs/attach/xls/index-4.xlsx → fbs_r7.xlsx
- 食料自給率の推移（1965〜2025年度）：https://www.maff.go.jp/j/zyukyu/zikyu_ritu/attach/xls/012-7.xls → zk_012-7.xls
- 令和7年度食料自給率について（品目別の国産熱量・供給熱量）：https://www.maff.go.jp/j/zyukyu/zikyu_ritu/attach/pdf/012-20.pdf
  → pdftotext -layout の結果を maff_r7_jikyuritsu_item_table.txt に置いた
- 令和6年度食料需給表（確報）の累年表（e-Stat、CSV）：
  https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040422{798,801,805,806,807,808,876,877}&fileKind=1 → estat/e*.csv
  （798 国内生産量、801 国内消費仕向量、805 供給純食料、806 1人1年当たり供給純食料、807 1人1日当たり供給純食料、
    808 1人1日当たり供給熱量、876 品目別自給率の推移、877 総合自給率等の推移）
- 基本計画（数値は手で data/plans*.csv・h27_consumption.csv に書き写し、該当箇所のテキストを plan_excerpts/ に置いた）
  - 平成12年：https://www.maff.go.jp/j/keikaku/k_aratana/pdf/12_keikaku.pdf
  - 平成17年：国立国会図書館 WARP（https://warp.da.ndl.go.jp/20191114/20191101040845/http://www.maff.go.jp/j/keikaku/k_aratana/pdf/20050325_honbun.pdf）
  - 平成22年：WARP（…/20191214/20191201040146/http://www.maff.go.jp/j/keikaku/k_aratana/pdf/kihon_keikaku_22.pdf）
  - 平成27年：WARP（…/20191214/20191201040142/http://www.maff.go.jp/j/keikaku/k_aratana/pdf/1_27keikaku.pdf）
  - 令和2年：https://www.maff.go.jp/j/keikaku/k_aratana/attach/pdf/r2_keikaku-4.pdf（参考資料：過去の計画の一覧を含む）
  - 令和7年：https://www.maff.go.jp/j/keikaku/k_aratana/attach/pdf/index-61.pdf
"""
import hashlib, json, pathlib

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
need = ["fbs_r7.xlsx", "zk_012-7.xls", "maff_r7_jikyuritsu_item_table.txt"] + [f"estat/e{i}.csv" for i in [798, 801, 805, 806, 807, 808, 876, 877]]
man = {}
for f in need + sorted(str(p.relative_to(RAW)) for p in (RAW / "plan_excerpts").glob("*.txt")):
    p = RAW / f
    if not p.exists():
        raise SystemExit(f"見つからない：{p}（上の取得元から置いてください）")
    man[f] = hashlib.md5(p.read_bytes()).hexdigest()
(RAW / "MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
print(len(man), "files ok")
