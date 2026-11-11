"""01 取得：損害保険料率算出機構（GIROJ）の公開データを data/raw に置く。
- graph_data_eq_ex.json：都道府県別の付帯率（年度）・世帯加入率（年末）。統計ページ https://www.giroj.or.jp/databank/earthquake.html が読むファイル
- graph_data_eq.json：都道府県別の地震保険の新契約件数・保有件数（月）
- k_2015/2020/2025.xlsx：「火災保険・地震保険の概況」第12表（照合用。F272 と同じファイル）
ファイルが既にあれば md5 を表示するだけ。無ければ公開 URL から取る（2026-11-11 に取得）。"""
import hashlib, pathlib, sys, urllib.request
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SRC = {
    "graph_data_eq_ex.json": "https://www.giroj.or.jp/databank/files/eq/graph_data_eq_ex.json",
    "graph_data_eq.json": "https://www.giroj.or.jp/databank/files/eq/graph_data_eq.json",
    "k_2015.xlsx": "https://www.giroj.or.jp/publication/outline_k/k_2015.xlsx",
    "k_2020.xlsx": "https://www.giroj.or.jp/publication/outline_k/k_2020.xlsx",
    "k_2025.xlsx": "https://www.giroj.or.jp/publication/outline_k/k_2025.xlsx",
}
EXPECT = {
    "graph_data_eq_ex.json": "b9ccc6b79ac6dad876e6667bac94c1e0",
    "graph_data_eq.json": "18ea66b6c8971ed33926a275c82674b9",
    "k_2015.xlsx": "fa8bc984136c00e475ed1139a787553c",
    "k_2020.xlsx": "4fdac3498eaef646d4d6e7512f629c39",
    "k_2025.xlsx": "465c1237119f244ca384763fe348fb66",
}
for name, url in SRC.items():
    p = RAW / name
    if not p.exists():
        print("download", name, file=sys.stderr)
        urllib.request.urlretrieve(url, p)
    h = hashlib.md5(p.read_bytes()).hexdigest()
    print(name, h, "OK" if h == EXPECT[name] else "（2026-11-11 版と違う。サイト側で更新された可能性）")
