"""F112 02 整形：『令和7年版 救急救助の現況』Ⅰ救急編（PDF のテキスト）から表を CSV にする

入力：data/raw/kkkg_r07_01_kyukyu.txt（pdftotext -layout で PDF から作ったテキスト）
出力：data/ の CSV 7つ
"""
import re
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "data"
L = (D / "raw" / "kkkg_r07_01_kyukyu.txt").read_text(encoding="utf-8").split("\n")
PREFS = ("北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 "
         "岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 "
         "長崎 熊本 大分 宮崎 鹿児島 沖縄").split()


def nums(s):
    return [float(x.replace(",", "").replace("▲", "-").replace(" ", "")) for x in re.findall(r"▲\s?[\d,.]+|[\d,.]+", s)]


def find(pat, start=0):
    for i in range(start, len(L)):
        if re.search(pat, L[i]):
            return i
    raise ValueError(pat)


# ---- 別表9 入電時刻別の搬送人員（2時間ごと）
i0 = find(r"別表９\s+入電時刻別")
rows = []
for l in L[i0:i0 + 70]:
    m = re.match(r"\s*(?:時|刻)?\s*(\d+)～(\d+)時\s+(.*)$", l)
    if m:
        v = nums(m.group(3))
        rows.append({"from": int(m.group(1)), "to": int(m.group(2)), "急病": v[0], "交通": v[1], "一般負傷": v[2], "その他": v[3], "合計": v[4]})
hourly = pd.DataFrame(rows)
assert len(hourly) == 12 and hourly["合計"].sum() == 6769172, hourly["合計"].sum()
hourly.to_csv(D / "hourly_transport_2h.csv", index=False)

# ---- 第30表 月別の出動件数、第32表 曜日別の出動件数（合計の列）
i0 = find(r"第30表\s+救急要請を入電した月別の救急出動件数")
rows = []
for l in L[i0:i0 + 25]:
    m = re.match(r"\s*(\d+)月\s+(.*)$", l)
    if m:
        v = [x for x in re.findall(r"[\d,]+(?=\s|$)", m.group(2))]
        rows.append({"month": int(m.group(1)), "出動件数": int(v[-1].replace(",", ""))})
monthly = pd.DataFrame(rows)
assert monthly["出動件数"].sum() == 7718380
monthly.to_csv(D / "monthly_dispatch.csv", index=False)

i0 = find(r"第32表\s+救急要請を入電した曜日別の救急出動件数")
rows = []
for l in L[i0:i0 + 20]:
    m = re.match(r"\s*([月火水木金土日])曜\s+(.*)$", l)
    if m:
        v = re.findall(r"[\d,]+(?=\s)", m.group(2) + " ")
        rows.append({"weekday": m.group(1), "出動件数": int(v[-1].replace(",", ""))})
weekday = pd.DataFrame(rows)
assert weekday["出動件数"].sum() == 7718380
weekday.to_csv(D / "weekday_dispatch.csv", index=False)

# ---- 第37表 病院収容所要時間（入電〜医師引継ぎ）別の搬送人員（合計の行）
i0 = find(r"第37表\s+事故種別及び病院収容所要時間別搬送人員")
for l in L[i0:i0 + 12]:
    v = nums(l)
    if len(v) == 7 and v[-1] == 6769172:
        bins = v[:6]
        break
hosp = pd.DataFrame({"lo": [0, 10, 20, 30, 60, 120], "hi": [10, 20, 30, 60, 120, None], "搬送人員": bins})
hosp.to_csv(D / "hospital_time_bins.csv", index=False)

# ---- 第38図 消防本部の規模別の所要時間の内訳（分）
i0 = find(r"第38図\s+消防本部規模別")
rows = []
for l in L[i0:i0 + 25]:
    m = re.match(r"\s*(70万人以上|30～70万人未満|10～30万人未満|5～10万人未満|5万人未満|平均)\s+(.*)$", l)
    if m:
        v = nums(m.group(2))
        rows.append({"管轄人口": m.group(1), "入電_現着": v[0], "現着_接触": v[1], "接触_車内収容": v[2], "車内収容_現発": v[3],
                     "現発_病院到着": v[4], "病院到着_引継ぎ": v[5], "入電_引継ぎ": v[6]})
