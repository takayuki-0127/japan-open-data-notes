"""共通：経済構造実態調査（製造業事業所調査）「品目別」第3表（品目別・都道府県別の出荷金額）を読む"""
from pathlib import Path
import re, io, logging, warnings, unicodedata
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA, FIG, RES = ROOT / "data" / "raw", ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"
SOURCE = "出典：総務省・経済産業省「経済構造実態調査（製造業事業所調査）」品目別統計表（e-Stat）をもとに作成者が加工して作成"
FILES = {2024: "128_2025_hinmoku.xls", 2021: "128_2022_hinmoku.xls"}   # 実績年: ファイル（2025年調査＝2024年実績）


def _parse(path, year):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(open(path, "rb").read()), read_only=True, data_only=True)
    out = []
    for i, r in enumerate(wb["第３表"].iter_rows(values_only=True)):
        if i < 10 or r[3] is None:
            continue
        v = r[10]
        out.append((year, str(r[3]), str(r[4]).strip(), str(r[5]), str(r[6]).strip(),
                    np.nan if v in ("X", "***", None, "") else float(v), v == "X", r[11]))
    return pd.DataFrame(out, columns=["year", "item_code", "item", "pref_code", "pref", "value_mil_yen", "secret", "establishments"])


def load():
    """品目×都道府県の出荷金額（百万円）。value が空で secret=True は秘匿（X）。
    data/ には容量を抑えるため、品目名・県名を別ファイルにして、年×品目コードの範囲で分けて置いている。"""
    parts = sorted(DATA.glob("ship_*.csv"))
    if parts:
        d = pd.concat([pd.read_csv(f, dtype={"item_code": str, "pref_code": str}) for f in parts], ignore_index=True)
        items = pd.read_csv(DATA / "items.csv", dtype={"item_code": str})
        prefs = pd.read_csv(DATA / "prefs.csv", dtype={"pref_code": str})
        d = d.merge(items, on=["year", "item_code"], how="left").merge(prefs, on="pref_code", how="left")
        d["secret"] = d["secret"].astype(bool)
        return d[["year", "item_code", "item", "pref_code", "pref", "value_mil_yen", "secret", "establishments"]]
    df = pd.concat([_parse(RAW / f, y) for y, f in FILES.items()], ignore_index=True)
    df[["year", "item_code", "item"]].drop_duplicates().to_csv(DATA / "items.csv", index=False)
    df[["pref_code", "pref"]].drop_duplicates().sort_values("pref_code").to_csv(DATA / "prefs.csv", index=False)
    out = df[["year", "item_code", "pref_code", "value_mil_yen", "secret", "establishments"]].copy()
    out["secret"] = out["secret"].astype(int)
    for y, g in out.groupby("year"):
        for k, gg in g.groupby(g.item_code.str[:2] < "26"):
            gg.to_csv(DATA / f"ship_{y}_{'a' if k else 'b'}.csv", index=False)
    return df


def concentration(df):
    """品目ごとに全国計と、公表された都道府県の値から集中度を計算する。
    秘匿（X）の県の合計＝全国計−公表値の合計（残り）。
    HHI_low：残りを秘匿の県で等分したとき、HHI_high：残りが1県にまとまっていたとき。
    top1_low：公表された県の最大値のシェア、top1_high：max(公表最大, 残り)のシェア。"""
    rows = []
    for (y, code, item), g in df.groupby(["year", "item_code", "item"]):
        nat = g[g.pref_code == "00"]
        if nat.empty or pd.isna(nat.value_mil_yen.iloc[0]) or nat.value_mil_yen.iloc[0] <= 0:
            continue
        T = nat.value_mil_yen.iloc[0]
        p = g[g.pref_code != "00"]
        prod = p[(p.value_mil_yen.fillna(0) > 0) | p.secret]
        disc = prod.value_mil_yen.dropna()
        nx = int(prod.secret.sum())
        rem = max(T - disc.sum(), 0.0)
        s = disc / T
        hhi_low = (s ** 2).sum() + (nx * (rem / T / nx) ** 2 if nx else 0)
        hhi_high = (s ** 2).sum() + (rem / T) ** 2
        top = prod.loc[disc.idxmax(), "pref"] if len(disc) else None
        rows.append({"year": y, "item_code": code, "item": item, "total_mil_yen": T, "n_pref": len(prod),
                     "n_secret": nx, "secret_share": rem / T, "top_pref": top, "top1_low": disc.max() / T if len(disc) else np.nan,
                     "top1_high": max(disc.max() if len(disc) else 0, rem) / T, "hhi_low": hhi_low * 1e4, "hhi_high": hhi_high * 1e4,
                     "establishments": nat.establishments.iloc[0]})
    return pd.DataFrame(rows)
