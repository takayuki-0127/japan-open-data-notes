"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
財務省「対外及び対内証券売買契約等の状況」投資家部門別対外証券投資（月次 CSV、Shift_JIS）。"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
BASE = "https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/{}.csv"
FILES = {"monthb1": "合計", "monthb2": "株式・投資ファンド持分", "monthb3": "中長期債", "monthb4": "短期債"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        (RAW / f"{f}.csv").write_bytes(urllib.request.urlopen(urllib.request.Request(BASE.format(f), headers=UA), timeout=120).read())


if __name__ == "__main__":
    main()
