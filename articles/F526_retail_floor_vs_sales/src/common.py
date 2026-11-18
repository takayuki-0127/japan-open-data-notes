"""共通の関数と決まり。表から値を読むときは、行・列とも見出しの文字で選ぶ。"""
import pathlib, re, unicodedata
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"

PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]
REGION_OF = {}
for reg, ps in [("北海道", PREFS[0:1]), ("東北", PREFS[1:7]), ("関東", PREFS[7:14]), ("中部", PREFS[14:23]),
                ("近畿", PREFS[23:30]), ("中国", PREFS[30:35]), ("四国", PREFS[35:39]), ("九州沖縄", PREFS[39:47])]:
    for p in ps:
        REGION_OF[p] = reg
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州沖縄"]  # 北から南
# 業態：短い名前 → 表の見出しの文字（空白・中黒の違いはならしてから比べる）
GYOTAI = {"total": "合計", "dept": "百貨店", "gms": "総合スーパー", "sm_cloth": "衣料品スーパー", "sm_food": "食料品スーパー",
          "sm_home": "住関連スーパー", "cvs": "コンビニエンスストア", "drug": "ドラッグストア", "other_super": "その他のスーパー",
          "specialty": "専門店", "center": "中心店", "other_store": "その他の小売店", "spec_super": "専門スーパー"}
GYOTAI_JA = {"total": "小売業の合計", "dept": "百貨店", "gms": "総合スーパー", "sm_cloth": "衣料品スーパー", "sm_food": "食料品スーパー",
             "sm_home": "住関連スーパー", "cvs": "コンビニ", "drug": "ドラッグストア", "other_super": "その他のスーパー",
             "specialty": "専門店", "center": "中心店", "other_store": "その他の小売店", "spec_super": "専門スーパー（計）"}


def norm(s):
    if s is None:
        return ""
    t = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[\s・･]+", "", t)


def gyotai_of(label):
    t = norm(label)
    for k, v in GYOTAI.items():
        if t == norm(v):
            return k
    return None


def pref_of(label):
    t = re.sub(r"^\d+", "", norm(label))
    if t in PREFS:
        return t
    t2 = re.sub(r"(都|府|県)$", "", t)
    return t2 if t2 in PREFS else None


def year_of(label):
    t = norm(label)
    m = re.fullmatch(r"(昭和|平成)(\d+|元)年(度)?", t)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1925 if m.group(1) == "昭和" else 1988) + n


def num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    t = norm(v)
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return float(t)
    return None  # 「x」（秘匿）・「-」・空白


def xls_sheets(fname):
    import xlrd
    b = xlrd.open_workbook(RAW / fname)
    return {b.sheet_by_index(i).name: [b.sheet_by_index(i).row_values(j) for j in range(b.sheet_by_index(i).nrows)] for i in range(b.nsheets)}


def xlsx_sheet(fname, name):
    wb = openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True)
    return [list(r) for r in wb[name].iter_rows(values_only=True)]
