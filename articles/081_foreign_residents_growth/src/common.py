"""共通：出入国在留管理庁「在留外国人統計」（都道府県別国籍別 2012〜2020年、テーブルデータ 2023〜2025年）を読む"""
from pathlib import Path
import glob, re, logging, warnings
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：出入国在留管理庁「在留外国人統計」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00250012）をもとに作成者が加工して作成"
BIG = ROOT / "data" / "big"   # 10MB を超えるテーブルデータ（リポジトリには入れない）
SSDSE = ROOT / "data" / "ssdse"
PREFS = ["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川","新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄"]


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")


def pref_short(s):
    s = str(s).replace(" ", "").replace("　", "")
    s = re.sub(r"^\d+[：:]", "", s)
    if s in ("北海道",): return s
    if s in ("京都", "京都府"): return "京都"
    if s in ("東京", "東京都"): return "東京"
    return re.sub(r"[府県]$", "", s)


NAT_MAP = {"韓国・朝鮮": "韓国", "朝鮮": "朝鮮", "ベトナム": "ベトナム", "中国": "中国"}


def load_pref_nat():
    """2012-12〜2020-06：都道府県×国籍の在留外国人数（long）"""
    out = []
    for f in sorted(RAW.glob("*_pref_nat_*.xlsx")):
        per = f.name[:7]
        d = pd.read_excel(f, header=None)
        hr = next(i for i in range(10) if "総数" in [str(x).strip() for x in d.iloc[i].tolist()])
        hdr = [str(x).strip() if pd.notna(x) else "" for x in d.iloc[hr]]
        ci = hdr.index("総数")
        body = d.iloc[hr + 1:]
        for _, r in body.iterrows():
            name = r.iloc[ci - 1] if pd.notna(r.iloc[ci - 1]) else (r.iloc[0] if ci >= 1 else None)
            if pd.isna(name): continue
            name = str(name).replace(" ", "").replace("　", "")
            if name in ("総数",) or name.startswith("未定") or name == "": continue
            pn = pref_short(name)
            if pn not in PREFS: continue
            for j in range(ci, len(hdr)):
                if hdr[j] == "" or pd.isna(r.iloc[j]): continue
                out.append((per, pn, hdr[j].replace(" ", ""), pd.to_numeric(r.iloc[j], errors="coerce")))
    x = pd.DataFrame(out, columns=["period", "pref", "nat", "n"])
    return x


def age_start(s):
    """「17_80歳以上」「09_40～44歳」「43歳」などから5歳階級の下限（0,5,…,80）"""
    s = str(s)
    if "_" in s: s = s.split("_", 1)[1]
    m = re.search(r"(\d+)", s)
    if not m: return np.nan
    return float(min(int(m.group(1)) // 5 * 5, 80))


def load_table(cache=True):
    """2023-12〜2025-12：国籍×在留資格×性別×年齢×都道府県（long）"""
    p = ROOT / "data" / "table.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    import openpyxl
    out = []
    for f in sorted(BIG.glob("*_table_*.xlsx")):
        per = f.name[:7]
        wb = openpyxl.load_workbook(f, read_only=True)
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            h = next(it)
            if not h or "在留外国人数" not in [str(v) for v in h if v is not None]: continue
            h = [str(v) for v in h]
            rows = [r for r in it if r and r[0] is not None]
            d = pd.DataFrame(rows, columns=h)
            age = "年齢（５歳階級）" if "年齢（５歳階級）" in d.columns else "年齢"
            d = pd.DataFrame({"period": per, "nat_raw": d["国籍・地域"], "status_raw": d["在留資格"], "sex": d["性別"].astype(str).str[-1],
                              "age_raw": d[age].astype(str), "pref_raw": d["都道府県"], "n": pd.to_numeric(d["在留外国人数"], errors="coerce")})
            out.append(d)
            break
    x = pd.concat(out, ignore_index=True)
    x["nat"] = x.nat_raw.astype(str).str.replace("\u3000", " ").str.split(r"[：:]|\s+").str[-1].str.replace(r"^\d+", "", regex=True)
    x["status"] = x.status_raw.astype(str).str.split("：").str[-1]
    x["pref"] = x.pref_raw.map(pref_short)
    x["age5"] = x.age_raw.map(age_start)
    x.to_pickle(p)
    return x


REGIONS = {"総数", "アジア", "ヨーロッパ", "アフリカ", "北米", "南米", "オセアニア", "無国籍", "その他"}


def nat_group(s):
    s = str(s)
    if s in ("韓国", "朝鮮", "韓国・朝鮮"): return "韓国・朝鮮"
    return s


STATUS_GROUP = [("技能実習", "技能実習"), ("特定技能", "特定技能"), ("技術・人文知識・国際業務", "技術・人文知識・国際業務"), ("留学", "留学"),
                ("永住者の配偶者等", "身分（配偶者・定住者）"), ("特別永住者", "特別永住者"), ("永住者", "永住者"), ("家族滞在", "家族滞在"),
                ("日本人の配偶者等", "身分（配偶者・定住者）"), ("定住者", "身分（配偶者・定住者）")]


def status_group(s):
    for k, v in STATUS_GROUP:
        if str(s).startswith(k): return v
    return "その他"


def pref_pop(year):
    """都道府県の総人口。2012〜2023年は SSDSE-B、2024年は SSDSE-E"""
    if year >= 2024:
        d = pd.read_csv(ROOT / "data" / "ssdse" / "SSDSE-E-2026.csv", encoding="cp932", header=None, dtype=str)
        d = d.iloc[3:]; return pd.Series(pd.to_numeric(d[2]).values, index=d[1].map(pref_short)).drop("全国", errors="ignore")
    d = pd.read_csv(SSDSE / "SSDSE-B-2026.csv", encoding="cp932", header=None, dtype=str)
    d = d[d[0] == str(year)]
    return pd.Series(pd.to_numeric(d[3]).values, index=d[2].map(pref_short))


def muni_pop():
    """市区町村の総人口（SSDSE-A、2020年国勢調査）"""
    d = pd.read_csv(SSDSE / "SSDSE-A-2026.csv", encoding="cp932", header=None, dtype=str).iloc[3:]
    return pd.DataFrame({"code": d[0].str[1:], "pref": d[1].map(pref_short), "name": d[2], "pop": pd.to_numeric(d[3])})
