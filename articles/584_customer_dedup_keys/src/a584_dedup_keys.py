"""584 同じ人が別のIDで登録された顧客表を、電話・メール・氏名＋生年月日で寄せると、
顧客数とリピート率はどれだけ変わるのか。架空の顧客表（seed 584）。実在の個人情報は使わない"""
import json
import unicodedata
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "出典：架空の顧客表と注文（作成者が乱数で作成、seed 584）。氏名・電話・メールはすべて架空"
rng = np.random.default_rng(584)

# ---- 1. 架空の人（20,000人）。氏名はありふれた姓・名を組み合わせた架空のもの ----
SEI = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田", "佐々木", "山口", "松本",
       "井上", "木村", "林", "斎藤", "清水", "山崎", "森", "池田", "橋本", "阿部", "石川", "山下", "中島", "石井", "小川"]
MEI = ["翔", "蓮", "大翔", "陽斗", "悠真", "湊", "健太", "大輔", "誠", "浩二", "陽菜", "結衣", "美咲", "葵", "さくら",
       "愛", "優子", "恵", "真由美", "直子", "花子", "太郎", "一郎", "和也", "拓也", "彩", "舞", "裕子", "智子", "明美"]
VARIANT = {"高橋": "髙橋", "山崎": "山﨑", "斎藤": "齋藤", "渡辺": "渡邊"}   # 異体字で登録されることがある
N = 20_000
sei = rng.choice(SEI, N, p=np.linspace(2, 1, len(SEI)) / np.linspace(2, 1, len(SEI)).sum())
mei = rng.choice(MEI, N)
birth = pd.to_datetime("1950-01-01") + pd.to_timedelta(rng.integers(0, 365 * 55, N), unit="D")
mobile = [f"090{rng.integers(10_000_000, 99_999_999)}" for _ in range(N)]
email = [f"user{i:05d}@example.com" for i in range(N)]
# 世帯：30%の人は2〜4人の世帯で、固定電話と家族のメールを共有することがある
hh = np.arange(N); i = 0; hh_id = 0
order_ = rng.permutation(N)
house = np.full(N, -1)
while i < int(N * 0.30):
    k = int(rng.integers(2, 5)); house[order_[i:i + k]] = hh_id; hh_id += 1; i += k
land = {h: f"03{rng.integers(10_000_000, 99_999_999)}" for h in range(hh_id)}
fam_mail = {h: f"family{h:05d}@example.net" for h in range(hh_id)}
person = pd.DataFrame({"person": np.arange(N), "sei": sei, "mei": mei, "birth": birth, "mobile": mobile, "email": email, "house": house})

# ---- 2. 登録（1人が別のIDで2〜3回登録することがある）と表記ゆれ ----
regs = []
for p in person.itertuples():
    n_reg = rng.choice([1, 2, 3], p=[0.82, 0.14, 0.04])
    for r in range(n_reg):
        # 電話：携帯70%／世帯の固定電話15%（世帯がある人）／番号を変えた携帯10%／空5%
        u = rng.random()
        if u < 0.70: ph = p.mobile
        elif u < 0.85: ph = land[p.house] if p.house >= 0 else p.mobile
        elif u < 0.95: ph = f"080{rng.integers(10_000_000, 99_999_999)}"
        else: ph = ""
        if ph and rng.random() < 0.3:    # ハイフンや全角で書かれる
            ph = f"{ph[:3]}-{ph[3:7]}-{ph[7:]}"
            if rng.random() < 0.3: ph = unicodedata.normalize("NFKC", ph).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))
        # メール：いつもの60%／別のアドレス20%／家族のアドレス5%（世帯がある人）／空15%
        u = rng.random()
        if u < 0.60: em = p.email
        elif u < 0.80: em = f"alt{p.person:05d}_{r}@example.org"
        elif u < 0.85: em = fam_mail[p.house] if p.house >= 0 else p.email
        else: em = ""
        if em and rng.random() < 0.1: em = em.upper()
        # 氏名：空白なし・半角空白・全角空白、異体字
        s_ = VARIANT.get(p.sei, p.sei) if (p.sei in VARIANT and rng.random() < 0.25) else p.sei
        nm = s_ + rng.choice(["", " ", "　"]) + p.mei
        # 生年月日：空10%、1日ずれ2%
        u = rng.random()
        bd = "" if u < 0.10 else (p.birth + pd.Timedelta(days=1) if u < 0.12 else p.birth).strftime("%Y-%m-%d")
        regs.append((p.person, nm, bd, ph, em))
