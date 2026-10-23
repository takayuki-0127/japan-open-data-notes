"""共通：厚生労働省「被保護者調査」（月次調査）の年度別 Excel（2012〜2024年度）を読む

使う表（各年度）
- 第5表  現に保護を受けた世帯数，月・１か月平均×世帯区分、世帯類型別        -> fy<年度>_ruikei
- 第9表  被保護実人員及び保護率（人口千対），都道府県－指定都市－中核市×月  -> fy<年度>_hogoritsu
- 第19表 保護の申請、取下げ、却下、…保護開始世帯数、…廃止世帯数，月×市部－郡部別 -> fy<年度>_shinsei
"""
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
# 年度ごとの Excel（39本）は GitHub では data/hogo_raw.zip にまとめて置いている。初回に展開する
if not any(RAW.glob("fy*_ruikei.*")) and (ROOT / "data" / "hogo_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "hogo_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：厚生労働省「被保護者調査」（e-Stat、https://www.e-stat.go.jp/stat-search/files?toukei=00450312）をもとに作成者が加工して作成"
FYS = list(range(2012, 2025))
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
SEIREI = {"札幌市": "北海道", "仙台市": "宮城県", "さいたま市": "埼玉県", "千葉市": "千葉県", "横浜市": "神奈川県", "川崎市": "神奈川県",
          "相模原市": "神奈川県", "新潟市": "新潟県", "静岡市": "静岡県", "浜松市": "静岡県", "名古屋市": "愛知県", "京都市": "京都府",
          "大阪市": "大阪府", "堺市": "大阪府", "神戸市": "兵庫県", "岡山市": "岡山県", "広島市": "広島県", "北九州市": "福岡県",
          "福岡市": "福岡県", "熊本市": "熊本県"}
CHUKAKU = {"函館市": "北海道", "旭川市": "北海道", "青森市": "青森県", "八戸市": "青森県", "盛岡市": "岩手県", "秋田市": "秋田県",
           "山形市": "山形県", "福島市": "福島県", "郡山市": "福島県", "いわき市": "福島県", "水戸市": "茨城県", "宇都宮市": "栃木県",
           "前橋市": "群馬県", "高崎市": "群馬県", "川越市": "埼玉県", "川口市": "埼玉県", "越谷市": "埼玉県", "船橋市": "千葉県",
           "柏市": "千葉県", "八王子市": "東京都", "横須賀市": "神奈川県", "富山市": "富山県", "金沢市": "石川県", "福井市": "福井県",
           "甲府市": "山梨県", "長野市": "長野県", "松本市": "長野県", "岐阜市": "岐阜県", "豊橋市": "愛知県", "岡崎市": "愛知県",
           "一宮市": "愛知県", "豊田市": "愛知県", "大津市": "滋賀県", "豊中市": "大阪府", "吹田市": "大阪府", "高槻市": "大阪府",
           "枚方市": "大阪府", "八尾市": "大阪府", "寝屋川市": "大阪府", "東大阪市": "大阪府", "姫路市": "兵庫県", "尼崎市": "兵庫県",
           "明石市": "兵庫県", "西宮市": "兵庫県", "奈良市": "奈良県", "和歌山市": "和歌山県", "鳥取市": "鳥取県", "松江市": "島根県",
           "倉敷市": "岡山県", "呉市": "広島県", "福山市": "広島県", "下関市": "山口県", "高松市": "香川県", "松山市": "愛媛県",
           "高知市": "高知県", "久留米市": "福岡県", "長崎市": "長崎県", "佐世保市": "長崎県", "大分市": "大分県", "宮崎市": "宮崎県",
           "鹿児島市": "鹿児島県", "那覇市": "沖縄県"}
TYPES = ["高齢者世帯", "母子世帯", "障害者世帯", "傷病者世帯", "その他の世帯"]


def _n(s):
    return re.sub(r"[\s　]", "", str(s))


def _file(fy, kind):
    f = sorted(glob.glob(str(RAW / f"fy{fy}_{kind}.xls*")))
    if not f: raise FileNotFoundError(f"fy{fy}_{kind}")
    return f[0]


def _monthly_block(d):
    """「総数」の行を探し、その次の12行（4月〜3月）を返す。数値の最初の列番号も返す"""
    isnum = lambda v: isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v)
    r0 = next(i for i in range(len(d)) if any(_n(d.iat[i, c]) == "総数" for c in (0, 1)) and any(isnum(v) for v in d.iloc[i]))
    c0 = next(c for c in range(d.shape[1]) if isnum(d.iat[r0, c]))
    body = d.iloc[r0 + 1:r0 + 13]
    lab = _n(d.iat[r0 + 13, 0])
    assert "平均" in lab, lab
    head = ["".join(_n(x) for x in d.iloc[:r0, c] if not pd.isna(x)) for c in range(d.shape[1])]
    return body, c0, head


