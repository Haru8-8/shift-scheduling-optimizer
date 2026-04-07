# solvers/heuristic_solver.py
import time
import random
from problem import ShiftProblem, ShiftSolution, EARLY, LATE, NIGHT


def solve_heuristic(problem: ShiftProblem, seed: int = 0, max_iter: int = 200, n_neighbors: int = 200) -> ShiftSolution:
    """
    優先度ルール（貪欲法）+ 局所探索でシフトスケジューリング問題を解く。
    差分計算・近傍サンプリング・反復制限により大規模問題にも対応。
    """
    N = problem.n_staff
    D = problem.n_days
    S = [EARLY, LATE, NIGHT]
    W = (D + 6) // 7

    start = time.perf_counter()
    rng = random.Random(seed)
    day_off_set = set(problem.day_off_requests)

    # -------------------------
    # ユーティリティ関数
    # -------------------------

    def week_of(d: int) -> int:
        return d // 7

    def calc_penalty(schedule: dict) -> float:
        """ソフト制約違反のペナルティを計算する（初期解構築時に使用）。"""
        penalty = 0.0
        for n in range(N):
            for w in range(W):
                week_days = range(w * 7, min((w + 1) * 7, D))
                work = sum(1 for d in week_days if schedule.get((n, d), -1) != -1)
                penalty += problem.penalty_overwork * max(0, work - problem.max_weekly_shifts)
        for (n, d) in day_off_set:
            if schedule.get((n, d), -1) != -1:
                penalty += problem.penalty_day_off
        return penalty

    def is_hard_feasible(schedule: dict) -> bool:
        """ハード制約をすべて満たしているか検証する（初期解構築後の確認に使用）。"""
        for d in range(D):
            for s in S:
                count = sum(1 for n in range(N) if schedule.get((n, d)) == s)
                if count != problem.required[(d, s)]:
                    return False
        for n in range(N):
            for d in range(D - 2):
                nights = sum(
                    1 for dd in (d, d + 1, d + 2)
                    if schedule.get((n, dd)) == NIGHT
                )
                if nights >= 3:
                    return False
        return True

    def can_assign(schedule: dict, n: int, d: int, s: int) -> bool:
        """スタッフnを日dのシフトsに割り当て可能か（ハード制約のみ）。"""
        if (n, d) in schedule:
            return False
        if s == NIGHT:
            consecutive = sum(
                1 for dd in range(max(0, d - 2), d)
                if schedule.get((n, dd)) == NIGHT
            )
            if consecutive >= 2:
                return False
        return True

    def priority_score(schedule: dict, n: int, d: int, s: int) -> float:
        score = 0.0
        if (n, d) in day_off_set:
            score += problem.penalty_day_off
        w = week_of(d)
        week_days = range(w * 7, min((w + 1) * 7, D))
        work = sum(1 for dd in week_days if schedule.get((n, dd), -1) != -1)
        score += problem.penalty_overwork * max(0, work + 1 - problem.max_weekly_shifts)
        score += rng.uniform(0, 0.01)
        return score

    # -------------------------
    # 差分計算
    # -------------------------

    def delta_dayoff(n1: int, n2: int, d: int, s1: int, s2: int) -> float:
        """希望休違反ペナルティの変化量を計算する。"""
        before = 0.0
        after = 0.0
        if (n1, d) in day_off_set:
            if s1 != -1:
                before += problem.penalty_day_off
            if s2 != -1:
                after += problem.penalty_day_off
        if (n2, d) in day_off_set:
            if s2 != -1:
                before += problem.penalty_day_off
            if s1 != -1:
                after += problem.penalty_day_off
        return after - before

    def delta_overwork(schedule: dict, n: int, d: int, s_before: int, s_after: int) -> float:
        """週の超過勤務ペナルティの変化量を計算する。"""
        # シフト↔シフトの交換は勤務日数が変わらない
        if s_before != -1 and s_after != -1:
            return 0.0
        work_delta = 1 if s_before == -1 else -1
        w = week_of(d)
        week_days = range(w * 7, min((w + 1) * 7, D))
        current_work = sum(1 for dd in week_days if schedule.get((n, dd), -1) != -1)
        before = max(0, current_work - problem.max_weekly_shifts)
        after  = max(0, current_work + work_delta - problem.max_weekly_shifts)
        return problem.penalty_overwork * (after - before)

    def delta_penalty(schedule: dict, n1: int, n2: int, d: int, s1: int, s2: int) -> float:
        """交換によるペナルティ変化量の合計を計算する。"""
        return (
            delta_dayoff(n1, n2, d, s1, s2)
            + delta_overwork(schedule, n1, d, s1, s2)
            + delta_overwork(schedule, n2, d, s2, s1)
        )

    def is_swap_hard_feasible(schedule: dict, n1: int, n2: int, d: int, s1: int, s2: int) -> bool:
        """
        交換後にハード制約を満たすか差分チェックする。
        必要人数は同日・同シフト内の交換なので変わらない。
        連続夜勤のみチェックする。
        """
        # 夜勤が関係しない交換はOK
        if s1 != NIGHT and s2 != NIGHT:
            return True

        def check_consecutive_night(n: int, d: int, new_shift: int) -> bool:
            """スタッフnの日dをnew_shiftに変えたとき連続夜勤制約を満たすか。"""
            # d-2〜d+2の範囲を確認
            for start_d in range(max(0, d - 2), min(D - 2, d + 1)):
                nights = 0
                for dd in range(start_d, start_d + 3):
                    if dd == d:
                        nights += 1 if new_shift == NIGHT else 0
                    else:
                        nights += 1 if schedule.get((n, dd)) == NIGHT else 0
                if nights >= 3:
                    return False
            return True

        # n1: s1→s2、n2: s2→s1 に変えた場合をチェック
        if not check_consecutive_night(n1, d, s2):
            return False
        if not check_consecutive_night(n2, d, s1):
            return False
        return True

    # -------------------------
    # ① 貪欲法で初期解を構築
    # -------------------------
    schedule: dict[tuple[int, int], int] = {}

    for d in range(D):
        for s in S:
            needed = problem.required[(d, s)]
            candidates = [n for n in range(N) if can_assign(schedule, n, d, s)]
            candidates.sort(key=lambda n: priority_score(schedule, n, d, s))
            for n in candidates[:needed]:
                schedule[(n, d)] = s

    # -------------------------
    # ② 局所探索で改善
    # -------------------------
    current_penalty = calc_penalty(schedule)
    all_pairs = [(n1, n2) for n1 in range(N) for n2 in range(n1 + 1, N)]

    for _ in range(max_iter):
        improved = False

        # 日・スタッフペアをランダムサンプリング
        sampled_days = rng.choices(range(D), k=n_neighbors)
        sampled_pairs = rng.choices(all_pairs, k=n_neighbors)

        for d, (n1, n2) in zip(sampled_days, sampled_pairs):
            s1 = schedule.get((n1, d), -1)
            s2 = schedule.get((n2, d), -1)

            if s1 == s2:
                continue

            # 差分でペナルティ変化量を計算
            delta = delta_penalty(schedule, n1, n2, d, s1, s2)
            if delta >= 0:
                continue

            # ハード制約の差分チェック
            if not is_swap_hard_feasible(schedule, n1, n2, d, s1, s2):
                continue

            # 交換を適用
            if s2 == -1:
                del schedule[(n1, d)]
            else:
                schedule[(n1, d)] = s2
            if s1 == -1:
                del schedule[(n2, d)]
            else:
                schedule[(n2, d)] = s1

            current_penalty -= delta  # deltaは負なので引くと減少
            improved = True

        if not improved:
            break

    solve_time = time.perf_counter() - start

    status = "feasible" if is_hard_feasible(schedule) else "infeasible"
    objective = calc_penalty(schedule)

    return ShiftSolution(
        solver_name="Heuristic (Greedy + Local Search)",
        status=status,
        schedule=schedule,
        objective=objective,
        solve_time=solve_time,
    )


if __name__ == "__main__":
    from problem import make_default_problem

    prob = make_default_problem()
    sol = solve_heuristic(prob)

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