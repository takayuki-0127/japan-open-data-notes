import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, FIG
C = {"清算の結了など": "#4C72B0", "合併": "#55A868", "登記官による閉鎖": "#C44E52"}

# 1. 株式会社・有限会社（制度開始時にあった法人）の行き先の累積
cif = pd.read_csv(RES / "old_kk_cif.csv", index_col=0)
import importlib; 
fig, ax = plt.subplots(figsize=(8, 4.6))
x = pd.period_range("2015-10", periods=len(cif), freq="M").to_timestamp()
for k in C: ax.plot(x, cif[k] * 100, color=C[k], lw=2.2, label=k)
ax.set_ylabel("2015年10月にあった株式会社に対する割合（%）"); ax.grid(alpha=.3); ax.legend(frameon=False)
ax.set_title("制度開始時にあった株式会社192万社の行き先（累積）\n登記官による閉鎖は毎年1月に階段状に増え、2025・26年に大きく跳ねた", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f148_old_kk_cif.png"); plt.close()

# 2. 年ごとの件数（すべての種別）
ty = pd.read_csv(RES / "old_yearly_by_kind.csv").groupby("year").sum(numeric_only=True)
ty = ty.loc[2016:2026]
fig, ax = plt.subplots(figsize=(8, 4.6)); b = np.zeros(len(ty))
for k in C:
    ax.bar(ty.index, ty[k] / 1e4, bottom=b, color=C[k], label=k); b += ty[k].values / 1e4
ax.set_ylabel("件数（万件）"); ax.set_xticks(ty.index); ax.legend(frameon=False, loc="upper left"); ax.grid(axis="y", alpha=.3)
ax.set_title("制度開始時にあった法人の、登記がなくなった件数（年ごと）\n2026年は10月まで", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f148_yearly.png"); plt.close()

# 3. 種別ごとの「閉鎖の内訳」
t1 = pd.read_csv(RES / "old_routes_by_kind.csv")
t1 = t1[t1["種別"] != "すべて"].set_index("種別").loc[["株式会社", "有限会社", "合同会社", "合名・合資会社", "一般社団・NPOなど"]]
sh = t1[list(C)].div(t1[list(C)].sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(8, 4.2)); left = np.zeros(len(sh))
for k in C:
    ax.barh(sh.index, sh[k], left=left, color=C[k], label=k)
    for i, v in enumerate(sh[k]):
        if v > 6: ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
    left += sh[k].values
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("登記がなくなった法人のうちの割合（%）")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, 1.0))
ax.set_title("どの道で登記がなくなったか（2015年10月〜2026年10月）", fontsize=11, pad=28)
fig.tight_layout(); fig.savefig(FIG / "f148_kind_share.png"); plt.close()

# 4. 新しく設立された法人の、設立からの年ごとの登記官による閉鎖
hy = pd.read_csv(RES / "new_route3_by_age.csv")
fig, ax = plt.subplots(figsize=(8, 4.4))
for k, col in [("株式会社", "#4C72B0"), ("一般社団・NPOなど", "#DD8452"), ("合同会社", "#8172B2")]:
    g = hy[hy["種別"] == k]; g = g[g["法人年"] > 3000]
    ax.plot(g["設立からの年"], g["1万法人年あたり"], marker="o", color=col, label=k)
ax.set_xlabel("設立からの年（0＝1年目）"); ax.set_ylabel("1万法人・年あたりの件数"); ax.grid(alpha=.3); ax.legend(frameon=False)
ax.set_title("2015年11月以降に設立された法人の「登記官による閉鎖」\n6年目（設立から60〜71か月）の1月に山がある", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f148_new_age.png"); plt.close()

# 5. 復活
ry = pd.read_csv(RES / "revival_by_year.csv"); ry = ry[ry.y.between(2016, 2026)]
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.bar(ry.y, ry.n, color="#937860")
for x_, v in zip(ry.y, ry.n): ax.text(x_, v + 8, str(v), ha="center", fontsize=8)
ax.set_xticks(ry.y); ax.set_ylabel("件数"); ax.grid(axis="y", alpha=.3)
ax.set_title("登記記録が「復活」した法人（最新の処理が復活のもの、年ごと）\nあとで別の変更があった法人は数えられないので下限。2026年は10月まで", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f148_revival.png"); plt.close()
print("ok")
