# app.py
import streamlit as st
from problem import make_default_problem, ShiftProblem, EARLY, LATE, NIGHT

st.set_page_config(page_title="シフトスケジューリング最適化", layout="wide")

st.title("シフトスケジューリング最適化")
st.caption("MIP・CP-SAT・ヒューリスティクスの3手法を比較します")

st.header("問題設定")

col1, col2 = st.columns(2)
with col1:
    n_staff = st.number_input("スタッフ数", min_value=5, max_value=200, value=8, step=1)
    n_days  = st.number_input("スケジュール日数", min_value=7, max_value=180, value=14, step=1)
    seed    = st.number_input("乱数シード", min_value=0, max_value=9999, value=42, step=1)

with col2:
    max_weekly_shifts = st.number_input("週の労働日数上限", min_value=1, max_value=7, value=5, step=1)
    penalty_overwork  = st.number_input("超過勤務ペナルティ係数", min_value=1.0, max_value=100.0, value=10.0, step=1.0)
    penalty_day_off   = st.number_input("希望休違反ペナルティ係数", min_value=1.0, max_value=100.0, value=5.0, step=1.0)

st.subheader("シフト別必要人数（全日共通）")
col3, col4, col5 = st.columns(3)
with col3:
    required_early = st.number_input("早番 必要人数", min_value=1, max_value=50, value=2, step=1)
with col4:
    required_late  = st.number_input("遅番 必要人数", min_value=1, max_value=50, value=2, step=1)
with col5:
    required_night = st.number_input("夜勤 必要人数", min_value=1, max_value=50, value=1, step=1)

# 必要人数の合計がスタッフ数を超えていないか検証
total_required = required_early + required_late + required_night
if total_required > n_staff:
    st.error(f"1日の必要人数合計（{total_required}人）がスタッフ数（{n_staff}人）を超えています。")

if st.button("問題を生成", type="primary", disabled=(total_required > n_staff)):
    # required を全日分設定
    required = {}
    for d in range(int(n_days)):
        required[(d, EARLY)] = int(required_early)
        required[(d, LATE)]  = int(required_late)
        required[(d, NIGHT)] = int(required_night)

    problem = make_default_problem(
        n_staff=int(n_staff),
        n_days=int(n_days),
        seed=int(seed),
    )
    problem.required          = required
    problem.max_weekly_shifts = int(max_weekly_shifts)
    problem.penalty_overwork  = float(penalty_overwork)
    problem.penalty_day_off   = float(penalty_day_off)

    st.session_state["problem"] = problem

    for key in ["solution_mip", "solution_cpsat", "solution_heuristic"]:
        st.session_state.pop(key, None)

    st.success("問題を生成しました。各手法ページで実行してください。")

# 問題が生成済みなら内容を表示
if "problem" in st.session_state:
    prob = st.session_state["problem"]
    st.divider()
    st.subheader("生成済み問題")

    col1, col2, col3 = st.columns(3)
    col1.metric("スタッフ数", prob.n_staff)
    col2.metric("スケジュール日数", prob.n_days)
    col3.metric("週の労働日数上限", prob.max_weekly_shifts)

    col4, col5, col6, col7, col8 = st.columns(5)
    col4.metric("超過勤務ペナルティ", prob.penalty_overwork)
    col5.metric("希望休違反ペナルティ", prob.penalty_day_off)
    col6.metric("早番 必要人数", prob.required[(0, EARLY)])
    col7.metric("遅番 必要人数", prob.required[(0, LATE)])
    col8.metric("夜勤 必要人数", prob.required[(0, NIGHT)])

    st.subheader("希望休一覧")
    if prob.day_off_requests:
        import pandas as pd
        df = pd.DataFrame(prob.day_off_requests, columns=["スタッフ", "日"])
        df["スタッフ"] = df["スタッフ"].apply(lambda n: f"スタッフ{n}")
        df["日"] = df["日"].apply(lambda d: f"{d + 1}日目")
        df = df.sort_values(["スタッフ", "日"]).reset_index(drop=True)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("希望休なし")

    st.divider()
    st.subheader("実行状況")
    col1, col2, col3 = st.columns(3)
    if "solution_mip" in st.session_state:
        col1.success("MIP: 実行済み")
    else:
        col1.warning("MIP: 未実行")
    if "solution_cpsat" in st.session_state:
        col2.success("CP-SAT: 実行済み")
    else:
        col2.warning("CP-SAT: 未実行")
    if "solution_heuristic" in st.session_state:
        col3.success("ヒューリスティクス: 実行済み")
    else:
        col3.warning("ヒューリスティクス: 未実行")
else:
    st.info("パラメータを設定して「問題を生成」ボタンを押してください。")