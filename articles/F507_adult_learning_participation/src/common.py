"""共通の関数と決まり。表から値を読むときは、行も列も見出しの文字で選ぶ。"""
import pathlib, re
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"

# 種類の見出し（表の文字）→ この記事での短い名前。取り上げない種類は読まない（総数には含まれたまま）。
KIND = [("総数", "total"), ("英語以外の外国語", "other_foreign"), ("英語", "english"), ("外国語", "foreign"),
        ("商業実務・ビジネス関係(総数)", "business_total"), ("パソコンなどの情報処理", "computing"),
        ("商業実務・ビジネス関係", "business"), ("家政・家事", "home"), ("人文・社会・自然科学", "humanities"),
        ("芸術・文化", "arts")]
KIND_JA = {"total": "総数", "foreign": "外国語", "english": "英語", "other_foreign": "英語以外の外国語",
           "business_total": "商業実務・ビジネス関係（パソコンを含む）", "computing": "パソコンなどの情報処理",
           "business": "商業実務・ビジネス関係（パソコンを除く）", "home": "家政・家事", "humanities": "人文・社会・自然科学",
           "arts": "芸術・文化"}

# 時系列表の年齢区分と、5歳階級からのまとめ方
TS_AGES = ["25～29歳", "30～39歳", "40～49歳", "50～59歳", "60～64歳", "65～69歳", "70歳以上"]
FIVE_TO_TS = {"25～29歳": "25～29歳", "30～34歳": "30～39歳", "35～39歳": "30～39歳", "40～44歳": "40～49歳",
              "45～49歳": "40～49歳", "50～54歳": "50～59歳", "55～59歳": "50～59歳", "60～64歳": "60～64歳",
              "65～69歳": "65～69歳", "70～74歳": "70歳以上", "75～79歳": "70歳以上", "80～84歳": "70歳以上",
              "85歳以上": "70歳以上"}
AGE_WIDTH = {"25～29歳": 5, "30～39歳": 10, "40～49歳": 10, "50～59歳": 10, "60～64歳": 5, "65～69歳": 5, "70歳以上": 15}
GROUPS = {"25_64": TS_AGES[:5], "30_64": TS_AGES[1:5], "65plus": TS_AGES[5:], "25plus": TS_AGES}
YEARS = [1986, 1991, 1996, 2001, 2006, 2011, 2016, 2021]


def clean(s):
    return re.sub(r"\s+", "", str(s)) if s is not None else ""


def kind_of(label):
    """見出しの文字（先頭の番号「21_」などを除く）を短い名前に。完全一致で、括弧の説明は前方一致。"""
    t = re.sub(r"^\d+_", "", clean(label))
    for ja, k in KIND:
        if t == ja or (ja in ("家政・家事", "人文・社会・自然科学") and t.startswith(ja)):
            return k
    return None


def rows_of(fname):
    ws = openpyxl.load_workbook(RAW / fname, data_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
