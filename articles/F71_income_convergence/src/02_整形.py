"""県民経済計算の各基準年の表をつなぎ、1人当たり県民所得の都道府県×年度パネルを作る。
相対所得 r = ln(県の1人当たり所得) − その年度の県の対数平均 を基準年ごとに計算し、\n最新の基準年の水準に合わせて古い基準年の系列をつなぐ（つなぎ目の段差を消す）。"""
import json, numpy as np, pandas as pd, pathlib
H = pathlib.Path(__file__).resolve().parents[1]
d = json.load(open(H/'data/raw/kenmin_raw.json', encoding='utf-8'))
NAMES = {}
def parse(rows):
    hdr = None; out = {}
    for r in rows:
        if hdr is None and any(isinstance(x, int) and 1950 < x < 2030 for x in r[3:]):
            hdr = r; continue
        if hdr and isinstance(r[0], str) and len(r[0]) == 2 and r[0].isdigit():
            NAMES[int(r[0])] = r[1]
            for j, y in enumerate(hdr):
                if isinstance(y, int) and 1950 < y < 2030:
                    v = r[j]
                    if isinstance(v, (int, float)): out[(int(r[0]), y)] = float(v)
    return out
order = ['v2023', 'v2018', 'h26', 'h21', 'h15', 's50', 's30']   # 新しい順
popk = {'v2023': 'pop2023', 'v2018': 'pop2018', 'h26': 'poph26', 'h21': 'poph21', 'h15': 'poph15', 's50': 'pops50', 's30': None}
m22 = pd.read_csv(H/'data/raw/v2022_missing5.csv', dtype={'code': int}).set_index('code')
recs = []
for k in order:
    inc = parse(d[k]); pop = parse(d[popk[k]]) if popk[k] else {}
    if k == 'v2023':   # 令和5年度版で未公表の5県は、令和4年度版の値で補う（2011〜2022年度）
        for c in m22.index:
            for y in m22.columns: inc[(c, int(y))] = float(m22.loc[c, y])
    df = pd.DataFrame([(c, y, v, pop.get((c, y), np.nan)) for (c, y), v in inc.items()], columns=['code', 'year', 'y', 'pop'])
    df['vintage'] = k
    recs.append(df)
raw = pd.concat(recs)
raw.to_csv(H/'data/kenmin_long_all_vintages.csv', index=False)
# 相対所得：その年の県の対数平均（単純平均）との差。人口の重みは頑健性で使う
raw['ly'] = np.log(raw['y'])
raw['r'] = raw['ly'] - raw.groupby(['vintage', 'year'])['ly'].transform('mean')
raw = raw[~((raw.vintage == 'v2023') & (raw.year == 2023))]   # 2023年度は5県が未公表なので除く
rank = {k: i for i, k in enumerate(order)}
raw['rk'] = raw['vintage'].map(rank)
# (a) 単純につなぐ：重なる年は新しい基準年の値を使うだけ（基準改定による水準の段差がそのまま残る）
naive = raw.sort_values('rk').drop_duplicates(['code', 'year']).sort_values(['code', 'year'])
# (b) 段差を消してつなぐ（基本）：最新の基準年の水準に合わせ、古い基準年は「年ごとの変化」だけを使う。
#     つなぎ目の年（新しい基準年の最初の年度）で、県ごとに 新−旧 の差を古い系列に足す。
wide = {k: raw[raw.vintage == k].pivot(index='code', columns='year', values='r') for k in order}
ch = wide['v2023'].copy(); link = []
prev = 'v2023'
for k in order[1:]:
    old = wide[k]; y0 = min(ch.columns)
    if y0 in old.columns:
        off = (ch[y0] - old[y0])
    else:  # 重なる年がない（昭和30年基準→昭和50年基準）：昭和50年基準の表に足したのと同じ差を足す
        off = ch[y0] - wide[prev][y0]
    link.append((k, y0, float(off.abs().mean()), float(off.get(13, np.nan))))
    add = old[[c for c in old.columns if c < y0]].add(off, axis=0)
    ch = pd.concat([add, ch], axis=1); prev = k
ch = ch.sub(ch.mean(axis=0), axis=1)   # 年ごとに平均0へそろえ直す
pd.DataFrame(link, columns=['古い基準年の表', 'つなぎ目の年度', '古い表に足した差の平均（絶対値、累積）', '東京に足した差（累積）']).to_csv(H/'results/splice_offsets.csv', index=False)
pan = ch.stack().rename('r').reset_index().rename(columns={'level_1': 'year'})
pan = pan.merge(naive[['code', 'year', 'y', 'pop', 'vintage']], on=['code', 'year'], how='left')
pan = pan.merge(naive[['code', 'year', 'r']].rename(columns={'r': 'r_naive'}), on=['code', 'year'], how='left')
pan['r_naive'] = pan['r_naive'] - pan.groupby('year')['r_naive'].transform('mean')
pan['name'] = pan['code'].map(NAMES)
pan[['code', 'name', 'year', 'y', 'pop', 'r', 'r_naive', 'vintage']].to_csv(H/'data/panel_rel_income.csv', index=False)
print(pd.read_csv(H/'results/splice_offsets.csv'))
# 重なる年での相対所得の差（基準年をまたいだときのずれの大きさ）
ov = raw.pivot_table(index=['code', 'year'], columns='vintage', values='r')
pairs = [('v2023', 'v2018'), ('v2018', 'h26'), ('h26', 'h21'), ('h21', 'h15'), ('h15', 's50'), ('s50', 's30')]
rows = []
for a, b in pairs:
    x = ov[[a, b]].dropna()
    if len(x): rows.append((a, b, len(x), float((x[a]-x[b]).abs().mean()), float(np.corrcoef(x[a], x[b])[0, 1])))
pd.DataFrame(rows, columns=['新', '旧', '重なる県×年', '相対所得の差の平均（絶対値）', '相関']).to_csv(H/'results/vintage_overlap.csv', index=False)
print(pd.read_csv(H/'results/vintage_overlap.csv'))
