"""F112 の各段階を順に実行する（python3 zz_f112_run.py 02 03 04）"""
import runpy, sys
from pathlib import Path
here = Path(__file__).resolve().parent
names = {"02": "02_整形.py", "03": "03_分析.py", "04": "04_図.py"}
for k in sys.argv[1:] or ["02", "03", "04"]:
    print("=====", names[k], flush=True)
    sys.path.insert(0, str(here))
    runpy.run_path(str(here / names[k]), run_name="__main__")
