"""02 整形（オフライン）：家計調査 第4-6表（2005〜2025年）から、菓子類の品目の1世帯当たり年間の支出金額を
世帯主の年齢階級別に取り出す。世帯人員と世帯数分布（抽出率調整）も取る。CPI の月次から年平均を作る。
出力：data/sweets.csv（year, group, item, amount）、data/households.csv（year, group, persons, weight）、data/cpi_annual.csv"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
GROUPS = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
ITEMS = {"菓子類": "sweets", "ようかん": "yokan", "まんじゅう": "manju", "他の和生菓子": "wagashi_other", "カステラ": "castella",
         "ケーキ": "cake", "ゼリー": "jelly", "プリン": "pudding", "他の洋生菓子": "yogashi_other", "せんべい": "senbei",
         "ビスケット": "biscuit", "スナック菓子": "snack", "キャンデー": "candy", "チョコレート": "chocolate",
         "チョコレート菓子": "choco_kashi", "アイスクリーム・シャーベット": "icecream", "他の菓子": "other"}
PH = {"...", "…", "-", "－", "***", "x", "X"}
YEARS = range(2005, 2026)


def norm(v):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(v)))


def cells_after(row, j):
    """名前の右の値。単位（円など）や空欄は飛ばし、数字と「...」の印だけを順に返す。"""
    out, started = [], False
    for v in row[j + 1:]:
        s = norm(v)
        if s in ("nan", ""):
            if started:
                out.append(None)
            continue
        if s in PH:
            out.append(None); started = True; continue
        try:
            out.append(float(s.replace(",", ""))); started = True
        except ValueError:
            if started:
                break
    return out


def main():
    recs, hh = [], []
    for y in YEARS:
        f = next(RAW.glob(f"kakei_4-6_{y}.*"))
        d = pd.read_excel(f, header=None)
        found, pers, wts, nh = set(), None, None, None
        in_food = False
        for i in range(len(d)):
            row = d.iloc[i].tolist()
            names = [(j, norm(v)) for j, v in enumerate(row[:15])]
            for j, n in names:
                if n.startswith("世帯人員") and pers is None:
                    pers = [v for v in cells_after(row, j) if v is not None]
                if n == "集計世帯数" and nh is None:
                    nh = [v for v in cells_after(row, j) if v is not None]
                if n.startswith("世帯数分布(抽出率調整)") and wts is None:
                    wts = [v for v in cells_after(row, j) if v is not None]
            hit = [(j, n) for j, n in names if n in ITEMS]
            if not hit:
                continue
            j, n = hit[0]
            key = ITEMS[n]
            if key == "sweets":
                in_food = True
            if not in_food or key in found:
                continue
            found.add(key)
            vals = cells_after(row, j)
            for g, name in enumerate(GROUPS):
                recs.append((y, name, key, vals[4 * g + 1]))  # 4列ずつ：頻度・金額・数量・平均価格
            if key == "other":
                in_food = False
        assert found == set(ITEMS.values()), (y, set(ITEMS.values()) - found)
        # 世帯人員・世帯数分布は年齢の7列（平均＋6）
        pers, wts, nh = pers[:7], wts[:7], nh[:7]
        assert abs(sum(nh[1:]) - nh[0]) <= 1, (y, nh)
        assert wts[0] == 10000 and abs(sum(wts[1:]) - 10000) <= 3, (y, wts)
        for g, name in enumerate(GROUPS):
            hh.append((y, name, pers[g], wts[g], int(nh[g])))
    out = pd.DataFrame(recs, columns=["year", "group", "item", "amount"])
    # 確かめ：品目の合計＝菓子類（各年・各年齢）
    p = out.pivot_table(index=["year", "group"], columns="item", values="amount")
    parts = p.drop(columns="sweets").sum(axis=1)
    assert ((parts - p["sweets"]).abs() <= 8).all(), (parts - p["sweets"]).abs().max()
    h = pd.DataFrame(hh, columns=["year", "group", "persons", "weight", "n_sample"])
    # 確かめ：年齢の支出を世帯数分布で重みづけした平均＝「平均」の列（丸めの範囲）
    m = out.merge(h, on=["year", "group"])
    sub = m[m.group != "平均"]
    wavg = (sub.amount * sub.weight).groupby([sub.year, sub.item]).sum() / sub.weight.groupby([sub.year, sub.item]).sum()
    avg = m[m.group == "平均"].set_index(["year", "item"]).amount
    rel = ((wavg - avg) / avg).abs()
    assert rel.max() < 0.01, rel.sort_values().tail()
    out["amount"] = out.amount.astype("int64")
    out.sort_values(["item", "group", "year"]).to_csv(DATA / "sweets.csv", index=False)
    h.sort_values(["group", "year"]).to_csv(DATA / "households.csv", index=False)

    c = pd.read_csv(RAW / "cpi_item_monthly.csv", encoding="cp932", header=None, dtype=str)
    head = [norm(v) for v in c.iloc[0]]
    cols = {"菓子類": "cpi_sweets", "チョコレート": "cpi_chocolate", "ポテトチップス": "cpi_potato_chips"}
    idx = {v: head.index(k) for k, v in cols.items()}
    body = c.iloc[6:].copy()
    body = body[body[0].str.fullmatch(r"\d{6}")]
    rows = []
    for y in YEARS:
        b = body[body[0].str[:4] == str(y)]
        assert len(b) == 12, (y, len(b))
        rows.append({"year": y, **{k: round(b[i].astype(float).mean(), 4) for k, i in idx.items()}})
    pd.DataFrame(rows).to_csv(DATA / "cpi_annual.csv", index=False)
    print("ok", out.shape, h.shape)


if __name__ == "__main__":
    main()
