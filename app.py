import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="精密採点Ai 安定性シミュレーター", layout="wide")

# ---------------------------------------------------------
# 1. セッションステートの初期化（状態の保持）
# ---------------------------------------------------------
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "ピッチ加点"
elif st.session_state.current_mode in ["揺れの規則性加点", "悪いビブラート減点"]:
    st.session_state.current_mode = "揺れの規則性&悪いビブ"

# --- 全体設定用ステート ---
if "total_frame" not in st.session_state:
    st.session_state.total_frame = 10000

# --- ピッチ加点用ステート ---
if "pitch_items" not in st.session_state:
    st.session_state.pitch_items = [
        {"id": 0, "diff": 0, "frames": 1000},
        {"id": 1, "diff": 10, "frames": 0},
        {"id": 2, "diff": 20, "frames": 0},
        {"id": 3, "diff": 30, "frames": 0},
        {"id": 4, "diff": 40, "frames": 0},
        {"id": 5, "diff": 50, "frames": 0},
    ]
    st.session_state.next_id = 6
else:
    for i, item in enumerate(st.session_state.pitch_items):
        if "id" not in item:
            item["id"] = i
    if "next_id" not in st.session_state:
        st.session_state.next_id = len(st.session_state.pitch_items)

# --- 揺れの規則性用ステート ---
if "thd_items" not in st.session_state:
    st.session_state.thd_items = [
        {"id": 0, "thd": 0, "frames": 1000},
        {"id": 1, "thd": 2, "frames": 0},
        {"id": 2, "thd": 5, "frames": 0},
        {"id": 3, "thd": 20, "frames": 0},
        {"id": 4, "thd": 40, "frames": 0},
    ]
    st.session_state.next_thd_id = 5
else:
    for i, item in enumerate(st.session_state.thd_items):
        if "id" not in item:
            item["id"] = i
        if "count" in item:
            item["frames"] = item.pop("count")
    if "next_thd_id" not in st.session_state:
        st.session_state.next_thd_id = len(st.session_state.thd_items)

# --- ピッチ加点用コールバック ---
def update_pitch_item(item_id):
    for item in st.session_state.pitch_items:
        if item["id"] == item_id:
            item["diff"] = st.session_state[f"diff_input_{item_id}"]
            item["frames"] = st.session_state[f"frames_input_{item_id}"]
            break
    st.session_state.pitch_items.sort(key=lambda x: x["diff"])

def add_pitch_item():
    st.session_state.pitch_items.append({"id": st.session_state.next_id, "diff": 0, "frames": 0})
    st.session_state.next_id += 1
    st.session_state.pitch_items.sort(key=lambda x: x["diff"])

def remove_pitch_item(item_id):
    st.session_state.pitch_items = [item for item in st.session_state.pitch_items if item["id"] != item_id]
    if f"diff_input_{item_id}" in st.session_state: del st.session_state[f"diff_input_{item_id}"]
    if f"frames_input_{item_id}" in st.session_state: del st.session_state[f"frames_input_{item_id}"]

# --- 揺れの規則性用コールバック ---
def update_thd_item(item_id):
    for item in st.session_state.thd_items:
        if item["id"] == item_id:
            item["thd"] = st.session_state[f"thd_input_{item_id}"]
            item["frames"] = st.session_state[f"thd_frames_input_{item_id}"]
            break
    st.session_state.thd_items.sort(key=lambda x: x["thd"])

def add_thd_item():
    st.session_state.thd_items.append({"id": st.session_state.next_thd_id, "thd": 0, "frames": 0})
    st.session_state.next_thd_id += 1
    st.session_state.thd_items.sort(key=lambda x: x["thd"])

def remove_thd_item(item_id):
    st.session_state.thd_items = [item for item in st.session_state.thd_items if item["id"] != item_id]
    if f"thd_input_{item_id}" in st.session_state: del st.session_state[f"thd_input_{item_id}"]
    if f"thd_frames_input_{item_id}" in st.session_state: del st.session_state[f"thd_frames_input_{item_id}"]

