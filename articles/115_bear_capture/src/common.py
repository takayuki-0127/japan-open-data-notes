"""共通：環境省「鳥獣関係統計」（狩猟免状、狩猟による捕獲数、都道府県知事の許可による捕獲数）を読む"""
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
DATA = ROOT / "data"
RAW, FIG, RES = DATA / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：環境省「鳥獣関係統計」（https://www.env.go.jp/nature/choju/docs/docs2/index.html）をもとに作成者が加工して作成"
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
# 獣類（狩猟鳥獣）。年によって名前が違うものはまとめる
MAMMALS = ["ツキノワグマ", "ヒグマ", "ニホンジカ", "イノシシ", "タヌキ", "キツネ", "アナグマ", "アライグマ", "ハクビシン",
           "ノウサギ", "ユキウサギ", "テン", "イタチ", "チョウセンイタチ", "ミンク", "ヌートリア", "タイワンリス", "シマリス",
           "ノイヌ", "ノネコ", "ノヤギ", "ニホンザル"]


def norm(s):
    return re.sub(r"[\s　\n]", "", str(s))


def fy(s):
    s = norm(s).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = re.search(r"(平成|令和)(元|\d+)年度", s)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return 1988 + n if m.group(1) == "平成" else 2018 + n


def num(v):
    if isinstance(v, (int, float, np.integer, np.floating)):
        return None if v != v else float(v)
    s = norm(v)
    if s in ("-", "－", "‐", "―", "…", "x", "X"):
        return 0.0
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def file_fy(path):
    n = Path(path).name
    return (1988 if n[0] == "h" else 2018) + int(n[1:3])


def area_name(key):
    k = re.sub(r"^\d+", "", norm(key))
    return k if k in PREFS else None


def blocks(path):
    """表の中の「年度3行＋47都道府県」のかたまりを探す"""
    out = []
    for s, d in pd.read_excel(path, sheet_name=None, header=None).items():
        col0 = [norm(v) if isinstance(v, str) else "" for v in d.iloc[:, 0]]
        isyr = [("年度" in c and re.search(r"(平成|令和)", c) is not None) for c in col0]
        i = 0
        while i < len(d):
            if isyr[i] and (i == 0 or not isyr[i - 1]):
                j = i
                while j < len(d) and (isyr[j] or re.match(r"^\d\d", col0[j])):
                    j += 1
                if j - i > 10:
                    title = " ".join(norm(v) for row in d.iloc[max(0, i - 9):i].values for v in row if isinstance(v, str))
                    out.append((s, i, j, title, d))
                i = j
            else:
                i += 1
    return out


SUB = {"計", "網", "わな", "第一種", "第二種", "第二種*", "甲", "乙", "丙", "小計", "年度及び", "都道府県", "区分", ""}


def canon(sp):
    s = sp.replace("（", "(").replace("）", ")")
    if s in ("ニホンジカ(合計)", "イノシシ(オス)", "イノシシ(メス)", "イノシシ(性不明)"):
        return None
    if re.match(r"ニホンジカ\(|オスジカ|メスジカ", s): return "ニホンジカ"
    if s.startswith("イノシシ"): return "イノシシ"
    if s == "クマ": return "ツキノワグマ"      # 2002年度までの表の名前
    if s in ("ホンドテン", "クロテン", "テン"): return "テン"
    if s in ("イタチ(オス)", "オスイタチ", "メスイタチ", "イタチ"): return "イタチ"
    if s.startswith("チョウセンイタチ") or s == "シベリアイタチ": return "チョウセンイタチ"
    if s.startswith("タイワンリス"): return "タイワンリス"
    if s.endswith("シマリス"): return "シマリス"
    if s == "ニホンノウサギ": return "ノウサギ"
    if s.startswith("ヌートリア"): return "ヌートリア"
    return s if s in MAMMALS else None


def parse_hunt(path):
    """表11 狩猟者登録を受けた者による捕獲鳥獣数：獣類の種類別（計の列）"""
    rows = []
    for s, i, j, t, d in blocks(path):
        hdr = [h for h in range(max(0, i - 9), i)
               if not any(isinstance(v, str) and re.search(r"年度狩猟|捕獲鳥獣数|（[ＡＢＣ]）|単位", norm(v)) for v in d.iloc[h, :])]
        starts = [c for c in range(1, d.shape[1]) if any(isinstance(d.iloc[h, c], str) and norm(d.iloc[h, c]) == "計" for h in hdr)]
        for k, c in enumerate(starts):
            e = starts[k + 1] if k + 1 < len(starts) else d.shape[1]
            parts = [norm(d.iloc[h, cc]) for h in hdr for cc in range(c, e) if isinstance(d.iloc[h, cc], str)]
            raw = "".join(p for p in parts if p not in SUB and not re.match(r"^(丙|網・わな|狩猟|捕獲|報告|登録|\(|（|Ｂ|B/)", p))
            sp = "獣類計" if (raw == "" and k == 0 and "獣類" in t) else canon(raw)
            if not sp:
                continue
            for r in range(i, j):
                v = num(d.iloc[r, c])
                if v is None:
                    continue
                y = fy(d.iloc[r, 0])
                rows.append(dict(file_fy=file_fy(path), fy=y or file_fy(path), area="全国" if y else area_name(d.iloc[r, 0]), species=sp, value=v))
    df = pd.DataFrame(rows)
    return df.groupby(["file_fy", "fy", "area", "species"], as_index=False).value.sum()


