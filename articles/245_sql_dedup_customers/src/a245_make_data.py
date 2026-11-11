"""245：重複の入った架空の顧客表を乱数で作る（正解の人IDつき）。seed 245
重複の種類：そのままの二重登録／名前の空白の違い／電話のハイフンの違い／メールの大文字小文字／電話かメールが変わった／姓が変わった
別人どうしで「名前と生年月日」が同じ組も少し入れる。重複の行の15%はメールも変わっている"""
import numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(245)
sei = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水"]
mei = ["翔太", "大輔", "健太", "拓也", "直樹", "美咲", "陽子", "彩", "優子", "真由美", "誠", "亮", "愛", "恵", "裕子", "和也", "達也", "舞", "結衣", "蓮"]
P = 6000
people = []
for pid in range(1, P + 1):
    s, m = rng.choice(sei), rng.choice(mei)
    bd = pd.Timestamp("1955-01-01") + pd.Timedelta(days=int(rng.integers(0, 365 * 48)))
    tel = f"0{rng.integers(70, 91)}{rng.integers(1000, 9999)}{rng.integers(1000, 9999)}"
    email = f"user{pid:05d}@example.com"
    people.append(dict(person_id=pid, sei=s, mei=m, birth=bd.date(), tel=tel, email=email))
# 別人で名前と生年月日が同じ組を作る（40組）
for k in range(40):
    a, b = people[k * 2], people[k * 2 + 1]
    b["sei"], b["mei"], b["birth"] = a["sei"], a["mei"], a["birth"]
rows = []


def fmt_tel(t, style):
    return {0: t, 1: f"{t[:3]}-{t[3:7]}-{t[7:]}", 2: f"{t[:3]} {t[3:7]} {t[7:]}"}[style]


for p in people:
    rows.append(dict(person_id=p["person_id"], name=p["sei"] + " " + p["mei"], birth=p["birth"], tel=fmt_tel(p["tel"], 1),
                     email=p["email"], dup_type="元の行", updated_at=pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 365)))))
types = ["そのまま二重", "名前の空白", "電話の書き方", "メールの大文字", "電話が変わった", "姓が変わった"]
probs = [0.25, 0.2, 0.2, 0.15, 0.12, 0.08]
ndup = int(P * 0.15)
for pid in rng.choice(np.arange(1, P + 1), ndup, replace=False):
    p = people[pid - 1]; base = rows[pid - 1].copy(); t = rng.choice(types, p=probs)
    r = base.copy(); r["dup_type"] = t
    r["updated_at"] = base["updated_at"] + pd.Timedelta(days=int(rng.integers(30, 900)))
    if t == "名前の空白": r["name"] = p["sei"] + rng.choice(["　", "", "  "]) + p["mei"] + rng.choice(["", " "])
    if t == "電話の書き方": r["tel"] = fmt_tel(p["tel"], int(rng.choice([0, 2])))
    if t == "メールの大文字": r["email"] = p["email"].upper() if rng.random() < .5 else p["email"].capitalize()
    if t == "電話が変わった": r["tel"] = fmt_tel(f"0{rng.integers(70, 91)}{rng.integers(1000, 9999)}{rng.integers(1000, 9999)}", 1)
    if t == "姓が変わった": r["name"] = rng.choice([x for x in sei if x != p["sei"]]) + " " + p["mei"]
    if rng.random() < 0.3: r["tel"] = None  # 新しい行で電話が空（入力しなかった）
    if t != "メールの大文字" and rng.random() < 0.15: r["email"] = f"new{int(rng.integers(0, 10**6)):06d}@example.net"  # メールも変わった
    rows.append(r)
df = pd.DataFrame(rows).sample(frac=1, random_state=245).reset_index(drop=True)
df.insert(0, "customer_id", np.arange(1, len(df) + 1))
df.to_csv(DATA / "customers.csv", index=False)
print(len(df), df.dup_type.value_counts().to_dict(), df.tel.isna().sum())
