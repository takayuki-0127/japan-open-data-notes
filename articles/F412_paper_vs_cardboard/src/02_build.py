"""生産動態統計の年報から、紙・板紙の品種別の生産・販売と、段ボールの生産・消費部門別内訳の年の系列をつくる。
2008〜2020年：分野別の年報（2012・2017・2020年版）の「製品時系列表」の年計の行。
2021〜2025年：全品目の年報（実数表）。2021〜2023年版は暦年の列、2024・2025年版は月次を12か月足す。"""
import datetime as dt
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"


def norm(x):
    return re.sub(r"[\s　]", "", str(x))


# 旧様式（製品時系列表）：(シートの区分, ラベルの正規表現, 系列名, 取る列のずれ（0=生産、1=販売数量）)
OLD_SHEETS = {
    "nenpo2012_paper.xls": {"paper": "製品時系列表　紙40-61", "board": "製品時系列表　板　紙62－70",
                            "cb": "製品時系列表　段ボール71-72", "cbuse": "消費部門別内訳　段ボール73"},
    "nenpo2017_paper.xls": {"paper": "P12-33_紙", "board": "P34-41_板紙", "cb": "P42-43_段ボール", "cbuse": "P44_段ボール(内訳)"},
    "nenpo2020_paper.xls": {"paper": "P17-38_紙", "board": "P39-46_板紙", "cb": "P47-48_段ボール", "cbuse": "P49_段ボール(内訳)"},
}
TARGETS = [
    ("paper", r"^１．紙計", "paper_total"), ("paper", r"^２．新聞巻取紙", "newsprint"),
    ("paper", r"^３．印刷・情報用紙", "printing_info"), ("paper", r"^４．包装用紙", "wrapping"),
    ("paper", r"^５．衛生用紙", "sanitary"), ("paper", r"^６．雑種紙", "misc_paper"),
    ("board", r"^１．板紙計", "board_total"), ("board", r"^２．段ボール原紙", "containerboard"),
    ("board", r"^３．紙器用板紙", "boxboard"), ("board", r"^４．雑板紙", "misc_board"),
    ("cb", r"^１．合計", "cb_sheet"),
]
# 段ボールの消費（次工程投入）部門別内訳：(ラベル, 系列名)
# 上の表（年はシリアル値で入っている）
CBUSE_UPPER = [("合計", "use_total"), ("電気器具・", "use_machinery"), ("薬品・洗剤", "use_medicine"),
               ("加工食品", "use_processed_food"), ("青果物", "use_produce")]
# 下の表（年は日付で入っている）
CBUSE_LOWER = [("繊維製品用", "use_textile"), ("陶磁器・ガラス", "use_ceramics"), ("通販・宅配", "use_mailorder"),
               ("包装用以外", "use_nonpack")]


def annual_rows(d, i, j):
    """ラベルの位置 (i, j) の下にある年計の行（1月1日の日付が入った行が続くところ）から、年と行番号を返す。"""
    out, last = [], None
    for r in range(i + 1, min(i + 40, d.shape[0])):
        stamp = None
        for c in range(j + 1, min(j + 11, d.shape[1])):
            v = d.iat[r, c]
            if isinstance(v, (dt.datetime, pd.Timestamp)):
                stamp = v
                break
        if stamp is None:
            if out:
                break
            continue
        if stamp.month != 1 or (last is not None and stamp.year <= last):
            break
        out.append((stamp.year, r))
        last = stamp.year
    return out


def annual_rows_serial(d, i, col=2):
    """上の表：col 列に Excel のシリアル値（1月1日）が入った年計の行を返す。"""
    out, last = [], None
    for r in range(i + 1, min(i + 20, d.shape[0])):
        v = d.iat[r, col]
        stamp = None
        if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v) and 30000 < v < 60000:
            stamp = dt.datetime(1899, 12, 30) + dt.timedelta(days=int(v))  # 2012・2017年版：シリアル値
        elif isinstance(v, str) and re.fullmatch(r"(19|20)\d\d", v.strip()):
            stamp = dt.datetime(int(v.strip()), 1, 1)  # 2020年版：年が文字で入っている
        if stamp is not None:
            if stamp.month != 1 or (last is not None and stamp.year <= last):
                break
            out.append((stamp.year, r))
            last = stamp.year
        elif out:
            break
    return out


def find_label(d, pattern, rows=range(0, 60)):
    for i in rows:
        if i >= d.shape[0]:
            break
        for j in range(d.shape[1]):
            if re.search(pattern, norm(d.iat[i, j])):
                return i, j
    return None


def parse_old():
    rec = []
    for fname, sh in OLD_SHEETS.items():
        cache = {k: pd.read_excel(RAW / fname, s, header=None) for k, s in sh.items()}
        for kind, pat, name in TARGETS:
            d = cache[kind]
            pos = find_label(d, pat)
            assert pos, (fname, name)
            i, j = pos
            rows = annual_rows(d, i + 1, j)
            assert len(rows) >= 4, (fname, name, rows)
            for y, r in rows:
                rec.append((fname, y, name, "production", float(d.iat[r, j])))
                if kind != "cb":
                    rec.append((fname, y, name, "sales_qty", float(d.iat[r, j + 1])))
        d = cache["cbuse"]
        for lab, name in CBUSE_UPPER:
            i, j = find_label(d, "^" + re.escape(lab) + ("$" if lab == "合計" else ""))
            rows = annual_rows_serial(d, i)
            assert len(rows) == 5, (fname, name, rows)
            for y, r in rows:
                rec.append((fname, y, name, "consumption", float(d.iat[r, j])))
        for lab, name in CBUSE_LOWER:
            i, j = find_label(d, "^" + re.escape(lab))
            rows = annual_rows(d, i, j)
            assert len(rows) == 5, (fname, name, rows)
            for y, r in rows:
                rec.append((fname, y, name, "consumption", float(d.iat[r, j])))
    return pd.DataFrame(rec, columns=["source", "year", "series", "measure", "value"])


