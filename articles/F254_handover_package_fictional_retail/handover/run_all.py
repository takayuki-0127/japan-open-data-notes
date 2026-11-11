"""サンプルマート（架空）の分析を、何もないところから作り直す入口。

    python run_all.py                 # mart と月次レポートまで（ふつうはこれ）
    python run_all.py --target all    # F246〜F251 の全部（図・PDF を含む。Chromium が要る）
    python run_all.py --check-only    # 作り直さずに、前回の結果を元の数字と照合だけする

やること（README の「全体の流れ」と同じ順）：
  1. 準備：config.toml の repo を、決めたコミットで work/repo に取る（git の sparse checkout）
  2. 掃除：git clean で、コミットにないファイル（前回の途中のファイル）だけ消す。コミットにあるファイルは消さない
     （F249 の powerbi/ のように、手で書いたファイルと作られるファイルが同じフォルダにあるため。作られたかどうかは時刻で見る）
  3. 段を順に流す：stages.py の表のとおり。ログは work/logs/、かかった時間は work/run_log.json
  4. 照合：作り直したファイルを、基準（expected/manifest.json の md5）と、コミットに入っている元のファイルの両方と比べる
     （work/verify.csv）。基準と比べて数字のファイル（csv・json・md・sql）が1つでも違えば、終了コード 1 で止まる
元のコード（各回の src/）は書き換えない。数字が同じことを確かめる仕組みを先に置き、直すのはその後、という順番にしている。
"""
import argparse, json, pathlib, resource, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from samplemart import stages, verify  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 以前
    sys.exit("Python 3.11 以上が要る（tomllib を使う）。README の「前提」を見てください。")


def sh(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"失敗：{' '.join(cmd)}\n{p.stderr.strip()[-800:]}")
    return p.stdout.strip()


def prepare(cfg, work, target):
    repo = work / "repo"
    arts = stages.articles(cfg, target)
    allarts = stages.articles(cfg, "all")  # テスト（tests/test_rules.py）が F250 も読むので、取るのは常に6回分
    if not (repo / ".git").exists():
        print(f"[準備] {cfg['source']['repo']} を取得（sparse）")
        sh(["git", "clone", "-q", "--filter=blob:none", "--sparse", "--no-checkout", cfg["source"]["repo"], str(repo)])
    sh(["git", "sparse-checkout", "set", *[f"articles/{a}" for a in allarts]], cwd=repo)
    sh(["git", "checkout", "-q", "--force", cfg["source"]["commit"]], cwd=repo)
    sh(["git", "clean", "-qfdx", "articles"], cwd=repo)  # 前回の生成物も消して、コミットの状態に戻す
    head = sh(["git", "rev-parse", "HEAD"], cwd=repo)
    print(f"[準備] コミット {head[:7]}、回：{', '.join(a[:4] for a in arts)}")
    return repo, arts, head


def run(cfg, work, target):
    repo, arts, head = prepare(cfg, work, target)
    stages.set_repo(repo)
    logs = work / "logs"; logs.mkdir(parents=True, exist_ok=True)
    rec = {"commit": head, "target": target, "python": sys.version.split()[0], "steps": []}
    t_all = time.time()
    for st in stages.plan(cfg, target):
        art = repo / "articles" / st["article"]
        t0 = time.time(); r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        if st.get("func"):
            msg = st["func"](repo / "articles", cfg); rc, out, err = 0, msg, ""
        else:
            # launch.py：コードは書き換えずに、DuckDB を1本で足すようにして流す（docs/troubleshooting.md の T3）
            p = subprocess.run([sys.executable, str(HERE / "samplemart" / "launch.py"), st["script"]],
                               cwd=art, capture_output=True, text=True)
            rc, out, err = p.returncode, p.stdout, p.stderr
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        sec = time.time() - t0; cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        name = f"{st['article'][:4]}_{st['label']}"
        (logs / f"{name}.log").write_text(out + "\n--- stderr ---\n" + err, encoding="utf-8")
        rec["steps"].append({"step": name, "what": st["what"], "rc": rc, "sec": round(sec, 1), "cpu": round(cpu, 1)})
        print(f"[{'OK' if rc == 0 else 'NG'}] {name:<22} {sec:6.1f} 秒  {st['what']}")
        if rc:
            (work / "run_log.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            sys.exit(f"止まりました：{name}。ログ：{logs / (name + '.log')}\n最後の行：{err.strip().splitlines()[-1] if err.strip() else ''}\n"
                     "docs/troubleshooting.md に、試走で出たエラーと直し方があります。")
    rec["sec_total"] = round(time.time() - t_all, 1)
    (work / "run_log.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return repo, arts, t_all


def main():
    ap = argparse.ArgumentParser(description="サンプルマート（架空）の分析を作り直す")
    ap.add_argument("--target", choices=["report", "all"], default="report")
    ap.add_argument("--work", default=str(HERE / "work"))
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--make-baseline", action="store_true", help="（渡す側が1回だけ）作り直した結果を基準として expected/ に書く")
    a = ap.parse_args()
    cfg = tomllib.loads((HERE / "config.toml").read_text(encoding="utf-8"))
    work = pathlib.Path(a.work).resolve(); work.mkdir(parents=True, exist_ok=True)
    if a.check_only:
        repo = work / "repo"; arts = stages.articles(cfg, a.target); since = 0
    else:
        repo, arts, since = run(cfg, work, a.target)
    if a.make_baseline:
        verify.make_manifest(repo, arts, since, a.target)
    ok = verify.check(repo, arts, since, work / "verify.csv", a.target)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
