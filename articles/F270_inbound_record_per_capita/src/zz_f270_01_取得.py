"""F270 01 取得：元データをダウンロードして data/raw に置く。
- 観光庁「訪日外国人消費動向調査」（2011〜2019・2022・2023年）・「インバウンド消費動向調査」（2024・2025年）の暦年の集計表（Excel）
  2011〜2018年は国立国会図書館 WARP に保存された旧ページから取る。
  Excel は大きいので GitHub には入れず、ここで取り直す（md5 は data/raw/MANIFEST_xls.csv）。
- 総務省「消費者物価指数」2020年基準 長期時系列（全国・月次、e-Stat statInfId 000032103842、CSV）
- FRED：年平均為替レート（H.10）、米国の消費者物価（CPIAUCSL）、各国の物価上昇率（世界銀行 FPCPITOTLZG）
- JNTO の国籍/月別 訪日外客数は、F68 で Excel から作った縦長の CSV（2026年10月21日公表版）を写して使う。
"""
import os, sys, hashlib, shutil, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
XLS = os.path.join(RAW, "xls")
os.makedirs(XLS, exist_ok=True)
W = "https://warp.ndl.go.jp/20240302/20240301044436/http://www.mlit.go.jp/"
M = "https://www.mlit.go.jp/kankocho/content/"
SPEND = {  # 年: URL（暦年の集計結果）
    2011: W + "common/000994041.xls", 2012: W + "common/000994340.xls", 2013: W + "common/001032144.xls",
    2014: W + "common/001084270.xls", 2015: W + "common/001173128.xls", 2016: W + "common/001179510.xls",
    2017: W + "common/001226298.xls", 2018: W + "common/001283010.xls", 2019: M + "002020401.xls",
    2022: M + "002021087.xls", 2023: M + "002020300.xls", 2024: M + "002022649.xls", 2025: M + "002025515.xls",
}
FRED = ["AEXJPUS", "AEXCHUS", "AEXKOUS", "AEXTAUS", "AEXHKUS", "AEXTHUS", "AEXSIUS", "AEXMAUS", "AEXINUS",
        "AEXUSUK", "AEXUSEU", "AEXCAUS", "AEXUSAL", "CPIAUCSL"] + \
       ["FPCPITOTLZG" + c for c in ["KOR", "CHN", "HKG", "THA", "SGP", "USA", "GBR", "AUS", "CAN", "DEU", "FRA", "MYS", "IND"]]
CPI = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103842&fileKind=1"
JNTO_SRC = os.path.join(HERE, "..", "..", "F68_inbound_seasonality_clusters", "data", "raw", "jnto_monthly_2003_2026.csv")

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return
    for k in range(3):
        r = subprocess.run(["curl", "-sL", "--max-time", "120", "-o", path, url])
        if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 200:
            return
        time.sleep(3)
    sys.exit("取得に失敗：" + url)

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

if __name__ == "__main__":
    rows = ["year,file,url,md5"]
    for y, u in SPEND.items():
        p = os.path.join(XLS, f"spend_{y}.xls"); get(u, p); time.sleep(1)
        rows.append(f"{y},spend_{y}.xls,{u},{md5(p)}")
    open(os.path.join(RAW, "MANIFEST_xls.csv"), "w").write("\n".join(rows) + "\n")
    for s in FRED:
        get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", os.path.join(RAW, f"fred_{s}.csv"))
    get(CPI, os.path.join(RAW, "cpi_2020base_monthly_estat.csv"))
    dst = os.path.join(RAW, "jnto_monthly_2003_2026.csv")
    if not os.path.exists(dst):
        shutil.copy(JNTO_SRC, dst)
    print("ok")
