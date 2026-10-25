"""トピックのラベル（上位語を見て手で付けた。04 の K=8・SEED の結果に対応）"""
import json
from common import RES
L = {0: "景気と物価（実質・デフレ）", 1: "企業の賃上げと税制・好循環", 2: "年金・給付の物価スライド",
     3: "金融政策（日銀・物価目標）", 4: "予算・支援策（介護・地方・高騰対策）", 5: "公務員給与・恩給の改定",
     6: "物価対策（輸入・農産物・料金）", 7: "春闘と労使交渉"}
json.dump({str(k): v for k, v in L.items()}, open(RES / "lda_k8_labels.json", "w"), ensure_ascii=False, indent=1)
