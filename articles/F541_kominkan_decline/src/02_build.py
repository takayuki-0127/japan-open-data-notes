"""data/raw の Excel から、全国の推移（data/national.csv）と都道府県の表（data/pref.csv）を作る。
都道府県の名前は行の順ではなく、表の見出しの文字（「青   森」「青森県」など）を正規化して付ける。
列は見出しの文字（「計」「町」「村」）で選ぶ。"""
import json, pathlib, re, unicodedata
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]
REGION = {**{p: "北海道" for p in ["北海道"]}, **{p: "東北" for p in PREFS[1:7]}, **{p: "関東" for p in PREFS[7:14]},
          **{p: "中部" for p in PREFS[14:23]}, **{p: "近畿" for p in PREFS[23:30]}, **{p: "中国" for p in PREFS[30:35]},
          **{p: "四国" for p in PREFS[35:39]}, **{p: "九州・沖縄" for p in PREFS[39:47]}}


def norm(x):
    s = unicodedata.normalize("NFKC", str(x))
    s = re.sub(r"\s+", "", s)
    return s


def pref_name(x):
    s = norm(x)
    if s in ("全国",):
        return "全国"
    if s in PREFS:
        return s
    if s.endswith(("県", "府", "都")) and s[:-1] in PREFS:
        return s[:-1]
    return None


def sheet_kind(v):
    for r in range(min(8, len(v))):
        for c in v.columns:
            s = norm(v.iloc[r, c])
            s2 = re.sub(r"^[0-9]+[.．、]?", "", s)
            if s2 in ("計", "本館", "分館") and re.match(r"^[0-9]", s):
                return s2
    return None


def read_rows(v, labels=("計",)):
    """全国と47都道府県の行を名前で拾い、見出しの文字で選んだ列の値を返す。"""
    rows = {}
    name_col = None
    first = None
    for r in range(len(v)):
        for c in v.columns:
            p = pref_name(v.iloc[r, c])
            if p:
                if p in rows:
                    raise ValueError(f"重複 {p}")
                rows[p] = r
                if p == "全国":
                    name_col, first = c, r
                break
    if len(rows) != 48:
        raise ValueError(f"行が {len(rows)} 個")
    out = {}
    for lab in labels:
        cand = []
        for r in range(first):
            for c in v.columns:
                if c > name_col and norm(v.iloc[r, c]) == lab:
                    cand.append(c)
        if not cand:
            raise ValueError(f"見出し {lab} なし")
        col = min(cand)
        out[lab] = {p: float(v.iloc[r, col]) for p, r in rows.items()}
    return pd.DataFrame(out)


def kominkan(fname):
    x = pd.read_excel(RAW / fname, header=None, sheet_name=None)
    got = {}
    for k, v in x.items():
        kind = sheet_kind(v)
        if kind:
            got[kind] = read_rows(v)["計"]
    d = pd.DataFrame(got)
    if "計" not in d:
        d["計"] = d["本館"] + d["分館"]
    elif not (d["計"] == d["本館"] + d["分館"]).all():
        raise ValueError("計 ≠ 本館＋分館")
    return d.rename(columns={"計": "total", "本館": "honkan", "分館": "bunkan"})


def municipal(fname):
    v = pd.read_excel(RAW / fname, header=None)
    d = read_rows(v, labels=("計", "町", "村"))
    return d.rename(columns={"計": "muni", "町": "town", "村": "village"})


def era_year(era, n):
    n = 1 if str(n).strip() in ("元",) else int(n)
    return {"昭和": 1925, "平成": 1988, "令和": 2018}[era] + n


def national():
    v = pd.read_excel(RAW / "nenji_01_facilities.xlsx", header=None)
    hr = [r for r in range(len(v)) if norm(v.iloc[r, 0]) == "区分"][0]
    cols = {norm(v.iloc[hr, c]): c for c in v.columns}
    ck = cols["公民館(類似施設含む)"]
    fac = {}
    for r in range(hr + 1, len(v)):
        m = re.match(r"^(昭和|平成|令和)(元|\d+)年度$", norm(v.iloc[r, 0]))
        if m:
            fac[era_year(m.group(1), m.group(2))] = float(v.iloc[r, ck])
    u = pd.read_excel(RAW / "nenji_07_users.xlsx", header=None)
    hr = [r for r in range(len(u)) if any(norm(u.iloc[r, c]) == "区分" for c in u.columns)][0]
    cu = [c for c in u.columns if norm(u.iloc[hr, c]) == "公民館(類似施設含む)"][0]
    users = {}
    for r in range(hr + 1, len(u)):
        e, n, t = norm(u.iloc[r, 0]), norm(u.iloc[r, 1]), norm(u.iloc[r, 2])
        if e in ("昭和", "平成", "令和") and t == "年度間":
            val = u.iloc[r, cu]
            try:
                users[era_year(e, n)] = float(val)
            except (TypeError, ValueError):
                users[era_year(e, n)] = None
    nat = pd.DataFrame({"facilities_incl_similar": pd.Series(fac), "users_thousand_fy": pd.Series(users)})
    nat.index.name = "year"
    return nat.sort_index()


def main():
    nat = national()
    nat.to_csv(BASE / "data" / "national.csv", float_format="%.0f")
    parts = {}
    for y, kf, mf in [(2002, "h14_kominkan_by_setter.xls", "h14_municipal_setting.xls"),
                      (2005, "h17_kominkan_honkan_bunkan.xls", "h17_municipal_setting.xls"),
                      (2024, "r6_kominkan_honkan_bunkan.xlsx", "r6_municipal_setting.xlsx")]:
        k = kominkan(kf); m = municipal(mf)
        d = k.join(m)
        # 全国＝47都道府県の和の確かめ
        for c in d.columns:
            s47 = d.loc[PREFS, c].sum()
            if abs(s47 - d.loc["全国", c]) > 0.5:
                raise ValueError((y, c, s47, d.loc["全国", c]))
        d.columns = [f"{c}_{y}" for c in d.columns]
        parts[y] = d
    pref = pd.concat(parts.values(), axis=1).loc[["全国"] + PREFS]
    pref.insert(0, "region", ["全国"] + [REGION[p] for p in PREFS])
    pref.index.name = "pref"
    pref.to_csv(BASE / "data" / "pref.csv", float_format="%.0f")
    checks = {"national_2024": nat.loc[2024, "facilities_incl_similar"], "national_2002": nat.loc[2002, "facilities_incl_similar"],
              "users_2023": nat.loc[2023, "users_thousand_fy"],
              "zenkoku_2002_total": pref.loc["全国", "total_2002"], "zenkoku_2024_honkan": pref.loc["全国", "honkan_2024"],
              "zenkoku_2024_bunkan": pref.loc["全国", "bunkan_2024"], "muni_2002": pref.loc["全国", "muni_2002"], "muni_2024": pref.loc["全国", "muni_2024"],
              "aomori_2002_total": pref.loc["青森", "total_2002"], "kumamoto_2024_bunkan": pref.loc["熊本", "bunkan_2024"],
              "hokkaido_2024_muni": pref.loc["北海道", "muni_2024"], "okinawa_2002_total": pref.loc["沖縄", "total_2002"],
              "sum47_equals_zenkoku": True}
    (BASE / "data" / "build_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))
    print(nat.to_string())


if __name__ == "__main__":
    main()