# ---------------------------------------------------------
# 2. 計算ロジック
# ---------------------------------------------------------
def calculate_secret_pitch_bonus(items):
    note_good_count, note_bad_count, note_penalty_frame_count, note_penalty_weighted_count = 0, 0, 0, 0
    for item in items:
        diff = item["diff"]
        frames = item["frames"]
        if diff < 0 or diff > 50: continue

        if diff <= 15: note_good_count += 10 * frames
        elif 16 <= diff <= 24: note_good_count += (25 - diff) * frames
        if diff >= 25: note_bad_count += 10 * frames

        note_penalty_frame_count += frames
        note_penalty_weighted_count += diff * frames

    total_good_bad = note_good_count + note_bad_count
    if total_good_bad == 0: pitch_bonus = 0.0
    else: pitch_bonus = math.floor((note_good_count / total_good_bad) * 1000) * 40

    return note_good_count, note_bad_count, note_penalty_frame_count, note_penalty_weighted_count, pitch_bonus

def calculate_secret_thd_bonus(items, total_frame):
    thd_good_count = 0
    thd_bad_count = 0
    thd_penalty_frame_count = 0
    histogram_samples = 0
    
    valid_thd_list = []

    for item in items:
        thd = item["thd"]
        frames = item["frames"]
        
        if thd < 0 or thd > 49: continue
        
        valid_thd_list.append({"thd": thd, "frames": frames})
        
        if 0 <= thd <= 12: thd_good_count += frames
        elif 13 <= thd <= 40: thd_bad_count += frames

        if 0 <= thd <= 49:
            thd_penalty_frame_count += frames
            histogram_samples += frames

    total_good_bad = thd_good_count + thd_bad_count
    if total_good_bad == 0: 
        thd_bonus = 0.0
    else: 
        ratio = thd_good_count / total_good_bad
        thd_bonus = math.floor(ratio * 1000) * 24

    thd_median = 0.0
    if histogram_samples > 0:
        valid_thd_list.sort(key=lambda x: x["thd"])
        cumulative = 0
        
        if histogram_samples % 2 != 0:
            target = histogram_samples // 2
            for item in valid_thd_list:
                cumulative += item["frames"]
                if cumulative > target:
                    thd_median = float(item["thd"])
                    break
        else:
            target1 = histogram_samples // 2 - 1
            target2 = histogram_samples // 2
            val1, val2 = -1, -1
            for item in valid_thd_list:
                cumulative += item["frames"]
                if val1 == -1 and cumulative > target1:
                    val1 = item["thd"]
                if val2 == -1 and cumulative > target2:
                    val2 = item["thd"]
                if val1 != -1 and val2 != -1:
                    thd_median = (val1 + val2) / 2.0
                    break

    if total_frame == 0:
        bad_vib_penalty = 0.0
    else:
        ratio_penalty = thd_penalty_frame_count / total_frame
        bad_vib_penalty = math.floor(ratio_penalty * thd_median * 100) * 40

    return thd_good_count, thd_bad_count, thd_penalty_frame_count, histogram_samples, thd_bonus, thd_median, bad_vib_penalty

def furue_to_stability(furue):
    if furue < 10000:
        return (furue / 10000) * 35.0
    elif furue < 45000:
        return 35.0 + ((furue - 10000) / 35000) * 40.0
    elif furue < 65000:
        return 75.0 + ((furue - 45000) / 20000) * 10.0
    elif furue < 85000:
        return 85.0 + ((furue - 65000) / 20000) * 8.0
    else:
        return 93.0 + ((furue - 85000) / 15000) * 7.0
    
