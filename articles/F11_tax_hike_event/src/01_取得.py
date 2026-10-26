"""e-Stat から家計調査（二人以上の世帯）の長期時系列表 CSV を取得する。
ブラウザ外から実行する場合はそのまま動く。（記事の作成時は、同じ URL をブラウザのページ内で取得した）
"""
import requests
from common import RAW, STAT_IDS

RAW.mkdir(parents=True, exist_ok=True)
for key, sid in STAT_IDS.items():
    url = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={sid}&fileKind=1"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    (RAW / f"kakei_{sid}.csv").write_text(r.content.decode("shift_jis"), encoding="utf-8")
    print(key, sid, len(r.content))
