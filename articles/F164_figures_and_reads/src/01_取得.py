# 取得はブラウザで行う（src/01_取得.js）。note.com はこの環境の外からは取れないため。
# できた f164_note_public.json を data/raw/ に置き、02_整形.py → 03_分析.py → 04_図.py の順に実行する。
import pathlib, json
p = pathlib.Path(__file__).resolve().parents[1]/'data/raw/f164_note_public.json'
d = json.load(open(p)); print(d['fetched_at'], len(d['rows']), '本')
