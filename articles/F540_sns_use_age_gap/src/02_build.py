"""data/raw の CSV（e-Stat、cp932）から、年×性別×年齢の表を作る。
列は見出しの文字で選び、行は「本人の性別・年齢」の見出しの文字で選ぶ（行の順には頼らない）。"""
import csv, io, json, pathlib, re
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
OUT = BASE / "data"

# 年ごとの SNS の列の見出し（列の見出しの文字そのもの）
SNS_LABEL = {
    2012: "ソーシャルメディアの利用", 2013: "ソーシャルメディアの利用", 2014: "ソーシャルメディアの利用",
    **{y: "ソーシャルネットワーキングサービスの利用" for y in range(2015, 2021)},
    **{y: "ＳＮＳ（無料通話機能を含む）の利用" for y in range(2021, 2026)},
}
CALL_LABEL = "無料通話アプリやボイスチャットの利用"
AGES = ["６～１２歳", "１３～１９歳", "２０～２９歳", "３０～３９歳", "４０～４９歳", "５０～５９歳", "６０～６９歳", "７０～７９歳", "８０歳以上"]
AGE_KEY = {a: k for a, k in zip(AGES, ["6-12", "13-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"])}


def read(path):
    txt = path.read_bytes().decode("cp932")
    return list(csv.reader(io.StringIO(txt)))


def num(x):
    x = x.strip()
    if x in ("-", "－"):
        return 0.0
    if x in ("", "…", "x", "X", "***"):
        return None
    return float(x)


def parse(path, labels):
    rows = read(path)
    head = next(r for r in rows if len(r) > 2 and r[2] == "集計人数")
    idx = {}
    for lab in labels:
        hits = [i for i, h in enumerate(head) if h.strip() == lab]
        if len(hits) != 1:
            raise ValueError(f"{path.name}: 見出し {lab} が {len(hits)} 個")
        idx[lab] = hits[0]
    out, sex = [], None
    for r in rows:
        if len(r) < 3 or not r[0].startswith("本人の性別"):
            continue
        lab = r[1].strip().replace("　", "")
        if "男女計" in lab or lab == "全体":
            sex = "計"; continue
        if lab.startswith("男性"):
            sex = "男"; continue
        if lab.startswith("女性"):
            sex = "女"; continue
        if lab in AGE_KEY and sex is not None:
            rec = {"sex": sex, "age": AGE_KEY[lab], "n": int(r[2])}
            for lab2, i in idx.items():
                rec[lab2] = num(r[i])
            out.append(rec)
    df = pd.DataFrame(out)
    if df.duplicated(["sex", "age"]).any():
        raise ValueError(f"{path.name}: 性別×年齢が重複")
    return df


def find(year, kinds):
    for k in kinds:
        hit = sorted(RAW.glob(f"y{year}_{k}_*.csv"))
        if hit:
            return hit[0]
    raise FileNotFoundError((year, kinds))


def use_table(year, target):
    """インターネット利用経験の表。target='all'（全員）か 'nona'（無回答除く）。注記の行で見分ける。"""
    cands = sorted(RAW.glob(f"y{year}_use_*.csv"))
    for p in cands:
        rows = read(p)
        note = " ".join(",".join(r) for r in rows[:16] if r and r[0].startswith("@Note"))
        is_nona = "無回答" in note and "除" in note
        head = next(r for r in rows if len(r) > 2 and r[2] == "集計人数")
        if target == "nona" and is_nona:
            return p
        if target == "all" and not is_nona and len([h for h in head if h.strip()]) >= 5:
            return p
    raise FileNotFoundError((year, target))


def main():
    recs, checks = [], {}
    for year in range(2012, 2026):
        labs = [SNS_LABEL[year]] + ([CALL_LABEL] if 2013 <= year <= 2019 else [])
        f = parse(find(year, ["func"]), labs).rename(columns={SNS_LABEL[year]: "s", CALL_LABEL: "call", "n": "n_users"})
        ua = parse(use_table(year, "all"), ["はい"]).rename(columns={"はい": "u_all", "n": "n_all"})
        un = parse(use_table(year, "nona"), ["はい"]).rename(columns={"はい": "u_nona", "n": "n_nona"})
        d = f.merge(ua, on=["sex", "age"]).merge(un, on=["sex", "age"])
        d["year"] = year
        d["sns_label"] = SNS_LABEL[year]
        recs.append(d)
        checks[year] = {"func": find(year, ["func"]).name, "use_all": use_table(year, "all").name,
                        "use_nona": use_table(year, "nona").name, "rows": int(len(d))}
    df = pd.concat(recs, ignore_index=True)
    if "call" not in df:
        df["call"] = None
    df["p_all"] = df["s"] * df["u_all"] / 100
    df["p_nona"] = df["s"] * df["u_nona"] / 100
    order = {k: i for i, k in enumerate(AGE_KEY.values())}
    df["age_order"] = df["age"].map(order)
    df = df.sort_values(["year", "sex", "age_order"]).drop(columns="age_order")
    cols = ["year", "sex", "age", "sns_label", "s", "call", "u_all", "u_nona", "p_all", "p_nona", "n_users", "n_all", "n_nona"]
    df[cols].to_csv(OUT / "panel.csv", index=False, float_format="%.4f")
    (OUT / "build_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(df[(df.sex == "計") & (df.age.isin(["20-29", "70-79"]))][["year", "age", "s", "u_all", "p_all"]].to_string())


if __name__ == "__main__":
    main()
