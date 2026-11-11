"""F265 01 取得：元データは政府サイトからブラウザで取り、data/raw に置いた（このスクリプトは中身と出典を確かめるだけ）。

- data/raw/mhlw_koyoukintou_male_leave.csv : 厚生労働省「令和7年度雇用均等基本調査」事業所調査 結果概要 図4
    https://www.mhlw.go.jp/toukei/list/dl/71-r07/02.pdf （2026-07-31 公表）
- data/raw/jilpt_g0504_paid_leave.csv : JILPT「早わかり グラフでみる長期労働統計」図4 年次有給休暇
    https://www.jil.go.jp/kokunai/statistics/timeseries/xls/g0504.xlsx （元：厚生労働省「就労条件総合調査」）
- data/raw/lfs_female_25_44_counts.csv : 総務省「労働力調査」長期時系列 表3(3) 年齢階級(5歳階級)別就業者数・表3(1) 15歳以上人口（女、年平均、万人）
    e-Stat statInfId=000001082684 / 000001082682 （2026-01-30 更新）
- data/raw/targets.csv : 目標値。こども家庭庁掲載「少子化社会対策大綱 施策に関する数値目標」、厚生労働省「雇用環境・均等行政の主要指標の動向」（2025-09-08）
"""
import hashlib, pathlib, sys
raw = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
need = ["mhlw_koyoukintou_male_leave.csv", "jilpt_g0504_paid_leave.csv", "lfs_female_25_44_counts.csv", "targets.csv"]
for n in need:
    p = raw / n
    if not p.exists():
        sys.exit(f"missing {p}")
    print(n, p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest())
