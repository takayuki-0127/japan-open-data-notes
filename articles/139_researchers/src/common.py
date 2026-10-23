"""共通：総務省「科学技術研究調査」企業 第5表「産業、専門別研究者数」（2012〜2025年調査）を読んで、年×産業×専門分野の表にする"""
from pathlib import Path
import io, re, logging, warnings
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省統計局「科学技術研究調査」企業 第5表 産業、専門別研究者数（e-Stat）をもとに作成者が加工して作成"
TIDY = DATA / "researchers_industry_field.csv"

# 専門分野（列）：2012〜2024年は「数学・物理」が1列、2025年は「数学」「物理」に分かれている
FIELDS = ["total", "share", "nat_total", "sci", "math_phys", "info", "chem", "bio", "geo", "eng", "mech", "elec", "civil",
          "material", "textile", "agri", "forestry", "vet", "fishery", "health", "medical", "pharmacy", "social_hum"]
FIELDS_2025 = ["total", "share", "nat_total", "sci", "math", "info", "phys", "chem", "bio", "geo", "eng", "mech", "elec", "civil",
               "material", "textile", "agri", "forestry", "vet", "fishery", "health", "medical", "pharmacy", "social_hum"]
FIELD_JA = {"sci": "理学", "math_phys": "数学・物理", "info": "情報科学", "chem": "化学", "bio": "生物", "geo": "地学",
            "eng": "工学", "mech": "機械・船舶・航空", "elec": "電気・通信", "civil": "土木・建築", "material": "材料", "textile": "繊維",
            "agri": "農学", "forestry": "農林", "vet": "獣医・畜産", "fishery": "水産", "health": "保健", "medical": "医学・歯学",
            "pharmacy": "薬学", "social_hum": "人文・社会科学"}
# 細かい分野（足すと総数になる）
LEAF_FIELDS = ["math_phys", "info", "chem", "bio", "geo", "mech", "elec", "civil", "material", "textile",
               "forestry", "vet", "fishery", "medical", "pharmacy", "social_hum"]


