"""01 取得：新しい取得はしない。F256（自然災害の保険金）で整えたデータを data/raw にコピーする。
元：articles/F256_natural_disaster_insurance_payouts/（同じリポジトリ）。出典は README の表。
このリポジトリを丸ごと持っていれば、F256 のフォルダから読む。なければ data/raw に入っている同じファイルを使う。"""
import pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
F256 = ROOT.parent / "F256_natural_disaster_insurance_payouts"
pairs = [("results/events_adjusted.csv", "f256_events_adjusted.csv"),   # 35事故（2012〜2025年度）、名目・件数・発生年月・種類
         ("data/processed/top10.csv", "f256_top10.csv"),                 # 上位10事故（1991年以降、名目）
         ("data/processed/deflator.csv", "f256_deflator.csv"),           # 建設工事費デフレーター・CPI（年度）
         ("data/processed/dwellings.csv", "f256_dwellings.csv")]         # 住宅数・世帯数（住宅・土地統計調査）
for src, dst in pairs:
    s = F256 / src
    if s.exists():
        shutil.copyfile(s, RAW / dst); print("copied", src)
    else:
        assert (RAW / dst).exists(), f"{dst} がない"; print("use existing", dst)
