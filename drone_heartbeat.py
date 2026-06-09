import streamlit as st
import streamlit_folium as sf
import folium
from folium.plugins import Draw
import time
import datetime
import pandas as pd
import math
import plotly.express as px

# 坐标系转换工具函数
def gcj02_to_wgs84(lat, lon):
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = _transformlat(lon - 105.0, lat - 35.0)
    dlon = _transformlon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat - dlat, lon - dlon

def wgs84_to_gcj02(lat, lon):
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = _transformlat(lon - 105.0, lat - 35.0)
    dlon = _transformlon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lat + dlat, lon + dlon

def _transformlat(lon, lat):
    ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(math.fabs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transformlon(lon, lat):
    ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(math.fabs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lon * math.pi) + 40.0 * math.sin(lon / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lon / 12.0 * math.pi) + 320 * math.sin(lon / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

# 初始化会话状态
if 'page' not in st.session_state:
    st.session_state.page = "航线规划"
if 'A_point' not in st.session_state:
    st.session_state.A_point = None
if 'B_point' not in st.session_state:
    st.session_state.B_point = None
if 'coordinate_system' not in st.session_state:
    st.session_state.coordinate_system = "GCJ-02(高德/百度)"
if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []
if 'running' not in st.session_state:
    st.session_state.running = False

# 侧边栏页面选择
st.sidebar.title("无人机监控系统")
menu = st.sidebar.radio("功能选择", ["航线规划", "飞行监控"])

# ========== 航线规划页面 ==========
if menu == "航线规划":
    st.title("无人机航线规划")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("坐标设置")
        coord_type = st.radio("坐标系", ["GCJ-02(高德/百度)", "WGS-84(GPS)"])
        lat_a = st.number_input("A点纬度", value=32.0, format="%.6f")
        lon_a = st.number_input("A点经度", value=118.0, format="%.6f")
        lat_b = st.number_input("B点纬度", value=32.01, format="%.6f")
        lon_b = st.number_input("B点经度", value=118.01, format="%.6f")
        fly_height = st.slider("飞行高度(m)", 10, 500, 100)

        if st.button("确认点位"):
            st.session_state.A_point = (lat_a, lon_a)
            st.session_state.B_point = (lat_b, lon_b)
            st.success("点位设置成功！")

    with col2:
        st.subheader("地图视图")
        center_lat = 32.0
        center_lon = 118.0
        if st.session_state.A_point:
            center_lat, center_lon = st.session_state.A_point

        # 创建地图
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
        Draw(export=True).add_to(m)

        # 标记A、B点
        if st.session_state.A_point:
            folium.Marker(
                location=st.session_state.A_point,
                popup="起飞点 A",
                icon=folium.Icon(color="green")
            ).add_to(m)
        if st.session_state.B_point:
            folium.Marker(
                location=st.session_state.B_point,
                popup="目标点 B",
                icon=folium.Icon(color="red")
            ).add_to(m)

        # 绘制航线
        if st.session_state.A_point and st.session_state.B_point:
            folium.PolyLine(
                [st.session_state.A_point, st.session_state.B_point],
                color="blue", weight=3, popup="规划航线"
            ).add_to(m)

        sf.folium_static(m, width=500, height=400)

# ========== 飞行监控 & 心跳包页面 ==========
elif menu == "飞行监控":
    st.title("无人机飞行状态监控（心跳包）")
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        start_btn = st.button("开始监测")
    with col_btn2:
        stop_btn = st.button("停止监测")

    if start_btn:
        st.session_state.running = True
        st.session_state.heartbeat_data = []
    if stop_btn:
        st.session_state.running = False

    # 实时心跳数据展示
    status_placeholder = st.empty()
    chart_placeholder = st.empty()
    data_table = st.empty()

    if st.session_state.running:
        for i in range(1000):
            now = datetime.datetime.now()
            timestamp = now.strftime("%H:%M:%S")
            # 模拟心跳数据
            signal = 50 + math.sin(i * 0.1) * 20
            altitude = 100 + math.sin(i * 0.05) * 10

            row = {
                "时间": timestamp,
                "信号强度": round(signal, 2),
                "飞行高度": round(altitude, 2)
            }
            st.session_state.heartbeat_data.append(row)

            # 状态文字
            status_placeholder.info(f"【正常飞行】当前时间：{timestamp} | 信号：{round(signal,2)}")

            # 图表
            df = pd.DataFrame(st.session_state.heartbeat_data)
            fig = px.line(df, x="时间", y=["信号强度", "飞行高度"], title="无人机实时状态曲线")
            chart_placeholder.plotly_chart(fig, use_container_width=True)

            # 数据表
            data_table.dataframe(df.tail(10), use_container_width=True)

            time.sleep(1)
            if not st.session_state.running:
                break
    else:
        status_placeholder.warning("监测已停止，请点击「开始监测」启动")
        if len(st.session_state.heartbeat_data) > 0:
            df = pd.DataFrame(st.session_state.heartbeat_data)
            fig = px.line(df, x="时间", y=["信号强度", "飞行高度"], title="历史状态曲线")
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            data_table.dataframe(df, use_container_width=True)
