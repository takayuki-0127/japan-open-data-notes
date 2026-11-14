"""代表的な短い記事を流し直し、結果がリポジトリと一致するかを確かめるテスト（pytest）。"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import repro_check as rc

QUICK = [601, 641, 662, 701, 742, 793]  # SQL と集計の落とし穴（数秒で終わるもの）
T = {no: (no, d, m) for no, d, m in rc.targets()}


@pytest.mark.parametrize("no", QUICK)
def test_article_reproduces(no):
    assert no in T, f"{no} の記事フォルダが見つからない"
    r = rc.check(*T[no])
    assert r["ok"], r["detail"]


def test_close_tolerates_tiny_float_noise():
    assert rc.close({"a": 1.0, "b": [1, 2.0000000001]}, {"a": 1.0000000001, "b": [1, 2.0]})
    assert not rc.close({"a": 1.0}, {"a": 1.01})
