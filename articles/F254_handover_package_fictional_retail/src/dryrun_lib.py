"""試走（ドライラン）の道具：README の「再現手順」だけを見て、きれいなフォルダで上から順に流す。
- 消すもの：生成物のフォルダ（results/ figures/ mart/ reports/ sheet/ dashboard/ powerbi/ と data/ の中。ただし F246 の data/raw は入力なので残す）
- 流すもの：README の「## 再現手順」のコードブロックにある `python ...` の行を、そのまま上から
- 記録：各手順の成否・かかった秒・エラーの最後の行。流したあとの git status で「元と同じ／違う／作られなかった」を数える
"""
import json, os, pathlib, re, resource, shutil, subprocess, sys, time

GEN_DIRS = ["results", "figures", "mart", "reports", "sheet", "dashboard", "powerbi"]


def clean(art: pathlib.Path):
    for d in GEN_DIRS:
        p = art / d
        if p.exists():
            shutil.rmtree(p)
    data = art / "data"
    if data.exists():
        for c in data.iterdir():
            if c.name == "raw" and art.name.startswith("F246"):
                continue  # 公開データの写し（入力）
            shutil.rmtree(c) if c.is_dir() else c.unlink()


def steps(art: pathlib.Path):
    t = (art / "README.md").read_text(encoding="utf-8")
    m = re.search(r"## 再現手順\s*\n```[^\n]*\n(.*?)```", t, re.S)
    out = []
    for line in m.group(1).splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("python "):
            out.append(line.split()[1])
    return out


def run_article(art, py, timeout=1800, env=None, keep_going=False):
    rec = {"article": art.name, "steps": []}
    for s in steps(art):
        t0 = time.time(); r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        p = subprocess.run(["nice", "-n", "10", py, s], cwd=art, capture_output=True, text=True,
                           timeout=timeout, env=env)
        err = [l for l in (p.stderr or "").strip().splitlines() if l.strip()]
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        rec["steps"].append({"script": s, "rc": p.returncode, "sec": round(time.time() - t0, 1), "cpu": round(cpu, 1),
                             "err": err[-1][:300] if (p.returncode and err) else ""})
        if p.returncode and not keep_going:
            break
    return rec


def git_status(repo, art):
    p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", f"articles/{art.name}"],
                       cwd=repo, capture_output=True, text=True)
    c = {"同じ": 0, "違う": [], "作られなかった": [], "新しく増えた": 0}
    tracked = subprocess.run(["git", "ls-files", "--", f"articles/{art.name}"], cwd=repo,
                             capture_output=True, text=True).stdout.split()
    changed = set()
    for line in p.stdout.splitlines():
        code, path = line[:2], line[3:].strip().strip('"')
        if code.strip() == "M":
            c["違う"].append(path); changed.add(path)
        elif code.strip() == "D":
            c["作られなかった"].append(path); changed.add(path)
        elif code == "??":
            c["新しく増えた"] += 1
    c["同じ"] = sum(1 for f in tracked if f not in changed)
    c["tracked"] = len(tracked)
    return c