def parse_permit(path):
    """表12(1) 都道府県知事の捕獲許可による捕獲鳥獣数（総括表）：獣類の捕獲数の合計"""
    if str(path).endswith(".xlsx"):
        b = [x for x in blocks(path) if x[0] == "12_1(獣類)"][0]
        s, i, j, t, d = b; col = 1
    else:
        b = [x for x in blocks(path) if "獣類" in x[3] and ("合計" in x[3] or "捕獲数計" in x[3])][-1]
        s, i, j, t, d = b
        col = max(c for c in range(1, d.shape[1]) if num(d.iloc[i + 2, c]) is not None)
    rows = []
    for r in range(i, j):
        y = fy(d.iloc[r, 0])
        rows.append(dict(file_fy=file_fy(path), fy=y or file_fy(path), area="全国" if y else area_name(d.iloc[r, 0]), value=num(d.iloc[r, col])))
    return pd.DataFrame(rows)


def parse_license(path):
    """表1 狩猟免状交付状況：総計と免許の種類別（全国）"""
    out = {}
    for s, i, j, t, d in blocks(path):
        for r in range(i, j):
            y = fy(d.iloc[r, 0])
            if not y:
                continue
            o = out.setdefault(y, {})
            a, b = num(d.iloc[r, 1]), num(d.iloc[r, 7])
            t = t.replace(" ", "")
            if "構造改革特区" in t:
                continue
            if "総計" in t:
                o["total"] = a
                if "甲種" in t: o["kou"] = b              # 2004年度まで：甲種（網・わな）
                if "網・わな" in t: o["ami_wana"] = b     # 2005・2006年度
            elif "乙種" in t:
                o["otsu"], o["hei"] = a, b               # 2004年度まで：乙種（装薬銃）・丙種（空気銃）
            elif "網" in t and "わな" in t:
                o["ami"], o["wana"] = a, b               # 2007年度から
            elif "第一種" in t:
                o["gun1"], o["gun2"] = a, b              # 2005年度から
    return pd.DataFrame([dict(file_fy=file_fy(path), fy=k, **v) for k, v in out.items()])


def latest(df, keys):
    """同じ年度が複数のファイルにあるときは、いちばん新しいファイルの値を使う（狩猟免状のみ）"""
    return df.sort_values("file_fy").drop_duplicates(keys, keep="last")


def build():
    fs = sorted(glob.glob(str(RAW / "*")))
    h = pd.concat([parse_hunt(f) for f in fs if re.search(r"-11\.xlsx?$", f)])
    h = h[h.area.notna()]
    nat = h[(h.area == "全国") & (h.fy == h.file_fy)]   # その年度の表に載った値（都道府県の値と合う）
    pref = h[(h.area != "全国") & (h.fy == h.file_fy) & h.species.isin(["ツキノワグマ", "ヒグマ", "ニホンジカ", "イノシシ", "獣類計"])]
    hunt = pd.concat([nat, pref])
    hunt = hunt[hunt.fy >= 1998]   # 1996・1997年度（1998年度の表の参考値）はメスジカなどの扱いが違うので使わない[["fy", "area", "species", "value"]].sort_values(["species", "area", "fy"])
    hunt.to_csv(DATA / "hunt_species.csv", index=False)
    p = pd.concat([parse_permit(f) for f in fs if re.search(r"-12-0?1\.xlsx?$", f)])
    p = p[p.area.notna()]
    own = p[p.fy == p.file_fy]
    # 1999・2000年度は表12がないので、2001年度の表に載った値を使う
    fill = latest(p[(p.area == "全国") & ~p.fy.isin(own.fy)], ["fy"])
    p = pd.concat([own, fill])
    p = p[p.fy >= 1998]
    p[["fy", "area", "value"]].sort_values(["area", "fy"]).to_csv(DATA / "permit_mammals.csv", index=False)
    l = pd.concat([parse_license(f) for f in fs if re.search(r"-0?1\.xlsx?$", f) and "-12" not in f and "-14" not in f])
    l = latest(l, ["fy"]).drop(columns="file_fy").sort_values("fy")
    l = l[l.fy >= 1998]
    l.to_csv(DATA / "license.csv", index=False)


def load():
    need = [DATA / n for n in ("hunt_species.csv", "permit_mammals.csv", "license.csv")]
    if not all(p.exists() for p in need):
        build()
    return [pd.read_csv(p) for p in need]


def foot(fig, extra=""):
    fig.text(0.0, -0.02, (extra + "\n" if extra else "") + SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
