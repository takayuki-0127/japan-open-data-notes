"""共通の設定（パス・フォント・X-13 の呼び出し・日本の祝日の変数）"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

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

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

COL = {"公表値": "#202124", "X-13（自作）": "#1a73e8", "STL": "#e37400", "原数値": "#9aa0a6",
       "X-11（回帰なし）": "#188038"}


# ---------------------------------------------------------------- X-13
def x13_binary():
    """pip の x13as パッケージに入っている X-13ARIMA-SEATS 本体（米国センサス局）を探す"""
    try:
        import x13as  # noqa
        p = Path(x13as.__file__).parent / "_bin" / "x13as"
        if p.exists():
            return str(p)
    except ImportError:
        pass
    p = shutil.which("x13as")
    if p:
        return p
    raise FileNotFoundError("X-13 が見つかりません。pip install x13as を実行してください")


def jp_holiday_var(start, end):
    """平日に当たる祝日（振替休日・国民の休日を含む）の日数から、同じ月の平均を引いた変数。
    経済産業省の鉱工業指数と同じ作り方（各年各月の平日祝日数 − 同じ月の平均）。平均は渡した期間全体でとる。"""
    import holidays
    idx = pd.period_range(start, end, freq="M")
    years = range(idx[0].year, idx[-1].year + 1)
    jp = holidays.Japan(years=years)
    cnt = []
    for p in idx:
        days = pd.date_range(p.start_time, p.end_time, freq="D")
        cnt.append(sum(1 for d in days if d.weekday() < 5 and d.date() in jp))
    s = pd.Series(cnt, index=idx, dtype=float)
    return s - s.groupby(s.index.month).transform("mean")


def _fmt(vals):
    return "\n".join(f"{v:.6f}" for v in vals)


def run_x13(y, *, mode="regarima", transform="log", td=False, holiday=False, lpyear=False,
            arima="auto", outliers=True, fixed_outliers=(), span=None, maxlead=14,
            sigmalim=None, seasonalma=None, name="s"):
    """X-13ARIMA-SEATS（X-11 方式）で季節調整する。
    y: 月次の pd.Series（index は月初の Timestamp）
    mode: "regarima"（事前調整あり）または "x11"（X-11 デフォルト：ARIMA の予測も回帰も使わない）
    戻り値: dict（sa, sf: 季節要素×暦要素, cal: 暦要素, fct: 予測, est: 推定値の表, model）"""
    y = y.dropna()
    if span is not None:
        y = y[(y.index >= pd.Timestamp(span[0])) & (y.index <= pd.Timestamp(span[1]))]
    start = y.index[0]
    b = x13_binary()
    d = Path(tempfile.mkdtemp(prefix="x13_"))
    lines = [f'series{{title="{name}" start={start.year}.{start.month} period=12 data=({_fmt(y.values)})}}']
    if transform == "log":
        lines.append("transform{function=log}")
    else:
        lines.append("transform{function=none}")
    if mode == "regarima":
        regs, user, utype = [], [], []
        if td:
            regs.append("td1coef")
        if lpyear and not td:   # td1coef を使うときは、うるう年は X-13 が自動で扱う（対数変換時は事前調整）
            regs.append("lpyear")
        for o in fixed_outliers:
            regs.append(o)
        reg = ""
        if regs:
            reg += f"variables=({' '.join(regs)}) "
        if holiday:
            end = (y.index[-1] + pd.DateOffset(months=maxlead + 2))
            h = jp_holiday_var(y.index[0].strftime("%Y-%m"), end.strftime("%Y-%m"))
            reg += (f"user=(hol) usertype=(holiday) start={start.year}.{start.month} "
                    f"data=({_fmt(h.values)}) ")
        if reg:
            lines.append(f"regression{{{reg}save=(td hol) }}")
        if arima == "auto":
            lines.append("automdl{}")
        else:
            lines.append(f"arima{{model={arima}}}")
        if outliers:
            lines.append("outlier{types=(ao ls)}")
        lines.append("estimate{save=(est)}")
        lines.append(f"forecast{{maxlead={maxlead}}}")
    x11 = "x11{save=(d10 d11 d16 d18)"
    if transform != "log":
        x11 += " mode=add"
    if sigmalim:
        x11 += f" sigmalim=({sigmalim[0]},{sigmalim[1]})"
    if seasonalma:
        x11 += f" seasonalma={seasonalma}"
    if mode == "regarima":
        x11 += " appendfcst=yes"
    x11 += "}"
    lines.append(x11)
    (d / "s.spc").write_text("\n".join(lines) + "\n")
    r = subprocess.run([b, "s", "-s"], cwd=d, capture_output=True, text=True)

    def tab(ext):
        p = d / f"s.{ext}"
        if not p.exists():
            return None
        t = pd.read_csv(p, sep="\t", skiprows=2, header=None, names=["date", "v"])
        t["date"] = pd.to_datetime(t["date"].astype(str), format="%Y%m")
        return t.set_index("date")["v"]

    mult = 100 if transform == "log" else 1
    sf, seas, cal = tab("d16"), tab("d10"), tab("d18")
    out = {"sa": tab("d11"), "sf": None if sf is None else sf * mult, "seas": None if seas is None else seas * mult,
           "cal": None if cal is None else cal * mult,
           "est": None, "model": None, "ok": (d / "s.d11").exists(), "err": ""}
    if not out["ok"]:
        out["err"] = (d / "s.err").read_text(errors="ignore")[-2000:] if (d / "s.err").exists() else r.stderr
    estp = d / "s.est"
    if estp.exists():
        rows, sec = [], None
        for ln in estp.read_text(errors="ignore").splitlines():
            if ln.startswith("$"):
                sec = ln.strip()
                continue
            parts = ln.split("\t")
            if sec == "$regression$estimates:" and len(parts) >= 4 and parts[0] not in ("group", "-----"):
                rows.append(("reg", parts[0], parts[1], float(parts[2].replace("E", "e")), float(parts[3].replace("E", "e"))))
            if sec == "$arima$estimates:" and len(parts) >= 6 and parts[0] not in ("operator", "--------"):
                rows.append(("arima", f"{parts[0]} {parts[1]}", f"lag{int(parts[3])}", float(parts[4].replace("E", "e")), float(parts[5].replace("E", "e"))))
        out["est"] = pd.DataFrame(rows, columns=["part", "group", "variable", "estimate", "se"])
    udg = d / "s.udg"
    if udg.exists():
        for ln in udg.read_text(errors="ignore").splitlines():
            if ln.startswith("arimamdl:"):
                out["model"] = ln.split(":", 1)[1].strip()
            if ln.startswith("outlier.identified:") or ln.startswith("nfinaloutlier:"):
                out.setdefault("outl", ln)
    shutil.rmtree(d, ignore_errors=True)
    return out


def stl_adjust(y, transform="log", seasonal=13, robust=True):
    from statsmodels.tsa.seasonal import STL
    z = np.log(y) if transform == "log" else y.copy()
    z = z.asfreq("MS")
    r = STL(z, period=12, seasonal=seasonal, robust=robust).fit()
    if transform == "log":
        return np.exp(z - r.seasonal), np.exp(r.seasonal) * 100
    return z - r.seasonal, r.seasonal


def mom(s):
    return s.pct_change() * 100


def compare(mine, pub, start, end, rate=False, ndigits=None):
    """自作と公表の季節調整値を比べる指標（rate=True のときは差をポイントで。ndigits を渡すと自作を公表と同じ桁に丸めて比べる）"""
    idx = (pub.index >= pd.Timestamp(start)) & (pub.index <= pd.Timestamp(end))
    p = pub[idx]
    m = mine.reindex(p.index)
    if ndigits is not None:
        m = m.round(ndigits)
    if rate:
        lev = (m - p).abs()
        dm, dp = m.diff(), p.diff()
        unit = "pt"
    else:
        lev = (np.log(m) - np.log(p)).abs() * 100
        dm, dp = mom(m), mom(p)
        unit = "%"
    ok = dm.notna() & dp.notna()
    sign = (np.sign(dm[ok]) == np.sign(dp[ok])).mean() * 100
    return {"水準の差の平均": lev.mean(), "水準の差の最大": lev.max(),
            "前月比の差の平均": (dm[ok] - dp[ok]).abs().mean(),
            "前月比の相関": np.corrcoef(dm[ok], dp[ok])[0, 1] if ok.sum() > 2 else np.nan,
            "前月比の向きの一致率": sign, "単位": unit, "月数": int(p.notna().sum())}
