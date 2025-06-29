#!/usr/bin/env python3

from glob import glob
import json
from pprint import pprint
import requests
import requests_cache
from shapely import Point
requests_cache.install_cache('cache')
from timezonefinder import TimezoneFinder
from tqdm.auto import tqdm
import re
import pandas as pd
import geopandas as gpd
from pprint import pprint
tf = TimezoneFinder()

dfs = []
for url in ["https://ingress.com/news/2024-sharedmem", "https://ingress.com/news/2024-erasedmem", "https://ingress.com/news/2025-plusalpha", "https://ingress.com/news/2025-plustheta", "https://ingress.com/news/2025-plusdelta"]:
  r = requests.get(url)
  df = pd.DataFrame(re.findall(r"(?P<lat>-?\d+.\d+), (?P<lng>-?\d+.\d+)]\).bindPopup\('(?P<type>Shard Skirmish|Anomaly)<br /> ?(?P<city>.+?)<br />(?P<date>.+?)'", r.text), columns=["lat", "lng", "type", "city", "date"])
  df["series"] = url.split("/")[-1]
  print(df)
  dfs.append(df)
df = pd.concat(dfs)
df["lat"] = df["lat"].astype(float)
df["lng"] = df["lng"].astype(float)
df["date"] = pd.to_datetime(df["date"])
df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lng"], df["lat"]), crs="EPSG:4326")
print(df)
df.drop(columns="geometry").sort_values("date").to_csv("events.csv", index=False)

files = glob("*.json")
all_data = {}

for f in tqdm(files):
  with open(f, "r") as file:
    print(f)
    data = json.load(file)
    filtered_data = [d for d in data["artifact"] if d.get("fragment")]
    for d in tqdm(filtered_data):
      if d["id"] == "abaddon1" and f != "shard-jump-times-2025.06.16.17.47.43.json":
        for shard in d["fragment"]:
          samplePortal = shard["history"][-1]["destinationPortalInfo"]
          lat = samplePortal["latE6"] / 1e6
          lng = samplePortal["lngE6"] / 1e6
          df["distance"] = df.distance(Point(lng, lat))
          df = df.sort_values("distance")
          city = df.iloc[0]["city"]
          timezone = tf.timezone_at(lng=lng, lat=lat)
          print(d["name"], city, timezone)
          #shard["city"] = city
          shard["timezone"] = timezone
      else:
        samplePortal = d["fragment"][0]["history"][-1]["destinationPortalInfo"]
        lat = samplePortal["latE6"] / 1e6
        lng = samplePortal["lngE6"] / 1e6
        df["distance"] = df.distance(Point(lng, lat))
        df = df.sort_values("distance")
        city = df.iloc[0]["city"]
        timezone = tf.timezone_at(lng=lng, lat=lat)
        print(d["name"], city, timezone)
        d["city"] = city
        d["timezone"] = timezone
  with open(f, "w") as file:
    json.dump(data, file, indent=2, ensure_ascii=False)
    all_data[f] = data


with open("all_data.json", "w") as file:
  json.dump(all_data, file, indent=2, ensure_ascii=False)
print("Done")
