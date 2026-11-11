"""F234 共通：パス・品目の区分・データの読み込み"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

SEED = 234

# 輸入の影響を受けやすい食料品（推測で決めた区分。頑健性で狭い版・広い版を比べる）
IMPORT_FOOD_NARROW = ["バナナ", "オレンジ", "キウイフルーツ", "コーヒー", "紅茶", "チーズ",
                      "ワイン", "食用油", "パスタ", "小麦粉", "えび", "さけ", "牛肉"]
IMPORT_FOOD_BROAD = IMPORT_FOOD_NARROW + ["塩さけ", "かに", "マーガリン", "マヨネーズ・マヨネーズ風調味料",
                                          "食パン", "他のパン", "中華麺", "即席麺", "カップ麺",
                                          "乾うどん・そば", "砂糖", "ハム", "ソーセージ", "ベーコン",
                                          "豚肉", "ウイスキー", "他の柑きつ類"]
ENERGY = ["電気代ガス代", "プロパンガス他の光熱", "灯油他の光熱のその他"]

# 交差弾力性を見る組（代わりになりそうな品目どうし）
CROSS_GROUPS = {
    "肉": ["牛肉", "豚肉", "鶏肉"],
    "油脂": ["バター", "マーガリン"],
    "主食": ["米", "食パン", "パスタ", "即席麺"],
    "お酒": ["ビール", "発泡酒・ビール風アルコール飲料1)", "清酒"],
    "飲み物": ["緑茶", "紅茶", "コーヒー"],
}


def load_panel():
    d = pd.read_csv(RAW / "kakei_items_panel_f113.csv")
    d = d[(d.price > 0) & (d.q > 0)].copy()
    d["lp"] = np.log(d.price)
    d["lq"] = np.log(d.q)
    d = d.sort_values(["name", "year"])
    g = d.groupby("name")
    d["dlp"] = g.lp.diff()
    d["dlq"] = g.lq.diff()
    d["dlp_l1"] = g.dlp.shift(1)
    d["gap"] = g.year.diff()
    d.loc[d.gap != 1, ["dlp", "dlq"]] = np.nan
    # 品目の区分の変更らしき年（量が1年で半分以下／値段が1.6倍以上動いた年）は前年差を使わない
    d["break"] = ((d.dlq.abs() > 0.7) | (d.dlp.abs() > 0.5)).astype(int)
    d["dlp_raw"], d["dlq_raw"] = d.dlp, d.dlq
    d.loc[d["break"] == 1, ["dlp", "dlq"]] = np.nan
    # 前年の支出のシェア（重み）
    d["w"] = g.exp.shift(1) / d.groupby("year").exp.transform("sum")
    d["fresh"] = d.group.isin(["野菜・海藻", "果物", "魚介類"]).astype(int)
    d["energy"] = d.name.isin(ENERGY).astype(int)
    return d


def load_boj_annual():
    b = pd.read_csv(RAW / "boj_import_prices_fx.csv", dtype={"date": str})
    b["year"] = b.date.str[:4].astype(int)
    a = b.groupby(["code", "year"]).value.mean().unstack(0)
    a = a.rename(columns={"PRCG20_2600120001": "imp_food", "PRCG20_2600520001": "imp_energy",
                          "PRCG20_2600000000": "imp_all", "FXERM07": "usdjpy"})
    for c in ["imp_food", "imp_energy", "imp_all", "usdjpy"]:
        a["dl_" + c] = np.log(a[c]).diff()
    return a.reset_index()
