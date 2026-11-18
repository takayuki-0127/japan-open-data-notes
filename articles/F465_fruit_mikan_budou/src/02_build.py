"""data/raw の Excel から、分析用の CSV を作る（オフライン）。
- data/fruit_national.csv：13品目の全国の結果樹面積（ha）・収穫量（t）・出荷量（t）、1973〜2024年
- data/fruit_pref.csv：みかん・ぶどうの都道府県別（数字のある年・県だけ）
- data/output_value.csv：果実の品目別の産出額（億円、全国、2003〜2024年。各年の上位50位（2020年からは100位）に入った品目）
- data/fruit_total_value.csv：果実の産出額の合計（億円、全国、1955〜2024年）
"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
ITEMS = {"mikan": "みかん", "ringo": "りんご", "budou": "ぶどう", "nashi": "日本なし", "younashi": "西洋なし", "momo": "もも",
         "sumomo": "すもも", "outou": "おうとう", "ume": "うめ", "biwa": "びわ", "kaki": "かき", "kuri": "くり", "kiwi": "キウイフルーツ"}
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]


def num(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        return float(v)
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan  # 「…」「x」「-」などは欠測にする


def read_fruit(path):
    v = pd.read_excel(path, header=None)
    assert str(v.iloc[5, 1]).strip() == "結果樹面積" and str(v.iloc[5, 2]).strip() == "収穫量" and str(v.iloc[5, 3]).strip() == "出荷量", path
    out = []
    for i in range(7, len(v)):
        m = re.search(r"\((\d{4})\)", str(v.iloc[i, 0]))
        if not m:
            continue
        out.append({"year": int(m.group(1)), "area_ha": num(v.iloc[i, 1]), "harvest_t": num(v.iloc[i, 2]), "shipped_t": num(v.iloc[i, 3])})
    return pd.DataFrame(out), str(v.iloc[2, 0]).strip(), str(v.iloc[3, 0]).strip()


def read_top(path, year):
    v = pd.read_excel(path, header=None)
    hdr = next(i for i in range(len(v)) if any(str(c).strip() in ("米", "米計") for c in v.iloc[i]))
    tot = next(i for i in range(hdr + 1, len(v)) if any(re.sub(r"\s", "", str(c)) == "合計" for c in v.iloc[i, :3]))
    out = []
    for j, c in enumerate(v.iloc[hdr]):
        name = re.sub(r"\s", "", str(c))
        if name in ITEMS.values():
            val = next((num(v.iloc[tot, k]) for k in (j, j + 1) if not pd.isna(num(v.iloc[tot, k]))), np.nan)
            out.append({"year": year, "item": name, "value_oku": val})
    return out


def main():
    nat = []
    for k, nm in ITEMS.items():
        df, item, area = read_fruit(RAW / "fruit" / f"{k}_00.xls")
        assert item == nm and area == "全国", (k, item, area)
        df.insert(0, "item", nm); nat.append(df)
    nat = pd.concat(nat, ignore_index=True)
    nat.to_csv(D / "fruit_national.csv", index=False)

    pref = []
    for k in ["mikan", "budou"]:
        for code in range(1, 48):
            df, item, area = read_fruit(RAW / "fruit" / f"{k}_{code:02d}.xls")
            assert item == ITEMS[k] and area == PREFS[code - 1], (k, code, item, area)
            df.insert(0, "pref", area); df.insert(0, "pref_code", code); df.insert(0, "item", item)
            pref.append(df)
    pref = pd.concat(pref, ignore_index=True).dropna(subset=["area_ha", "harvest_t", "shipped_t"], how="all")
    pref.to_csv(D / "fruit_pref.csv", index=False)

    val = []
    for y in range(2003, 2025):
        val += read_top(RAW / "sanshutsu" / f"top_{y}.xls", y)
    val = pd.DataFrame(val).sort_values(["item", "year"]).reset_index(drop=True)
    val.to_csv(D / "output_value.csv", index=False)

    t = pd.read_excel(RAW / "sanshutsu" / "total.xls", header=None)
    col = next(j for j, c in enumerate(t.iloc[5]) if re.sub(r"\s", "", str(c)) == "果実")
    rows = []
    for i in range(9, len(t)):
        m = re.search(r"\((\d{4})\)", str(t.iloc[i, 0]))
        if m:
            rows.append({"year": int(m.group(1)), "fruit_total_oku": num(t.iloc[i, col]), "all_agri_oku": num(t.iloc[i, 1])})
    pd.DataFrame(rows).to_csv(D / "fruit_total_value.csv", index=False)

    # 確かめ：みかん・ぶどうの都道府県の合計と全国（都道府県の数字がそろう年だけ）
    chk = []
    for nm in ["みかん", "ぶどう"]:
        p = pref[pref.item == nm].groupby("year").agg(area_sum=("area_ha", "sum"), n_pref=("area_ha", "count"), harvest_sum=("harvest_t", "sum"))
        n = nat[nat.item == nm].set_index("year")
        p = p.join(n[["area_ha", "harvest_t"]])
        p["area_ratio"] = p.area_sum / p.area_ha
        p["harvest_ratio"] = p.harvest_sum / p.harvest_t
        p.insert(0, "item", nm); chk.append(p.reset_index())
    chk = pd.concat(chk, ignore_index=True)
    chk.to_csv(R / "build_checks.csv", index=False, float_format="%.4f")
    cov = val.groupby("item").year.agg(["min", "max", "count"])
    cov.to_csv(R / "output_value_coverage.csv")
    print(cov.to_string())
    print(chk.groupby("item")[["n_pref", "area_ratio", "harvest_ratio"]].describe().T.to_string())


if __name__ == "__main__":
    main()
