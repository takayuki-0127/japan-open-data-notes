"""data/raw の JSON を長い形の表 data/pref_monthly.csv にまとめ、公表資料の Excel と照らす（オフライン）。
地域の名前は系列名（「青森／東北計／全国計／預金合計／国内銀行」）の見出しの文字から付ける。"""
import json, pathlib
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ITEMS = {"預金合計": "deposits", "一般預金": "general", "個人預金": "personal", "公金預金": "public", "金融機関預金": "fin", "譲渡性預金": "cd", "貸出金": "loans"}
REGIONS = ["北海道", "東北計", "関東計", "北陸計", "中部計", "近畿計", "中国計", "四国計", "九州・沖縄計"]

def main():
    rows = []
    for f in sorted(RAW.glob("boj_MD12_*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        for r in j["RESULTSET"]:
            p = [x.strip() for x in r["NAME_OF_TIME_SERIES_J"].split("／")]
            assert p[-1] == "国内銀行"
            item = ITEMS[p[-2]]
            area = p[0]
            if area == "全国計":
                kind, region = "全国", "全国計"
            elif area == "北海道":
                kind, region = "都道府県", "北海道"
            elif area.endswith("計"):
                kind, region = "地方", area
            else:
                kind, region = "都道府県", p[1]
            assert region in REGIONS or region == "全国計", (area, region)
            for d, v in zip(r["VALUES"]["SURVEY_DATES"], r["VALUES"]["VALUES"]):
                if v is None: continue
                rows.append((kind, region, area, item, str(d), float(v)))
    df = pd.DataFrame(rows, columns=["kind", "region", "area", "item", "ym", "oku_yen"]).sort_values(["kind", "region", "area", "item", "ym"])
    assert df[df.kind == "都道府県"].area.nunique() == 47
    df.to_csv(ROOT / "data" / "pref_monthly.csv", index=False, encoding="utf-8")

    # 照らし合わせ：公表資料（2026年3月末）の値と、API の 2026年3月の値を、都道府県名で突き合わせる
    ws = openpyxl.load_workbook(RAW / "boj_pref_pre2603.xlsx", data_only=True).active
    col = {"deposits": 1, "general": 2, "personal": 6, "public": 7, "fin": 8, "cd": 10, "loans": 14}
    hdr = [ws.cell(7, 2).value, ws.cell(8, 3).value, ws.cell(9, 7).value, ws.cell(8, 8).value, ws.cell(8, 9).value, ws.cell(7, 11).value, ws.cell(7, 15).value]
    assert hdr == ["預金", "一般預金", "個人預金", "公金預金", "金融機関預金", "譲渡性預金", "貸出金"], hdr
    x = {}
    for r in ws.iter_rows(min_row=13, values_only=True):
        if r[0] is None or not isinstance(r[1], (int, float)): continue
        name = str(r[0]).strip().replace("　", "")
        x[name] = {k: float(r[c]) for k, c in col.items()}
    api = df[df.ym == "202603"].pivot_table(index="area", columns="item", values="oku_yen")
    chk = []
    for name, vals in x.items():
        key = name if name in api.index else (name + "計" if name + "計" in api.index else None)
        if key is None:
            continue
        for k, v in vals.items():
            chk.append({"area": key, "item": k, "excel": v, "api": float(api.loc[key, k]), "diff": float(api.loc[key, k]) - v})
    chk = pd.DataFrame(chk)
    chk.to_csv(ROOT / "data" / "check_vs_excel_202603.csv", index=False, encoding="utf-8")
    print("照らした地域", chk.area.nunique(), "項目", len(chk), "最大の差", chk["diff"].abs().max())
    assert chk[chk.area.isin(df[df.kind == "都道府県"].area.unique())].area.nunique() == 47
    assert chk["diff"].abs().max() < 1.0

if __name__ == "__main__":
    main()
