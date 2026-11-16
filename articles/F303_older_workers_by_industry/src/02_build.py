"""労働力調査 第II-2-1表から、年×産業×年齢（男女計）の就業者数（万人）の長い表を作る（オフライン）。
出力：data/employed_age_industry.csv"""
import glob, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AGES = ["総数", "15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65歳以上"]
recs = []
ref_names = None
for f in sorted(glob.glob(str(RAW / "lfs_II-2-1_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    v = pd.read_excel(f, header=None)
    if y >= 2018:
        c0, name_row, lev_row = 14, 9, 6
        names = [str(v.iloc[name_row, j]).strip() for j in range(c0, v.shape[1])]
        levels = [int(v.iloc[lev_row, j]) for j in range(c0, v.shape[1])]
        ref_names, ref_levels = names, levels
        # 男女計の行：age ラベルが col 11
        start = next(i for i in range(10, 20) if str(v.iloc[i, 12]).strip() == "男女計")
        rows = range(start, start + 12)
        agecol = 12
    else:
        c0 = 11
        start = next(i for i in range(8, 15) if str(v.iloc[i, 7]).strip() == "男女計")
        rows = range(start, start + 12)
        agecol = 9
    n = len(ref_names) if ref_names else None
    for k, i in enumerate(rows):
        lab = AGES[k]
        if y >= 2018:
            assert (k == 0 and str(v.iloc[i, agecol]).strip() == "男女計") or str(v.iloc[i, agecol]).strip() == lab, (y, i, v.iloc[i, agecol])
        else:
            assert k == 0 or str(v.iloc[i, agecol]).strip() == lab, (y, i, v.iloc[i, agecol])
        for j in range(99):
            val = v.iloc[i, c0 + j]
            recs.append((y, j, lab, float(val) if str(val).strip() not in ("-", "nan", "…", "") else float("nan")))
d = pd.DataFrame(recs, columns=["year", "col", "age", "employed_10k"])
# 産業名と階層は 2018年以降の表から（2013年の表は同じ順に99列並ぶことを、大分類の位置で確かめる）
assert ref_names[0] == "就業者" and ref_names[98].startswith("分類不能")
d["industry"] = d.col.map(dict(enumerate(ref_names))); d["level"] = d.col.map(dict(enumerate(ref_levels)))
v13 = pd.read_excel(sorted(glob.glob(str(RAW / "lfs_II-2-1_2013*")))[0], header=None)
for j, key in ((9, "建設業"), (42, "運輸業"), (78, "医療"), (98, "分類不能")):
    assert key in str(v13.iloc[7, 11 + j]) and key in ref_names[j], (j, key)
d = d.sort_values(["year", "col", "age"]).reset_index(drop=True)
d.to_csv(DATA / "employed_age_industry.csv", index=False)
print(d.year.unique(), len(d))
