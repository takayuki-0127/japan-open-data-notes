"""492 Excel の日付のシリアル値を読み替えるとき、何日ずれるのか（実務の型）

架空の日付の列を、Excel の決まり（1900年基準：1900/1/1 = 1、1900/2/29 が存在する扱い／1904年基準：1904/1/1 = 0）で
シリアル値にし、よく見る5通りの読み替え方で日付に戻して、ずれた行の数と日数を数える。
Excel 本体では試していない（決まりを Python で再現。openpyxl の変換と突き合わせた）。
"""
import json, datetime as dt
import numpy as np, pandas as pd
from openpyxl.utils.datetime import from_excel, to_excel, CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 492
D1900 = dt.datetime(1899, 12, 30)        # s >= 61 で正しい原点
D1904 = dt.datetime(1904, 1, 1)


def excel_1900_serial(d: dt.datetime) -> float:
    """Excel（1900年基準）のシリアル値。1900/3/1 より前は、存在しない 1900/2/29 の分だけ1小さい"""
    s = (d - D1900).total_seconds() / 86400
    return s - 1 if d < dt.datetime(1900, 3, 1) else s


def make_data(rng):
    n_main = 9_800
    days = rng.integers(0, (dt.date(2026, 12, 31) - dt.date(2015, 1, 1)).days + 1, n_main)
    base = [dt.datetime(2015, 1, 1) + dt.timedelta(days=int(x)) for x in days]
    # 「日付が分からない」の代わりに入れられた 1900/1/1 や、1900年1〜2月の値（200行）
    early = [dt.datetime(1900, 1, 1)] * 120 + [dt.datetime(1900, 1, 1) + dt.timedelta(days=int(x)) for x in rng.integers(0, 59, 80)]
    dates = base + early
    rng.shuffle(dates)
    df = pd.DataFrame({"true_date": dates})
    df["serial_1900"] = [excel_1900_serial(d) for d in df["true_date"]]
    df["serial_1904"] = [(d - D1904).days for d in df["true_date"]]
    return df


