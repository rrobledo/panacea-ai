import json, datetime as dt, collections as C, statistics as st
src=open("merma2.py").read().split("P=C.defaultdict(float)")[0]
exec(src)  # define MAP (con equivalencias corregidas y paquetes), M, price no
raw=json.load(open("plan_raw.json"))
def mapref(r):
    if r in MAP: return MAP[r]
    if len(r)==4 and r[0] in "246" and r[1:] in MAP: return MAP[r[1:]]
    return []
MAE={r[0]:r for r in raw["mae"]}
D=dt.date.fromisoformat
W0=D("2026-08-17"); NW=8
# demanda[pid][lugar][dow][semana]
dem=C.defaultdict(lambda: C.defaultdict(lambda: [[0.0]*NW for _ in range(7)]))
vgb=C.defaultdict(lambda: C.defaultdict(float)); vgb_days=set()
unm=C.defaultdict(float)
for r,l,f,u in raw["v"]:
    d=D(f); u=float(u); mp=mapref(r)
    if l=="Villa General Belgrano":
        if d>=D("2026-09-26"):
            vgb_days.add(f)
            for pid,c in mp: vgb[pid][d.weekday()>=5]+=u*c
        continue
    if not (W0<=d<=D("2026-10-11")): continue
    w=(d-W0).days//7
    for pid,c in mp: dem[pid][l][d.weekday()][w]+=u*c
nd=C.Counter(D(f).weekday()>=5 for f in vgb_days); print("VGB dias", sorted(vgb_days), nd)
prod=C.defaultdict(float)
for pid,f,x in raw["p"]: prod[pid]+=float(x)
out=[]
for pid in set(dem)|set(vgb):
    if pid not in MAE: continue
    mae=MAE[pid]
    tot=sum(sum(sum(dw) for dw in dl) for dl in dem[pid].values())/NW
    vg=(vgb[pid][False]/max(nd[False],1)*5 + vgb[pid][True]/max(nd[True],1)*2)
    if tot+vg < 2: continue
    out.append((mae[1].strip(), mae[2], round(tot,1), round(vg,1), round(prod[pid]/NW,1), mae[4]))
out.sort(key=lambda x:(x[1],-x[2]))
for o in out: print(o)

# ---------- datos para la programación ----------
pdw=C.defaultdict(dict)
for pid,dow,n,med in json.load(open("prod_dow.json")): pdw[pid][dow-1]=(n,float(med))
mf={r["id"]:r for r in json.load(open("merma_final.json"))["rows"]}
DAILY={"MEDIALUNAS","FACTURAS","PANADERIA","BOLLERIA","PIZZAS"}
items=[]
for pid in set(dem)|set(vgb):
    if pid not in MAE: continue
    mae=MAE[pid]; nombre=mae[1].strip()
    ret=[[sum(dem[pid][l][d][w] for l in dem[pid] if l!='Dietetica') for w in range(NW)] for d in range(7)]
    may=[[dem[pid]['Dietetica'][d][w] if 'Dietetica' in dem[pid] else 0 for w in range(NW)] for d in range(7)]
    mean=[round(st.mean(x),2) for x in ret]; var=[round(st.pvariance(x),2) for x in ret]
    mm=[round(st.mean(x),2) for x in may]
    vg=[round(vgb[pid][d>=5]/max(nd[d>=5],1),2) for d in range(7)]
    if sum(mean)+sum(vg)+sum(mm)<2: continue
    # reparto por local (participación semanal)
    loc={l:round(sum(sum(dem[pid][l][d]) for d in range(7))/NW,1) for l in dem[pid]}
    pd=pdw.get(pid,{}); totn=sum(n for n,_ in pd.values())
    days=sorted(d for d,(n,_) in pd.items() if totn and n/totn>=0.12 and d<=5)
    if not days: days=[0,1,2,3,4,5] if mae[2] in DAILY else [0,3]
    lot=round(st.median([med for _,med in pd.values()]),1) if pd else None
    r=mf.get(pid,{})
    items.append(dict(id=pid,n=nombre,cat=mae[2].capitalize(),um=mae[3],mean=mean,var=var,mm=mm,vgb=vg,loc=loc,days=days,lot=lot,
        p=r.get("p_caja"),prod_sem=r.get("prod_sem"),vend_sem=r.get("vend_sem")))
items.sort(key=lambda x:(x["cat"],-(sum(x["mean"])+sum(x["mm"]))))
print(len(items))
for it in items[:8]: print(it["n"],it["days"],it["lot"],it["mean"],it["vgb"],it["loc"],it["p"],it["prod_sem"])
json.dump(items,open("plan_items.json","w"),ensure_ascii=False,separators=(",",":"))
import os; print(os.path.getsize("plan_items.json"))
