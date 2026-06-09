import pandas as pd
import matplotlib.pyplot as plt

# 读取你刚上传的csv文件
df = pd.read_csv("gps_rtk_data.csv")

# 提取三组轨迹坐标
gps_lon, gps_lat = df.iloc[:,2], df.iloc[:,1]
rtk_lon, rtk_lat = df.iloc[:,4], df.iloc[:,3]
real_lon, real_lat = df.iloc[:,6], df.iloc[:,5]

# 绘制对比图
plt.figure(figsize=(10,6))
plt.plot(gps_lon, gps_lat, label='GPS轨迹', alpha=0.7)
plt.plot(rtk_lon, rtk_lat, label='RTK轨迹', alpha=0.9)
plt.plot(real_lon, real_lat, label='真实轨迹', linestyle='--')
plt.xlabel('经度')
plt.ylabel('纬度')
plt.title('GPS/RTK与真实轨迹对比')
plt.legend()
plt.show()
