"""370：雇われて働く人が8割を超えたのは、いつだったのか。
労働力調査 長期時系列表4（従業上の地位別就業者数、1953年〜）。1948〜52年は「日本の長期統計系列」19-7（参考）。
割合は、就業者の総数（従業上の地位不詳を含む）に対する割合。
"""
import json
import numpy as np, pandas as pd, openpyxl, xlrd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省統計局「労働力調査」長期時系列表4（従業上の地位別就業者数）をもとに作成者が加工して作成"
ws = openpyxl.load_workbook(DATA / "raw" / "roudou_lt04_000001082690.xlsx", data_only=True).worksheets[0]
rec = []; seen = set()
for r in ws.iter_rows(values_only=True):
    y = r[1]
    try: y = int(str(y).strip())
    except Exception: continue
    if not (1900 < y < 2100) or not isinstance(r[2], (int, float)): continue
    okinawa = y in seen           # 1973年は2行ある（沖縄県を含まない／含む）
    seen.add(y)
    f = lambda v: float(v) if isinstance(v, (int, float)) else np.nan
    for sex, c in (("男女計", 2), ("男", 10), ("女", 18)):
        rec.append({"year": y, "row": 2 if okinawa else 1, "sex": sex, "total": f(r[c]), "self": f(r[c + 1]), "self_with_emp": f(r[c + 2]), "family": f(r[c + 3]), "employee": f(r[c + 4])})
A = pd.DataFrame(rec)
# 1973年は沖縄県を含む行を使う（1972年までは沖縄県を含まない）
T = A[~((A.year == 1973) & (A.row == 1))].drop(columns="row").copy()
for k in ("self", "family", "employee"): T["s_" + k] = T[k] / T.total * 100
T.to_csv(DATA / "status_1953_latest.csv", index=False)
B = T[T.sex == "男女計"].set_index("year"); M = T[T.sex == "男"].set_index("year"); W = T[T.sex == "女"].set_index("year")
# 参考：1948〜52年（14歳以上）
s = xlrd.open_workbook(DATA / "raw" / "chouki_19-07.xls").sheet_by_index(0); pre = {}
for r in range(s.nrows):
    y = s.cell_value(r, 1)
    if isinstance(y, float) and 1948 <= y <= 1952 and int(y) not in pre:
        pre[int(y)] = {"total": float(s.cell_value(r, 2)), "self": float(s.cell_value(r, 3)), "family": float(s.cell_value(r, 6)), "employee": float(s.cell_value(r, 7))}
PRE = pd.DataFrame(pre).T; 
for k in ("self", "family", "employee"): PRE["s_" + k] = PRE[k] / PRE.total * 100
def first_over(S, col, v):
    x = S[S[col] > v]; return int(x.index.min()) if len(x) else None
def first_below_n(S, col, v):
    x = S[S[col] <= v]; return int(x.index.min()) if len(x) else None
Y0, Y1 = int(B.index.min()), int(B.index.max())
b0, b1 = B.loc[Y0], B.loc[Y1]
res = {"years": [Y0, Y1], "okinawa_1973": {"excl": A[(A.year == 1973) & (A.row == 1) & (A.sex == "男女計")][["total", "employee"]].iloc[0].to_dict(), "incl": A[(A.year == 1973) & (A.row == 2) & (A.sex == "男女計")][["total", "employee"]].iloc[0].to_dict()},
       "pre_1948_1952": {int(y): {k: round(float(v), 1) for k, v in r.items()} for y, r in PRE.iterrows()},
       "share": {int(y): {"employee": round(float(B.loc[y].s_employee), 1), "self": round(float(B.loc[y].s_self), 1), "family": round(float(B.loc[y].s_family), 1)} for y in [1953, 1955, 1958, 1959, 1960, 1964, 1965, 1970, 1975, 1976, 1980, 1990, 1992, 1993, 2000, 2010, 2018, 2019, 2020, Y1] if y in B.index},
       "employee_over": {str(v): first_over(B, "s_employee", v) for v in (50, 60, 70, 80, 85, 90)},
       "employee_over_men": {str(v): first_over(M, "s_employee", v) for v in (50, 60, 70, 80, 85, 90)}, "employee_over_women": {str(v): first_over(W, "s_employee", v) for v in (50, 60, 70, 80, 85, 90)},
       "men": {int(y): round(float(M.loc[y].s_employee), 1) for y in [1953, 1970, 1990, 2000, Y1]}, "women": {int(y): round(float(W.loc[y].s_employee), 1) for y in [1953, 1970, 1990, 2000, Y1]},
       "women_family_share": {int(y): round(float(W.loc[y].s_family), 1) for y in [1953, 1960, 1970, 1980, 1990, 2000, Y1]},
       "women_over_men_employee_share": first_over(pd.DataFrame({"d": W.s_employee - M.s_employee}), "d", 0),
       "family_n": {int(y): float(B.loc[y].family) for y in [1953, 1960, 1970, 1975, 1980, 1990, 2000, 2010, Y1]}, "family_peak": {"year": int(B.family.idxmax()), "n": float(B.family.max())},
       "family_half_of_1953": first_below_n(B, "family", b0.family / 2), "family_quarter_of_1953": first_below_n(B, "family", b0.family / 4), "family_tenth_of_1953": first_below_n(B, "family", b0.family / 10),
       "self_n": {int(y): float(B.loc[y].self) for y in [1953, 1957, 1970, 1980, 1990, 2000, 2010, Y1]}, "self_peak": {"year": int(B.self.idxmax()), "n": float(B.self.max())},
       "self_below_900": first_below_n(B.loc[1980:], "self", 900), "self_half_of_peak": first_below_n(B.loc[1960:], "self", B.self.max() / 2),
       "employee_n": {int(y): float(B.loc[y].employee) for y in [1953, 1960, 1970, 1980, 1990, 2000, 2010, Y1]}, "employee_x": round(float(b1.employee / b0.employee), 2), "total_x": round(float(b1.total / b0.total), 2),
       "change_pt": {"employee": round(float(b1.s_employee - b0.s_employee), 1), "family": round(float(b1.s_family - b0.s_family), 1), "self": round(float(b1.s_self - b0.s_self), 1)},
       "per_decade_employee_pt": {f"{a}-{b}": round(float(B.loc[b].s_employee - B.loc[a].s_employee), 1) for a, b in [(1953, 1963), (1963, 1973), (1973, 1983), (1983, 1993), (1993, 2003), (2003, 2013), (2013, Y1)]},
       "self_with_emp_share_of_self": {int(y): round(float(B.loc[y].self_with_emp / B.loc[y].self * 100), 1) for y in [1953, 1990, Y1]},
       "counterfactual_1953_structure": {"employees_if_1953_share_man": round(float(b1.total * b0.s_employee / 100), 0), "actual_man": float(b1.employee)}}
