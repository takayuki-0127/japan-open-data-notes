"""03 試走（引き継ぎ後）：新しい人の役で、handover/README.md の「まず、これだけ」のコマンドだけを、上から順に流す。

    python src/03_試走_引き継ぎ後.py <空のフォルダ> <名前> [local|github]

- github：README のとおり、GitHub から clone するところから（F254 を GitHub に上げた後）
- local ：clone の4行の代わりに、このフォルダの handover/ を空のフォルダに写す（上げる前の試走）
- 記録：コマンドごとの成否・秒・出力の最後の数行 → results/C_after_<名前>.json
"""
import json, pathlib, re, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
dst, name, mode = pathlib.Path(sys.argv[1]), sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "local")
if dst.exists() and any(dst.iterdir()):
    sys.exit("空のフォルダを渡してください")
dst.mkdir(parents=True, exist_ok=True)
t = (ROOT / "handover" / "README.md").read_text(encoding="utf-8")
block = re.search(r"## まず、これだけ\s*\n```bash\n(.*?)```", t, re.S).group(1)
cmds = [c.strip() for c in block.splitlines() if c.strip() and not c.strip().startswith("#")]
cwd = dst; rec = {"mode": mode, "commands": []}
if mode == "local":
    # clone・cd・sparse-checkout・cd の4行の代わり
    shutil.copytree(ROOT / "handover", dst / "handover", ignore=shutil.ignore_patterns("work", ".venv", "__pycache__"))
    cwd = dst / "handover"; cmds = cmds[4:]
    rec["commands"].append({"cmd": "（handover/ を写す：clone の4行の代わり）", "rc": 0, "sec": 0.0, "tail": ""})
t_all = time.time()
for c in cmds:
    if c.startswith("cd "):
        cwd = (cwd / c[3:].strip()).resolve()
        rec["commands"].append({"cmd": c, "rc": 0, "sec": 0.0, "tail": ""}); continue
    t0 = time.time()
    p = subprocess.run(["bash", "-c", f"nice -n 10 {c}"], cwd=cwd, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip().splitlines()
    rec["commands"].append({"cmd": c, "rc": p.returncode, "sec": round(time.time() - t0, 1), "tail": "\n".join(out[-14:])})
    print(f"[{p.returncode}] {time.time() - t0:7.1f}s  {c}", flush=True)
    if p.returncode:
        break
rec["sec_total"] = round(time.time() - t_all, 1)
rl = cwd / "work" / "run_log.json"
if rl.exists():
    rec["run_log"] = json.loads(rl.read_text(encoding="utf-8"))
vf = cwd / "work" / "verify.csv"
if vf.exists():
    shutil.copyfile(vf, ROOT / "results" / f"C_verify_{name}.csv")
(ROOT / "results" / f"C_after_{name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
print("total", rec["sec_total"])
