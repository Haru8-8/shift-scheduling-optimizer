# solvers/cpsat_solver.py
import time
from ortools.sat.python import cp_model
from problem import ShiftProblem, ShiftSolution, EARLY, LATE, NIGHT


def solve_cpsat(problem: ShiftProblem) -> ShiftSolution:
    """
    CP-SAT（OR-Tools）でシフトスケジューリング問題を解く。
    """
    N = problem.n_staff
    D = problem.n_days
    S = [EARLY, LATE, NIGHT]
    W = (D + 6) // 7

    start = time.perf_counter()

    model = cp_model.CpModel()

    # -------------------------
    # ① 決定変数
    # -------------------------
    # x[n][d][s]: BoolVar（CP-SATではBinaryの代わりにBoolVarを使う）
    x = {}
    for n in range(N):
        for d in range(D):
            for s in S:
                x[n, d, s] = model.NewBoolVar(f"x_n{n}_d{d}_s{s}")

    # ソフト制約用補助変数
    # over[n][w]: 週の超過勤務日数（IntVar、0以上）
    over = {}
    for n in range(N):
        for w in range(W):
            over[n, w] = model.NewIntVar(0, 7, f"over_n{n}_w{w}")

    # violation[n][d]: 希望休違反（BoolVar）
    day_off_set = set(problem.day_off_requests)
    violation = {}
    for (n, d) in day_off_set:
        violation[n, d] = model.NewBoolVar(f"violation_n{n}_d{d}")

    # -------------------------
    # ② ハード制約
    # -------------------------

    # 各日・各シフトの必要人数を確保
    for d in range(D):
        for s in S:
            model.Add(
                sum(x[n, d, s] for n in range(N)) == problem.required[(d, s)]
            )

    # 1人1日1シフト
    for n in range(N):
        for d in range(D):
            model.AddAtMostOne(x[n, d, s] for s in S)

    # 連続夜勤は2日以内
    for n in range(N):
        for d in range(D - 2):
            model.Add(
                x[n, d, NIGHT] + x[n, d + 1, NIGHT] + x[n, d + 2, NIGHT] <= 2
            )

    # -------------------------
    # ③ ソフト制約（補助変数で表現）
    # -------------------------

    # 週の労働日数上限
    for n in range(N):
        for w in range(W):
            week_days = range(w * 7, min((w + 1) * 7, D))
            weekly_work = sum(x[n, d, s] for d in week_days for s in S)
            # over[n,w] >= weekly_work - max_weekly_shifts
            # over[n,w]は0以上なので、超過分だけ正の値になる
            model.Add(
                over[n, w] >= weekly_work - problem.max_weekly_shifts
            )

    # 希望休違反
    for (n, d) in day_off_set:
        # violation[n,d] >= sum_s x[n,d,s]
        # BoolVarどうしの和なのでAddMaxEqualityで表現する方がCP-SAT的に自然
        model.AddMaxEquality(
            violation[n, d],
            [x[n, d, s] for s in S]
        )

    # -------------------------
    # ④ 目的関数
    # -------------------------
    # CP-SATの目的関数は整数のみ対応→ペナルティ係数を整数にスケーリング
    penalty_overwork = int(problem.penalty_overwork * 100)
    penalty_day_off  = int(problem.penalty_day_off  * 100)

    model.Minimize(
        penalty_overwork * sum(over[n, w] for n in range(N) for w in range(W))
        + penalty_day_off * sum(violation[n, d] for (n, d) in day_off_set)
    )

    # -------------------------
    # ⑤ ソルバー実行
    # -------------------------
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False
    status_code = solver.Solve(model)

    solve_time = time.perf_counter() - start

    # -------------------------
    # ⑥ 結果変換
    # -------------------------
    status_map = {
        cp_model.OPTIMAL:    "optimal",
        cp_model.FEASIBLE:   "feasible",
        cp_model.INFEASIBLE: "infeasible",
        cp_model.UNKNOWN:    "unknown",
        cp_model.MODEL_INVALID: "model_invalid",
    }
    status = status_map.get(status_code, "unknown")

    schedule = {}
    if status in ("optimal", "feasible"):
        for n in range(N):
            for d in range(D):
                for s in S:
                    if solver.Value(x[n, d, s]) == 1:
                        schedule[(n, d)] = s
                        break

    # 目的関数値はスケーリングを戻す
    objective = solver.ObjectiveValue() / 100.0 if status in ("optimal", "feasible") else 0.0

    return ShiftSolution(
        solver_name="CP-SAT (OR-Tools)",
        status=status,
        schedule=schedule,
        objective=objective,
        solve_time=solve_time,
    )


if __name__ == "__main__":
    from problem import make_default_problem

    prob = make_default_problem()
    sol = solve_cpsat(prob)

    print(f"ステータス : {sol.status}")
    print(f"目的関数値 : {sol.objective:.2f}")
    print(f"求解時間   : {sol.solve_time:.3f} 秒")
    print()

    shift_label = {0: "早", 1: "遅", 2: "夜", -1: "休"}
    header = "スタッフ＼日 " + " ".join(f"{d+1:2}" for d in range(prob.n_days))
    print(header)
    for n in range(prob.n_staff):
        row = f"  スタッフ{n:2}  "
        for d in range(prob.n_days):
            row += f" {shift_label[sol.get_shift(n, d)]} "
        print(row)