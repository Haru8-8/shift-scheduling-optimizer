# benchmark.py
from problem import make_default_problem
from solvers.mip_solver import solve_mip
from solvers.cpsat_solver import solve_cpsat
from solvers.heuristic_solver import solve_heuristic

for n_staff, n_days in [(8, 14), (20, 30), (50, 60), (100, 90)]:
    prob = make_default_problem(n_staff=n_staff, n_days=n_days)
    print(f"\n=== スタッフ{n_staff}人・{n_days}日 ===")
    for solve_fn in [solve_mip, solve_cpsat, solve_heuristic]:
        sol = solve_fn(prob)
        print(f"  {sol.solver_name:<40} status={sol.status:<12} obj={sol.objective:7.2f}  time={sol.solve_time:.3f}秒")