def _num(v):
    s = str(v).strip().replace(",", "")
    if s in ("-", "－", "‐", "―"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan            # X（秘匿）など


def _rows(path):
    b = Path(path).read_bytes()
    if b[:2] == b"PK":
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        return [list(r) for r in wb[wb.sheetnames[0]].iter_rows(values_only=True)]
    import xlrd
    s = xlrd.open_workbook(file_contents=b).sheet_by_index(0)
    return [s.row_values(i) for i in range(s.nrows)]


LABEL = {"研究者数（実数）": "total", "研究者数の産業別構成比": "share", "専門分野_自然科学": "nat_total", "理学": "sci",
         "数学・物理": "math_phys", "数学": "math", "物理": "phys", "情報科学": "info", "化学": "chem", "生物": "bio", "地学": "geo",
         "工学": "eng", "機械・船舶・航空": "mech", "電気･通信": "elec", "電気・通信": "elec", "土木・建築": "civil", "材料": "material",
         "繊維": "textile", "農学": "agri", "農林": "forestry", "獣医・畜産": "vet", "水産": "fishery", "保健": "health",
         "医学・歯学": "medical", "薬学": "pharmacy", "専門分野_人文・社会科学": "social_hum"}


def parse(path, year):
    R = _rows(path)
    out = []
    hdr = None
    if year >= 2021:      # 2021年以降は表頭の名前で列を決める（2022年から「数学」「物理」が分かれる）
        hr = next(r for r in R if any(str(v) in ("数学", "数学・物理") for v in r))
        hdr = {i: LABEL[str(v)] for i, v in enumerate(hr) if str(v) in LABEL}
    for r in R:
        r = list(r)
        txt = [str(v) for v in r]
        if year >= 2021:
            # 例：[... '全国', 階層, 名前, 番号, 総数, 構成比, ...]
            if "全国" not in txt:
                continue
            k = txt.index("全国")
            level, name, no = int(float(r[k + 1])), str(r[k + 2]).strip(), int(float(r[k + 3]))
            rec = dict(year=year, no=no, name=name, level=level)
            for i, c in hdr.items():
                rec[c] = _num(r[i])
            if "math" in rec:
                rec["math_phys"] = rec["math"] + rec["phys"]
            out.append(rec)
            continue
        else:
            # 例：['206', '2012', '', '01', '', 1.0, '', '1　全産業', 534908, ...]
            k = next((i for i, v in enumerate(txt) if re.match(r"^\s*\d+[\s　]+\S", v) and i > 3), None)
            if k is None or not str(r[0]).strip().isdigit():
                continue
            m = re.match(r"^\s*(\d+)[\s　]*(.*)$", txt[k], re.S)
            no, name = int(m.group(1)), m.group(2).replace("\n", "").strip()
            level = None
            vals = r[k + 1:]
        rec = dict(year=year, no=no, name=name, level=level)
        for c, v in zip(FIELDS, vals):
            rec[c] = _num(v)
        out.append(rec)
    df = pd.DataFrame(out)
    return df[df.no <= 49]


def build():
    dfs = [parse(p, int(re.search(r"(\d{4})", p.name).group(1))) for p in sorted(RAW.glob("139_*.k0"))]
    df = pd.concat(dfs, ignore_index=True)
    # 産業名と階層は2021年調査の表（階層の列がある）にそろえる
    ref = df[df.year == 2021].set_index("no")[["name", "level"]]
    df["name"] = df.no.map(ref.name); df["level"] = df.no.map(ref.level)
    keep = ["year", "no", "name", "level", "total", "nat_total", "sci", "eng", "agri", "health"] + LEAF_FIELDS + (["math", "phys"])
    df = df[[c for c in keep if c in df.columns]]
    df.to_csv(TIDY, index=False)
    return df


def load():
    return pd.read_csv(TIDY) if TIDY.exists() else build()


def leaves(df):
    """足し合わせると全産業になる、いちばん細かい産業（男女の再掲は除く）"""
    lv = df[df.year == 2021].set_index("no").level.sort_index()
    nos = [n for n in lv.index if n <= 47]
    out = []
    for i, n in enumerate(nos):
        nxt = lv[nos[i + 1]] if i + 1 < len(nos) else 0
        if n != 1 and nxt <= lv[n]:
            out.append(n)
    return out


SHORT = {"農林水産業": "農林水産", "鉱業，採石業，砂利採取業": "鉱業", "建設業": "建設", "食料品製造業": "食料品",
         "繊維工業": "繊維", "パルプ・紙・紙加工品製造業": "パルプ・紙", "印刷・同関連業": "印刷", "医薬品製造業": "医薬品",
         "総合化学工業": "総合化学", "油脂・塗料製造業": "油脂・塗料", "その他の化学工業": "その他の化学",
         "石油製品・石炭製品製造業": "石油・石炭", "プラスチック製品製造業": "プラスチック", "ゴム製品製造業": "ゴム",
         "窯業・土石製品製造業": "窯業・土石", "鉄鋼業": "鉄鋼", "非鉄金属製造業": "非鉄金属", "金属製品製造業": "金属製品",
         "はん用機械器具製造業": "はん用機械", "生産用機械器具製造業": "生産用機械", "業務用機械器具製造業": "業務用機械",
         "電子部品・デバイス・電子回路製造業": "電子部品・デバイス", "電子応用・電気計測器製造業": "電子応用・計測器",
         "その他の電気機械器具製造業": "その他の電気機械", "情報通信機械器具製造業": "情報通信機械",
         "自動車・同附属品製造業": "自動車", "その他の輸送用機械器具製造業": "その他の輸送機械", "その他の製造業": "その他の製造",
         "電気・ガス・熱供給・水道業": "電気・ガス", "通信業": "通信", "放送業": "放送", "情報サービス業": "情報サービス",
         "インターネット附随・その他の情報通信業": "インターネット附随等", "運輸業，郵便業": "運輸・郵便", "卸売業": "卸売",
         "金融業，保険業": "金融・保険", "学術・開発研究機関": "学術・開発研究機関", "専門サービス業（他に分類されないもの）": "専門サービス",
         "技術サービス業（他に分類されないもの）": "技術サービス", "サービス業（他に分類されないもの）": "その他のサービス"}


def short(name):
    n = str(name).replace("･", "・").replace(",", "，").strip()
    for k, v in SHORT.items():
        if n.startswith(k[:6]):
            return v
    return n
