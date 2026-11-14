"""実行後のマートの中身を、表ごとの行数とハッシュにまとめて表示する（2回流して同じかを見るため）。
使い方: python3 orchestration/snapshot.py > 出力先.json
"""
import hashlib, json, os
import duckdb

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target", "retail_mart.duckdb")
out = {}
with duckdb.connect(DB, read_only=True) as c:
    names = [r[0] for r in c.execute(
        "select table_name from information_schema.tables where table_schema='main' order by 1").fetchall()]
    for t in names:
        df = c.execute(f"select * from main.{t}").df()
        df = df.sort_values(list(df.columns)).reset_index(drop=True)
        out[t] = {"rows": len(df), "md5": hashlib.md5(df.to_csv(index=False, float_format="%.9f").encode()).hexdigest()}
print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
