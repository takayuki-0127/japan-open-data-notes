"""抽出した記事フォルダを、記事ごとの新しい仮想環境で最初から実行し直す。
使い方: python 03_実行.py <articlesディレクトリ> <作業ディレクトリ> <抽出リストCSV> <出力CSV> [--constraints 制約ファイル] [--cap 秒]
- 仮想環境は uv で記事ごとに作り、その記事の requirements.txt だけを入れる（システムのパッケージは見せない）
- 手順は README のコードブロック（cd / python / bash）から読み、読めなければ run_all.sh → src の番号順
- results/ と figures/ は空にしてから実行し、もとの results/ と比べる（03 で比較）
"""
import sys, os, re, csv, shutil, subprocess, time, json, argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("arts"); ap.add_argument("work"); ap.add_argument("sample"); ap.add_argument("out")
ap.add_argument("--constraints", default=None); ap.add_argument("--cap", type=int, default=600)
ap.add_argument("--only", default=None)
ap.add_argument("--system", action="store_true", help="仮想環境を作らず、記事を書いた環境（このマシンの python）でそのまま動かす")
a = ap.parse_args()
arts, work = Path(a.arts).resolve(), Path(a.work).resolve(); work.mkdir(parents=True, exist_ok=True)
UV = shutil.which("uv")
ENV0 = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
ENV0.update(MPLBACKEND="Agg", UV_CACHE_DIR=str(work / "_uvcache"), PIP_DISABLE_PIP_VERSION_CHECK="1")

def readme_steps(d):
    t = (d / "README.md").read_text(errors="ignore")
    blocks = re.findall(r"```(?:bash|sh|shell|console)?\n(.*?)```", t, re.S)
    for b in blocks:
        cmds, cwd = [], "."
        for line in b.splitlines():
            line = line.split("#")[0].strip().lstrip("$ ").strip()
            for c in [x.strip() for x in line.split("&&") if x.strip()]:
                if c.startswith("cd "):
                    cwd = os.path.normpath(os.path.join(cwd, c[3:].strip()))
                elif re.match(r"^(python3?|bash|sh)\s+\S+", c):
                    cmds.append((cwd, c))
        ok = [x for x in cmds if (d / x[0] / x[1].split()[1]).exists()]
        if cmds and ok:
            return "README", cmds
    return None, []

def fallback_steps(d):
    for p in (d / "src" / "run_all.sh", d / "run_all.sh"):
        if p.exists(): return "run_all", [(str(p.parent.relative_to(d)), "bash run_all.sh")]
    src = d / "src"
    fs = sorted(f.name for f in src.glob("*.py") if re.match(r"^\d{2}", f.name))
    if not fs: fs = sorted(f.name for f in src.glob("*.py") if f.stem not in ("common", "util", "utils", "config"))
    return "番号順", [("src", f"python {f}") for f in fs]

def classify(err):
    e = err[-4000:]
    if re.search(r"TIMEOUT", e): return "時間切れ"
    if re.search(r"ConnectionError|URLError|ProxyError|HTTPError|Max retries|getaddrinfo|Name or service|NewConnectionError|RemoteDisconnected|403 Forbidden|Tunnel connection failed|SSLError|ConnectTimeout|ReadTimeout|Temporary failure in name", e): return "ネットワーク"
    if re.search(r"ModuleNotFoundError|No module named", e): return "パッケージの記載漏れ"
    if re.search(r"FileNotFoundError|No such file|does not exist|can't open file", e): return "ファイルが見つからない"
    if re.search(r"ImportError|AttributeError|TypeError|got an unexpected keyword|has no attribute|deprecated|removed in|FutureWarning|ValueError: .*(dtype|keyword|parameter)", e): return "ライブラリの版の違い"
    if re.search(r"MemoryError|Killed", e): return "メモリ不足"
    return "その他"

done = set()
if Path(a.out).exists():
    done = {r["folder"] for r in csv.DictReader(open(a.out))}
sample = [r["folder"] for r in csv.DictReader(open(a.sample))]
if a.only: sample = [s for s in sample if s in a.only.split(",")]
fields = ["folder", "steps_from", "n_steps", "install_ok", "install_sec", "install_err", "steps_ok", "first_fail_step",
          "first_fail_cat", "fail_cats", "net_fail_fetch_only", "run_sec", "timed_out", "log"]
