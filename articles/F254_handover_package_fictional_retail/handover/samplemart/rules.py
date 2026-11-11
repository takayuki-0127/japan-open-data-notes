"""決めごとを1か所に書いたもの（会社設定書 docs/company_spec.md の文の、そのままの読み方）。

いまは各回のコードがそれぞれ自分で書いている（docs/decisions.md の表）。ここに置いた関数は、
それらが同じ答えを出しているかを確かめる「ものさし」として使う（tests/test_rules.py）。
各回のコードをこの関数に置き換えるのは、テストで差がないことを確かめた後の、次の段階でやる。
"""
import pandas as pd

EXISTING_MONTHS = 13  # 既存店：開店から何か月以上


def is_existing(open_date, close_date, ym, months=EXISTING_MONTHS):
    """既存店か：「その月の月初で開店から13か月以上、かつその月の末日まで営業している店」

    「開店から13か月以上」は、開店日の13か月後の日付が、その月の月初より前か同じ日、と読む。
    （開店日が月の途中のとき、暦の月の差で数えるやり方とは1か月ずれる。docs/decisions.md の D1）
    """
    p = pd.Period(ym, "M")
    start, end = p.start_time.normalize(), p.end_time.normalize()
    ok_open = pd.Timestamp(open_date) + pd.DateOffset(months=months) <= start
    ok_close = pd.isna(close_date) or pd.Timestamp(close_date) >= end
    return bool(ok_open and ok_close)


def fiscal_year(ym):
    """会計年度（4月はじまり）。2025-04〜2026-03 が FY2025"""
    y, m = int(ym[:4]), int(ym[5:7])
    return y if m >= 4 else y - 1