json.dump(res, open(RES / "a370_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：3つの地位の割合
fig, ax = plt.subplots(figsize=(9.2, 4.5))
for k, c, lab in [("s_employee", BLUE, "雇用者"), ("s_self", ORANGE, "自営業主"), ("s_family", GRAY, "家族従業者")]:
    ax.plot(B.index, B[k], color=c, lw=2.2)
    ax.annotate(f"{lab} {B[k].iloc[-1]:.0f}%", (Y1, B[k].iloc[-1]), xytext=(5, 0), textcoords="offset points", fontsize=9, va="center")
for v in (50, 80):
    y = res["employee_over"][str(v)]; ax.axhline(v, color=GRAY, lw=0.6, ls=":")
    ax.annotate(f"{y}年に{v}%を超える", (y, B.s_employee.loc[y]), xytext=(y + 3, v - 9), fontsize=8.5, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.7))
ax.set_xlim(1951, 2036); ax.set_ylim(0, 100); ax.set_ylabel("就業者に占める割合（%）")
ax.set_title(f"雇われて働く人は1953年の42%から、{res['employee_over']['50']}年に5割、{res['employee_over']['80']}年に8割を超えた")
save(fig, "a370_shares.png", SRC + "\n1972年までは沖縄県を含まない")

# 図2：男女別の雇用者の割合と、女性の家族従業者の割合
fig, ax = plt.subplots(figsize=(9.2, 4.5))
ax.plot(M.index, M.s_employee, color=BLUE, lw=2.2, label="男　雇用者の割合")
ax.plot(W.index, W.s_employee, color=ORANGE, lw=2.2, label="女　雇用者の割合")
ax.plot(W.index, W.s_family, color=GRAY, lw=1.8, ls="--", label="女　家族従業者の割合")
ax.annotate(f"{M.s_employee.iloc[-1]:.0f}%", (Y1, M.s_employee.iloc[-1]), xytext=(5, -6), textcoords="offset points", fontsize=9)
ax.annotate(f"{W.s_employee.iloc[-1]:.0f}%", (Y1, W.s_employee.iloc[-1]), xytext=(5, 2), textcoords="offset points", fontsize=9)
ax.annotate(f"{W.s_family.iloc[-1]:.0f}%", (Y1, W.s_family.iloc[-1]), xytext=(5, 0), textcoords="offset points", fontsize=9)
ax.annotate(f"1953年 {W.s_family.iloc[0]:.0f}%", (1953, W.s_family.iloc[0]), xytext=(4, 6), textcoords="offset points", fontsize=9)
ax.set_xlim(1951, 2030); ax.set_ylim(0, 100); ax.set_ylabel("就業者に占める割合（%）")
ax.set_title(f"1953年、働く女性の{W.s_family.iloc[0]:.0f}%は家族従業者だった。女性の雇用者の割合は{res['women_over_men_employee_share']}年に男性を上回った")
ax.legend(frameon=False, fontsize=9, loc="center right")
save(fig, "a370_by_sex.png", SRC)

# 図3：人数
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axes[0]
ax.plot(B.index, B.self, color=ORANGE, lw=2.2, label="自営業主"); ax.plot(B.index, B.family, color=GRAY, lw=2.2, label="家族従業者")
ax.set_ylim(0, 1400); ax.set_ylabel("万人"); ax.set_title("自営業主と家族従業者の人数", fontsize=11); ax.legend(frameon=False, fontsize=9)
ax = axes[1]
ax.plot(B.index, B.employee, color=BLUE, lw=2.2, label="雇用者"); ax.plot(B.index, B.total, color=INK, lw=1.4, ls="--", label="就業者の総数")
ax.set_ylim(0, 7500); ax.set_ylabel("万人"); ax.set_title("雇用者と就業者の人数", fontsize=11); ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.suptitle(f"家族従業者は{res['family_half_of_1953']}年に1953年の半分に。自営業主は1980年代まで900万人台で、そこから減った", fontsize=12.5, y=1.0); fig.tight_layout()
save(fig, "a370_numbers.png", SRC)
print(json.dumps(res, ensure_ascii=False)[:5000])
