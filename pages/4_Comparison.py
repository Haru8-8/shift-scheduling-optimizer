# pages/4_Comparison.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from solvers.mip_solver import solve_mip
from solvers.cpsat_solver import solve_cpsat
from solvers.heuristic_solver import solve_heuristic
from utils import render_schedule_table

st.set_page_config(page_title="比較", layout="wide")
st.title("3手法の比較")

if "problem" not in st.session_state:
    st.warning("トップページで問題を生成してください。")
    st.stop()

prob = st.session_state["problem"]

# 未実行の手法だけ実行
missing = []
if "solution_mip" not in st.session_state:
    missing.append("MIP")
if "solution_cpsat" not in st.session_state:
    missing.append("CP-SAT")
if "solution_heuristic" not in st.session_state:
    missing.append("ヒューリスティクス")

if missing:
    st.info(f"未実行の手法: {', '.join(missing)}")
    if st.button("未実行の手法を実行して比較", type="primary"):
        with st.spinner("求解中..."):
            if "solution_mip" not in st.session_state:
                st.session_state["solution_mip"] = solve_mip(prob)
            if "solution_cpsat" not in st.session_state:
                st.session_state["solution_cpsat"] = solve_cpsat(prob)
            if "solution_heuristic" not in st.session_state:
                st.session_state["solution_heuristic"] = solve_heuristic(prob)
        st.rerun()
else:
    sol_mip        = st.session_state["solution_mip"]
    sol_cpsat      = st.session_state["solution_cpsat"]
    sol_heuristic  = st.session_state["solution_heuristic"]
    solutions      = [sol_mip, sol_cpsat, sol_heuristic]

    # -------------------------
    # サマリーテーブル
    # -------------------------
    st.subheader("サマリー")
    df_summary = pd.DataFrame([
        {
            "手法": sol.solver_name,
            "ステータス": sol.status,
            "目的関数値（ペナルティ）": sol.objective,
            "求解時間（秒）": round(sol.solve_time, 3),
        }
        for sol in solutions
    ])
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    # -------------------------
    # グラフ比較
    # -------------------------
    st.divider()
    st.subheader("求解時間の比較")
    fig_time = go.Figure(go.Bar(
        x=[sol.solver_name for sol in solutions],
        y=[sol.solve_time for sol in solutions],
        marker_color=["#AED6F1", "#A9DFBF", "#F9E79F"],
        text=[f"{sol.solve_time:.3f}秒" for sol in solutions],
        textposition="outside",
    ))
    fig_time.update_layout(yaxis_title="求解時間（秒）", showlegend=False)
    st.plotly_chart(fig_time, use_container_width=True)

    st.subheader("目的関数値（ペナルティ）の比較")
    fig_obj = go.Figure(go.Bar(
        x=[sol.solver_name for sol in solutions],
        y=[sol.objective for sol in solutions],
        marker_color=["#AED6F1", "#A9DFBF", "#F9E79F"],
        text=[f"{sol.objective:.2f}" for sol in solutions],
        textposition="outside",
    ))
    fig_obj.update_layout(yaxis_title="ペナルティ", showlegend=False)
    st.plotly_chart(fig_obj, use_container_width=True)

    # -------------------------
    # 各手法のシフト表
    # -------------------------
    st.divider()
    st.subheader("シフト表の比較")
    for sol in solutions:
        st.markdown(f"#### {sol.solver_name}")
        render_schedule_table(prob, sol)