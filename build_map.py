# -*- coding: utf-8 -*-
"""生成非遗地图所需的 SVG 片段。

数据源：阿里云 DataV.GeoAtlas 公开行政区划边界
  650000.json      新疆省级边界
  650000_full.json 含各地州市边界（带名称）

输出：templates/_map_path.svg
  1) 经纬网格（每 2 度）
  2) 各地州轮廓（带 data-name，供悬停高亮与浮层显示）
  3) 省级边界（粗描边）

重新生成：python build_map.py
"""
import json
import math
import os

import requests

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "templates", "_map_path.svg")
URL_PROV = "https://geo.datav.aliyun.com/areas_v3/bound/650000.json"
URL_FULL = "https://geo.datav.aliyun.com/areas_v3/bound/650000_full.json"

VIEW_W, VIEW_H = 800, 620
PAD = 16

# 非遗点位（真实经纬度）
SITES = {
    "kashgar": (75.99, 39.47),   # 喀什市 —— 维吾尔族刺绣
    "yining": (81.32, 43.92),    # 伊宁市 —— 冬不拉
    "hotan": (79.92, 37.11),     # 和田市 —— 艾德莱斯绸 / 地毯
    "wuqia": (75.25, 39.72),     # 克州（乌恰一带）—— 玛纳斯
}


def outer_rings(geom):
    if not geom:
        return []
    kind = geom.get("type")
    if kind == "Polygon":
        return [geom["coordinates"][0]]
    if kind == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


print("下载边界数据 ...")
prov = requests.get(URL_PROV, timeout=90).json()
full = requests.get(URL_FULL, timeout=120).json()
print(f"  省级 features={len(prov.get('features', []))}  地州 features={len(full.get('features', []))}")

prov_rings = []
for feat in prov.get("features", []):
    prov_rings += [r for r in outer_rings(feat.get("geometry")) if len(r) >= 4]

city_features = []
for feat in full.get("features", []):
    name = (feat.get("properties") or {}).get("name") or "未知区域"
    rings = [r for r in outer_rings(feat.get("geometry")) if len(r) >= 4]
    if rings:
        city_features.append((name, rings))

all_rings = prov_rings + [r for _, rings in city_features for r in rings]

LAT_REF = math.radians(41.5)
K_LON = math.cos(LAT_REF)


def project(lon, lat):
    return (lon - 73.0) * K_LON, (49.2 - lat)


pts = [project(lon, lat) for ring in all_rings for lon, lat in ring]
min_x, max_x = min(p[0] for p in pts), max(p[0] for p in pts)
min_y, max_y = min(p[1] for p in pts), max(p[1] for p in pts)
lon_min = 73.0 + min_x / K_LON
lon_max = 73.0 + max_x / K_LON
lat_min = 49.2 - max_y
lat_max = 49.2 - min_y

scale = min((VIEW_W - 2 * PAD) / (max_x - min_x), (VIEW_H - 2 * PAD) / (max_y - min_y))
off_x = (VIEW_W - (max_x - min_x) * scale) / 2 - min_x * scale
off_y = (VIEW_H - (max_y - min_y) * scale) / 2 - min_y * scale


def to_svg(lon, lat):
    x, y = project(lon, lat)
    return round(x * scale + off_x, 1), round(y * scale + off_y, 1)


def simplify(points, tol):
    out = [points[0]]
    for p in points[1:]:
        if math.dist(p, out[-1]) >= tol:
            out.append(p)
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def rings_to_d(rings, tol):
    sub = []
    for ring in rings:
        sp = simplify([to_svg(lon, lat) for lon, lat in ring], tol)
        if len(sp) >= 4:
            sub.append("M " + " L ".join(f"{x},{y}" for x, y in sp) + " Z")
    return " ".join(sub) if sub else None


lines = ["<!-- 新疆维吾尔自治区行政边界与经纬网格 -->",
         "<!-- 由 build_map.py 依据 DataV.GeoAtlas 公开数据生成，请勿手工编辑 -->"]

# 1) 经纬网格
grid = []
for lon in range(74, 97, 2):
    x1, y1 = to_svg(lon, lat_min)
    x2, y2 = to_svg(lon, lat_max)
    grid.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
for lat in range(36, 49, 2):
    x1, y1 = to_svg(lon_min, lat)
    x2, y2 = to_svg(lon_max, lat)
    grid.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
lines.append('<g class="map-grid">')
lines += grid
lines.append("</g>")

# 2) 地州轮廓（带名称）
lines.append('<g class="map-cities">')
city_count = 0
for name, rings in city_features:
    d = rings_to_d(rings, 2.0)
    if not d:
        continue
    lines.append(f'  <path class="map-city" data-name="{name}" d="{d}"/>')
    city_count += 1
lines.append("</g>")

# 3) 省界
for ring in prov_rings:
    d = rings_to_d([ring], 1.2)
    if d:
        lines.append(f'<path class="map-province" d="{d}"/>')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"\n地州 {city_count} 个，网格线 {len(grid)} 条")
print(f"输出: {OUT}  ({os.path.getsize(OUT):,} 字节)")
print("\n=== 非遗点位坐标 ===")
for key, (lon, lat) in SITES.items():
    x, y = to_svg(lon, lat)
    print(f'  {key:<9} cx={x:>6.1f} cy={y:>6.1f}')
