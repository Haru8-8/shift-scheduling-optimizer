# problem.py
from dataclasses import dataclass, field
import random


# シフト定数
EARLY = 0   # 早番
LATE = 1    # 遅番
NIGHT = 2   # 夜勤
SHIFT_NAMES = {EARLY: "早番", LATE: "遅番", NIGHT: "夜勤"}


@dataclass
class ShiftProblem:
    """
    シフトスケジューリング問題のインスタンス。
    全ソルバーはこのオブジェクトを受け取って解を返す。
    """
    n_staff: int                        # スタッフ数
    n_days: int                         # スケジュール日数
    required: dict[tuple[int,int], int] # required[(d, s)] = 必要人数
    max_weekly_shifts: int = 5          # 週の労働日数上限（ソフト制約）
    day_off_requests: list[tuple[int,int]] = field(default_factory=list)
                                        # [(n, d), ...] 希望休リスト
    penalty_overwork: float = 10.0      # 週上限超過ペナルティ係数
    penalty_day_off: float = 5.0        # 希望休違反ペナルティ係数


def make_default_problem(
    n_staff: int = 8,
    n_days: int = 14,
    seed: int = 42,
) -> ShiftProblem:
    """
    デフォルト問題インスタンスを生成する。
    - 早番2人・遅番2人・夜勤1人／日
    - 希望休をランダムに生成
    """
    # 全日・全シフトの必要人数を設定
    required = {}
    for d in range(n_days):
        required[(d, EARLY)] = 2
        required[(d, LATE)]  = 2
        required[(d, NIGHT)] = 1

    # 希望休をランダム生成（各スタッフが平均2日程度）
    rng = random.Random(seed)
    day_off_requests = []
    for n in range(n_staff):
        n_requests = rng.randint(1, 3)
        days = rng.sample(range(n_days), n_requests)
        for d in days:
            day_off_requests.append((n, d))

    return ShiftProblem(
        n_staff=n_staff,
        n_days=n_days,
        required=required,
        max_weekly_shifts=5,
        day_off_requests=day_off_requests,
        penalty_overwork=10.0,
        penalty_day_off=5.0,
    )


@dataclass
class ShiftSolution:
    """
    ソルバーが返す解の共通フォーマット。
    """
    solver_name: str
    status: str                         # "optimal" / "feasible" / "infeasible"
    schedule: dict[tuple[int,int], int] # schedule[(n, d)] = s (シフト番号) or -1 (休み)
    objective: float                    # 目的関数値（ペナルティ合計）
    solve_time: float                   # 求解時間（秒）

    def get_shift(self, n: int, d: int) -> int:
        """スタッフnの日dのシフトを返す。休みは-1。"""
        return self.schedule.get((n, d), -1)