# solvers/mip_solver.py
import time
import pulp
from problem import ShiftProblem, ShiftSolution, EARLY, LATE, NIGHT


def solve_mip(problem: ShiftProblem) -> ShiftSolution:
    """
    MIP（PuLP + HiGHS）でシフトスケジューリング問題を解く。
    """
    N = problem.n_staff
    D = problem.n_days
    S = [EARLY, LATE, NIGHT]
    W = (D + 6) // 7  # 週数（切り上げ）

    start = time.perf_counter()

    # -------------------------
    # ① 決定変数
    # -------------------------
    # x[n][d][s] = 1: スタッフnが日dのシフトsに入る
    x = pulp.LpVariable.dicts(
        "x",
        [(n, d, s) for n in range(N) for d in range(D) for s in S],
        cat="Binary",
    )

    # ソフト制約用の補助変数
    # over[n][w]: スタッフnの第w週の超過勤務日数
    over = pulp.LpVariable.dicts(
        "over",
        [(n, w) for n in range(N) for w in range(W)],
        lowBound=0,
        cat="Continuous",
    )

    # violation[n][d]: 希望休違反（希望休の日に勤務したら1）
    day_off_set = set(problem.day_off_requests)
    violation = pulp.LpVariable.dicts(
        "violation",
        [(n, d) for (n, d) in day_off_set],
        lowBound=0,
        upBound=1,
        cat="Continuous",
    )

    # -------------------------
    # モデル定義
    # -------------------------
    prob = pulp.LpProblem("ShiftScheduling", pulp.LpMinimize)

    # -------------------------
    # ② 目的関数
    # -------------------------
    # ソフト制約違反のペナルティを最小化
    prob += (
        problem.penalty_overwork * pulp.lpSum(over[n, w] for n in range(N) for w in range(W))
        + problem.penalty_day_off * pulp.lpSum(violation[n, d] for (n, d) in day_off_set)
    )

    # -------------------------
    # ③ ハード制約
    # -------------------------

    # 各日・各シフトの必要人数を確保
    for d in range(D):
        for s in S:
            prob += (
                pulp.lpSum(x[n, d, s] for n in range(N)) == problem.required[(d, s)],
                f"required_d{d}_s{s}",
            )

    # 1人1日1シフト
    for n in range(N):
        for d in range(D):
            prob += (
                pulp.lpSum(x[n, d, s] for s in S) <= 1,
                f"one_shift_n{n}_d{d}",
            )

    # 連続夜勤は2日以内（3日連続夜勤の禁止）
    for n in range(N):
        for d in range(D - 2):
            prob += (
                x[n, d, NIGHT] + x[n, d + 1, NIGHT] + x[n, d + 2, NIGHT] <= 2,
                f"no_3consec_night_n{n}_d{d}",
            )

    # -------------------------
    # ④ ソフト制約（補助変数で線形化）
    # -------------------------

    # 週の労働日数上限
    # over[n,w] >= 勤務日数 - max_weekly_shifts （負にはならない）
    for n in range(N):
        for w in range(W):
            week_days = range(w * 7, min((w + 1) * 7, D))
            prob += (
                over[n, w] >= pulp.lpSum(x[n, d, s] for d in week_days for s in S)
                - problem.max_weekly_shifts,
                f"overwork_n{n}_w{w}",
            )

    # 希望休違反
    # violation[n,d] >= sum_s x[n,d,s]（希望休の日に勤務したら1以上になる）
    for (n, d) in day_off_set:
        prob += (
            violation[n, d] >= pulp.lpSum(x[n, d, s] for s in S),
            f"dayoff_n{n}_d{d}",
        )

    # -------------------------
    # ⑤ ソルバー実行
    # -------------------------
    # HiGHSを指定（PuLP 2.8以降はデフォルトだが明示する）
    solver = pulp.HiGHS(msg=False)
    prob.solve(solver)

    solve_time = time.perf_counter() - start

    # -------------------------
    # ⑥ 結果を ShiftSolution に変換
    # -------------------------
    status_map = {
        pulp.LpStatusOptimal:    "optimal",
        pulp.LpStatusInfeasible: "infeasible",
        pulp.LpStatusUnbounded:  "unbounded",
        pulp.LpStatusNotSolved:  "not_solved",
        pulp.LpStatusUndefined:  "undefined",
    }
    status = status_map.get(prob.status, "feasible")

    schedule = {}
    if status in ("optimal", "feasible"):
        for n in range(N):
            for d in range(D):
                for s in S:
                    if pulp.value(x[n, d, s]) > 0.5:
                        schedule[(n, d)] = s
                        break  # 1日1シフトなので見つかったら次の日へ

    objective = pulp.value(prob.objective) or 0.0

    return ShiftSolution(
        solver_name="MIP (PuLP + HiGHS)",
        status=status,
        schedule=schedule,
        objective=objective,
        solve_time=solve_time,
    )


if __name__ == "__main__":
    from problem import make_default_problem

    prob = make_default_problem()
    sol = solve_mip(prob)

    print(f"ステータス : {sol.status}")
    print(f"目的関数値 : {sol.objective:.2f}")
    print(f"求解時間   : {sol.solve_time:.3f} 秒")
    print()

    # スケジュール表示
    shift_label = {0: "早", 1: "遅", 2: "夜", -1: "休"}
    header = "スタッフ＼日 " + " ".join(f"{d+1:2}" for d in range(prob.n_days))
    print(header)
    for n in range(prob.n_staff):
        row = f"  スタッフ{n:2}  "
        for d in range(prob.n_days):
            row += f" {shift_label[sol.get_shift(n, d)]} "
        print(row)