def methods_1900(s: pd.Series) -> dict:
    """1900年基準のシリアル値 s を日付に戻す5通り"""
    out = {}
    out["①1899/12/30 起点（pandas の origin='1899-12-30' など）"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(s, unit="D")
    out["②1899/12/31 起点（1 = 1900/1/1 をそのまま足す）"] = pd.to_datetime("1899-12-31") + pd.to_timedelta(s, unit="D")
    out["③1900/1/1 起点（s 日後と読む）"] = pd.to_datetime("1900-01-01") + pd.to_timedelta(s, unit="D")
    out["④UNIX 時刻に直す（(s−25569)×86400 秒）"] = pd.to_datetime((s - 25569) * 86400, unit="s")
    out["⑤openpyxl の from_excel（2/29 の扱いを含む）"] = pd.Series([pd.Timestamp(from_excel(x)) for x in s], index=s.index)
    return out


def main():
    rng = np.random.default_rng(SEED)
    df = make_data(rng)
    df.to_csv(DATA / "fictional_dates.csv", index=False)
    truth = pd.to_datetime(df["true_date"])
    is_early = truth < pd.Timestamp("1900-03-01")

    # openpyxl の to_excel と、自前のシリアル値が一致することを確かめる
    assert all(abs(to_excel(d) - s) < 1e-9 for d, s in zip(df["true_date"].iloc[:2000], df["serial_1900"].iloc[:2000]))
    assert all(abs(to_excel(d, epoch=CALENDAR_MAC_1904) - s) < 1e-9 for d, s in zip(df["true_date"].iloc[:2000], df["serial_1904"].iloc[:2000]))

    rows = []
    for name, got in methods_1900(df["serial_1900"]).items():
        diff = (got.dt.normalize() - truth).dt.days
        rows.append({"method": name, "wrong_rows": int((diff != 0).sum()), "wrong_share": float((diff != 0).mean()),
                     "wrong_main": int(((diff != 0) & ~is_early).sum()), "wrong_early": int(((diff != 0) & is_early).sum()),
                     "shift_main": sorted(set(diff[~is_early].tolist())), "shift_early": sorted(set(diff[is_early].tolist()))})
    m = pd.DataFrame(rows)
    m.to_csv(RES / "methods_1900.csv", index=False)

    # 1900/2/29（シリアル値 60）が入っていたら
    s60 = {"openpyxl": str(from_excel(60)), "origin_1899_12_30": str(pd.Timestamp("1899-12-30") + pd.Timedelta(days=60)),
           "origin_1899_12_31": str(pd.Timestamp("1899-12-31") + pd.Timedelta(days=60))}

    # 1904年基準のファイルを 1900年基準として読む（とその逆）
    got_as1900 = pd.to_datetime("1899-12-30") + pd.to_timedelta(df["serial_1904"], unit="D")
    d1 = (got_as1900 - truth).dt.days
    got_as1904 = pd.to_datetime("1904-01-01") + pd.to_timedelta(df["serial_1900"], unit="D")
    d2 = (got_as1904 - truth).dt.days
    mix = {"read_1904_as_1900_shift_days": sorted(set(d1[~is_early].tolist())), "read_1900_as_1904_shift_days": sorted(set(d2[~is_early].tolist())),
           "share_wrong_1904_as_1900": float((d1 != 0).mean())}
    # 2つの基準のファイルを1つに結合したとき（2割が1904年基準のファイルから来たとする）
    from_mac = rng.random(len(df)) < 0.2
    combined_serial = np.where(from_mac, df["serial_1904"], df["serial_1900"])
    combined = pd.Series(pd.to_datetime("1899-12-30") + pd.to_timedelta(combined_serial, unit="D"), index=df.index)
    dc = (combined - truth).dt.days
    mix["combined_rows_from_1904"] = int(from_mac.sum())
    mix["combined_main_rows_from_1904"] = int((from_mac & ~is_early.values).sum())
    mix["combined_wrong_rows"] = int((dc != 0).sum())
    mix["combined_wrong_main_rows"] = int(((dc != 0) & ~is_early).sum())
    # 年ごとの件数がどう見えるか（2015〜2026年の行だけ）
    yr_true = truth[~is_early].dt.year.value_counts().sort_index()
    yr_comb = combined[~is_early].dt.year.value_counts().sort_index()
    yr = pd.DataFrame({"true": yr_true, "combined": yr_comb}).fillna(0).astype(int)
    yr.to_csv(RES / "year_counts_combined.csv")

    # 時刻つきのシリアル値：日付だけ取り出すとき、四捨五入でずれる行
    n = 20_000
    t_days = rng.integers(0, 3650, n)
    secs = rng.integers(0, 86400, n)
    secs[: n // 10] = rng.integers(86400 - 60, 86400, n // 10)      # 1割は 23:59 台（締めの直前に入る記録）
    true_dt = [dt.datetime(2016, 1, 1) + dt.timedelta(days=int(a), seconds=int(b)) for a, b in zip(t_days, secs)]
    ser = np.array([excel_1900_serial(x) for x in true_dt])
    ser_csv = np.round(ser, 5)                                        # CSV に5桁で書き出されたとする
    true_date = pd.Series([x.date() for x in true_dt])
    trunc = pd.Series([(D1900 + dt.timedelta(days=float(np.floor(x)))).date() for x in ser_csv])
    rnd_day = pd.Series([(D1900 + dt.timedelta(days=float(np.round(x)))).date() for x in ser_csv])
    via_min = pd.Series([(D1900 + dt.timedelta(minutes=float(np.round(x * 1440)))).date() for x in ser_csv])
    tm = {"rows": n, "rows_2359": int(n // 10),
          "floor_wrong": int((trunc != true_date).sum()), "round_day_wrong": int((rnd_day != true_date).sum()),
          "round_minute_wrong": int((via_min != true_date).sum()),
          "round_day_wrong_share": float((rnd_day != true_date).mean())}
    # 四捨五入で日付が変わる時刻（12:00 以降）の行の割合
    tm["share_after_noon"] = float((secs >= 43200).mean())

    res = {"rows": len(df), "rows_before_1900_03_01": int(is_early.sum()), "rows_1900_01_01": 120,
           "methods_1900": rows, "serial_60": s60, "mix_1904": mix, "time_fraction": tm}
    json.dump(res, open(RES / "a492_main.json", "w"), ensure_ascii=False, indent=1, default=str)

    # 図1：読み替え方ごとの、ずれた行
    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    y = np.arange(len(m))[::-1]
    ax.barh(y, m["wrong_main"], color=ORANGE, label="2015〜2026年の行（9,800行）")
    ax.barh(y, m["wrong_early"], left=m["wrong_main"], color=BLUE, label="1900年1〜2月の行（200行）")
    for yy, a, b, sm, se in zip(y, m["wrong_main"], m["wrong_early"], m["shift_main"], m["shift_early"]):
        tx = f"{a+b:,}行" + (f"（{sm[-1]:+d}日" if a else "（") + ("" if not a else "、") + (f"1900年の行は{se[-1]:+d}日）" if b else "1900年の行は0日）")
        ax.text(a + b + 120, yy, tx, va="center", fontsize=9, color=INK)
    ax.set_yticks(y, [s.split("（")[0] + "\n（" + s.split("（", 1)[1] for s in m["method"]], fontsize=8.5)
    ax.set_xlim(0, 15_500); ax.set_xlabel("日付がずれた行の数（1万行のうち）")
    ax.legend(fontsize=9, frameon=False, loc="lower right")
    ax.set_title("1900年基準のシリアル値を、5通りの読み替え方で日付に戻すと")
    save(fig, "a492_methods.png", "架空の日付1万行（seed 492）で作成。Excel 本体では未検証（決まりを Python で再現）")

    # 図2：1904年基準が混ざった結合
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.0), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axs[0]
    vals = [mix["combined_main_rows_from_1904"], mix["combined_wrong_main_rows"]]
    ax.bar([0, 1], vals, color=[GRAY, ORANGE])
    for i, v in enumerate(vals): ax.text(i, v + 40, f"{v:,}行", ha="center", fontsize=10)
    ax.set_xticks([0, 1], ["1904年基準の\nファイルの行", "日付が\nずれた行"])
    ax.set_title("2割が1904年基準（2015〜2026年の行）", fontsize=10.5); ax.set_ylim(0, max(vals) * 1.25)
    ax = axs[1]
    yy = yr.index.values
    ax.bar(yy - 0.2, yr["true"], width=0.4, color=BLUE, label="本当の年")
    ax.bar(yy + 0.2, yr["combined"], width=0.4, color=ORANGE, label="結合して1900年基準で読んだ年")
    ax.set_xticks(yy[::2]); ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.set_ylim(0, yr.values.max() * 1.3)
    ax.set_title("年ごとの件数（2015〜2026年の行）", fontsize=11); ax.set_ylabel("行の数")
    fig.suptitle(f"1904年基準の値を1900年基準で読むと、日付は{mix['read_1904_as_1900_shift_days'][0]:+,}日（4年と1日前）にずれる", fontsize=12, y=1.04)
    save(fig, "a492_mix1904.png", "架空の日付1万行（seed 492）で作成。2割の行を1904年基準のシリアル値に置き換えて結合")

    # 図3：時刻つきの値から日付を取り出す
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    labs = ["切り捨て\n（INT・floor）", "分に丸めてから\n日付を取る", "四捨五入\n（ROUND）"]
    vv = [tm["floor_wrong"], tm["round_minute_wrong"], tm["round_day_wrong"]]
    ax.bar(range(3), vv, color=[BLUE, GREEN, ORANGE])
    for i, v in enumerate(vv): ax.text(i, v + 150, f"{v:,}行（{v/n*100:.1f}%）", ha="center", fontsize=10)
    ax.set_xticks(range(3), labs); ax.set_ylim(0, max(vv) * 1.25 + 500)
    ax.set_ylabel(f"日付がずれた行（{n:,}行のうち）")
    ax.set_title("時刻つきのシリアル値から、日付だけを取り出すと")
    save(fig, "a492_time_fraction.png", "架空の日時2万行（seed 492、1割は23:59台）。シリアル値は小数5桁で保存されたとする")
    print(json.dumps({k: v for k, v in res.items() if k != "methods_1900"}, ensure_ascii=False, default=str, indent=0)[:2500])
    print(m[["method", "wrong_rows", "wrong_main", "wrong_early", "shift_main", "shift_early"]].to_string())


if __name__ == "__main__":
    main()
