"""各回のスクリプトを、コードを書き換えずに流すための小さな起動役。

    python samplemart/launch.py src/03_整える.py      （cwd は、その回のフォルダ）

やっていることは1つだけ：DuckDB の接続を作ったら、すぐ `SET threads TO 1` を流す。
DuckDB は並列で足し算するので、同じ版・同じデータでも、足す順番が実行ごとに変わり、小数の最後の桁が揺れる。
F247 の mart は人時を 0.1 の単位で書き出すので、四捨五入の境目にある値が 0.1 ずれ、F248 の人時粗利まで動いた
（docs/troubleshooting.md の T3）。1本で足すと、何回流しても同じバイトになる。
"""
import runpy, sys, pathlib

try:
    import duckdb
    _connect = duckdb.connect

    def connect(*a, **k):
        con = _connect(*a, **k)
        con.execute("SET threads TO 1")
        return con
    duckdb.connect = connect
except ImportError:
    pass

script = pathlib.Path(sys.argv[1])
sys.argv = [str(script)] + sys.argv[2:]
sys.path.insert(0, str(script.resolve().parent))
runpy.run_path(str(script), run_name="__main__")
