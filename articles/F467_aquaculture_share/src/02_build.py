"""長期累年の表を見出しの文字で読み、部門別の量・金額と、養殖の品目群の量・金額を CSV にする。合計の一致を確かめる。"""
import pathlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, read_table, pick

OUT = ROOT / "data"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)
maps, chk = [], []


def load(name):
    df, n = read_table(name)
    maps.extend((name, x) for x in n)
    return df.set_index("year"), n


def pick_after(df, names, anchor, key):
    """見出し anchor の列より右で、最初に見出しが key になる列（同じ見出しが部門ごとに繰り返す表のため）"""
    i = names.index(anchor)
    j = next(k for k in range(i + 1, len(names)) if names[k].split("#")[0].split("/")[-1] == key)
    return df[names[j]].to_numpy(float)


# 量：部門別（1979〜）
s, ns = load("vol_sector.xlsx")
vol = pd.DataFrame(index=s.index)
vol["total"] = pick(s, ns, "総生産量")
vol["marine_total"] = pick(s, ns, "海面", "計")
vol["mf_total"] = pick(s, ns, "漁業", "小計")
vol["mf_enyo"] = pick(s, ns, "遠洋"); vol["mf_okiai"] = pick(s, ns, "沖合"); vol["mf_engan"] = pick(s, ns, "沿岸")
vol["ma"] = pick_after(s, ns, "沿岸", "養殖業")
vol["inland_total"] = pick(s, ns, "内水面", "計")
vol["if"] = pick_after(s, ns, "内水面/計", "漁業")
vol["ia"] = pick_after(s, ns, "内水面/計", "養殖業")
vol.loc[vol.index <= 2002] *= 1000  # 表の注記：2002年以前は千t、2003年以降は t
# 量：1956〜1978 は表2・表6・表7 から（t）
g, ng = load("vol_marine_gear.xlsx")
sp, nsp = load("vol_marine_species.xlsx")
aq, naq = load("vol_aqua_species.xlsx")
inl, ninl = load("vol_inland.xlsx")
long = pd.DataFrame(index=g.index)
long["mf_total"] = pick(g, ng, "漁獲量計")
long["mf_seaweed"] = pick(sp, nsp, "海藻類", "計")
long["mf_check_species_total"] = pick(sp, nsp, "漁獲量計")
long["ma"] = pick(aq, naq, "計")
for k, lab in [("fish", "魚類"), ("shell", "貝類"), ("seaweed", "海藻類")]:
    long[f"ma_{k}"] = pick(aq, naq, lab, "小計")
long["ma_kuruma"] = pick(aq, naq, "くるまえび"); long["ma_hoya"] = pick(aq, naq, "ほや類")
long["ma_otherani"] = pick(aq, naq, "その他の水産動物類"); long["ma_pearl"] = pick(aq, naq, "真珠（浜揚量）")
long["if"] = pick(inl, ninl, "漁業", "計"); long["ia"] = pick(inl, ninl, "養殖業", "計")
long = long.fillna(0.0)
long.to_csv(OUT / "volume_long.csv")

# 金額
v, nv = load("val_summary.xls")
val = pd.DataFrame(index=v.index)
val["total"] = pick(v, nv, "漁業産出額")
val["mf"] = pick(v, nv, "海面", "漁業"); val["ma"] = pick(v, nv, "海面", "養殖業")
val["if"] = pick(v, nv, "内水面", "漁業"); val["ia"] = pick(v, nv, "内水面", "養殖業")
va, nva = load("val_aqua_species.xls")
val["ma_species_total"] = pick(va, nva, "海面養殖業計イ")
for k, lab in [("fish", "魚類"), ("shell", "貝類"), ("seaweed", "海藻類")]:
    val[f"ma_{k}"] = pick(va, nva, lab, "計")
val["ma_pearl"] = pick(va, nva, "真珠")
val["ma_kuruma"] = pick(va, nva, "くるまえび"); val["ma_hoya"] = pick(va, nva, "ほや類"); val["ma_otherani"] = pick(va, nva, "その他の水産動物類")
for k, lab in [("buri", "ぶり類"), ("madai", "まだい"), ("ginzake", "ぎんざけ"), ("maguro", "くろまぐろ")]:
    val[f"ma_fish_{k}"] = pick(va, nva, "魚類", lab)
for k, lab in [("hotate", "ほたてがい"), ("kaki", "かき類")]:
    val[f"ma_shell_{k}"] = pick(va, nva, "貝類", lab)
val["ma_nori"] = pick(va, nva, "海藻類", "のり類", "小計")
val = val * 1e6  # 100万円 → 円
val.to_csv(OUT / "value_long.csv")
vol.to_csv(OUT / "volume_sector.csv")

# 点検
def mx(a): return float(np.nanmax(np.abs(a)))
y = vol
chk.append(("量：海面漁業の遠洋＋沖合＋沿岸＝小計（最大の差、t）", mx(y.mf_enyo + y.mf_okiai + y.mf_engan - y.mf_total)))
chk.append(("量：海面漁業＋海面養殖＝海面計（t）", mx(y.mf_total + y.ma - y.marine_total)))
chk.append(("量：内水面漁業＋内水面養殖＝内水面計（t）", mx(y["if"] + y.ia - y.inland_total)))
chk.append(("量：海面計＋内水面計＝総生産量（t）", mx(y.marine_total + y.inland_total - y.total)))
yy = y.index
chk.append(("量：表1の海面漁業と表2の漁獲量計（1979〜、最大の差、t）", mx(y.mf_total - long.loc[yy, "mf_total"])))
chk.append(("量：表1の海面養殖と表6の計（1979〜、t）", mx(y.ma - long.loc[yy, "ma"])))
chk.append(("量：表1の内水面漁業と表7の漁業計（1979〜、t）", mx(y["if"] - long.loc[yy, "if"])))
chk.append(("量：表1の内水面養殖と表7の養殖業計（1979〜、t）", mx(y.ia - long.loc[yy, "ia"])))
chk.append(("量：表2と表3の漁獲量計（1964〜、t。1963年以前は表3が大きい）", mx((long.mf_total - long.mf_check_species_total).loc[1964:])))
parts = long[["ma_fish", "ma_shell", "ma_seaweed", "ma_kuruma", "ma_hoya", "ma_otherani"]].sum(1)
chk.append(("量：養殖の群の和（真珠を除く）と計の差（1990〜、t）", mx((parts - long.ma).loc[1990:])))
chk.append(("量：養殖の群の和（真珠を含む）と計の差（1990〜、t）", mx((parts + long.ma_pearl - long.ma).loc[1990:])))
chk.append(("金額：4部門の和＝漁業産出額（100万円）", mx((val.mf + val.ma + val["if"] + val.ia - val.total) / 1e6)))
chk.append(("金額：総括表の海面養殖と魚種別の計（100万円）", mx((val.ma - val.ma_species_total) / 1e6)))
p = val[["ma_fish", "ma_shell", "ma_seaweed", "ma_pearl", "ma_kuruma", "ma_hoya", "ma_otherani"]].sum(1)
chk.append(("金額：海面養殖の群の和と計の差（1990〜、100万円）", mx(((p - val.ma) / 1e6).loc[1990:])))
pd.DataFrame(chk, columns=["check", "value"]).to_csv(RES / "build_checks.csv", index=False)
pd.DataFrame(maps, columns=["file", "column_from_headers"]).to_csv(RES / "build_header_map.csv", index=False)
print(pd.DataFrame(chk).to_string())
