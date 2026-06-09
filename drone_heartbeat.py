import streamlit as st
import time
import datetime
import pandas as pd

# 初始化会话状态
if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []
if 'last_received_time' not in st.session_state:
    st.session_state.last_received_time = time.time()
if 'packet_index' not in st.session_state:
    st.session_state.packet_index = 0

st.title("无人机心跳监测可视化")

# 控制按钮
start_button = st.button("开始监测")
stop_button = st.button("停止监测")

if start_button:
    st.session_state.running = True
if stop_button:
    st.session_state.running = False

if 'running' not in st.session_state:
    st.session_state.running = False

# 占位符用于动态更新内容
status_placeholder = st.empty()
chart_placeholder = st.empty()
data_placeholder = st.empty()

if st.session_state.running:
    while True:
        current_time = time.time()
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        st.session_state.packet_index += 1
        
        # 生成并保存心跳包
        heartbeat_packet = {"序号": st.session_state.packet_index, "时间": timestamp}
        st.session_state.heartbeat_data.append(heartbeat_packet)
        st.session_state.last_received_time = current_time
        
        # 掉线检测
        if current_time - st.session_state.last_received_time > 3:
            status_placeholder.error("⚠️ 连接超时！3秒未收到心跳包")
        else:
            status_placeholder.success("✅ 连接正常")
        
        # 更新图表和数据
        df = pd.DataFrame(st.session_state.heartbeat_data)
        chart_placeholder.line_chart(df, x="时间", y="序号")
        data_placeholder.dataframe(df)
        
        time.sleep(1)