def load_types(cache=True):
    """世帯類型別の被保護世帯数（月次、2012年4月〜2025年3月）"""
    p = ROOT / "data" / "types_monthly.csv"
    if cache and p.exists(): return pd.read_csv(p, parse_dates=["month"])
    out = []
    for fy in FYS:
        d = pd.read_excel(_file(fy, "ruikei"), header=None)
        body, c0, head = _monthly_block(d)
        # 列の並び：総数（計・高齢者・母子・障害者・傷病者・その他・医療扶助単給再掲）、単身者世帯（計・高齢者・…）
        want = {"total": (0, ""), "高齢者世帯": (1, "高齢"), "母子世帯": (2, "母子"), "障害者世帯": (3, "障害"),
                "傷病者世帯": (4, "傷病"), "その他の世帯": (5, "その他"), "単身計": (7, "単身"), "単身高齢者世帯": (8, "高齢")}
        for k, (o, tok) in want.items():
            assert tok in head[c0 + o], (fy, k, head[c0 + o])
        assert "２人以上" in head[c0 + 13] and "医療" in head[c0 + 6] and "医療" in head[c0 + 12]
        for i in range(12):
            m = pd.Timestamp(fy + (i >= 9), (i + 3) % 12 + 1, 1)
            row = {"fy": fy, "month": m}
            for k, (o, _) in want.items(): row[k] = int(body.iat[i, c0 + o])
            out.append(row)
    x = pd.DataFrame(out)
    x.to_csv(p, index=False)
    return x


def load_flow(cache=True):
    """申請件数・保護開始世帯数・保護廃止世帯数（月次、全国）"""
    p = ROOT / "data" / "flow_monthly.csv"
    if cache and p.exists(): return pd.read_csv(p, parse_dates=["month"])
    out = []
    for fy in FYS:
        d = pd.read_excel(_file(fy, "shinsei"), header=None)
        body, c0, head = _monthly_block(d)
        want = {"申請件数": (0, "申請件数総数"), "開始世帯数": (12, "保護開始世帯数総数"), "廃止世帯数": (18, "保護廃止世帯数総数")}
        for k, (o, tok) in want.items():
            assert tok in head[c0 + o].replace("（世帯）", "").replace("（件）", ""), (fy, k, head[c0 + o])
        for i in range(12):
            m = pd.Timestamp(fy + (i >= 9), (i + 3) % 12 + 1, 1)
            row = {"fy": fy, "month": m}
            for k, (o, _) in want.items(): row[k] = int(body.iat[i, c0 + o])
            out.append(row)
    x = pd.DataFrame(out)
    x.to_csv(p, index=False)
    return x


def load_units(cache=True):
    """都道府県（指定都市・中核市を除く）・指定都市・中核市ごとの被保護実人員（月次）と年度の保護率"""
    p = ROOT / "data" / "units_fy.csv"
    if cache and p.exists(): return pd.read_csv(p)
    out = []
    for fy in FYS:
        d = pd.read_excel(_file(fy, "hogoritsu"), header=None)
        for i in range(len(d)):
            names = [_n(d.iat[i, c]) for c in (0, 1) if isinstance(d.iat[i, c], str)]
            name = next((s for s in names if s in PREFS or s in SEIREI or s in CHUKAKU or s == "全国"), None)
            if name is None: continue
            # 数値は右端の15列（12か月累計・4月〜3月・1か月平均・年度保護率）。年度途中に中核市になった市は「-」がある
            nums = [float(v) if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool) else np.nan
                    for v in d.iloc[i, -15:].tolist()]
            kind = "全国" if name == "全国" else "都道府県" if name in PREFS else "指定都市" if name in SEIREI else "中核市"
            pref = name if kind in ("全国", "都道府県") else (SEIREI.get(name) or CHUKAKU.get(name))
            row = {"fy": fy, "kind": kind, "name": name, "pref": pref, "total12": nums[0], "avg": nums[13], "rate": nums[14]}
            for j in range(12): row[f"m{j + 1:02d}"] = nums[1 + j]
            out.append(row)
    x = pd.DataFrame(out)
    x.to_csv(p, index=False)
    return x


def pref_rates(units=None):
    """都道府県全体（指定都市・中核市を含む）の保護率（人口千対）

    実人員：都道府県（市を除く）と県内の指定都市・中核市の月ごとの値を足し、12か月で平均する
    人口  ：各単位の「1か月平均の実人員÷年度保護率×1000」の合計で近似する（保護率は多くの年度で小数1位に丸め）
    """
    u = load_units() if units is None else units
    u = u[u.kind != "全国"].copy()
    u["pop"] = u["avg"] / u["rate"] * 1000
    ms = [f"m{j:02d}" for j in range(1, 13)]
    g = u.groupby(["fy", "pref"]).agg(**{m: (m, "sum") for m in ms}, pop=("pop", "sum")).reset_index()
    g["avg"] = g[ms].mean(axis=1)
    g["rate"] = g["avg"] / g["pop"] * 1000
    return g[["fy", "pref", "avg", "pop", "rate"]]
