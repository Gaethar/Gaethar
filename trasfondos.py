# -*- coding: utf-8 -*-
import re,sys,json,unicodedata
RUTA=sys.argv[1] if len(sys.argv)>1 else "/mnt/project/Gaethar_Completo_en_Revisión_18062026.docx"
L=open(RUTA,encoding="utf-8").read().split("\n")
def lim(s): return re.sub(r"\s+"," ",re.sub(r"\*+","",s)).strip()
def norm(s):
    s=unicodedata.normalize("NFD",s.lower()); return "".join(c for c in s if unicodedata.category(c)!="Mn")

HAB=['Acrobacia','Juego de Manos','Sigilo','Forzar Cerraduras','Atletismo','Manejo de Animales','Historia',
     'Investigación','Medicina','Naturaleza','Percepción','Supervivencia','Arcana','Reparación','Religión',
     'Engaño','Perspicacia','Intimidación','Actuación','Persuasión']
HN={norm(h):h for h in HAB}; HN["acrobacias"]="Acrobacia"
ATR=r"(?:FUE|AGI|CON|INT|VOL|CM|CD)"
NIVMAP={"practic":"Practicado","entrenad":"Entrenado","expert":"Experto"}
re_niv=re.compile(r"\b(practicad[oa]s?|practica|entrenad[oa]s?|expert[oa]s?)\b",re.I)

def secciones(ini,fin):
    out,cur=[],None
    for i in range(ini,fin):
        s=lim(L[i])
        m=re.match(r"^\d+\.\s+(.+)$",s)
        if m:
            cur={"nombre":m.group(1).strip(),"_i":i,"lineas":[]}; out.append(cur)
        elif cur and s: cur["lineas"].append(s)
    return out

def parse_trasfondo(sec):
    d={"nombre":sec["nombre"],"bonosAtributo":{},"competencias":[],"beneficios":[]}
    for s in sec["lineas"]:
        sa=re.sub(r"C\.\s*M\.?","CM",s,flags=re.I); sa=re.sub(r"C\.\s*D\.?","CD",sa,flags=re.I)
        pares=re.findall(r"\+\s*(\d+)\s*("+ATR+r")",sa,re.I)
        if pares and not s.startswith("-"):
            if re.search(r"\so\s",sa) and len(pares)>1:
                d["eleccionAtributo"]=[{"atributo":a.upper(),"valor":int(n)} for n,a in pares]
            else:
                for n,a in pares: d["bonosAtributo"][a.upper()]=int(n)
            continue
        t=s.lstrip("- ").rstrip(" .")
        me=re.match(r"^(\d+)\s+habilidad(?:es)?\s+(Practicad|Entrenad|Expert)",t,re.I)
        if me:
            d.setdefault("competenciasAEleccion",[]).append(
                {"cantidad":int(me.group(1)),
                 "nivel":next(v for k,v in NIVMAP.items() if me.group(2).lower().startswith(k[:6]))})
            continue
        mn=re_niv.search(t)
        if mn:
            niv=next(v for k,v in NIVMAP.items() if norm(mn.group(1)).startswith(k))
            resto=re_niv.sub("",t); resto=re.sub(r"^\s*en\s+","",resto,flags=re.I).strip(" .")
            hall=[HN[norm(p.strip(" ."))] for p in re.split(r"\s+[ye]\s+|,\s*",resto) if norm(p.strip(" ."))in HN]
            if hall:
                d["competencias"]+=[{"habilidad":x,"nivel":niv} for x in hall]; continue
        d["beneficios"].append(t)
    return d

ini=next(i for i,l in enumerate(L) if l.strip()=="TRASFONDOS")
fdef=next(i for i,l in enumerate(L) if l.strip()=="DEFECTOS" and i>ini)
fdot=next(i for i,l in enumerate(L) if l.strip()=="DOTES" and i>ini)
tras=[parse_trasfondo(s) for s in secciones(ini,min(fdef,fdot))]
defec=[{"nombre":s["nombre"],"efecto":" ".join(s["lineas"])[:400]} for s in secciones(fdef,fdef+200)]
dotes=[]
for i in range(fdot,fdef):
    m=re.match(r"^\|\s*\*{0,2}(\d+)\*{0,2}\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",L[i].strip())
    if m: dotes.append({"n":int(m.group(1)),"nombre":lim(m.group(2)),"efecto":lim(m.group(3))})

print(f"TRASFONDOS: {len(tras)}  DEFECTOS: {len(defec)}  DOTES: {len(dotes)}\n")
for t in tras:
    c=", ".join(f"{x['habilidad']}({x['nivel'][:4]})" for x in t["competencias"]) or "—"
    print(f"  {t['nombre']:20s} {str(t['bonosAtributo']):16s} {c[:52]:52s} +{len(t['beneficios'])} benef.")
sin=[t["nombre"] for t in tras if not t["competencias"]]
print("\nsin competencias detectadas:",sin or "ninguno")
print("sin bono de atributo:",[t["nombre"] for t in tras if not t["bonosAtributo"]] or "ninguno")
json.dump({"trasfondos":tras,"defectos":defec,"dotes":dotes},open("trasfondos.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
