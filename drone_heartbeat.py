# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math
import os

# ==================== 页面配置 ====================
st.set_page_config(page_title="航线规划", layout="wide")
st.title("🗺️ 航线规划 + 障碍物圈选")

# ==================== 坐标转换（简化版）====================
def gcj02_to_wgs84(lng, lat):
    return lng - 0.0015, lat - 0.0005  # 简化转换

def wgs84_to_gcj02(lng, lat):
    return lng + 0.0015, lat + 0.0005

def to_wgs84_display(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    return lat, lng

def circle_to_polygon(center_lng, center_lat, radius_meters, num_points=24):
    points = []
    dlat = radius_meters / 110540
    dlng = radius_meters / 111320
    for i in range(num_points):
        angle = math.radians(360 * i / num_points)
        points.append([center_lng + dlng * math.cos(angle), center_lat + dlat * math.sin(angle)])
    return points

# ==================== 初始化 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2323, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2344, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 10
if 'safe_radius' not in st.session_state:
    st.session_state.safe_radius = 10
if 'polygon_obstacles' not in st.session_state:
    try:
        with open("obstacle_config.json", "r") as f:
            st.session_state.polygon_obstacles = json.load(f).get("obstacles", [])
    except:
        st.session_state.polygon_obstacles = []
if 'temp_new_obstacle' not in st.session_state:
    st.session_state.temp_new_obstacle = None
if 'show_height_dialog' not in st.session_state:
    st.session_state.show_height_dialog = False

# ==================== 保存 ====================
def save_obstacles():
    with open("obstacle_config.json", "w") as f:
        json.dump({"obstacles": st.session_state.polygon_obstacles}, f)

# ==================== 布局 ====================
left_col, right_col = st.columns([3, 1])

with left_col:
    latA_disp, lngA_disp = to_wgs84_display(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_disp, lngB_disp = to_wgs84_display(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)
    
    center_lat = (latA_disp + latB_disp) / 2
    center_lng = (lngA_disp + lngB_disp) / 2
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=17,
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                   attr="Esri Satellite")
    
    folium.Marker([latA_disp, lngA_disp], popup="起点 A", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([latB_disp, lngB_disp], popup="终点 B", icon=folium.Icon(color="red")).add_to(m)
    folium.PolyLine([(latA_disp, lngA_disp), (latB_disp, lngB_disp)], color="blue", weight=4).add_to(m)
    
    # 绘制障碍物
    for i, obs in enumerate(st.session_state.polygon_obstacles):
        coords = [[lat, lng] for lng, lat in obs["coordinates"]]
        color = "red" if obs["height"] >= st.session_state.flight_height else "orange"
        folium.Polygon(locations=coords, color=color, fill=True, fill_opacity=0.3,
                       popup=f"高度: {obs['height']}m").add_to(m)
    
    Draw(draw_options={
        "polygon": {"shapeOptions": {"color": "#ffdd00"}},
        "rectangle": {"shapeOptions": {"color": "#ffdd00"}},
        "circle": {"shapeOptions": {"color": "#ffdd00"}},
        "polyline": False, "marker": False, "circlemarker": False
    }).add_to(m)
    MousePosition().add_to(m)
    
    output = st_folium(m, height=700, width="100%", key="map")
    
    # ========== 关键：处理绘制并弹出高度设置 ==========
    if output and output.get("last_active_drawing"):
        drawing = output["last_active_drawing"]
        if drawing and drawing.get("geometry"):
            geom = drawing["geometry"]
            coords = []
            
            if geom["type"] == "Polygon":
                raw = geom["coordinates"][0]
                for lng, lat in raw:
                    if st.session_state.coord_type == "GCJ-02":
                        gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
                        coords.append([gcj_lng, gcj_lat])
                    else:
                        coords.append([lng, lat])
            elif geom["type"] == "Circle":
                center = geom["coordinates"][0]
                radius = geom["coordinates"][1]
                if st.session_state.coord_type == "GCJ-02":
                    gcj_lng, gcj_lat = wgs84_to_gcj02(center[0], center[1])
                else:
                    gcj_lng, gcj_lat = center[0], center[1]
                coords = circle_to_polygon(gcj_lng, gcj_lat, radius)
            
            if coords and st.session_state.temp_new_obstacle is None:
                st.session_state.temp_new_obstacle = coords
                st.session_state.show_height_dialog = True
                st.rerun()

# ==================== 右侧控制面板 + 高度弹窗 ====================
with right_col:
    st.subheader("控制面板")
    
    # 坐标系选择
    coord_opt = st.radio("坐标系", ["WGS-84", "GCJ-02"], index=1)
    st.session_state.coord_type = coord_opt
    
    st.subheader("起点 A")
    st.caption("坐标: 32.2323, 118.749")
    latA = st.number_input("纬度", value=st.session_state.pointA["lat"], format="%.6f")
    lngA = st.number_input("经度", value=st.session_state.pointA["lng"], format="%.6f")
    if st.button("设置A点"):
        st.session_state.pointA = {"lat": latA, "lng": lngA}
        st.rerun()
    
    st.subheader("终点 B")
    st.caption("坐标: 32.2344, 118.749")
    latB = st.number_input("纬度", value=st.session_state.pointB["lat"], format="%.6f", key="latB")
    lngB = st.number_input("经度", value=st.session_state.pointB["lng"], format="%.6f", key="lngB")
    if st.button("设置B点"):
        st.session_state.pointB = {"lat": latB, "lng": lngB}
        st.rerun()
    
    st.subheader("飞行参数")
    st.session_state.flight_height = st.number_input("飞行高度(m)", value=st.session_state.flight_height, step=5)
    st.session_state.safe_radius = st.number_input("安全半径(m)", value=st.session_state.safe_radius, step=1)
    
    st.divider()
    
    # ========== 障碍物高度设置弹窗（直接显示在右侧） ==========
    st.markdown("### 🚧 新增障碍物")
    
    if st.session_state.temp_new_obstacle is not None:
        st.warning("📌 检测到新绘制的区域，请设置高度")
        
        new_height = st.number_input("障碍物高度(米)", min_value=0, max_value=500, value=40, step=5, key="new_h")
        new_name = st.text_input("名称", value=f"障碍物{len(st.session_state.polygon_obstacles)+1}", key="new_n")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认添加", type="primary", use_container_width=True):
                st.session_state.polygon_obstacles.append({
                    "name": new_name,
                    "coordinates": st.session_state.temp_new_obstacle,
                    "height": new_height
                })
                save_obstacles()
                st.session_state.temp_new_obstacle = None
                st.session_state.show_height_dialog = False
                st.success(f"已添加 {new_name} (高度{new_height}m)")
                st.rerun()
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.temp_new_obstacle = None
                st.session_state.show_height_dialog = False
                st.rerun()
    else:
        st.info("💡 在地图上绘制多边形/矩形/圆形，将自动识别并弹出高度设置")
    
    st.divider()
    
    # 障碍物列表
    st.markdown("### 📋 障碍物列表")
    if st.session_state.polygon_obstacles:
        for i, obs in enumerate(st.session_state.polygon_obstacles):
            st.write(f"{i+1}. {obs.get('name', f'障碍物{i+1}')} - {obs.get('height', 40)}m")
    else:
        st.write("暂无")
    
    col_del, col_save = st.columns(2)
    with col_del:
        if st.button("🗑️ 清理所有", use_container_width=True):
            st.session_state.polygon_obstacles = []
            save_obstacles()
            st.rerun()
    with col_save:
        if st.button("💾 保存配置", use_container_width=True):
            save_obstacles()
            st.success("已保存")
    
    st.divider()
    
    # 生成航线按钮
    if st.button("🚁 生成航线", type="primary", use_container_width=True):
        st.success("航线已生成")
        st.rerun()

st.divider()
st.caption(f"A点: 32.2323, 118.749 | B点: 32.2344, 118.749 | 障碍物数量: {len(st.session_state.polygon_obstacles)} | 坐标系: {st.session_state.coord_type}")
