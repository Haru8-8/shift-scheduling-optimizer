# pages/1_MIP.py
import streamlit as st
from solvers.mip_solver import solve_mip
from utils import render_solution_metrics, render_schedule_table, render_shift_summary

st.set_page_config(page_title="MIP", layout="wide")
st.title("MIP（PuLP + HiGHS）")

if "problem" not in st.session_state:
    st.warning("トップページで問題を生成してください。")
    st.stop()

prob = st.session_state["problem"]

if st.button("実行", type="primary"):
    with st.spinner("求解中..."):
        sol = solve_mip(prob)
    st.session_state["solution_mip"] = sol

if "solution_mip" in st.session_state:
    sol = st.session_state["solution_mip"]
    render_solution_metrics(sol)
    st.divider()
    st.subheader("シフト表")
    render_schedule_table(prob, sol)
    st.divider()
    st.subheader("スタッフ別勤務サマリー")
    render_shift_summary(prob, sol)
else:
    st.info("「実行」ボタンを押してください。")