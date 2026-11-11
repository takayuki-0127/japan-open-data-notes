"""01 取得：前の2回（F246・F247）の成果物を data/ に写す。公開データの新しい取得はなし（市場の前年比は F231 の取得データの写しを使う）。

- F247 の mart（店×月・会員の月次・dim）：コミット e8ba90f 時点の articles/F247_data_mart_fictional_retail/mart/
- F247 の会計の店×月（売上高。締めの時点で「届いた割合」を出すのに使う）：同じコミットの data/raw_synth/acct_store_month.csv
- F246 の結果（偶然の幅・曜日の並びの効果）：コミット 3006b82 時点の articles/F246_kpi_definitions_fictional_retail/results/
- 市場の前年比（参考）：経済産業省「商業動態統計」スーパー販売額（F231 で取得し F246 の data/raw に写したもの）から、スーパーの合計だけを data/in/market_super_monthly.csv に
- リポジトリの隣のフォルダ（../F246_*, ../F247_*）があればそこから写し、なければ GitHub から取る。
会社・数字はすべて架空（合成データ）。
"""
import pathlib, shutil, urllib.request, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT.parent
OUT = ROOT / "data" / "in"; OUT.mkdir(parents=True, exist_ok=True)
GH = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/"
SRC = {
    "F247": ("e8ba90f", "F247_data_mart_fictional_retail", "mart",
             ["store_month.csv", "fact_member_month.csv", "dim_store.csv", "dim_date.csv"]),
    "F247raw": ("e8ba90f", "F247_data_mart_fictional_retail", "data/raw_synth", ["acct_store_month.csv"]),
    "F246": ("3006b82", "F246_kpi_definitions_fictional_retail", "results",
             ["C_noise_by_grain.csv", "D_calendar_adjust.csv"]),
}

for key, (commit, folder, sub, files) in SRC.items():
    for f in files:
        dst = OUT / f
        local = ART / folder / sub / f
        if local.exists():
            shutil.copyfile(local, dst)
        elif not dst.exists():
            urllib.request.urlretrieve(f"{GH}{commit}/articles/{folder}/{sub}/{f}", dst)
        print(key, f, dst.stat().st_size, hashlib.md5(dst.read_bytes()).hexdigest()[:10])

# 市場の前年比（参考の行）：経済産業省「商業動態統計」スーパー販売額（F246 の data/raw にある F231 の取得データの写し）
f = "sales_monthly_6types.csv"; tmp = OUT / f
local = ART / "F246_kpi_definitions_fictional_retail" / "data" / "raw" / f
if local.exists():
    shutil.copyfile(local, tmp)
else:
    urllib.request.urlretrieve(f"{GH}3006b82/articles/F246_kpi_definitions_fictional_retail/data/raw/{f}", tmp)
import pandas as pd
s = pd.read_csv(tmp); s = s[(s["業態"] == "スーパー") & (s["品目"] == "合計")][["ym", "販売額_百万円"]]
s["前年比_%"] = (s["販売額_百万円"] / s["販売額_百万円"].shift(12) - 1) * 100
s[s.ym >= "2022-04"].to_csv(OUT / "market_super_monthly.csv", index=False, encoding="utf-8-sig"); tmp.unlink()
print("market", len(s), s.ym.min(), s.ym.max())