newfile = not Path(a.out).exists()
fo = open(a.out, "a", newline=""); w = csv.DictWriter(fo, fieldnames=fields)
if newfile: w.writeheader()
for name in sample:
    if name in done: continue
    src = arts / name; wd = work / name
    if wd.exists(): shutil.rmtree(wd)
    shutil.copytree(src, wd, ignore=shutil.ignore_patterns(".venv"))
    exp = work / "_expected" / name
    if exp.exists(): shutil.rmtree(exp)
    exp.mkdir(parents=True)
    for sub in ("results", "figures"):
        if (wd / sub).exists():
            shutil.move(str(wd / sub), str(exp / sub)); (wd / sub).mkdir()
    log = []
    t0 = time.time()
    if a.system:
        inst_ok, inst_err = True, ""
    else:
      subprocess.run([UV, "venv", "-q", "--python", sys.executable, str(wd / ".venv")], env=ENV0, capture_output=True)
      cmd = [UV, "pip", "install", "-q", "--python", str(wd / ".venv" / "bin" / "python"), "-r", str(wd / "requirements.txt")]
      if a.constraints: cmd += ["-c", a.constraints]
      try:
          p = subprocess.run(cmd, env=ENV0, capture_output=True, text=True, timeout=900)
          inst_ok, inst_err = p.returncode == 0, p.stderr[-600:]
      except subprocess.TimeoutExpired:
          inst_ok, inst_err = False, "TIMEOUT install"
    inst_sec = round(time.time() - t0, 1)
    how, steps = readme_steps(wd)
    if not steps: how, steps = fallback_steps(wd)
    env = dict(ENV0); env["PYTHONNOUSERSITE"] = "1"
    if not a.system:
        env["PATH"] = str(wd / ".venv" / "bin") + ":" + env["PATH"]; env["VIRTUAL_ENV"] = str(wd / ".venv")
    chk = subprocess.run(["bash", "-c", "python -c 'import sys;print(sys.prefix)'"], cwd=wd / "src" if (wd / "src").exists() else wd, env=env, capture_output=True, text=True)
    log.append("python prefix: " + chk.stdout.strip())
    ok, cats, first_step, t1, timed = 0, [], "", time.time(), 0
    fetch_net_only = True
    for i, (cwd, c) in enumerate(steps):
        left = a.cap - (time.time() - t1)
        if left <= 5:
            cats.append("時間切れ"); timed = 1; first_step = first_step or c; break
        if not inst_ok:
            pass
        try:
            r = subprocess.run(["nice", "-n", "10", "bash", "-c", c.replace("python3 ", "python ")], cwd=wd / cwd, env=env,
                               capture_output=True, text=True, timeout=left)
            rc, err = r.returncode, (r.stderr or "") + (r.stdout or "")[-1500:]
        except subprocess.TimeoutExpired:
            rc, err, timed = -9, "TIMEOUT", 1
        log.append(f"### {cwd}$ {c}\nrc={rc}\n{err[-2500:]}")
        if rc == 0:
            ok += 1
        else:
            cat = classify(err) if inst_ok or "TIMEOUT" in err else ("パッケージが入らない" if "No module named" in err else classify(err))
            cats.append(cat); first_step = first_step or c
            is_fetch = bool(re.search(r"取得|fetch|download|01_|00_", c))
            if not (cat == "ネットワーク" and is_fetch): fetch_net_only = False
            if timed: break
    (work / "_logs").mkdir(exist_ok=True)
    (work / "_logs" / f"{name}.log").write_text(f"install_ok={inst_ok}\n{inst_err}\n" + "\n".join(log))
    row = dict(folder=name, steps_from=how, n_steps=len(steps), install_ok=int(inst_ok), install_sec=inst_sec,
               install_err=inst_err.replace("\n", " ")[:300], steps_ok=ok, first_fail_step=first_step,
               first_fail_cat=cats[0] if cats else "", fail_cats=";".join(cats),
               net_fail_fetch_only=int(bool(cats) and fetch_net_only), run_sec=round(time.time() - t1, 1),
               timed_out=timed, log=f"_logs/{name}.log")
    w.writerow(row); fo.flush()
    print(name, how, f"{ok}/{len(steps)}", row["first_fail_cat"], row["run_sec"], flush=True)
    shutil.rmtree(wd / ".venv", ignore_errors=True)
