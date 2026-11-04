from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RAW, RES, FIG): p.mkdir(parents=True, exist_ok=True)
SEED = 191
# 系列（日本銀行 時系列統計データ検索サイト）
SERIES = {
    "MD01": {"MABS1AN11": "mb", "MABS1AN113": "mb_current", "MABS2AN116": "mb_notes"},
    "MD02": {"MAM1NAM2M2MO": "m2_new", "MAM1NAM3M3MO": "m3", "MAMS3ANM2C": "m2cd_old", "MAM1NAM3M1MO": "m1"},
    "MD13": {"FAAPOBAL1": "loan_banks", "FAAPOBSB": "loan_shinkin", "FAAPOBRDCD": "dep_banks"},
    "MD11": {"DLCLBADBLTTO": "loan_dom_avg", "DLCLBEDBLTTO": "loan_dom_end", "DLCLBEDBLTPN": "loan_dom_hh", "DLCLBEDB2STO": "loan_dom_sme"},
}
# 金融緩和の主な出来事（日本銀行の公表に基づく。図の目印用）
EVENTS = [("2001-03", "量的緩和"), ("2006-03", "量的緩和の解除"), ("2013-04", "量的・質的緩和"),
          ("2016-01", "マイナス金利"), ("2020-04", "コロナ対応"), ("2024-03", "マイナス金利の解除")]
