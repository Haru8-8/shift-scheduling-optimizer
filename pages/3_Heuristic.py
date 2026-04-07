# pages/3_Heuristic.py
import streamlit as st
from solvers.heuristic_solver import solve_heuristic
from utils import render_solution_metrics, render_schedule_table, render_shift_summary

st.set_page_config(page_title="ヒューリスティクス", layout="wide")
st.title("ヒューリスティクス（貪欲法 + 局所探索）")

if "problem" not in st.session_state:
    st.warning("トップページで問題を生成してください。")
    st.stop()

prob = st.session_state["problem"]

if st.button("実行", type="primary"):
    with st.spinner("求解中..."):
        sol = solve_heuristic(prob)
    st.session_state["solution_heuristic"] = sol

if "solution_heuristic" in st.session_state:
    sol = st.session_state["solution_heuristic"]
    render_solution_metrics(sol)
    st.divider()
    st.subheader("シフト表")
    render_schedule_table(prob, sol)
    st.divider()
    st.subheader("スタッフ別勤務サマリー")
    render_shift_summary(prob, sol)
else:
    st.info("「実行」ボタンを押してください。")