from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 156
PREFS = ["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川","新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄"]
# 地方（7区分、北海道は東北と合わせる）
REGION = {**{p:"北海道・東北" for p in PREFS[0:7]}, **{p:"関東" for p in PREFS[7:14]},
          **{p:"中部" for p in PREFS[14:23]}, **{p:"近畿" for p in PREFS[23:30]},
          **{p:"中国" for p in PREFS[30:35]}, **{p:"四国" for p in PREFS[35:39]},
          **{p:"九州・沖縄" for p in PREFS[39:47]}}
