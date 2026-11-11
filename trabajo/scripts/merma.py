import json, datetime as dt, collections as C
d=json.load(open("merma_raw.json"))
D=lambda s: dt.date.fromisoformat(s)
wk=lambda s: (D(s)-dt.timedelta(days=D(s).weekday())).isoformat()
loaded=set(r[0] for r in d["loaded"])
# semana completa: todos los días lun-vie con registros cargados (producción > 0 en alguna fila)
dias=C.defaultdict(list)
for f,dow in d["allrows"]:
    if 1<=dow<=5: dias[wk(f)].append(f in loaded)
weeks=sorted(dias); complete=[w for w in weeks if all(dias[w]) and len(dias[w])>=4]
print("semanas",len(weeks),"completas",len(complete))
P=C.defaultdict(float); V=C.defaultdict(float); VS=C.defaultdict(float)
for pid,f,x in d["prod"]: P[(pid,wk(f))]+=float(x)
for pid,f,u,s in d["ventas"]: V[(pid,wk(f))]+=float(u); VS[(pid,wk(f))]+=float(s)
price={pid:float(p) for pid,p in d["precio"] if p}
M={r[0]:r for r in d["maestro"]}
GRANEL={43:28000,25:20000,48:18000}  # precio informado por 100 g → por kg
pids=set(k[0] for k in P)|set(k[0] for k in V)
rows=[]
for pid in pids:
    pr=sum(P[(pid,w)] for w in complete); ve=sum(V[(pid,w)] for w in complete)
    if pr<=0 or ve<=0: continue
    n=len(complete); sob=pr-ve
    pc=price.get(pid); pi=GRANEL.get(pid, pc)
    rows.append(dict(id=pid,n=M.get(pid,[0,'?'])[1].strip(),um=M.get(pid,[0,0,'?'])[2],prod_sem=pr/n,vend_sem=ve/n,sob_sem=sob/n,pct=100*sob/pr,
        precio_inf=pi,precio_caja=pc,perd_mes_inf=(sob/n*52/12*pi) if (sob>0 and pi) else 0,perd_mes_caja=(sob/n*52/12*pc) if (sob>0 and pc) else 0))
rows.sort(key=lambda r:-r["perd_mes_inf"])
for r in rows[:45]: print(f'{r["id"]:4} {r["n"][:30]:30} {r["um"]:3} prod/sem={r["prod_sem"]:8.1f} vend/sem={r["vend_sem"]:8.1f} sob%={r["pct"]:6.1f} p_inf={r["precio_inf"] or 0:8.0f} p_caja={r["precio_caja"] or 0:8.0f} perd_mes={r["perd_mes_inf"]/1e6:6.2f}M caja={r["perd_mes_caja"]/1e6:6.2f}M')
neg=[r for r in rows if r["sob_sem"]<0]; print("negativos",len(neg),[ (r["n"],round(r["pct"])) for r in neg][:20])
tot_inf=sum(r["perd_mes_inf"] for r in rows); tot_caja=sum(r["perd_mes_caja"] for r in rows)
print("TOTAL mes inf",tot_inf/1e6,"caja",tot_caja/1e6)
# serie semanal (valor a precio informado) top productos positivos
pos=[r for r in rows if r["sob_sem"]>0]
serie=[]
for w in complete:
    s=sum(max(P[(r["id"],w)]-V[(r["id"],w)],0)*0 + (P[(r["id"],w)]-V[(r["id"],w)])*(r["precio_inf"] or 0) for r in pos)
    p_tot=sum(P[(r["id"],w)]*(r["precio_inf"] or 0) for r in pos)
    serie.append([w,round(s),round(p_tot)])
print(serie)
json.dump(dict(rows=rows,serie=serie,complete=complete,weeks=weeks), open("merma_out.json","w"), default=str)
