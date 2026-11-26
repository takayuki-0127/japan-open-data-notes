"""1299 で使う、箱に荷物が並べて入るかの判定（作成者の作った探し方）

荷物も箱も縦・横・高さが整数（cm）の直方体。荷物は箱の面に平行に置く。
rot="all"：6通りの向きを使ってよい。rot="flat"：上下はそのまま、横に90度回すだけ（天地無用）。

1) fits_one / pair_ok：1つで入るか、2つで入るか（2つまでは、この判定で入る・入らないが確かに決まる）
2) cut_ok：箱を面に平行な平面で2つに切り分け、それぞれに荷物を分けて入れることをくり返す並べ方
   （切り分けられる並べ方）をすべて試す。見つかれば入る。
3) corner_search：切り分けられない並べ方も探すため、置いた荷物の面の位置を組み合わせた所に次の荷物を置く探し方
   （順番・向き・置き場所をすべて試す。試す回数に上限あり）。これで見つからなくても、確かに入らないとは言い切れない
"""
from functools import lru_cache
from itertools import permutations

ORIENT_ALL = list(set(permutations(range(3))))


def orients(item, rot):
    a, b, c = item
    if rot == "all":
        return sorted(set((item[i], item[j], item[k]) for i, j, k in ORIENT_ALL))
    return sorted(set([(a, b, c), (b, a, c)]))   # c が高さ


def key_box(box, rot):
    x, y, z = box
    if rot == "all":
        return tuple(sorted(box))
    return (min(x, y), max(x, y), z)


def key_item(item, rot):
    a, b, c = item
    if rot == "all":
        return tuple(sorted(item))
    return (min(a, b), max(a, b), c)


def fits_one(item, box, rot):
    return any(o[0] <= box[0] and o[1] <= box[1] and o[2] <= box[2] for o in orients(item, rot))


def pair_ok(p, q, box, rot):
    for o in orients(p, rot):
        if not (o[0] <= box[0] and o[1] <= box[1] and o[2] <= box[2]):
            continue
        for r in orients(q, rot):
            if not (r[0] <= box[0] and r[1] <= box[1] and r[2] <= box[2]):
                continue
            if any(o[k] + r[k] <= box[k] for k in range(3)):
                return True
    return False


def vol(t):
    return t[0] * t[1] * t[2]


def make_cut_ok(rot):
    @lru_cache(maxsize=None)
    def cut_ok(box, items):
        # box：key_box の形、items：key_item の形を並べた tuple（並べ替え済み）
        n = len(items)
        if n == 0:
            return True
        if sum(vol(i) for i in items) > vol(box):
            return False
        if n == 1:
            return fits_one(items[0], box, rot)
        if not all(fits_one(i, box, rot) for i in items):
            return False
        for mask in range(1, 1 << n):
            if not (mask & 1) or mask == (1 << n) - 1:
                continue           # 1つ目の荷物を含む側だけを数える（左右の入れかえは同じ）
            s = tuple(items[i] for i in range(n) if mask >> i & 1)
            t = tuple(items[i] for i in range(n) if not mask >> i & 1)
            for ax in range(3):
                L = box[ax]
                if L < 2:
                    continue

                def sub(c):
                    b = list(box); b[ax] = c
                    return key_box(tuple(b), rot)
                # s を入れるのに要る最小の長さ c を二分で探す（長いほど入りやすい）
                lo, hi = 1, L - 1
                if not cut_ok(sub(hi), s):
                    continue
                while lo < hi:
                    mid = (lo + hi) // 2
                    if cut_ok(sub(mid), s):
                        hi = mid
                    else:
                        lo = mid + 1
                if cut_ok(sub(L - lo), t):
                    return True
        return False
    return cut_ok


CUT = {"all": make_cut_ok("all"), "flat": make_cut_ok("flat")}


def corner_search(items, box, rot, limit=3000000):
    """置いた荷物の面の位置（縦・横・高さそれぞれ、0か、置いた荷物の向こう側の面）を組み合わせた所に次を置く探し方。
    荷物の順番・向き・置き場所をすべて試す。見つかれば True、試しきって無ければ False、上限で None"""
    placed = []
    order = []
    seen = set()
    cnt = [0]
    ors = [orients(it, rot) for it in items]

    def overlap(p, q):
        return all(p[0][k] < q[0][k] + q[1][k] and q[0][k] < p[0][k] + p[1][k] for k in range(3))

    def rec(left):
        if not left:
            return True
        st = frozenset(zip(order, placed))
        if st in seen:
            return False
        seen.add(st)
        xs = sorted({0} | {p[0] + d[0] for p, d in placed})
        ys = sorted({0} | {p[1] + d[1] for p, d in placed})
        zs = sorted({0} | {p[2] + d[2] for p, d in placed})
        for i in left:
            for o in ors[i]:
                for x in xs:
                    if x + o[0] > box[0]:
                        continue
                    for y in ys:
                        if y + o[1] > box[1]:
                            continue
                        for z in zs:
                            if z + o[2] > box[2]:
                                continue
                            cnt[0] += 1
                            if cnt[0] > limit:
                                raise TimeoutError
                            cand = ((x, y, z), o)
                            if any(overlap(cand, q) for q in placed):
                                continue
                            placed.append(cand); order.append(i)
                            if rec([j for j in left if j != i]):
                                return True
                            placed.pop(); order.pop()
        return False
    try:
        return rec(list(range(len(items))))
    except TimeoutError:
        return None


def judge(items, box, rot):
    """戻り値：'single'（1つで入らない荷物がある）/'pair'（2つの組で入らない）/'fit'（切り分けで入る）
    /'fit_corner'（切り分けでは無く、角の探し方で入る）/'nf_search'（角の探し方を試しきって無い）/'unknown'"""
    if not all(fits_one(i, box, rot) for i in items):
        return "single"
    n = len(items)
    for a in range(n):
        for b in range(a + 1, n):
            if not pair_ok(items[a], items[b], box, rot):
                return "pair"
    kb = key_box(box, rot)
    ki = tuple(sorted(key_item(i, rot) for i in items))
    if CUT[rot](kb, ki):
        return "fit"
    if n <= 2:
        return "pair"
    r = corner_search(items, box, rot)
    if r is True:
        return "fit_corner"
    if r is False:
        return "nf_search"
    return "unknown"
