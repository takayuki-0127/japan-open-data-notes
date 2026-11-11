"""287 頑健性チェックは、いくつやれば十分か（④ 振り返り R014）

使い方: python a287.py <japan-open-data-notes のクローン>
  A. すべての README の「頑健性」の節から、チェックの数（表の行・箇条書き、基本の行と見出しを除く）を数え、記事のグループで比べる
  B. F163 の手作業の判定（data/f163_hand_labels.csv：F01〜F125 のうち113本、「結論が動いたか」と「いちばん動かしたチェックの種類」）と
     F163 が取り出したチェックの一覧（data/f163_items.json）を使い、
     「チェックを k 個だけしていたら、結論を動かした種類のチェックを含んでいた割合」を計算する
     （ランダムに k 個選ぶ場合と、種類を1つずつ選ぶ場合）
  種類の辞書は F163 の src/02_整形.py と同じもの
"""
import re, sys, os, json
from math import comb
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, group_of, dedup, title_of, section

repo = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")

# ---------- A. チェックの数
BASE = re.compile(r"^\**(基本|主設定|ベース|本文|基準|元の|既定|base\b)")
def count_checks(block):
    n, hdr = 0, None
    for ln in block.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            hdr = None; continue
        if s.startswith("|"):
            c = [x.strip() for x in s.strip("|").split("|")]
            if set("".join(c)) <= set("-: "):
                continue
            if hdr is None:
                hdr = c; continue
            if BASE.search(c[0]):
                continue
            n += 1
        elif re.match(r"^([-*・]|\d+[.)．])\s+", s):
            n += 1
    return n

docs = dedup(readmes(repo))
rows = []
for folder, t in docs:
    secs = section(t, r"頑健|ロバスト")
    n = sum(count_checks(s) for s in secs)
    rows.append({"article": folder, "group": group_of(folder), "has_section": bool(secs), "checks": n})
A = pd.DataFrame(rows)
A.to_csv(os.path.join(OUT, "data", "checks_per_article.csv"), index=False)
G = (A[A.has_section].groupby("group").checks.describe(percentiles=[.25, .5, .75])[["count", "25%", "50%", "75%"]]
     .rename(columns={"count": "articles", "25%": "q1", "50%": "median", "75%": "q3"}))
G = G.reindex(A.group.unique())
G["readmes"] = A.groupby("group").size()
G["share_with_section"] = A.groupby("group").has_section.mean().round(3)
G["share_3plus"] = A[A.has_section].assign(x=lambda d: d.checks >= 3).groupby("group").x.mean().round(3)
ORDER = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]
G = G.reindex([g for g in ORDER if g in G.index])
G.index.name = "group"
G.to_csv(os.path.join(OUT, "results", "checks_by_group.csv"))

# ---------- B. 何個で、結論を動かした種類に当たるか
TYPES = [
 ('プラセボ・並べ替え', r'プラセボ|並べ替え|偽の|ランダムに選び|置換|でたらめ'),
 ('検証の分け方', r'検証|交差|ブロック|分割|fold|ホールドアウト|起点|テスト期間|評価用'),
 ('期間・時期', r'期間|\d{4}年|年度|年以降|年まで|〜\d{4}|学習\s*\d|コロナ|延長|前半|後半|年代|時期'),
 ('対象を絞る・除く', r'人以上|以上$|以上（|除く|除外|だけ|のみ|限る|以上の|未満|外す|抜く|サンプル|標本'),
 ('定義・指標', r'あたり|にそろえ|粗く|近似|移動平均|処置を|項目|系列|対照|賃金|世帯|支給|で見る|で数える|物差し|含める|含めない|考えない|まとめる|向き|出発点|定義|指標|にする|に変え|入れ替|代わりに|別の|原数値|名目|実質|当たり|割合で|で測|対数|基準|水準'),
 ('変数・調整', r'使わない|入れない|なし$|FE|引く|共変量|特徴量|変数|ダミー|トレンド|固定効果|コントロール|調整|入れる|加える|足す|抜いた'),
 ('モデル・推定法', r'ブートストラップ|LWZ|X-13|管理限界|UMAP|HDBSCAN|TF-IDF|SVD|STL|マッチング|GCN|Rational|Matern|MICE|補完|分解|組み替え|仮定|モデル|ARIMA|SARIMA|LightGBM|GBM|回帰|推定|手法|OLS|ポアソン|ロジット|ベイズ|事前分布|カーネル|線形|ランダムフォレスト|GMM|PPML|DEA|IPF|クラスタ|k-means|ウォード|分布の形|辞書|埋め込み'),
 ('設定値・パラメータ', r'h\s*=|キャリパー|最近傍|1対\d|葉|深さ|seasonal|robust=|上位\d|下位\d|次元|因子\d|因子[一二三2-9]つ|状態|自由度|×\s*\d|[+\-−]\d+\s*%|初期を|階級|分位|正規化|平均の取り|幾何|算術|t分布|足し算|最小|最大|数を|の数|閾値|しきい|次数|ラグ|窓|帯域|バンド幅|倍率|重み|長さ|区分|ハイパー|k\s*=|\d+通り|乱数|シード'),
 ('データ源・集計単位', r'データ|出典|調査|集計|単位|市区町村|都道府県|地域|境界|隣接|隣'),
]
def types_of(label):
    if re.search(r'どの設定|どれでも|すべての(チェック|設定|条件)|いずれの|どの仮定|どのチェック|どの組み合わせ|どの条件', label):
        return None  # まとめの行は1つのチェックとして数えない
    return [t for t, p in TYPES if re.search(p, label)] or ['その他']