reg = pd.DataFrame(regs, columns=["person", "name", "birth_date", "phone", "email"])
reg = reg.sample(frac=1, random_state=584).reset_index(drop=True)
reg.insert(0, "customer_id", [f"C{i + 1:06d}" for i in range(len(reg))])

# ---- 3. 注文（1年）：人ごとの購入回数を、その人の登録のどれかに付ける ----
lam = rng.gamma(0.8, 1.6, N)
n_buy = rng.poisson(lam)
ids_of = reg.groupby("person")["customer_id"].apply(list)
ords = []
for pid, k in enumerate(n_buy):
    ids = ids_of[pid]
    for _ in range(k):
        ords.append(ids[int(rng.integers(0, len(ids)))])
od = pd.DataFrame({"customer_id": ords})
od.insert(0, "order_id", np.arange(1, len(od) + 1))
reg[["customer_id", "name", "birth_date", "phone", "email"]].to_csv(DATA / "customers.csv", index=False)
od.to_csv(DATA / "orders.csv", index=False)
reg[["customer_id", "person"]].to_csv(DATA / "answer_person.csv", index=False)   # 正解（確かめ用）


# ---- 4. 正規化と寄せ方 ----
def norm_phone(x):
    x = unicodedata.normalize("NFKC", x)
    return "".join(c for c in x if c.isdigit())


def norm_name(x):
    x = unicodedata.normalize("NFKC", x).replace(" ", "")
    for a, b in VARIANT.items():
        x = x.replace(b, a)
    return x


reg["k_phone"] = reg["phone"].map(norm_phone).replace("", np.nan)
reg["k_email"] = reg["email"].str.lower().replace("", np.nan)
reg["k_namebirth"] = np.where(reg["birth_date"] != "", reg["name"].map(norm_name) + "|" + reg["birth_date"], np.nan)
reg["k_namebirth"] = reg["k_namebirth"].replace("nan", np.nan)


def cluster(keys):
    parent = np.arange(len(reg))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for k in keys:
        for _, idx in reg.groupby(k).indices.items():
            r0 = find(idx[0])
            for j in idx[1:]:
                rj = find(j)
                if rj != r0: parent[rj] = r0
    return np.array([find(a) for a in range(len(reg))])


ord_n = od.groupby("customer_id").size()
reg["n_orders"] = reg["customer_id"].map(ord_n).fillna(0).astype(int)


def evaluate(lab):
    df = pd.DataFrame({"c": lab, "person": reg["person"], "n": reg["n_orders"]})
    n_cust = df["c"].nunique()
    per_c = df.groupby("c")
    over = int((per_c["person"].nunique() > 1).sum())                    # 別の人が混ざった顧客
    over_regs = int(df[df["c"].map(per_c["person"].nunique()) > 1].shape[0])
    under = int((df.groupby("person")["c"].nunique() > 1).sum())          # 別々のままの人
    buy = per_c["n"].sum(); buy = buy[buy > 0]
    repeat = float((buy >= 2).mean() * 100)
    return {"customers": int(n_cust), "over_merged_customers": over, "regs_in_over_merged": over_regs,
            "persons_split": under, "buyers": int(len(buy)), "repeat_rate_pct": round(repeat, 2)}


METHODS = {"寄せない（IDのまま）": [], "電話": ["k_phone"], "メール": ["k_email"], "氏名＋生年月日": ["k_namebirth"],
           "電話またはメール": ["k_phone", "k_email"], "3つのどれか": ["k_phone", "k_email", "k_namebirth"]}
rows = {}
for name, keys in METHODS.items():
    lab = cluster(keys) if keys else np.arange(len(reg))
    rows[name] = evaluate(lab)
truth = evaluate(reg["person"].to_numpy())
rows["正解（本当の人）"] = truth
tab = pd.DataFrame(rows).T
tab.to_csv(RES / "methods.csv")

