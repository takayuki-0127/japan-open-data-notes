"""01 取得：e-Stat のファイル（statInfId）をダウンロードして data/raw/ に保存する。

- API キー（appId）は使わない。e-Stat の「ファイル」の公開URL（file-download）から取る
- 失敗したら指数バックオフで再試行（最大5回）。前回の取得物はキャッシュとして残し、
  取れなかったときはキャッシュで続行する（--strict で失敗扱い）
- ネットワークが使えない環境用に、ブラウザで取得したバンドル（JSON）からも作れる（--bundle）
"""
import argparse, base64, hashlib, json, re, sys, time, datetime as dt
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SRC = json.loads((ROOT / "src" / "sources.json").read_text(encoding="utf-8"))
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={id}&fileKind={kind}"


def http_get(url, tries=5, base=2.0, opener=urllib.request.urlopen, sleep=time.sleep):
    """指数バックオフ付きの GET。opener と sleep は試験で差し替えられるようにしておく"""
    last = None
    for i in range(tries):
        try:
            with opener(url, timeout=60) as r:
                b = r.read()
            if len(b) < 1000:
                raise IOError(f"too small response ({len(b)} bytes)")
            return b, i + 1
        except Exception as e:  # noqa: BLE001
            last = e
            sleep(base ** i)
    raise RuntimeError(f"failed after {tries} tries: {last}")


def discover_latest_id(cfg):
    """毎月IDが変わる表は、一覧ページから表題で最新の statInfId を探す"""
    html, _ = http_get(cfg["discover_list"])
    html = html.decode("utf-8", "ignore")
    for block in re.split(r"<li", html):
        if cfg["discover_title"] in block:
            m = re.search(r"statInfId=(\d+)", block)
            if m:
                return m.group(1)
    return cfg["statInfId"]


def save(name, data, ext, meta):
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"{name}.{ext}"
    p.write_bytes(data)
    meta[name] = {"file": p.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()[:16]}


def from_bundle(path):
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    meta = {"fetched_at": b["fetched_at"], "mode": "bundle"}
    save("cpi", b["cpi_csv"].encode("utf-8"), "csv", meta)
    save("lfs", base64.b64decode(b["lfs_xlsx_b64"]), "xlsx", meta)
    save("jobs", base64.b64decode(b["jobs_xlsx_b64"]), "xlsx", meta)
    save("wage", b["wage_csv_TL_5plus_all"].encode("utf-8"), "csv", meta)
    return meta


def from_web(strict=False):
    meta = {"fetched_at": dt.datetime.utcnow().isoformat() + "Z", "mode": "web"}
    for name, cfg in SRC.items():
        sid = cfg["statInfId"]
        try:
            if "discover_list" in cfg:
                sid = discover_latest_id(cfg)
            data, n = http_get(URL.format(id=sid, kind=cfg["fileKind"]))
            if cfg["format"] == "csv":
                text = data.decode("cp932", "ignore")
                if name == "wage":  # 1,600万字あるので必要な系列だけ残す
                    lines = text.splitlines()
                    keep = [lines[0]] + [l for l in lines[1:] if (f := l.split(","))[3:6] and f[3].strip() == "TL" and f[4] == "0" and f[5] == "0"]
                    text = "\n".join(keep)
                data = text.encode("utf-8")
            save(name, data, cfg["format"], meta)
            meta[name].update({"statInfId": sid, "tries": n})
        except Exception as e:  # noqa: BLE001
            cache = RAW / f"{name}.{cfg['format']}"
            if strict or not cache.exists():
                raise
            meta[name] = {"file": cache.name, "cached": True, "error": str(e)[:200]}
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    meta = from_bundle(a.bundle) if a.bundle else from_web(a.strict)
    (ROOT / "results" / "fetch_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
