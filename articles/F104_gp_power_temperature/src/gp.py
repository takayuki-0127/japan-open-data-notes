"""ガウス過程回帰（PyTorch で実装、float64）。成分ごとにカーネルを足し合わせる。

成分：
  cal    暦のダミー（曜日・祝日・お盆・年末年始・GW・コロナ期）の線形カーネル（ベイズ線形回帰と同じ）
  trend  時刻の RBF（ゆっくりした水準の変化）
  season 1年周期のカーネル × RBF（季節の形が少しずつ変わってよい）
  short  時刻の Matern 1/2（数日〜数週間続くずれ）
  temp   日平均気温の RBF（または Matern 5/2）
  noise  白色雑音
"""
import math
import numpy as np
import torch

torch.set_default_dtype(torch.float64)
CAL = ["dow1", "dow2", "dow3", "dow4", "dow5", "dow6", "holiday", "obon", "nenmatsu", "gw", "covid"]

INIT = dict(cal_s=0.1, trend_s=0.1, trend_l=3.0, season_s=0.1, season_lp=1.0, season_ld=5.0,
            short_s=0.03, short_l=0.03, temp_s=0.2, temp_l=6.0, noise=0.03, const=0.3)
# 学習の範囲（log をとった値の下限・上限）
BOUNDS = dict(trend_l=(2.0, 30.0), season_ld=(1.0, 50.0), short_l=(2 / 365, 0.25), temp_l=(1.0, 40.0),
              season_lp=(0.1, 10.0), noise=(0.005, 0.5))


class GP:
    def __init__(self, comps, temp_kernel="rbf", cal_cols=CAL, seed=42):
        self.comps = list(comps)
        self.temp_kernel = temp_kernel
        self.cal_cols = cal_cols
        torch.manual_seed(seed)
        p = {}
        for c in self.comps:
            for k, v in INIT.items():
                if k.startswith(c + "_") or k == c:
                    p[k] = v
        p["noise"] = INIT["noise"]
        p["const"] = INIT["const"]
        if "cal" in self.comps:
            p.pop("cal_s", None)
            for col in cal_cols:
                p["cal_" + col] = INIT["cal_s"]
        self.raw = {k: torch.tensor(math.log(v), requires_grad=True) for k, v in p.items()}

    def par(self, k):
        v = torch.exp(self.raw[k])
        if k in BOUNDS:
            lo, hi = BOUNDS[k]
            v = torch.clamp(v, lo, hi)
        return v

    def _X(self, df):
        X = {"t": torch.tensor(df.t.values), "T": torch.tensor(df.temp_mean.values)}
        if "cal" in self.comps:
            C = df.reindex(columns=self.cal_cols, fill_value=0)  # 曲線を描くときなど、暦の列がない表は0で埋める
            X["C"] = torch.tensor(C.values.astype(float))
        return X

    def comp_k(self, c, A, B):
        if c == "cal":
            s = torch.stack([self.par("cal_" + col) for col in self.cal_cols])
            return (A["C"] * s**2) @ B["C"].T
        dt = A["t"][:, None] - B["t"][None, :]
        if c == "trend":
            return self.par("trend_s")**2 * torch.exp(-0.5 * (dt / self.par("trend_l"))**2)
        if c == "season":
            per = torch.exp(-2 * torch.sin(math.pi * dt)**2 / self.par("season_lp")**2)
            return self.par("season_s")**2 * per * torch.exp(-0.5 * (dt / self.par("season_ld"))**2)
        if c == "short":
            return self.par("short_s")**2 * torch.exp(-dt.abs() / self.par("short_l"))
        if c == "temp":
            d = (A["T"][:, None] - B["T"][None, :]).abs() / self.par("temp_l")
            if self.temp_kernel == "rbf":
                return self.par("temp_s")**2 * torch.exp(-0.5 * d**2)
            r = math.sqrt(5) * d
            return self.par("temp_s")**2 * (1 + r + r**2 / 3) * torch.exp(-r)
        raise ValueError(c)

    def K(self, A, B):
        k = self.par("const")**2 * torch.ones(len(A["t"]), len(B["t"]))
        for c in self.comps:
            k = k + self.comp_k(c, A, B)
        return k

    def nll(self):
        K = self.K(self.X, self.X) + (self.par("noise")**2 + 1e-8) * torch.eye(self.n)
        L = torch.linalg.cholesky(K)
        a = torch.cholesky_solve(self.y[:, None], L)
        return 0.5 * (self.y[:, None] * a).sum() + torch.log(torch.diagonal(L)).sum() + 0.5 * self.n * math.log(2 * math.pi)

    def fit(self, df, iters=60, params=None):
        self.X = self._X(df)
        self.ymean = float(df.log_d.mean())
        self.y = torch.tensor(df.log_d.values) - self.ymean
        self.n = len(df)
        if params is not None:  # 保存しておいたハイパーパラメータを使う（最適化しない）
            for k, v in params.items():
                self.raw[k] = torch.tensor(math.log(v), requires_grad=True)
            iters = 0
        opt = torch.optim.LBFGS(list(self.raw.values()), lr=0.5, max_iter=iters, line_search_fn="strong_wolfe")

        def closure():
            opt.zero_grad()
            l = self.nll()
            l.backward()
            return l
        try:
            if iters:
                opt.step(closure)
        except Exception as e:  # 数値が不安定なとき
            print("fit warn", e)
        with torch.no_grad():
            K = self.K(self.X, self.X) + (self.par("noise")**2 + 1e-8) * torch.eye(self.n)
            self.L = torch.linalg.cholesky(K)
            self.alpha = torch.cholesky_solve(self.y[:, None], self.L)
            self.nll_ = float(self.nll())
        return self

    @torch.no_grad()
    def predict(self, df, noise=True):
        Xs = self._X(df)
        Ks = self.K(Xs, self.X)
        m = (Ks @ self.alpha)[:, 0] + self.ymean
        v = torch.cholesky_solve(Ks.T, self.L)
        kss = torch.diagonal(self.K(Xs, Xs))
        var = kss - (Ks * v.T).sum(1)
        if noise:
            var = var + self.par("noise")**2
        return m.numpy(), np.sqrt(np.clip(var.numpy(), 1e-12, None))

    @torch.no_grad()
    def component(self, c, df, n_samples=0, seed=42):
        """訓練データから見た成分 c の事後平均（と事後サンプル）"""
        Xs = self._X(df)
        Kc = self.comp_k(c, Xs, self.X)
        m = (Kc @ self.alpha)[:, 0].numpy()
        if not n_samples:
            return m
        v = torch.cholesky_solve(Kc.T, self.L)
        C = self.comp_k(c, Xs, Xs) - Kc @ v
        C = 0.5 * (C + C.T) + 1e-9 * torch.eye(len(m))
        g = torch.Generator().manual_seed(seed)
        Lc = torch.linalg.cholesky(C)
        z = torch.randn(len(m), n_samples, generator=g)
        return m, (m[:, None] + (Lc @ z).numpy())

    def hyper(self):
        return {k: float(self.par(k).detach()) for k in self.raw}
