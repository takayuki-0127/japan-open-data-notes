"""F123 02 整形：3つのデータを「目的変数 y・特徴量・平面座標（km）・グループ（都道府県／予報区）」にそろえ、行数を確かめる。
実際の読み込みは common.load() にまとめてある（03 もこれを使う）。"""
from common import load
for name in ["地価", "出生率", "気温"]:
    d, feats = load(name)
    print(f"{name}: {len(d):,} 行, 特徴量 {len(feats)} 個, x {d.xk.min():.0f}〜{d.xk.max():.0f} km, "
          f"y {d.yk.min():.0f}〜{d.yk.max():.0f} km, グループ {d['pref'].nunique()}")
