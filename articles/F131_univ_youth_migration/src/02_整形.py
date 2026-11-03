"""02 整形：学校基本調査（出身高校の所在地県別 入学者数）と住民基本台帳人口移動報告（年齢5歳階級別 転入超過数）を
都道府県×年の表にする。

出力
- data/flows_univ.csv  : year, kind(univ/junior), sheet(計/国立/公立/私立/男/女), dest(大学の所在地), orig(出身高校の所在地), n
- data/netmig_age.csv  : year, pref, sex(総数/男/女), age(15-19 など), net (日本人移動者の転入超過数)
- data/hs_grads.csv    : year, pref, hs_grads, jhs_grads, pop  (SSDSE-B-2026、2012〜2023年度)
"""
import json, csv, io, re, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")

PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]


def norm(s):
    s = re.sub(r"[\s　]", "", str(s))
    if s in PREFS:
        return s
    s2 = re.sub(r"(都|府|県)$", "", s)
    return s2 if s2 in PREFS else None


def num(s):
    s = str(s).replace(",", "").replace(" ", "").strip()
    if s in ("", "-", "－", "…", "x", "X"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def sheet_label(text):
    head = " ".join(text.split("\n")[:6])
    head = re.sub(r"[\s　]", "", head)
    for key, lab in [("計のうち男", "男"), ("計のうち女", "女"), ("国立", "国立"), ("公立", "公立"), ("私立", "私立")]:
        if key in head:
            return lab
    if re.search(r"[0-9１-９]計", head):
        return "計"
    return None


def parse_matrix(text):
    """1シート分の行列を {(dest, orig): n} で返す。列見出し行（県名が並ぶ行）を探す。"""
    rows = list(csv.reader(io.StringIO(text)))
    hdr_i, cols = None, None
    for i, r in enumerate(rows[:12]):
        names = [norm(c) for c in r]
        if sum(n is not None for n in names) >= 10:
            hdr_i, cols = i, names
            break
    if hdr_i is None:
        return {}
    out = {}
    for r in rows[hdr_i + 1:]:
        # 行ラベル：先頭側で最初に県名になるセル
        lab = None
        for j, c in enumerate(r[:4]):
            if norm(c):
                lab = norm(c)
                break
        if lab is None:
            continue
        for j, o in enumerate(cols):
            if o and j < len(r):
                v = num(r[j])
                if v is not None:
                    out[(lab, o)] = v
    return out


def main():
    D = json.load(open(os.path.join(RAW, "f131_school_mig.json"), encoding="utf-8"))
    # --- 学校基本調査
    rec = []
    for k, sheets in D.items():
        if not k.startswith("S"):
            continue
        year = int(k[1:5])
        first = sheets[list(sheets)[0]]
        kind = "junior" if "短期大学の所在地" in first or re.search(r"^\s*,*\s*4[1-6][\s　]", first) else "univ"
        if "大学の所在地" in first and "短期大学の所在地" not in first:
            kind = "univ"
        cur = None
        for name, txt in sheets.items():
            lab = sheet_label(txt)
            if "つづき" in re.sub(r"[\s　]", "", " ".join(txt.split("\n")[:6])):
                lab = cur  # 続きのシートは直前の区分
            cur = lab
            if lab is None:
                continue
            for (d, o), v in parse_matrix(txt).items():
                rec.append((year, kind, lab, d, o, v))
    f = pd.DataFrame(rec, columns=["year", "kind", "sheet", "dest", "orig", "n"])
    f = f.groupby(["year", "kind", "sheet", "dest", "orig"], as_index=False)["n"].max()
    f["n"] = f["n"].astype(int)
    f[f.n > 0].to_csv(os.path.join(ROOT, "data", "flows_univ.csv"), index=False)  # 0 の組は省く
    chk = f[(f.sheet == "計")].groupby(["kind", "year"]).agg(n=("n", "sum"), cells=("n", "size"))
    print(chk.to_string())

    # --- 人口移動報告（日本人移動者）
    ages = ["総数", "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59",
            "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
    use = {2010: "000008636883", 2011: "000012678261"}
    mrec = []
    for k, sheets in D.items():
        if not k.startswith("M"):
            continue
        year, sid = int(k[1:5]), k.split(":")[1]
        if year in use and use[year] != sid:
            continue
        if year >= 2020:
            txt = sheets[list(sheets)[0]]
            for r in csv.reader(io.StringIO(txt)):
                if len(r) >= 67 and r[1].strip() == "61000":
                    p = norm(r[6])
                    if not p:
                        continue
                    for si, sex in enumerate(["総数", "男", "女"]):
                        for ai, a in enumerate(ages):
                            mrec.append((year, p, sex, a, num(r[7 + si * 20 + ai])))
        else:
            txt = sheets["日本人移動者"] if "日本人移動者" in sheets else sheets[list(sheets)[0]]
            for r in csv.reader(io.StringIO(txt)):
                if len(r) > 81 and norm(r[10]):
                    p = norm(r[10])
                    for si, base in enumerate([12, 37, 62]):
                        sex = ["総数", "男", "女"][si]
                        for ai, a in enumerate(ages):
                            mrec.append((year, p, sex, a, num(r[base + ai])))
    m = pd.DataFrame(mrec, columns=["year", "pref", "sex", "age", "net"]).drop_duplicates(["year", "pref", "sex", "age"])
    m.to_csv(os.path.join(ROOT, "data", "netmig_age.csv"), index=False)
    print(m[(m.sex == "総数") & (m.age == "15-19")].groupby("year").agg(n=("pref", "size"), s=("net", "sum"),
                                                                        tokyo=("net", lambda x: x[m.loc[x.index, "pref"] == "東京"].sum())).to_string())

    # --- SSDSE-B（高校卒業者数など）
    s = pd.read_csv(os.path.join(RAW, "SSDSE-B-2026.csv"), encoding="cp932", header=1)
    s = s.rename(columns={"年度": "year", "都道府県": "pref"})
    s["pref"] = s["pref"].map(norm)
    out = s[["year", "pref", "高等学校卒業者数", "高等学校卒業者のうち進学者数", "中学校卒業者数", "総人口"]].copy()
    out.columns = ["year", "pref", "hs_grads", "hs_grads_to_higher", "jhs_grads", "pop"]
    out.to_csv(os.path.join(ROOT, "data", "hs_grads.csv"), index=False)
    print(out.groupby("year")[["hs_grads", "hs_grads_to_higher"]].sum().to_string())


if __name__ == "__main__":
    main()