# 新様式（2021年以降の実数表）
PAPER_GROUPS = {
    "newsprint": ["新聞巻取紙"],
    "printing_info": ["上級印刷紙", "中級印刷紙", "下級印刷紙", "薄葉印刷紙", "微塗工印刷用紙", "アート紙", "コート紙", "軽量コート紙",
                      "その他塗工印刷紙", "色上質紙", "その他特殊印刷用紙", "複写原紙", "フォーム用紙", "ＰＰＣ用紙", "情報記録紙", "その他情報用紙"],
    "wrapping": ["重袋用両更クラフト紙", "その他両更クラフト紙", "その他未ざらし包装紙", "純白ロール紙", "さらしクラフト紙", "その他さらし包装紙"],
    "sanitary": ["ティシュペーパー", "トイレットペーパー", "タオル用紙", "その他衛生用紙"],
    "misc_paper": ["加工原紙", "電気絶縁紙", "その他工業用雑種紙", "家庭用雑種紙"],
}
BOARD_GROUPS = {
    "containerboard": ["外装用クラフト", "外装用ジュート", "内装用ライナー", "中芯原紙"],
    "boxboard": ["マニラボール", "白ボール", "黄・チップ・色板紙"],
    "misc_board": ["建材原紙", "紙管原紙", "その他板紙"],
}
USE_ITEMS = {"電気器具・機械器具用": "use_machinery", "薬品・洗剤・化粧品用": "use_medicine", "加工食品用（飲料を含む）": "use_processed_food",
             "青果物": "use_produce", "繊維製品用": "use_textile", "陶磁器・ガラス製品・雑貨用": "use_ceramics",
             "通販・宅配・引越用": "use_mailorder", "包装用以外": "use_nonpack", "合計": "use_total"}


def parse_new():
    rec = []
    for y in range(2021, 2026):
        fname = f"nenpo{y}.xlsx"
        d = pd.read_excel(RAW / fname, "実数表", header=None, dtype=object)
        hdr = [str(x) for x in d.iloc[1].tolist()]
        if f"{y}年(CY)" in hdr:  # 2021〜2023年版は暦年の列がある
            mcols = [hdr.index(f"{y}年(CY)")]
        else:  # 2024・2025年版は月次だけなので12か月を足す
            mcols = [k for k, h in enumerate(hdr) if re.fullmatch(rf"{y}(0[1-9]|1[0-2])", h)]
            assert len(mcols) == 12, (fname, mcols)
        body = d.iloc[2:].copy()
        body["q"] = body[0].astype(str).str.strip()
        body["hin"] = body[5].astype(str).str.strip()
        body["item"] = body[6].astype(str).str.strip()

        def ysum(q, hin, item):
            z = body[(body["q"] == q) & (body["hin"] == hin) & (body["item"] == item)]
            assert len(z) == 1, (fname, q, hin, item, len(z))
            vals = pd.to_numeric(z.iloc[0, mcols], errors="coerce")
            assert vals.notna().all(), (fname, hin, item, "秘匿か欠け")
            return float(vals.sum())

        for groups, q in [(PAPER_GROUPS, "4240"), (BOARD_GROUPS, "4260")]:
            for g, names in groups.items():
                rec.append((fname, y, g, "production", sum(ysum(q, n, "生産") for n in names)))
                rec.append((fname, y, g, "sales_qty", sum(ysum(q, n, "販売数量") for n in names)))
        rec.append((fname, y, "cb_sheet", "production", ysum("4290", "段ボールシート計", "生産")))
        for item, name in USE_ITEMS.items():
            rec.append((fname, y, name, "consumption", ysum("4290", "消費（次工程投入）部門別内訳", item)))
    df = pd.DataFrame(rec, columns=["source", "year", "series", "measure", "value"])
    tot = []
    for meas in ["production", "sales_qty"]:
        for y in range(2021, 2026):
            a = df[(df["year"] == y) & (df["measure"] == meas)]
            tot.append((f"nenpo{y}.xlsx", y, "paper_total", meas, a[a["series"].isin(PAPER_GROUPS)]["value"].sum()))
            tot.append((f"nenpo{y}.xlsx", y, "board_total", meas, a[a["series"].isin(BOARD_GROUPS)]["value"].sum()))
    return pd.concat([df, pd.DataFrame(tot, columns=df.columns)], ignore_index=True)


def main():
    old, new = parse_old(), parse_new()
    allrec = pd.concat([old, new], ignore_index=True).sort_values(["series", "measure", "year", "source"]).reset_index(drop=True)
    allrec.to_csv(OUT / "series_by_source.csv", index=False, float_format="%.1f")
    # 年ごとに1つの値：新しい版を優先（2020年版 > 2017年版 > 2012年版）
    pri = {"nenpo2012_paper.xls": 1, "nenpo2017_paper.xls": 2, "nenpo2020_paper.xls": 3}
    allrec["pri"] = allrec["source"].map(pri).fillna(9)
    best = allrec.sort_values("pri").groupby(["series", "measure", "year"], sort=True).tail(1)
    wide = best.pivot_table(index="year", columns=["measure", "series"], values="value")
    wide.columns = [f"{m}__{s}" for m, s in wide.columns]
    wide = wide.sort_index()
    wide.to_csv(OUT / "annual.csv", float_format="%.1f")
    print(wide.index.min(), wide.index.max(), wide.shape)


if __name__ == "__main__":
    main()
