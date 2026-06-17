"""scripts/generate_data.py — Sprint 1 synthetic data seeder."""
import sys, os
sys.path.insert(0, '.')
import pandas as pd, numpy as np
from datetime import datetime, timedelta
from sklearn.cluster import DBSCAN

RNG = np.random.default_rng(42)
os.makedirs("data/processed", exist_ok=True)

ROUTES = {f"R{i:03d}": f"CBD–Route{i}" for i in range(1, 21)}
ROUTE_IDS = list(ROUTES.keys())
SUBS = ["Westlands","Langata","Kasarani","Embakasi","Dagoretti","Mathare","Kibra","Ruaraka"]
ACC_TYPES = ["Head-on","Rear-end","Pedestrian","Rollover","Side-swipe","Single vehicle"]
CAUSES = ["Speeding","Drunk driving","Overloading","Mechanical failure","Poor road","Pedestrian fault"]
HOLIDAYS = {"2023-01-01","2023-04-07","2023-05-01","2023-06-01","2023-12-25",
            "2024-01-01","2024-04-19","2024-05-01","2024-06-01","2024-12-25"}
HOTSPOTS = [(-1.2833,36.8167),(-1.3100,36.8300),(-1.2650,36.8050),(-1.2950,36.8750),
            (-1.2400,36.8900),(-1.3300,36.7700),(-1.2200,36.8600),(-1.3500,36.8200),
            (-1.2700,36.8400),(-1.3000,36.8500),(-1.2550,36.7900),(-1.3200,36.8600)]

# --- Accidents ---
print("Generating accidents...")
recs = []
start = datetime(2021,1,1)
for i in range(3200):
    hs = HOTSPOTS[RNG.integers(0,len(HOTSPOTS))]
    lat = np.clip(hs[0]+RNG.normal(0,0.012),-1.45,-1.16)
    lon = np.clip(hs[1]+RNG.normal(0,0.012),36.65,37.10)
    days = int(RNG.integers(0,365*3)); dt = start+timedelta(days=days)
    dow = dt.weekday()
    hw = np.ones(24); hw[6:9]*=2.8; hw[16:20]*=3.2; hw[22:24]*=1.8
    if dow in(4,5): hw*=1.4
    hw/=hw.sum(); hour=int(RNG.choice(24,p=hw))
    route = RNG.choice(ROUTE_IDS) if RNG.random()<0.75 else None
    sev = RNG.choice(["Fatal","Serious","Minor"],p=[0.12,0.33,0.55])
    recs.append({"accident_id":f"ACC{i+1:05d}","date":dt.strftime("%Y-%m-%d"),"hour":hour,
                 "day_of_week":dow,"latitude":round(lat,6),"longitude":round(lon,6),
                 "sub_county":RNG.choice(SUBS),"route_id":route,
                 "route_name":ROUTES.get(route,"Non-matatu") if route else "Non-matatu",
                 "accident_type":RNG.choice(ACC_TYPES),"cause":RNG.choice(CAUSES),
                 "severity":sev,"vehicles_involved":int(RNG.integers(1,5)),
                 "casualties":int(RNG.integers(0,4)) if sev!="Minor" else 0,
                 "road_surface":RNG.choice(["Tarmac","Gravel","Murram"],p=[0.70,0.18,0.12]),
                 "lighting":RNG.choice(["Daylight","Darkness","Dawn/Dusk"],p=[0.52,0.36,0.12]),
                 "weather_condition":RNG.choice(["Fine","Raining","Foggy"],p=[0.68,0.28,0.04]),
                 "is_peak_hour":int(6<=hour<9 or 16<=hour<20)})
acc = pd.DataFrame(recs)
acc.to_csv("data/processed/accidents_clean.csv",index=False)
print(f"  ✓ {len(acc)} accidents")

