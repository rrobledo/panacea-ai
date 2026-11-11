import json, datetime as dt, collections as C
d=json.load(open("merma_raw.json")); s=json.load(open("ventas_ref.json"))
D=dt.date.fromisoformat
wk=lambda x:(D(x)-dt.timedelta(days=D(x).weekday())).isoformat()
M={r[0]:r for r in d["maestro"]}
MAP=C.defaultdict(list)
for r,pid,c in s["ref"]: MAP[r].append((pid,float(c)))
MAP.pop('332',None)  # Criollos 250gr: se arma con criollos a granel
EXTRA={5:{'2516':1,'4228':1,'6228':1},26:{'6110':1,'519':1,'2550':1,'2549':1,'579':4},27:{'499':.5,'6111':1},
 28:{'4112':1,'539':1,'6112':1},51:{'6114':2,'4277':1,'6277':1,'4278':1,'6278':1,'4463':1,'6463':1},
 92:{'479':1,'4394':2,'6394':2},103:{'203':1,'4203':1,'166':1,'542':1,'543':1,'558':1},137:{'537':1,'2571':1,'2572':1},
 36:{'6107':1,'555':1},33:{'6108':1,'549':1},
 43:{'342':.25,'477':.25,'2348':.25,'2604':.25,'348':.2,'6348':.2,'6119':.25,'564':.25,'2610':.25},
 25:{'282':.25,'2282':.25,'476':.25,'6332':.25,'4282':.2,'6282':.2,'6101':.2,'332':.25},
 48:{'4281':.5,'6281':.5,'2452':.2,'2459':.2,'2460':.2,'2462':.2},
 45:{'6542':1,'4533':2,'6533':2,'6208':2,'504':2,'503':2},
 31:{'4161':1},84:{'4164':1},110:{'6403':1},112:{'6411':1},83:{'6163':1},116:{'6432':1},
 52:{'6147':1},75:{'6148':1},73:{'4151':1},82:{'4330':1},96:{'4402':1,'6402':1},63:{'6158':1},6:{'6157':1},99:{'6410':1}}
for pid,refs in EXTRA.items():
    for r,f in refs.items(): MAP[r]=[(pid,float(f))]
for r in ('114','2114'): MAP[r]=[(51,2.0)]
# Unidades por paquete de venta (producción se registra por unidad): Pan Chip x6, Pancho x2, Hamburguesa x2
PACK={26:6,28:2,27:2}
for r in list(MAP): MAP[r]=[(pid,c*PACK.get(pid,1)) for pid,c in MAP[r]]   # Pizzetas x2: igual que la ref 4114 (1 bolsa = 2 pizzetas)
P=C.defaultdict(float); V=C.defaultdict(float)
for pid,f,x in d["prod"]: P[(pid,wk(f))]+=float(x)
for r,w,u,sub in s["v"]:
    for pid,c in MAP.get(r,[]): V[(pid,w)]+=float(u)*c
pu=C.defaultdict(float); ps=C.defaultdict(float)
for r,u,sub in s["pr"]:
    for pid,c in MAP.get(r,[]): pu[pid]+=float(u)*c; ps[pid]+=float(sub)
price={p:ps[p]/pu[p] for p in pu if pu[p]>0}
GRANEL={43:28000,25:20000,48:18000}
weeks=sorted({w for (_,w) in P}); n=len(weeks); F=52/12
out=[]
for pid in set(k[0] for k in P):
    pt=sum(P[(pid,w)] for w in weeks); vt=sum(V[(pid,w)] for w in weeks)
    if pt<=0 or vt<=0 or pid not in price: continue
    lo=max(pt-vt,0); up=sum(max(P[(pid,w)]-V[(pid,w)],0) for w in weeks)
    pc=price[pid]; pi=GRANEL.get(pid,pc)
    out.append(dict(id=pid,n=M[pid][1].strip(),um=M[pid][2],gr=pid in GRANEL,prod_sem=round(pt/n,1),vend_sem=round(vt/n,1),
      pct_lo=round(100*lo/pt,1),pct_up=round(100*up/pt,1),lo_u=round(lo/n*F,1),up_u=round(up/n*F,1),
      p_inf=round(pi),p_caja=round(pc),lo=round(lo/n*F*pi),up=round(up/n*F*pi),lo_c=round(lo/n*F*pc),up_c=round(up/n*F*pc)))
out.sort(key=lambda r:-(r["lo"]+r["up"]))
print("semanas",n,"TOTAL mes bajo",sum(r["lo"] for r in out)/1e6,"alto",sum(r["up"] for r in out)/1e6,"| a caja", sum(r["lo_c"] for r in out)/1e6, sum(r["up_c"] for r in out)/1e6)
vp=sum(r["prod_sem"]*r["p_caja"] for r in out)*F; print("valor producido/mes caja",vp/1e6, "prods",len(out))
for r in out[:25]: print(r["id"],r["n"][:28],r["um"],r["prod_sem"],r["vend_sem"],r["pct_lo"],r["pct_up"],r["p_inf"],r["p_caja"],round(r["lo"]/1e6,2),round(r["up"]/1e6,2))
neg=[(r["n"],round(100*(r["vend_sem"]/r["prod_sem"]-1))) for r in out if r["vend_sem"]>r["prod_sem"]*1.15]; print("vendido>producido+15%:",neg)
gw={pid:[[w,round(P[(pid,w)],1),round(V[(pid,w)],1)] for w in weeks] for pid in (43,25,48)}
mes=C.defaultdict(lambda:[0,0])
for r in out:
    for w in weeks:
        k=w[:7]; mes[k][0]+=max(P[(r["id"],w)]-V[(r["id"],w)],0)*r["p_inf"]; mes[k][1]+=P[(r["id"],w)]*r["p_inf"]
print({k:(round(a/1e6,2),round(100*a/b,1)) for k,(a,b) in sorted(mes.items())})
json.dump(dict(rows=out,gw=gw,weeks=weeks,mes={k:[round(a),round(b)] for k,(a,b) in sorted(mes.items())}), open("merma_final.json","w"))
