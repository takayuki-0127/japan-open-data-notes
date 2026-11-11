"""01 取得：UCI「Online Retail II」(CC BY 4.0) の zip を取得し、md5 を確かめる。
xlsx は 45MB あるのでリポジトリには入れない（data/raw/ は .gitignore）。"""
import hashlib, pathlib, urllib.request, zipfile, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
MD5 = "dc74ff2011818f6baebf525b50f19a07"
z = RAW / "online_retail_ii.zip"
if not z.exists():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src: z.write_bytes(pathlib.Path(src).read_bytes())
    else: urllib.request.urlretrieve(URL, z)
h = hashlib.md5(z.read_bytes()).hexdigest()
assert h == MD5, h
with zipfile.ZipFile(z) as f: f.extractall(RAW)
print("ok", h, [p.name for p in RAW.iterdir()])