# --- Blackspots ---
cr = np.radians(acc[["latitude","longitude"]].values)
db = DBSCAN(eps=600/6371000,min_samples=5,metric="haversine").fit(cr)
acc["cluster"]=db.labels_
bsc=[]
for cid in sorted(set(db.labels_)):
    if cid==-1: continue
    g=acc[acc["cluster"]==cid]
    bsc.append({"cluster_id":int(cid),"centroid_lat":round(g.latitude.mean(),6),
                "centroid_lon":round(g.longitude.mean(),6),
                "radius_m":max(50,int(g[["latitude","longitude"]].std().mean()*111000)),
                "n_incidents":len(g),"n_fatal":int((g.severity=="Fatal").sum()),
                "dominant_hour":int(g.hour.mode()[0]),"dominant_type":g.accident_type.mode()[0],
                "dominant_cause":g.cause.mode()[0],
                "severity_score":round((g.severity=="Fatal").sum()*3+(g.severity=="Serious").sum()*1.5+(g.severity=="Minor").sum()*0.5,1),
                "risk_tier":min(5,max(1,len(g)//6))})
bs=pd.DataFrame(bsc).sort_values("n_incidents",ascending=False)
bs.to_csv("data/processed/blackspot_clusters.csv",index=False)
print(f"  ✓ {len(bs)} blackspots")

# --- Route profiles ---
print("Generating route profiles...")
rp=[]
for rid in ROUTE_IDS:
    ag=acc[acc["route_id"]==rid]; n=len(ag); nf=(ag.severity=="Fatal").sum()
    dist=round(float(RNG.uniform(5,26)),1)
    rp.append({"route_id":rid,"route_name":ROUTES[rid],"sub_county":RNG.choice(SUBS),
               "distance_km":dist,"n_stops":int(RNG.integers(8,22)),
               "n_intersections":int(RNG.integers(5,30)),"pct_tarmac":round(float(RNG.uniform(0.55,1.0)),2),
               "pct_gravel":round(float(RNG.uniform(0,0.30)),2),"avg_lane_count":round(float(RNG.uniform(1.5,4.0)),1),
               "has_bus_lane":int(RNG.random()<0.25),"n_schools_nearby":int(RNG.integers(0,6)),
               "n_markets_nearby":int(RNG.integers(1,8)),"n_hospitals_nearby":int(RNG.integers(0,4)),
               "speed_limit_kph":int(RNG.choice([50,60,80])),"lighting_score":round(float(RNG.uniform(0.3,1.0)),2),
               "accidents_24mo":n,"fatalities_24mo":int(nf),"accidents_per_km":round(n/max(dist,1),3),
               "peak_am_volume":int(RNG.integers(120,600)),"peak_pm_volume":int(RNG.integers(180,700)),
               "avg_daily_trips":int(RNG.integers(80,350)),"avg_fare_ksh":int(RNG.integers(30,150)),
               "drought_freq":round(float(RNG.uniform(0.05,0.20)),3),"population_density":int(RNG.integers(2000,45000))})
rp_df=pd.DataFrame(rp)
raw=(rp_df.accidents_per_km*0.40+(rp_df.fatalities_24mo/rp_df.distance_km)*0.25+(1-rp_df.pct_tarmac)*0.15+(1-rp_df.lighting_score)*0.10+(rp_df.n_intersections/30)*0.10)
rp_df["risk_score"]=pd.cut(raw,bins=[-np.inf,raw.quantile(0.20),raw.quantile(0.40),raw.quantile(0.60),raw.quantile(0.80),np.inf],labels=[1,2,3,4,5]).astype(int)
rp_df["raw_risk"]=round(raw,4)
rp_df.to_csv("data/processed/route_profiles.csv",index=False)
print(f"  ✓ {len(rp_df)} route profiles")

# --- Demand dataset ---
print("Generating demand dataset (2 years)...")
drecs=[]
for days_off in range(730):
    dt=datetime(2023,1,1)+timedelta(days=days_off)
    dow=dt.weekday(); month=dt.month; ds=dt.strftime("%Y-%m-%d")
    ih=int(month in[1,2,3,5,6,7,9,10,11]); ih2=int(ds in HOLIDAYS)
    for h in range(5,23):
        for rid in ROUTE_IDS:
            base=float(RNG.uniform(8,25))*18
            if 6<=h<9: hm=float(RNG.uniform(1.8,2.6))
            elif 17<=h<20: hm=float(RNG.uniform(1.9,2.8))
            elif 9<=h<12: hm=float(RNG.uniform(0.9,1.3))
            else: hm=float(RNG.uniform(0.3,0.8))
            dm=1.0
            if dow==4: dm=1.15
            elif dow==5: dm=0.75
            elif dow==6: dm=0.45
            if ih2: dm*=0.35
            drecs.append({"date":ds,"hour":h,"route_id":rid,"day_of_week":dow,"month":month,
                          "is_weekend":int(dow>=5),"is_holiday":ih2,"in_school_term":ih,
                          "passengers":max(0,int(base*hm*dm*float(RNG.normal(1.0,0.08))))})
dem=pd.DataFrame(drecs)
dem.to_csv("data/processed/demand_dataset.csv",index=False)
print(f"  ✓ {len(dem):,} demand records")

# --- Social ---
print("Generating social data...")
TOPICS={"breakdown":["Matatu imesimama {r} foleni kubwa","Breakdown on {r} route avoid",
                     "Vehicle stuck {r} abiria wanangoja"],"accident":["Accident {r} police on scene",
                     "Ajali kubwa {r} gari zimegongana","Crash {r} serious injury reported"],
        "police_block":["Roadblock {r} polisi wanachunguza","Police checkpoint {r} expect delays"],
        "flooding":["Maji mengi {r} mvua kubwa","Road flooded near {r} impassable"],
        "positive":["Clear roads {r} smooth ride","Traffic flowing well {r} good morning"],
        "overloading":["Matatu imejaa sana {r} dangerous","Overcrowded {r} driver won't move"]}
SENT={"breakdown":-0.55,"accident":-0.75,"police_block":-0.30,"flooding":-0.65,"positive":0.70,"overloading":-0.45}
route_names=[f"Route{i}" for i in range(1,21)]
srecs=[]
start2=datetime(2024,1,1)
for i in range(2800):
    tp=RNG.choice(list(TOPICS.keys()),p=[0.25,0.20,0.15,0.12,0.18,0.10])
    rn=RNG.choice(route_names); tmpl=RNG.choice(TOPICS[tp])
    text=tmpl.format(r=rn)
    comp=round(float(np.clip(SENT[tp]+RNG.normal(0,0.15),-1,1)),3)
    ts=start2+timedelta(days=int(RNG.integers(0,550)),hours=int(RNG.integers(5,23)))
    srecs.append({"tweet_id":f"TW{i+1:06d}","timestamp":ts.strftime("%Y-%m-%d %H:%M:%S"),
                  "date":ts.strftime("%Y-%m-%d"),"hour":ts.hour,"text":text,"topic":tp,
                  "route_ref":rn,"compound":comp,
                  "sentiment":"Positive" if comp>0.05 else "Negative" if comp<-0.05 else "Neutral",
                  "is_incident":int(tp in["breakdown","accident","flooding","overloading"]),
                  "retweets":int(RNG.integers(0,45)),"likes":int(RNG.integers(0,120))})
soc=pd.DataFrame(srecs)
soc.to_csv("data/processed/social_sentiment.csv",index=False)
print(f"  ✓ {len(soc)} social records")

# --- Weather ---
print("Generating weather...")
dates=pd.date_range("2021-01-01","2024-12-31",freq="D")
wrecs=[]
for d in dates:
    doy=d.day_of_year
    lr=np.exp(-((doy-105)**2)/(2*30**2)); sr=np.exp(-((doy-305)**2)/(2*25**2))
    rp2=0.05+0.55*lr+0.40*sr
    rf=float(RNG.exponential(8.5)) if RNG.random()<rp2 else 0.0
    tm=19.5+3*np.sin(2*np.pi*(doy-60)/365)
    wrecs.append({"date":d.strftime("%Y-%m-%d"),"rainfall_mm":round(max(0,rf),2),
                  "temp_max_c":round(tm+float(RNG.uniform(4,8)),1),
                  "temp_min_c":round(tm-float(RNG.uniform(2,5)),1),
                  "temp_mean_c":round(tm,1),"humidity_pct":round(float(RNG.uniform(45,85)),1),
                  "is_rainy_day":int(rf>2.0),"heavy_rain":int(rf>15.0),"month":d.month,
                  "season":"Long Rains" if 3<=d.month<=5 else "Short Rains" if 10<=d.month<=12 else "Dry"})
pd.DataFrame(wrecs).to_csv("data/processed/nairobi_weather.csv",index=False)
print(f"  ✓ {len(wrecs)} weather records")
print("\n✅ All datasets generated.")
