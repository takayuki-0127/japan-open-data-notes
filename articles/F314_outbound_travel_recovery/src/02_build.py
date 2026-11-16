"""02 整形（オフライン）：data/raw の表から、縦長の CSV を作る。
出力：data/outbound_pref_age_sex.csv（年・都道府県・年齢・男女・出国者数）
      data/outbound_port_month.csv（年・月・港・区分・出国者数）
      data/pop_pref_age_sex.csv（2019・2024年の日本人人口、千人）
      data/monthly_fx_price.csv（月：ドル・円、実質実効為替レート、外国パック旅行費・航空運賃の物価指数）
      data/annual_price.csv（年：外国パック旅行費・航空運賃・総合の物価指数）"""
import glob, io, pathlib, re, warnings
import pandas as pd, xlrd, openpyxl

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井",
         "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川",
         "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70+"]
clean = lambda s: re.sub(r"[\s　]", "", str(s))

def num(x):
    if clean(x) in ("-", "－", "―", "‐"):
        return 0.0  # 「-」は該当なし（その月の出国者がいない）
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return float("nan")

# --- 住所地別 年齢・男女別 出国日本人 ---
recs = []
for f in sorted(glob.glob(str(RAW / "imm_pref_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    v = list(pd.read_excel(f, sheet_name=None, header=None).values())[0]
    hr = [i for i in range(8) if any(clean(x) == "0～4歳" for x in v.iloc[i])][0]
    head = {clean(v.iloc[hr, j]): j for j in range(v.shape[1]) if clean(v.iloc[hr, j]) not in ("nan", "")}
    sexrow = hr + 1
    agecols = {}
    for lab, j in head.items():
        m = re.fullmatch(r"(\d+)～(\d+)歳", lab)
        key = f"{m.group(1)}-{m.group(2)}" if m else ("70+" if lab == "70歳以上" else ("unk" if lab == "不詳" else ("total" if lab == "総数" else None)))
        if key is None:
            continue
        assert clean(v.iloc[sexrow, j]) == "男" and clean(v.iloc[sexrow, j + 1]) == "女", (y, lab)
        agecols[key] = j
    assert all(a in agecols for a in AGES), (y, agecols.keys())
    for i in range(hr + 2, v.shape[0]):
        lab = clean(v.iloc[i, 0])
        if lab in ("nan", ""):
            continue
        if lab not in PREFS + ["総数", "外国", "不詳"]:
            continue
        for key, j in agecols.items():
            for k, sex in enumerate(["男", "女"]):
                recs.append(dict(year=y, pref=lab, age=key, sex=sex, n=num(v.iloc[i, j + k])))
d = pd.DataFrame(recs)
assert d.groupby("year").pref.nunique().eq(50).all(), d.groupby("year").pref.nunique()
# 確かめ：年齢の合計（不詳を含む）＝総数、都道府県＋外国＋不詳の合計＝総数
a = d[d.age != "total"].groupby(["year", "pref", "sex"]).n.sum()
t = d[d.age == "total"].set_index(["year", "pref", "sex"]).n
assert (a - t).abs().max() == 0, (a - t).abs().sort_values().tail()
p = d[(d.age == "total") & (d.pref != "総数")].groupby(["year", "sex"]).n.sum()
t2 = d[(d.age == "total") & (d.pref == "総数")].set_index(["year", "sex"]).n
assert (p - t2).abs().max() == 0
d.sort_values(["year", "pref", "age", "sex"]).to_csv(DATA / "outbound_pref_age_sex.csv", index=False)

# --- 月別 主要港の出国日本人 ---
NORM = {"富士山静岡": "静岡", "大阪（阪神）": "大阪", "神戸（阪神）": "神戸"}
recs = []
for f in sorted(glob.glob(str(RAW / "imm_port_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    v = list(pd.read_excel(f, sheet_name=None, header=None).values())[0]
    hr = [i for i in range(5) if any(clean(x) == "1月" for x in v.iloc[i])][0]
    mcol = {int(clean(v.iloc[hr, j])[:-1]): j for j in range(v.shape[1]) if re.fullmatch(r"\d+月", clean(v.iloc[hr, j]))}
    tcol = [j for j in range(v.shape[1]) if clean(v.iloc[hr, j]) == "総数"][0]
    group = None
    for i in range(hr + 1, v.shape[0]):
        name = next((clean(v.iloc[i, j]) for j in range(tcol) if clean(v.iloc[i, j]) not in ("nan", "")), None)
        if name is None:
            continue
        if name in ("総数", "空港", "海港"):
            group = {"総数": "総数", "空港": "空港", "海港": "海港"}[name]
            port = name
        else:
            port = NORM.get(name, name)
        total = num(v.iloc[i, tcol])
        ms = [num(v.iloc[i, mcol[m]]) for m in range(1, 13)]
        assert abs(sum(ms) - total) < 1, (y, port, sum(ms), total)
        for m in range(1, 13):
            recs.append(dict(year=y, month=m, kind=group, port=port, n=ms[m - 1]))
pm = pd.DataFrame(recs)
# 確かめ：空港＋海港＝総数、各港の合計＝空港（海港）の行
for y, g in pm.groupby("year"):
    s = g.groupby(["kind", "port"]).n.sum()
    assert abs(s[("空港", "空港")] + s[("海港", "海港")] - s[("総数", "総数")]) < 1
    for k in ("空港", "海港"):
        assert abs(s[k].drop(k).sum() - s[(k, k)]) < 1, (y, k)
pm.to_csv(DATA / "outbound_port_month.csv", index=False)

# --- 人口推計 第10表（日本人人口、千人） ---
PA = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
recs = []
s = xlrd.open_workbook(str(RAW / "pop_t10_2019.xls")).sheet_by_index(0)
blocks = [(i, clean(s.cell_value(i, 15))[-1]) for i in range(s.nrows)
          if clean(s.cell_value(i, 15)).startswith("日本人人口") and not clean(s.cell_value(i, 15)).endswith("男女計")]
assert [b[1] for b in blocks] == ["男", "女"], blocks
for start, sex in blocks:
    for i in range(start, min(start + 62, s.nrows)):
        code = clean(s.cell_value(i, 8))
        if re.fullmatch(r"\d{2}", code):
            assert PREFS[int(code) - 1] in clean(s.cell_value(i, 9))
            for j, a in enumerate(PA):
                recs.append(dict(year=2019, pref=PREFS[int(code) - 1], age=a, sex=sex, pop_k=float(s.cell_value(i, 13 + j))))
ws = openpyxl.load_workbook(str(RAW / "pop_t10_2024.xlsx"), read_only=True).worksheets[0]
for r in ws.iter_rows(min_row=8, values_only=True):
    if r[9] != "日本人人口" or r[12] not in ("男", "女") or r[10] == "00000":
        continue
    pc = int(str(r[10])[:2])
    for j, a in enumerate(PA):
        recs.append(dict(year=2024, pref=PREFS[pc - 1], age=a, sex=r[12], pop_k=float(r[16 + j])))
pop = pd.DataFrame(recs)
assert pop.groupby("year").size().eq(47 * 18 * 2).all()
pop["age"] = pop.age.where(~pop.age.isin(["70-74", "75-79", "80-84", "85+"]), "70+")
pop = pop.groupby(["year", "pref", "age", "sex"], as_index=False).pop_k.sum()
pop.to_csv(DATA / "pop_pref_age_sex.csv", index=False)

# --- 為替（日本銀行） ---
def boj(name, col):
    txt = (RAW / name).read_bytes().decode("cp932")
    lines = txt.splitlines()
    k = [i for i, l in enumerate(lines) if l.startswith("SERIES_CODE")][0]
    b = pd.read_csv(io.StringIO("\n".join(lines[k:])))
    return pd.DataFrame({"ym": b.SURVEY_DATES.astype(int), col: pd.to_numeric(b.VALUES, errors="coerce")})
fx = boj("boj_usdjpy_monthly.csv", "usdjpy").merge(boj("boj_reer_monthly.csv", "reer"), on="ym", how="outer")

# --- 消費者物価指数（品目別） ---
def cpi(name, items, monthly):
    t = pd.read_csv(RAW / name, encoding="cp932", header=None, dtype=str)
    head = t.iloc[0].tolist()
    cols = {}
    for it in items:
        js = [j for j, x in enumerate(head) if str(x).strip() == it]
        cols[it] = js[-1]  # 同じ名の類と品目があるときは品目（右側）
    t[0] = t[0].str.strip()
    b = t[t[0].str.fullmatch(r"\d{6}" if monthly else r"\d{4}", na=False)]
    out = pd.DataFrame({("ym" if monthly else "year"): b[0].astype(int).values})
    for it, j in cols.items():
        out[it] = pd.to_numeric(b[j], errors="coerce").values
    return out
ITEMS = ["総合", "外国パック旅行費", "航空運賃"]
cm = cpi("cpi_item_monthly.csv", ITEMS, True).rename(columns={"総合": "cpi_all", "外国パック旅行費": "cpi_foreign_pack", "航空運賃": "cpi_airfare"})
ca = cpi("cpi_item_annual.csv", ITEMS, False).rename(columns={"総合": "cpi_all", "外国パック旅行費": "cpi_foreign_pack", "航空運賃": "cpi_airfare"})
mon = fx.merge(cm, on="ym", how="left")
mon = mon[(mon.ym >= 201201) & (mon.ym <= 202512)].sort_values("ym")
mon.to_csv(DATA / "monthly_fx_price.csv", index=False)
ca[(ca.year >= 2012) & (ca.year <= 2025)].to_csv(DATA / "annual_price.csv", index=False)
print(d.groupby("year").n.sum() / 2, pm[pm.port == "総数"].groupby("year").n.sum(), pop.groupby("year").pop_k.sum(), mon.tail(3), ca.tail(3), sep="\n")
