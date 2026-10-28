import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
P = lambda *a: os.path.join(ROOT, *a)
CATS = ['総合', '家賃を除く総合', '食料', '住居', '光熱・水道', '家具・家事用品', '被服及び履物', '保健医療', '交通・通信', '教育', '教養娯楽', '諸雑費']
TEN = CATS[2:]
TOKYO_AREA = [11, 12, 13, 14]           # 東京圏（埼玉・千葉・東京・神奈川）
NAGOYA_OSAKA = [21, 23, 24, 26, 27, 28, 29]  # 名古屋圏・大阪圏（岐阜・愛知・三重・京都・大阪・兵庫・奈良）

def area(code):
    return '東京圏' if code in TOKYO_AREA else ('名古屋圏・大阪圏' if code in NAGOYA_OSAKA else '地方圏')
