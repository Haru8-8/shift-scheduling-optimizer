# utils.py
import pandas as pd
import streamlit as st
from problem import ShiftProblem, ShiftSolution, SHIFT_NAMES


SHIFT_COLORS = {
    0: "#AED6F1",   # 早番: 青
    1: "#A9DFBF",   # 遅番: 緑
    2: "#F9E79F",   # 夜勤: 黄
    -1: "#F2F3F4",  # 休み: グレー
}


def render_solution_metrics(sol: ShiftSolution):
    """ステータス・目的関数値・求解時間を表示する。"""
    col1, col2, col3 = st.columns(3)
    col1.metric("ステータス", sol.status)
    col2.metric("目的関数値（ペナルティ）", f"{sol.objective:.2f}")
    col3.metric("求解時間", f"{sol.solve_time:.3f} 秒")


def render_schedule_table(prob: ShiftProblem, sol: ShiftSolution):
    """シフト表をDataFrameで表示する。"""
    shift_label = {0: "早", 1: "遅", 2: "夜", -1: "休"}

    data = {}
    for d in range(prob.n_days):
        col = {}
        for n in range(prob.n_staff):
            col[f"スタッフ{n}"] = shift_label[sol.get_shift(n, d)]
        data[f"{d + 1}日"] = col

    df = pd.DataFrame(data).T
    
    def color_cell(val):
        color_map = {"早": SHIFT_COLORS[0], "遅": SHIFT_COLORS[1], "夜": SHIFT_COLORS[2], "休": SHIFT_COLORS[-1]}
        return f"background-color: {color_map.get(val, '#ffffff')}"

    st.dataframe(
        df.style.map(color_cell),
        use_container_width=True,
    )


def render_shift_summary(prob: ShiftProblem, sol: ShiftSolution):
    """スタッフごとの勤務日数サマリーを表示する。"""
    import pandas as pd
    rows = []
    for n in range(prob.n_staff):
        early = sum(1 for d in range(prob.n_days) if sol.get_shift(n, d) == 0)
        late  = sum(1 for d in range(prob.n_days) if sol.get_shift(n, d) == 1)
        night = sum(1 for d in range(prob.n_days) if sol.get_shift(n, d) == 2)
        total = early + late + night
        rows.append({
            "スタッフ": f"スタッフ{n}",
            "早番": early,
            "遅番": late,
            "夜勤": night,
            "合計勤務日数": total,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)