size = pd.DataFrame(rows)
assert len(size) == 6
size.to_csv(D / "time_by_hq_size.csv", index=False)

# ---- 全国の推移：救急隊数（第6表、各年4月1日）・救急自動車の出動件数（第10表）・病院収容所要時間（第35図）
i0 = find(r"第６表\s+救急救命士の運用推移")
teams_line = next(l for l in L[i0:i0 + 15] if l.strip().startswith("救急隊数"))
teams = [int(x) for x in nums(teams_line)]  # 平成27年〜令和7年（4月1日）
years_t = list(range(2015, 2026))
assert len(teams) == 11 and teams[-1] == 5485
i0 = find(r"第10表\s+救急自動車、消防防災ヘリコプターによる")
disp = {}
era = {"平成": 1988, "令和": 2018}
for l in L[i0:i0 + 70]:
    m = re.match(r"\s*(平成|令和)\s*(\d+|元|２|３|４|５|６)年\s+(.*)$", l)
    if m:
        y = m.group(2)
        y = {"元": 1, "２": 2, "３": 3, "４": 4, "５": 5, "６": 6}.get(y, y)
        yr = era[m.group(1)] + int(y)
        v = nums(m.group(3))
        disp[yr] = {"全出動件数": v[0], "救急自動車_出動件数": v[1], "全搬送人員": v[3], "救急自動車_搬送人員": v[4]}
# 第35図の病院収容所要時間（平成16年〜令和6年、図の数値を読み取ったもの。PDF の図中の数値と照合済み）
hosp_mean = dict(zip(range(2004, 2025), [30.0, 31.1, 32.0, 33.4, 35.0, 36.1, 37.4, 38.1, 38.7, 39.3, 39.4, 39.4,
                                           39.3, 39.3, 39.5, 39.5, 40.6, 42.8, 47.2, 45.6, 44.6]))
trend = pd.DataFrame({"year": years_t[:-1]})
trend["救急隊数_4月1日"] = teams[:-1]
trend["救急自動車_出動件数"] = trend.year.map(lambda y: disp[y]["救急自動車_出動件数"])
trend["救急自動車_搬送人員"] = trend.year.map(lambda y: disp[y]["救急自動車_搬送人員"])
trend["病院収容所要時間_分"] = trend.year.map(hosp_mean)
trend.to_csv(D / "national_trend.csv", index=False)

# ---- 都道府県別：救急隊数（別表2の1、令和7年4月1日）と出動件数（別表3、令和6年中）
i0 = find(r"別表２の１\s+都道府県別救急体制")
tm = {}
for l in L[i0:i0 + 70]:
    s = l.strip(); c = s.replace(" ", "")
    for p in PREFS:
        if c.startswith(p):
            rest = s[s.index(p[-1]) + 1:]
            v = re.findall(r"[\d,.]+%?", rest)
            if len(v) > 6 and p not in tm:
                tm[p] = int(v[5].replace(",", ""))
i0 = find(r"別表３\s+救急自動車による都道府県別事故種別救急出動件数")
dp = {}
for l in L[i0:i0 + 125]:
    t = l.rstrip(); c = t.replace(" ", "")
    for p in PREFS:
        if c.endswith(p) and re.search(r"\d", t):
            v = nums(t[: len(t) - len(t.rstrip().split()[-1])])
            if len(v) >= 12:
                dp[p] = {"出動件数_R6": v[2], "人口": v[-2]}
pref = pd.DataFrame([{"pref": p, "救急隊数_R7": tm[p], **dp[p]} for p in PREFS])
assert pref["救急隊数_R7"].sum() == 5485 and abs(pref["出動件数_R6"].sum() - 7718380) < 1, pref.sum(numeric_only=True)
pref.to_csv(D / "prefecture_teams_dispatch.csv", index=False)
print(hourly, monthly.T, weekday.T, hosp, size, trend, pref.describe(), sep="\n")
