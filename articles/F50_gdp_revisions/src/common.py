"""共通の設定（パス・フォント・乱数の種・CSV の読み取り）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

QMAP = {"1": 1, "4": 2, "7": 3, "10": 4}


def release_id(menu_url):
    """メニューの URL から公表回（例 qe262_2）を取り出す"""
    m = re.search(r"/(qe\d{3}[^/]*)/gdemenuja(r)?\.html", menu_url)
    if not m:
        return None
    rid = m.group(1)
    if m.group(2) and not rid.endswith("r"):
        rid += "r"  # gdemenujar.html は訂正版
    return rid


def release_info(rid):
    """qe262_2 → 対象四半期 2026Q2・2次速報。qe201_2r は 2次の再公表"""
    m = re.fullmatch(r"qe(\d{2})(\d)(_2)?(r)?", rid)
    yy, q, sec, r = m.groups()
    return {"rid": rid, "ref": pd.Period(f"{2000 + int(yy)}Q{q}", "Q"),
            "stage": 2 if sec else 1, "reissue": bool(r)}


def parse_series(csv_text, col_pattern=r"国内総(生産|支出)|GDE|GDP"):
    """速報の CSV から GDP の列だけを四半期の Series にする（最初の表だけ）"""
    # 改行を含むセル（"民間最終\n消費支出" など）があるので csv モジュールで読む
    text = csv_text.replace("\r", "")
    import csv, io
    rows = list(csv.reader(io.StringIO(text)))
    gcol = None
    for r in rows[:12]:
        for j, c in enumerate(r):
            if j > 0 and re.search(col_pattern, c.replace("\n", "")):
                gcol = j
                break
        if gcol is not None:
            break
    if gcol is None:
        raise ValueError("GDP の列が見つからない")
    out, year, started = {}, None, False
    for r in rows:
        if not r or not r[0].strip():
            if started and len(out) > 8 and all(not c.strip() for c in r):
                break
            continue
        lab = r[0].strip()
        m = re.match(r"(\d{4})/\s*(\d{1,2})\s*-", lab)
        if m:
            year, mon = int(m.group(1)), m.group(2)
        else:
            m2 = re.match(r"(\d{1,2})\s*-\s*\d{1,2}", lab)
            if not m2 or year is None:
                continue
            mon = m2.group(1)
        if mon not in QMAP:
            continue
        started = True
        v = r[gcol].strip() if gcol < len(r) else ""
        per = pd.Period(f"{year}Q{QMAP[mon]}", "Q")
        try:
            out[per] = float(v)
        except ValueError:
            out[per] = np.nan
    return pd.Series(out).sort_index()


def recession_quarters():
    """景気基準日付から、後退期（山の翌月〜谷）を含む月が2か月以上ある四半期を後退期とする"""
    c = pd.read_csv(RAW / "cycle_dates.csv")
    c["month"] = pd.PeriodIndex(c["month"], freq="M")
    months = pd.period_range("1975-01", "2026-12", freq="M")
    flag = pd.Series(0, index=months)
    peaks = c[c.type == "peak"].month.tolist()
    troughs = c[c.type == "trough"].month.tolist()
    for p in peaks:
        t = [x for x in troughs if x > p]
        end = t[0] if t else months[-1]
        flag[(flag.index > p) & (flag.index <= end)] = 1
    q = flag.groupby(flag.index.asfreq("Q")).sum()
    return (q >= 2).astype(int)
