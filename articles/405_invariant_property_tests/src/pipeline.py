"""架空のデータ処理（5段）。bug=None が正しい処理、bug='b01'〜'b20' は誤りを1つ入れた処理。
入力：orders＝[(注文ID, 顧客, 部門, 金額, 状態)]、master＝[(顧客, 地域)]、cost＝按分する費用（円、整数）
決まり（仕様）：
 1 つなぐ：顧客のキーは前後の空白を除いて比べる。マスタに同じ顧客が2行あれば先の行を使う。マスタにない顧客・地域が空の顧客は「不明」
 2 絞る：状態が cancel（大文字小文字は問わない）の注文を除く。状態が空の注文は残す
 3 集計：地域×部門ごとに、件数と金額の合計
 4 按分：費用を金額の割合で分ける（金額がマイナスの区分は0として扱う。全部0なら均等）。円未満は、端数の大きい区分から1円ずつ配り、合計を費用とぴったり合わせる
 5 出力：地域・部門の順に並べ、利益＝金額−按分した費用"""


def run(orders, master, cost, bug=None):
    # 1 つなぐ
    m = {}
    for cust, region in master:
        k = cust if bug == "b05" else cust.strip()
        if bug == "b03": m[k] = region                       # 後の行で上書き
        elif bug == "b02": m.setdefault(k, []).append(region)  # 重複を除かない
        elif k not in m: m[k] = region
    joined = []
    for oid, cust, dept, amt, st in orders:
        k = cust if bug == "b05" else cust.strip()
        if bug == "b02":
            regs = m.get(k, [None])
        else:
            if k not in m:
                if bug == "b01": continue                    # 内部結合：マスタにない顧客の注文が消える
                regs = [None]
            else: regs = [m[k]]
        for r in regs:
            if r is None:
                if bug == "b04": r = None                    # 「不明」に置き換えない
                else: r = "不明"
            joined.append((oid, cust.strip(), dept, amt, st, r))
    # 2 絞る
    kept = []
    for oid, cust, dept, amt, st, r in joined:
        if bug == "b06":
            if st != "done": continue                        # done だけ残す（空の状態が消える）
        elif bug == "b07":
            if st == "cancel": continue                      # 大文字の CANCEL が残る
        else:
            if (st or "").lower() == "cancel": continue
        if bug == "b08" and amt <= 0: continue               # 返品（マイナス）と0円を除いてしまう
        kept.append((oid, cust, dept, amt, st, r))
    # 3 集計
    g, first_dept, custs, order_of = {}, {}, {}, []
    for oid, cust, dept, amt, st, r in kept:
        if r is None: continue                               # キーが空の行は集計から落ちる（pandas の groupby と同じ）
        if bug == "b09":
            dept = first_dept.setdefault(r, dept)            # 地域だけで集計
        key = (r, dept)
        if key not in g: g[key] = [0, 0]; custs[key] = set(); order_of.append(key)
        g[key][0] += 1
        g[key][1] += abs(amt) if bug == "b11" else amt
        custs[key].add(cust)
    if bug == "b10":
        for key in g: g[key][0] = len(custs[key])            # 件数を顧客の数で数える
    keys = order_of if bug == "b16" else sorted(g)
    # 4 按分
    if bug == "b14": w = {k: g[k][0] for k in keys}
    elif bug == "b17": w = {k: g[k][1] for k in keys}
    else: w = {k: max(g[k][1], 0) for k in keys}
    alloc = {k: 0 for k in keys}

    def split(ks, c):
        W = sum(w[k] for k in ks)
        if W == 0:
            if bug == "b20" or not ks: return
            ww = {k: 1 for k in ks}; W = len(ks)
        else: ww = {k: w[k] for k in ks}
        if bug == "b12":
            for k in ks: alloc[k] = int(round(c * ww[k] / W))   # それぞれ四捨五入して終わり
            return
        base = {k: (c * ww[k]) // W for k in ks}
        for k in ks: alloc[k] = base[k]
        if bug == "b13": return                                # 切り捨てて終わり
        rem = c - sum(base.values())
        if bug == "b16":
            if ks: alloc[ks[0]] += rem                         # 端数を最初の行に全部足す
            return
        order = sorted(ks, key=lambda k: (-((c * ww[k]) % W), k))
        for k in order[:rem]: alloc[k] += 1

    if bug == "b15":
        for r in sorted({k[0] for k in keys}): split([k for k in keys if k[0] == r], cost)   # 地域ごとに費用をまるごと配る
    else:
        split(list(keys), cost)
    # 5 出力
    out = []
    for k in sorted(g):
        n, a = g[k]; c = alloc[k]
        out.append((k[0], k[1], n, a, c, a + c if bug == "b18" else a - c))
    if bug == "b19": out = out[:50]                            # 先頭50行で切る
    return out


BUGS = {
 "b01": ("つなぐ", "内部結合にして、マスタにない顧客の注文が消える"),
 "b02": ("つなぐ", "マスタの重複を除かず、行が増える"),
 "b03": ("つなぐ", "マスタの重複で、先の行ではなく後の行を使う"),
 "b04": ("つなぐ", "地域が空の顧客を「不明」にせず、集計から落ちる"),
 "b05": ("つなぐ", "キーの前後の空白を除かず、つながらない（「不明」になる）"),
 "b06": ("絞る", "done だけ残し、状態が空の注文が消える"),
 "b07": ("絞る", "大文字の CANCEL を除かない"),
 "b08": ("絞る", "金額が0以下の行（返品）を除いてしまう"),
 "b09": ("集計", "地域だけで集計し、部門が1つにまとまる"),
 "b10": ("集計", "件数を、行ではなく顧客の数で数える"),
 "b11": ("集計", "返品のマイナスを、絶対値で足す"),
 "b12": ("按分", "区分ごとに四捨五入して、端数を合わせない"),
 "b13": ("按分", "区分ごとに切り捨てて、端数を合わせない"),
 "b14": ("按分", "金額ではなく件数の割合で分ける"),
 "b15": ("按分", "地域ごとに費用をまるごと配る"),
 "b16": ("按分", "端数を、入力で最初に出た区分に全部足す"),
 "b17": ("按分", "金額がマイナスの区分に、マイナスの費用を配る"),
 "b18": ("出力", "利益を、金額＋費用で計算する"),
 "b19": ("出力", "先頭の50行で切る"),
 "b20": ("按分", "金額が全部0のとき、費用を配らない"),
}
