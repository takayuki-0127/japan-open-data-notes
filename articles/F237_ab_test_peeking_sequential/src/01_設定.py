"""シミュレーションの前提を書き出す（データの取得はない）。"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import *
P = dict(alpha=ALPHA, base=BASE, lift=LIFT, daily_per_arm=DAILY_PER_ARM, fix_days=FIX_DAYS, max_days=MAX_DAYS,
         hours_per_day=HOURS, site="みどりモール（架空のECサイト）",
         note="基準の購入率5%・相対+10%・1日5,000人（2群合計）は F236 の設計の表と同じ前提")
os.makedirs("data", exist_ok=True)
json.dump(P, open("data/params.json", "w"), ensure_ascii=False, indent=1)
print(P)