# 正規化しないで寄せた場合（電話・氏名）
reg["k_phone_raw"] = reg["phone"].replace("", np.nan)
reg["k_namebirth_raw"] = np.where(reg["birth_date"] != "", reg["name"] + "|" + reg["birth_date"], np.nan)
reg["k_namebirth_raw"] = reg["k_namebirth_raw"].replace("nan", np.nan)
raw = {"電話（正規化なし）": evaluate(cluster(["k_phone_raw"])), "氏名＋生年月日（正規化なし）": evaluate(cluster(["k_namebirth_raw"]))}
pd.DataFrame(raw).T.to_csv(RES / "no_normalize.csv")

# ---- 5. SQL（DuckDB、1スレッド）：電話だけで寄せた顧客数を、正規化してから数える ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE customers AS SELECT * FROM read_csv_auto('{DATA / 'customers.csv'}', all_varchar=true)")
sq = con.execute((SQL / "02_dedup_duckdb.sql").read_text()).fetchone()
sql_match = bool(int(sq[0]) == rows["電話"]["customers"])

res = {"persons_true": N, "registrations": int(len(reg)), "orders": int(len(od)),
       "persons_with_2plus_ids": int((reg.groupby("person").size() > 1).sum()),
       "methods": {k: {kk: (float(vv) if kk == "repeat_rate_pct" else int(vv)) for kk, vv in v.items()} for k, v in rows.items()},
       "no_normalize": raw, "sql_phone_customers": int(sq[0]), "sql_match_python": sql_match}
json.dump(res, open(RES / "a584_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 6. 図 ----
order_m = list(METHODS) + ["正解（本当の人）"]
t = tab.loc[order_m]
fig, ax = plt.subplots(figsize=(9, 4.2))
cols = [GRAY, BLUE, BLUE, BLUE, ORANGE, ORANGE, GREEN]
ax.barh(range(len(t))[::-1], t["customers"], color=cols)
for i, v in enumerate(t["customers"]):
    ax.text(v + 150, len(t) - 1 - i, f"{int(v):,}人（{(v / N - 1) * 100:+.1f}%）", va="center", fontsize=9)
ax.set_yticks(range(len(t))[::-1]); ax.set_yticklabels(t.index)
ax.set_xlim(0, t["customers"].max() * 1.25); ax.set_xlabel("顧客数（かっこ内は本当の人数20,000人との差）")
ax.set_title("どのキーで寄せるかで、顧客数はどれだけ変わるか")
save(fig, "a584_customers.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
ax.barh(range(len(t))[::-1], t["repeat_rate_pct"] - 45, left=45, color=cols)
for i, v in enumerate(t["repeat_rate_pct"]):
    ax.text(v + 0.15, len(t) - 1 - i, f"{v:.1f}%", va="center", fontsize=9)
ax.set_yticks(range(len(t))[::-1]); ax.set_yticklabels(t.index)
ax.axvline(truth["repeat_rate_pct"], color=GREEN, lw=1, ls="--")
ax.set_xlim(45, 60); ax.set_xlabel("リピート率（1年に2回以上買った顧客の割合、%。横軸は45%から）")
ax.set_title("寄せ方で、リピート率はどれだけ変わるか")
save(fig, "a584_repeat.png", SRC)

tt = t.drop(index=["寄せない（IDのまま）", "正解（本当の人）"])
fig, ax = plt.subplots(figsize=(9, 4.2))
y = np.arange(len(tt))[::-1]; h = 0.38
ax.barh(y + h / 2, tt["persons_split"], h, color=BLUE, label="寄せ漏れ：別々の顧客のままの人")
ax.barh(y - h / 2, tt["over_merged_customers"], h, color=ORANGE, label="寄せすぎ：別の人が混ざった顧客")
for yy, a, b in zip(y, tt["persons_split"], tt["over_merged_customers"]):
    ax.text(a + 20, yy + h / 2, f"{int(a):,}", va="center", fontsize=8.5); ax.text(b + 20, yy - h / 2, f"{int(b):,}", va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(tt.index); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_xlabel("件数"); ax.set_title(f"寄せ漏れと寄せすぎ（2つ以上のIDを持つ人は{res['persons_with_2plus_ids']:,}人）")
save(fig, "a584_errors.png", SRC)
