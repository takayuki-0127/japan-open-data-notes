# 公開ページの数字（スキ・コメント）と記事の作り（図の数・字数・タイトルの長さ）を1表にする
import json, pandas as pd, pathlib
B = pathlib.Path(__file__).resolve().parents[1]
d = json.load(open(B/'data/raw/f164_note_public.json'))
df = pd.DataFrame(d['rows'])
df['publishAt'] = pd.to_datetime(df['publishAt'])
asof = pd.Timestamp(d['fetched_at']).tz_convert('Asia/Tokyo')  # 取得時点
df['days'] = ((asof - df['publishAt']).dt.total_seconds()/86400).round(2)
df['title_len'] = df['title'].str.len()
df['n_tags'] = df['hashtags'].fillna('').str.count('#')
df['q_title'] = df['title'].str.contains('？').astype(int)
def fam(r):
    if r.chars >= 3000 and r.n_img >= 5: return '看板型（3,000字以上・図5枚以上）'
    if r.github: return '短い分析・技術（GitHubつき）'
    return 'その他（体験・業務の記事）'
df['family'] = df.apply(fam, axis=1)
df['fig_bin'] = pd.cut(df.n_img, [-1,0,2,4,6], labels=['0枚','1〜2枚','3〜4枚','5〜6枚'])
cols = ['key','publishAt','days','like','comment','chars','n_img','n_h2','n_code','n_link','title_len','n_tags','q_title','github','family','fig_bin','title']
(B/'data').mkdir(exist_ok=True)
df[cols].sort_values('publishAt').to_csv(B/'data/articles.csv', index=False)
print(df.family.value_counts()); print(df[['like','comment']].sum())
