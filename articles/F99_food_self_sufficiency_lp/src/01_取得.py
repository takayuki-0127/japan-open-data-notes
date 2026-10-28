"""01 取得：政府のサイトはこの環境のスクリプトから直接取れないため、2026-10-28 にブラウザ（e-Stat のページ内）で
ファイルを読み、JSON にまとめて data/raw/ に置いた。ここではその JSON から必要な表を CSV に書き出す。

使った表（e-Stat、statInfId）
- 食料需給表 令和6年度（概算値）年度別食料需給表 ……………… 000040422796（CSV）
- 食料需給表 （参考）総人口及び年度中の日数 ……………………… 000040422793
- 食料需給表 品目別自給率の推移 ………………………………… 000040422876
- 食料需給表 総合自給率等の推移 ………………………………… 000040422877
- 食料需給表 飼料需給表 ……………………………………………… 000040422890
- 作物統計調査 収穫量累年統計（全国）水稲 000040433903／小麦 000040383862／二条大麦 000040383923／
  六条大麦 000040383984／はだか麦 000040384045／大豆 000040384106／かんしょ 000040384167／牧草 000040384224／
  青刈りとうもろこし 000040384281／ソルゴー 000040384338
- 野菜生産出荷統計 作付面積・収穫量累年統計（全国）主要野菜計 000040470473／根菜類 000040470474
- 耕地及び作付面積統計 令和6年 田畑別耕地面積 000040250502／延べ面積（田畑計・田・畑）000040405323〜25／
  飼料用米・WCS用稲 000040308914
水稲・牧草・ソルゴーの2024年の行は f99_raw3.json に写した（表が大きく注記が多いため）。
"""
import json, csv, io
from common import RAW, DATA, num

def rows(text):
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]

if __name__ == "__main__":
    d1 = json.load(open(RAW / "f99_raw1.json", encoding="utf-8"))
    d2 = json.load(open(RAW / "f99_raw2.json", encoding="utf-8"))
    d3 = json.load(open(RAW / "f99_raw3.json", encoding="utf-8"))
    # 1) 食料需給表 2024（概算）
    R = rows(d1["y2024"]); hi = [i for i, r in enumerate(R) if r[0] == "需給品目"][0]
    with open(DATA / "fbs_2024.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(R[hi])
        for r in R[hi + 1:]:
            w.writerow(r)
    # 2) 人口
    P = {r[0]: num(r[1]) for r in rows(d1["pop"]) if r[0].endswith("年度") and r[0][:4].isdigit()}
    # 3) 品目別自給率・総合自給率（2024年度＝最後の列）
    ss = {}
    for key in ["ss_item", "ss_total"]:
        for r in rows(d2[key]):
            if r and r[0] and r[-1].replace(".", "").isdigit():
                ss[r[0]] = num(r[-1])
    # 4) 飼料需給（2024年度概算＝最後の列）
    feed = {r[0]: num(r[-1]) for r in rows(d2["feed"]) if r[0] and "【TDN" in r[0]}
    # 5) 作物（2024年産）
    crops = {}
    def last_year(text, tag="令.6(2024)"):
        for r in rows(text):
            if r[0].startswith(tag):
                return r
    for k, name in [("c_komugi", "小麦"), ("c_nijo", "二条大麦"), ("c_rokujo", "六条大麦"), ("c_hadaka", "はだか麦"),
                    ("c_daizu", "大豆"), ("c_kansho", "かんしょ"), ("c_aogari", "青刈りとうもろこし"),
                    ("c_tensai", "てんさい"), ("c_satokibi", "さとうきび")]:
        r = last_year(d1[k]); crops[name] = dict(area_ha=num(r[1]), yield_kg10a=num(r[2]), harvest_t=num(r[3]))
    r = d3["c_suito_2024"].split(",")
    crops["水稲（子実用）"] = dict(area_ha=num(r[1]), yield_kg10a=num(r[20]), harvest_t=num(r[21]))
    crops["水稲（主食用）"] = dict(area_ha=num(r[2]), yield_kg10a=num(r[20]), harvest_t=num(r[22]))
    r = d3["c_bokuso_2024"].split(","); crops["牧草"] = dict(area_ha=num(r[1]), yield_kg10a=num(r[2]), harvest_t=num(r[3]))
    r = d3["c_sorgo_2024"].split(","); crops["ソルゴー"] = dict(area_ha=num(r[1]), yield_kg10a=num(r[2]), harvest_t=num(r[3]))
    V = rows(d1["v_470474"].split("\n", 1)[1]); h = [x for x in V if x[0] == "年次"][0]; i = h.index("ばれいしょ")
    r = [x for x in V if x[0].startswith("令.6(2024)")][0]
    crops["ばれいしょ"] = dict(area_ha=num(r[i]), harvest_t=num(r[i + 1])); crops["ばれいしょ"]["yield_kg10a"] = crops["ばれいしょ"]["harvest_t"] / crops["ばれいしょ"]["area_ha"] * 100
    V = rows(d1["v_470473"].split("\n", 1)[1]); r = [x for x in V if x[0].startswith("令.6(2024)")][0]
    crops["主要野菜計"] = dict(area_ha=num(r[1]), harvest_t=num(r[2])); crops["主要野菜計"]["yield_kg10a"] = num(r[2]) / num(r[1]) * 100
    F = rows(d1["feedrice"].split("\n", 1)[1]); r = [x for x in F if len(x) > 5 and x[2] == "6" and x[1] == ""][-1]
    crops["飼料用米"] = dict(area_ha=num(r[4])); crops["WCS用稲"] = dict(area_ha=num(r[5]))
    with open(DATA / "crops_2024.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["作物", "作付面積_ha", "10a当たり収量_kg", "収穫量_t"])
        for k, v in crops.items():
            w.writerow([k, v.get("area_ha"), v.get("yield_kg10a"), v.get("harvest_t")])
    # 6) 耕地面積 2024（田・畑）と延べ面積
    K = rows(d1["kouchi"]); r = [x for x in K if x[0] == "全国"][0]
    land = dict(耕地_計=num(r[5]), 田=num(r[6]), 畑=num(r[7]))
    for key, nm in [("nobe_total", "延べ_田畑計"), ("nobe_ta", "延べ_田"), ("nobe_hata", "延べ_畑")]:
        X = rows(d1[key]); hdr = [x for x in X if x[0] == "年次"][0]
        r6 = [x for x in X if len(x) > 4 and x[2].strip() == "6"][-1]
        for j, c in enumerate(hdr):
            if c and j >= 4 and j < len(r6) and r6[j].strip():
                land[nm + "_" + c.replace("\n", "")] = num(r6[j])
    json.dump(dict(population_2024=P["2024年度"], ss=ss, feed=feed, land=land), open(DATA / "misc_2024.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("人口", P["2024年度"], "千人"); print("土地", land); print("飼料", feed)
    print("総合自給率", {k: v for k, v in ss.items() if "総合" in k})