items = json.load(open(os.path.join(OUT, "data", "f163_items.json"), encoding="utf-8"))
hand = pd.read_csv(os.path.join(OUT, "data", "f163_hand_labels.csv"))
per = {}
for it in items:
    if it["kind"] not in ("row", "bul"):
        continue
    if it["kind"] == "row" and BASE.search(it["label"]):
        continue
    tt = types_of(it["label"])
    if tt is None:
        continue
    per.setdefault(it["fid"], []).append(tt)

K = list(range(1, 16))
recs = []
for _, h in hand.dropna(subset=["level"]).iterrows():
    L = per.get(h.fid, [])
    n = len(L)
    rec = {"fid": h.fid, "level": int(h.level), "mover": h.mover, "n": n}
    if int(h.level) >= 1 and n:
        nt = sum(1 for tt in L if h.mover in tt)
        m = len({t for tt in L for t in tt})
        rec.update({"n_mover_type": nt, "distinct_types": m})
        for k in K:
            kk = min(k, n)
            rec[f"rand_{k}"] = 1 - comb(n - nt, kk) / comb(n, kk) if nt else 0.0
            rec[f"type_{k}"] = (min(k, m) / m) if nt else 0.0
    recs.append(rec)
R = pd.DataFrame(recs)
R.to_csv(os.path.join(OUT, "data", "f163_articles_coverage.csv"), index=False)
# 表の行・箇条書きのチェックが1つもない記事（頑健性を文章だけで書いた記事）は除く
mv = R[(R.level >= 1) & (R.n > 0)]
mv2 = R[(R.level == 2) & (R.n > 0)]
curve = pd.DataFrame({"k": K,
                      "rand_moved": [mv[f"rand_{k}"].mean() for k in K],
                      "type_moved": [mv[f"type_{k}"].mean() for k in K],
                      "rand_changed": [mv2[f"rand_{k}"].mean() for k in K]}).round(3)
curve.to_csv(os.path.join(OUT, "results", "coverage_curve.csv"), index=False)

summary = {
    "readmes": int(len(A)), "with_section": int(A.has_section.sum()),
    "by_group": G.reset_index().to_dict("records"),
    "f163_judged": int(len(R)), "moved_all": int((R.level >= 1).sum()), "changed_all": int((R.level == 2).sum()),
    "moved": int(len(mv)), "changed": int(len(mv2)),
    "moved_no_items_of_mover_type": int((mv.n_mover_type == 0).sum()),
    "moved_n_median": float(mv.n.median()), "moved_ntype_median": float(mv.n_mover_type.median()),
    "curve": curve.to_dict("records"),
    "n_by_level_median": R.groupby("level").n.median().to_dict(),
}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in summary.items() if k != "curve"}, ensure_ascii=False, indent=1, default=float))
print(curve.to_string())

# 図1：グループごとのチェックの数
order = [g for g in ORDER if g in G.index and G.loc[g, "articles"] > 0]
fig, ax = plt.subplots(figsize=(8, 4.4))
S = A[A.has_section]
data = [S[S.group == g].checks.values for g in order]
ax.boxplot(data, showfliers=False, widths=0.5)
ax.set_xticks(range(1, len(order) + 1)); ax.set_xticklabels([f"{g}\n（{len(d)}本）" for g, d in zip(order, data)], fontsize=8.5)
for i, d in enumerate(data, 1):
    ax.text(i, pd.Series(d).median() + 0.3, f"{pd.Series(d).median():.0f}", ha="center", fontsize=9, color="#2f6fb0")
ax.set_ylabel("頑健性の節のチェックの数（基本の行を除く）")
ax.set_title("1本あたりの頑健性チェックの数（頑健性の節がある記事）", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a287_counts.png"), dpi=150); plt.close(fig)

# 図2：k 個で、動かした種類に当たる割合
fig, ax = plt.subplots(figsize=(7.6, 4.6))
ax.plot(curve.k, curve.rand_moved * 100, marker="o", label=f"ランダムに k 個（結論が動いた {len(mv)}本）", color="#2f6fb0")
ax.plot(curve.k, curve.type_moved * 100, marker="s", label="種類を1つずつ k 種類", color="#d9822b")
ax.plot(curve.k, curve.rand_changed * 100, marker="^", ls="--", label=f"ランダムに k 個（結論が変わった {len(mv2)}本）", color="#5a9e5a")
for k in (3, 5, 7):
    y = curve.loc[curve.k == k, "rand_moved"].iloc[0] * 100
    ax.annotate(f"{y:.0f}%", (k, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
ax.set_xlabel("していたチェックの数 k"); ax.set_ylabel("動かした種類のチェックを含んでいた割合（%）")
ax.set_ylim(0, 105); ax.legend(fontsize=8.5, loc="lower right")
ax.set_title("チェックを k 個に減らしていたら、結論を動かした種類に当たったか", fontsize=11.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a287_curve.png"), dpi=150); plt.close(fig)

# 図3：k ごとの表（ランダム／種類を1つずつ／結論が変わった記事）
T = curve[curve.k <= 8]
cell = [[f"{int(r.k)}個", f"{r.rand_moved*100:.0f}%", f"{r.type_moved*100:.0f}%", f"{r.rand_changed*100:.0f}%"] for r in T.itertuples()]
fig, ax = plt.subplots(figsize=(8.4, 3.9)); ax.axis("off")
tb = ax.table(cellText=cell, colLabels=["チェックの数", f"ランダムに選ぶ（{len(mv)}本）", "種類を1つずつ選ぶ", f"ランダム・結論が変わった{len(mv2)}本"], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.55)
for (r, c), cl in tb.get_celld().items():
    if r == 0: cl.set_facecolor("#e8eef6"); cl.set_text_props(weight="bold")
ax.set_title("動かした種類のチェックを含んでいた割合（記事ごとの確率の平均）", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figures", "a287_table.png"), dpi=150); plt.close(fig)
