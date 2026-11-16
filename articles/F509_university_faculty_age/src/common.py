"""共通の関数。職名を年度をまたいで比べられる形にまとめる。"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
HARM = {"教授": "教授", "准教授": "准教授", "講師": "講師", "助教": "助教・助手", "助手": "助教・助手", "学長・副学長": "学長・副学長"}
POS_ORDER = ["学長・副学長", "教授", "准教授", "講師", "助教・助手"]


def load():
    d = pd.read_csv(ROOT / "data" / "faculty_age.csv")
    return d


def harmonized(d, setter="計"):
    x = d[(d.setter == setter) & (d.position != "計")].copy()
    x["pos"] = x.position.map(HARM)
    return x.groupby(["year", "pos", "age"], as_index=False)["n"].sum()


def age_value(age, top=71, bottom=24):
    """24＝25歳未満、70＝70歳以上を、仮の年齢に置きかえる。"""
    return age.where(age != 70, top).where(age != 24, bottom)


def mean_age(g, top=71, bottom=24):
    a = age_value(g["age"], top, bottom)
    return float((a * g["n"]).sum() / g["n"].sum())


def share(g, lo=None, hi=None):
    m = pd.Series(True, index=g.index)
    if lo is not None:
        m &= g["age"] >= lo
    if hi is not None:
        m &= g["age"] < hi
    return float(g.loc[m, "n"].sum() / g["n"].sum())
