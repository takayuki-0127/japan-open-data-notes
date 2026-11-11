from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(exist_ok=True)
IND16 = list("CDEFGHIJKLMNOPQR")
IND_NAME = {"C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス", "G": "情報通信", "H": "運輸・郵便",
            "I": "卸売・小売", "J": "金融・保険", "K": "不動産", "L": "学術研究", "M": "飲食・宿泊",
            "N": "生活関連・娯楽", "O": "教育", "P": "医療・福祉", "Q": "複合サービス", "R": "その他サービス"}
SIZE_NAME = {"4": "500人以上", "5": "100〜499人", "7": "30〜99人", "9": "5〜29人"}
