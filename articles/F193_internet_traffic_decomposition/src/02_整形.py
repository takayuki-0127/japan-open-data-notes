"""xlsx の3つの表を CSV に整形する。
semiannual.csv : 半年ごと（5月・11月、2004年は9〜11月）の全国推計（協力ISP5社・9社）、IX、契約数
ix_monthly.csv : 国内主要IXの1日平均トラヒックの月平均（Gbps）と1日ピークの月平均
diurnal.csv    : 協力ISP9社のブロードバンド契約者（A1）の一週間の2時間ごとの平均（Gbps）、2020年11月〜2026年5月"""
import re, openpyxl, pandas as pd
from common import XLSX, DATA
wb = openpyxl.load_workbook(XLSX, data_only=True)
num = lambda v: float(v) if isinstance(v, (int, float)) else (float(v) if isinstance(v, str) and re.fullmatch(r"-?[\d.]+", v.strip()) else None)

# 1) 半年ごと
rows = list(wb.worksheets[0].iter_rows(values_only=True)); out = []; y = None
for r in rows[6:]:
    if r[1] is None or not str(r[1]).endswith("月"): break
    if r[0]: y = int(str(r[0]).rstrip("年"))
    m = int(str(r[1]).rstrip("月"))
    out.append(dict(date=f"{y}-{m:02d}", isp9_up=num(r[2]), isp9_down=num(r[3]), isp9_up_per=num(r[4]), isp9_down_per=num(r[5]),
                    isp9_a1_up=num(r[6]), isp9_a1_down=num(r[7]),
                    isp5_up=num(r[16]), isp5_down=num(r[17]), isp5_up_per=num(r[18]), isp5_down_per=num(r[19]),
                    isp5_a1_up=num(r[20]), isp5_a1_down=num(r[21]),
                    ix_avg=num(r[30]), ix_peak=num(r[31]), share9=num(r[32]), share5=num(r[33]), contracts_k=num(r[34])))
semi = pd.DataFrame(out); semi.to_csv(DATA / "semiannual.csv", index=False); print("semi", semi.shape, semi.date.iloc[0], semi.date.iloc[-1])

# 2) IX 月次
rows = list(wb.worksheets[3].iter_rows(values_only=True)); out = []; y = None
for r in rows[5:]:
    if r[1] is None or not str(r[1]).endswith("月"):
        if out: break
        continue
    if r[0]: y = int(str(r[0]).rstrip("年"))
    m = int(str(r[1]).rstrip("月"))
    out.append(dict(date=f"{y}-{m:02d}", ix_avg=num(r[2]), ix_peak=num(r[3])))
ix = pd.DataFrame(out); ix.to_csv(DATA / "ix_monthly.csv", index=False); print("ix", ix.shape, ix.date.iloc[0], ix.date.iloc[-1], ix.ix_avg.notna().sum())

# 3) 一週間の時間帯別
rows = list(wb.worksheets[1].iter_rows(values_only=True))
yr = rows[4]; mo = rows[5]; labels = []; cy = None
for j in range(3, len(mo)):
    if yr[j]: cy = int(str(yr[j]).rstrip("年"))
    labels.append(f"{cy}-{int(str(mo[j]).rstrip('月')):02d}")
half = len(labels) // 2; out = []
for k, r in enumerate(rows[6:90]):
    if r[0] is None: break
    st = str(r[1])[:5]
    for j in range(half):
        out.append(dict(slot=k, day=str(r[0]), start=st, period=labels[j], up=float(r[3 + j]), down=float(r[3 + half + j])))
di = pd.DataFrame(out); di.to_csv(DATA / "diurnal.csv", index=False); print("diurnal", di.shape, sorted(di.period.unique()))