def get_furue_table():
    return pd.DataFrame({
        "Furue値": ["～ 10,000", "10,000 ～ 45,000", "45,000 ～ 65,000", "65,000 ～ 85,000", "85,000 ～"],
        "安定性点数": ["0 ～ 35.0", "35.0 ～ 75.0", "75.0 ～ 85.0", "85.0 ～ 93.0", "93.0 ～ 100.0"]
    }).T


# ---------------------------------------------------------
# 3. 画面上部のモード切り替えボタン群
# ---------------------------------------------------------
st.title("🎤 精密採点Ai 安定性シミュレーター")

modes = ["全体を見る", "ピッチ加点", "揺れの規則性&悪いビブ", "第二の減点"]
cols = st.columns(len(modes))

for i, mode in enumerate(modes):
    with cols[i]:
        button_type = "primary" if st.session_state.current_mode == mode else "secondary"
        if st.button(mode, type=button_type, use_container_width=True):
            st.session_state.current_mode = mode
            st.rerun()

st.divider()

# ---------------------------------------------------------
# 4. 各モードごとの画面描画
# ---------------------------------------------------------
if st.session_state.current_mode == "ピッチ加点":
    st.header("🎵 ピッチ加点 設定")
    st.markdown("各PitchDiffとフレーム数を設定してください。（PitchDiffの値は0〜50の範囲で自由に編集でき、項目の増減も可能です）")

    left_col, right_col = st.columns([4.5, 5.5])

    with left_col:
        st.subheader("入力パラメータ")
        col_color, col_diff, col_slider, col_del = st.columns([0.3, 1.2, 3.2, 0.5])
        with col_diff: st.markdown("**PitchDiff**")
        with col_slider: st.markdown("**フレーム数**")

        for item in st.session_state.pitch_items:
            item_id, diff_val, frames_val = item["id"], item["diff"], item["frames"]
            is_invalid = diff_val < 0 or diff_val > 50

            if is_invalid: color = "#9E9E9E"
            elif diff_val <= 15: color = "#4CAF50"
            elif 16 <= diff_val <= 24: color = "#FFC107"
            else: color = "#F44336"
            
            col_color, col_diff, col_slider, col_del = st.columns([0.3, 1.2, 3.2, 0.5])
            with col_color:
                st.markdown(f"<div style='width: 14px; height: 14px; border-radius: 50%; background-color: {color}; margin-top: 12px; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
            with col_diff:
                st.number_input("Diff", value=diff_val, step=1, key=f"diff_input_{item_id}", label_visibility="collapsed", on_change=update_pitch_item, args=(item_id,))
            with col_slider:
                st.slider("Frames", min_value=0, max_value=10000, value=frames_val, step=100, key=f"frames_input_{item_id}", label_visibility="collapsed", on_change=update_pitch_item, args=(item_id,))
            with col_del:
                st.button("✖", key=f"del_btn_{item_id}", help="この行を削除", on_click=remove_pitch_item, args=(item_id,))

            if is_invalid:
                st.warning(f"⚠️ 0〜50の範囲で入力してください。(この行は計算から除外されます)")

        st.button("➕ PitchDiffを追加", on_click=add_pitch_item)

    with right_col:
        st.subheader("各パラメータの内訳")
        table_data = []
        valid_frames_total = 0

        for item in st.session_state.pitch_items:
            diff, val = item["diff"], item["frames"]
            if diff < 0 or diff > 50:
                table_data.append({"PitchDiff": f"Diff = {diff} (無効)", "フレーム": val, "Good": "-", "Bad": "-", "PenFrame": "-", "PenWeight": "-"})
                continue
            
            valid_frames_total += val
            good = 10 * val if diff <= 15 else ((25 - diff) * val if 16 <= diff <= 24 else 0)
            bad = 10 * val if diff >= 25 else 0
            
            table_data.append({"PitchDiff": f"Diff = {diff}", "フレーム": val, "Good": good, "Bad": bad, "PenFrame": val, "PenWeight": diff * val})
        
        good_cnt, bad_cnt, pen_frame_cnt, pen_weight_cnt, final_bonus = calculate_secret_pitch_bonus(st.session_state.pitch_items)

        table_data.append({"PitchDiff": "合計", "フレーム": valid_frames_total, "Good": good_cnt, "Bad": bad_cnt, "PenFrame": pen_frame_cnt, "PenWeight": pen_weight_cnt})
        df = pd.DataFrame(table_data)

        def style_pitchdiff(val):
            val_str = str(val)
            if "無効" in val_str: return 'color: #9E9E9E; text-decoration: line-through;'
            elif val_str.startswith("Diff = "):
                try:
                    d = int(val_str.split("=")[1].strip())
                    if d <= 15: return 'color: #4CAF50; font-weight: bold;'
                    elif 16 <= d <= 24: return 'color: #FFC107; font-weight: bold;'
                    else: return 'color: #F44336; font-weight: bold;'
                except: pass
            elif val_str == "合計": return 'font-weight: bold;'
            return ''

        try: styled_df = df.style.map(style_pitchdiff, subset=["PitchDiff"])
        except AttributeError: styled_df = df.style.applymap(style_pitchdiff, subset=["PitchDiff"])

        def format_number(x): return f"{int(x):,}" if isinstance(x, (int, float)) else x
        for col in ["フレーム", "Good", "Bad", "PenFrame", "PenWeight"]: styled_df = styled_df.format({col: format_number})
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("算出パラメータ ＆ 結果")
    res_cols = st.columns(5)
    res_cols[0].metric("NoteGoodCount", f"{good_cnt:,}")
    res_cols[1].metric("NoteBadCount", f"{bad_cnt:,}")
    res_cols[2].metric("NotePenaltyFrameCount", f"{pen_frame_cnt:,}")
    res_cols[3].metric("NotePenaltyWeightedCount", f"{pen_weight_cnt:,}")
    res_cols[4].metric("✨ ピッチ加点", f"{final_bonus:,}")
    st.latex(r"PitchBonus = \lfloor (\frac{NoteGoodCount}{NoteGoodCount + NoteBadCount}) \times 1000 \rfloor \times 40")


elif st.session_state.current_mode == "揺れの規則性&悪いビブ":
    st.header("揺れの規則性 ＆ 悪いビブラート減点 設定")
    st.markdown("各THD（0〜49%）とフレーム数を設定してください。（THDの値は0〜49の範囲で自由に編集でき、項目の増減も可能です）")

    left_col, right_col = st.columns([4.5, 5.5])

    with left_col:
        st.subheader("入力パラメータ")
        col_color, col_thd, col_slider, col_del = st.columns([0.3, 1.2, 3.2, 0.5])
        with col_thd: st.markdown("**THD(%)**")
        with col_slider: st.markdown("**フレーム数**")

        for item in st.session_state.thd_items:
            item_id, thd_val, frames_val = item["id"], item["thd"], item["frames"]
            is_invalid = thd_val < 0 or thd_val > 49

            if is_invalid: color = "#9E9E9E"
            elif thd_val <= 12: color = "#4CAF50"
            elif 13 <= thd_val <= 40: color = "#F44336"
            else: color = "currentColor"
            
            col_color, col_thd, col_slider, col_del = st.columns([0.3, 1.2, 3.2, 0.5])
            with col_color:
                st.markdown(f"<div style='width: 14px; height: 14px; border-radius: 50%; background-color: {color}; margin-top: 12px; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
            with col_thd:
                st.number_input("THD", value=thd_val, step=1, key=f"thd_input_{item_id}", label_visibility="collapsed", on_change=update_thd_item, args=(item_id,))
            with col_slider:
                st.slider("Frames", min_value=0, max_value=10000, value=frames_val, step=100, key=f"thd_frames_input_{item_id}", label_visibility="collapsed", on_change=update_thd_item, args=(item_id,))
            with col_del:
                st.button("✖", key=f"del_thd_btn_{item_id}", help="この行を削除", on_click=remove_thd_item, args=(item_id,))

            if is_invalid:
                st.warning(f"⚠️ 0〜49の範囲で入力してください。(この行は計算から除外されます)")

        st.button("➕ THDを追加", on_click=add_thd_item)

    with right_col:
        st.subheader("📊 各パラメータの内訳")
        table_data = []
        valid_frames_total = 0

        for item in st.session_state.thd_items:
            thd, val = item["thd"], item["frames"]
            if thd < 0 or thd > 49:
                table_data.append({"THD(%)": f"THD = {thd} (無効)", "フレーム数": val, "THDGood": "-", "THDBad": "-", "PenFrame": "-"})
                continue
            
            valid_frames_total += val
            good = val if 0 <= thd <= 12 else 0
            bad = val if 13 <= thd <= 40 else 0
            pen_frame = val
            
            table_data.append({"THD(%)": f"THD = {thd}", "フレーム数": val, "THDGood": good, "THDBad": bad, "PenFrame": pen_frame})
        
        good_cnt, bad_cnt, pen_frame_cnt, hist_cnt, final_thd_bonus, thd_median, bad_vib_penalty = calculate_secret_thd_bonus(st.session_state.thd_items, st.session_state.total_frame)

        table_data.append({"THD(%)": "合計", "フレーム数": valid_frames_total, "THDGood": good_cnt, "THDBad": bad_cnt, "PenFrame": pen_frame_cnt})
        df = pd.DataFrame(table_data)

        def style_thd(val):
            val_str = str(val)
            if "無効" in val_str: return 'color: #9E9E9E; text-decoration: line-through;'
            elif val_str.startswith("THD = "):
                try:
                    t = int(val_str.split("=")[1].strip())
                    if t <= 12: return 'color: #4CAF50; font-weight: bold;'
                    elif 13 <= t <= 40: return 'color: #F44336; font-weight: bold;'
                except: pass
            elif val_str == "合計": return 'font-weight: bold;'
            return ''

        try: styled_df = df.style.map(style_thd, subset=["THD(%)"])
        except AttributeError: styled_df = df.style.applymap(style_thd, subset=["THD(%)"])

        def format_number(x): return f"{int(x):,}" if isinstance(x, (int, float)) else x
        for col in ["フレーム数", "THDGood", "THDBad", "PenFrame"]: styled_df = styled_df.format({col: format_number})
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.divider()
        # ここに TotalFrame スライダーを移動
        st.session_state.total_frame = st.slider(
            "TotalFrame (曲全体の発声フレーム数)",
            min_value=1,
            max_value=50000,
            value=st.session_state.total_frame,
            step=100
        )

    st.divider()

    st.subheader("算出パラメータ ＆ 結果")
    res_cols1 = st.columns(4)
    res_cols1[0].metric("THDGoodCount", f"{good_cnt:,}")
    res_cols1[1].metric("THDBadCount", f"{bad_cnt:,}")
    res_cols1[2].metric("THDPenFrameCount", f"{pen_frame_cnt:,}")
    res_cols1[3].metric("THDMedian (中央値)", f"{thd_median:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    res_cols2 = st.columns(2)
    res_cols2[0].metric("揺れの規則性加点", f"{final_thd_bonus:,}")
    res_cols2[1].metric("悪いビブラート減点", f"{bad_vib_penalty:,}")

    st.latex(r"THDBonus = \lfloor (\frac{THDGoodCount}{THDGoodCount + THDBadCount}) \times 1000 \rfloor \times 24")
    st.latex(r"Z = \lfloor (\frac{THDPenaltyFrameCount}{TotalFrame}) \times THDMedian \times 100 \rfloor \times 40")

elif st.session_state.current_mode == "第二の減点":
    st.header("第二の減点 詳細")
    st.markdown("ここでは、ロングトーンとビブラートのどちらを優先して評価するかを判定し、減点幅（W）を算出します。")

    # 1. 必要なデータを各計算関数から取得
    ng, nb, npf, npw, _ = calculate_secret_pitch_bonus(st.session_state.pitch_items)
    thd_res = calculate_secret_thd_bonus(st.session_state.thd_items, st.session_state.total_frame)
    # thd_res = [thd_good, thd_bad, thd_pen_frame, histogram_samples, thd_bonus, thd_median, bad_vib_penalty]
    thd_npf = thd_res[2]
    thd_med = thd_res[5]

    # 2. 導出値の表示
    st.subheader("判定に使用するパラメータ")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NotePenaltyFrameCount", f"{npf:,}")
    col2.metric("THDPenaltyFrameCount", f"{thd_npf:,}")
    col3.metric("NotePenaltyWeightedCount", f"{npw:,}")
    col4.metric("THDMedian", f"{thd_med:.1f}")

    st.divider()

    # 3. 判定ロジックと減点幅(W)の表示
    st.subheader("算出プロセス")
    if npf == 0 and thd_npf == 0:
        st.warning("データが入力されていません。")
    elif thd_npf < npf:
        w = math.floor(npw / npf) * 965 if npf > 0 else 0
        st.success("判定モード: **ロングトーン優先** (THD < Note)")
        st.latex(r"W = \lfloor \frac{NotePenaltyWeightedCount}{NotePenaltyFrameCount} \rfloor \times 965")
        st.metric("第二の減点幅 (W)", f"{w:,}")
    else:
        w = math.floor(thd_med * 0.8) * 965
        st.success("判定モード: **ビブラート優先** (THD ≧ Note)")
        st.latex(r"W = \lfloor THDMedian \times 0.8 \rfloor \times 965")
        st.metric("第二の減点幅 (W)", f"{w:,}")

elif st.session_state.current_mode == "全体を見る":
    st.header("全体評価サマリー")
    
    # --- 1. 各種データの再計算 ---
    _, _, npf, npw, pitch_bonus = calculate_secret_pitch_bonus(st.session_state.pitch_items)
    thd_res = calculate_secret_thd_bonus(st.session_state.thd_items, st.session_state.total_frame)
    thd_bonus = thd_res[4]
    bad_vib = thd_res[6]
    
    # --- 2. 第二の減点 (W) ---
    if thd_res[2] < npf:
        w = math.floor(npw / npf) * 965 if npf > 0 else 0
        penalty_type = "ロングトーン優先"
    else:
        w = math.floor(thd_res[5] * 0.8) * 965
        penalty_type = "ビブラート優先"

    # --- 3. 安定性の算出式 (Furue) ---
    fixed_point = 45570
    furue = fixed_point + pitch_bonus + thd_bonus - bad_vib - w
    furue = min(furue, 100000)

    # --- 4. Furueから安定性への変換ロジック ---
    # グラフの関係性に基づいた目安のスコア変換（例として線形近似）
    # 実際のグラフの傾向に合わせて調整してください
    estimated_stability = furue_to_stability(furue)

    # --- 5. ダッシュボード表示 ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ピッチ加点 (X)", f"{pitch_bonus:,}")
    col2.metric("揺れの規則性加点 (Y)", f"{thd_bonus:,}")
    col3.metric("悪いビブラート減点 (Z)", f"{bad_vib:,}")
    col4.metric("第二の減点 (W)", f"{w:,}")
    
    st.divider()
    
    # Furueと安定性スコアを横並びで表示
    res_col1, res_col2, res_col3 = st.columns([1, 1, 2])
    with res_col1:
        st.metric("Furue", f"{furue:,}")
    with res_col2:
        st.metric("安定性スコア", f"{estimated_stability:.3f}")
    with res_col3:
        st.latex(r"Furue = \min(45570 + X + Y - Z - W, 100000)")

    st.divider()


else:
    st.header(f" {st.session_state.current_mode} 設定")
    st.info("この機能は現在実装待ちです。")