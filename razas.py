# -*- coding: utf-8 -*-
import re,sys,json,unicodedata
RUTA=sys.argv[1] if len(sys.argv)>1 else "/mnt/project/Gaethar_Completo_en_Revisión_18062026.docx"
L=open(RUTA,encoding="utf-8").read().split("\n")
def lim(s): return re.sub(r"\s+"," ",re.sub(r"\*+","",s)).strip()

# campo tipo  **Etiqueta: **valor   /  **Etiqueta**: valor
re_rac=re.compile(r"^(.+?)\s*\((Pasiva|Reacción|Acción Mayor|Acción Menor|Acción Libre|Acción)"
                    r"(?:\s+(Nieten|Menisc))?"
                    r"(?:,\s*(\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñ ]+?))?"
                    r"(?:,\s*(FUE|AGI|CON|INT|VOL|CM|CD))?\)$")
re_campo=re.compile(r"^\*{0,2}([A-Za-zÁÉÍÓÚáéíóúñ ]+?)\*{0,2}\s*:\s*\*{0,2}\s*(.+?)\*{0,2}\s*$")
# racial:  **Nombre** (Pasiva)  |  **Nombre **(Reacción, 1 Versatilidad)
ATR=r"(?:FUE|AGI|CON|INT|VOL|CM|CD|Afinidad Mágica)"

# --- jerarquía tomada del índice: especie (Título) seguida de sus razas (MAYÚSCULAS) ---
def jerarquia():
    esp,orden=[],[]
    dentro=False
    for l in L[:1100]:
        s=l.strip().split("\t")[0].strip()
        if s=="COMPENDIO DE RAZAS": dentro=True; continue
        if not dentro or not s: continue
        if s in ("CLASES","COMPENDIO DE CLASES","TRASFONDOS"): break
        if s.startswith(("Historia","Cultura","Conflictos","Relaciones","La ","Los ","El ","Sociedad","Características","Lo Que","Medicina","Monturas","Conocimiento","Comercio")): continue
        if s==s.upper() and re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ -]+$",s):
            if esp: orden.append(("raza",s.title(),esp[-1]))
        elif (s[0].isupper() and len(s)<22 and re.match(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ ]+$",s)
              and (len(s.split())==1 or s=="Ogros de Clan")):
            esp.append(s); orden.append(("especie",s,None))
    return esp,orden
ESPECIES_ORD,ORDEN=jerarquia()
ES_MAY=lambda s: s==s.upper()
def encabezado(i,tipo):
    for k in range(i-1,max(0,i-260),-1):
        s=L[k].strip()
        if not s or len(s)>24 or len(s)<3: continue
        if not re.match(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ][A-Za-zÁÉÍÓÚÑáéíóúñ -]+$",s): continue
        if tipo=="raza" and ES_MAY(s): return s.title()
        if tipo=="especie" and not ES_MAY(s) and s[0].isupper(): return s
    return None

def leer_bloque(i):
    d={"campos":{},"raciales":[]}
    for k in range(i+1,min(i+60,len(L))):
        s=L[k].strip()
        if not s: continue
        if s==s.upper() and 3<=len(s)<=24 and re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ -]+$",s): break
        if s.startswith("Características"): break
        mr=re_rac.match(lim(s)) if s.startswith("**") else None
        if mr:
            desc=""
            for j in range(k+1,min(k+3,len(L))):
                if L[j].strip(): desc=lim(L[j]); break
            d["raciales"].append({"nombre":mr.group(1).strip(),"accion":mr.group(2),
                "forma":mr.group(3),
                "costo":int(mr.group(4)) if mr.group(4) else None,
                "recurso":lim(mr.group(5)) if mr.group(5) else None,
                "salvacion":mr.group(6),"_desc":desc})
            continue
        mc=re_campo.match(s)
        if mc and len(mc.group(1))<40: d["campos"][lim(mc.group(1))]=lim(mc.group(2))
    return d

especies,razas=[],[]
for i,l in enumerate(L):
    s=l.strip()
    if s=="Características de Especie": especies.append((None,leer_bloque(i)))
    elif s=="Características de Raza":  razas.append((None,leer_bloque(i)))

# asignar nombres por orden documental usando la jerarquía del índice
_e=[x for x in ORDEN if x[0]=="especie"]; _r=[x for x in ORDEN if x[0]=="raza"]
especies=[(_e[i][1] if i<len(_e) else "???",d) for i,(_,d) in enumerate(especies)]
razas=[((_r[i][1],_r[i][2]) if i<len(_r) else ("???",None),d) for i,(_,d) in enumerate(razas)]
def bonos(t):
    if not t: return {}
    out={}
    for n,a in re.findall(r"\+\s*(\d+)\s*("+ATR+r")",t,re.I): out[a.upper().replace("AFINIDAD MÁGICA","AM")]=int(n)
    return out

# el nombre fiable de la especie viene en Movimiento: "9 m (30 pies) (Humanoide, Elfo)"
def especie_de(c):
    m=re.search(r"\(Humanoide,\s*([^)]+)\)",c.get("Movimiento",""))
    return m.group(1).strip() if m else None
print(f"ESPECIES: {len(especies)}   RAZAS: {len(razas)}\n")
for n,d in especies:
    c=d["campos"]
    print(f"◆ {n}   (tipo: {especie_de(c) or '—'})")
    print(f"   bonos={bonos(c.get('Bonificación de Atributos'))} "
          f"mov={c.get('Movimiento','—')[:12]} tam={c.get('Tamaño','—')[:10]} rec={c.get('Recurso Racial','—')}")
    comp=c.get('Competencias Practicadas') or c.get('Competencia Practicada') or '—'
    print(f"   comp={comp[:46]} | debilidad={(c.get('Debilidad Racial') or '—')[:38]}")
    for r in d["raciales"]: print(f"     · {r['nombre']} ({r['accion']}{', '+str(r['costo'])+' '+r['recurso'] if r['costo'] else ''})")
print("\n— RAZAS —")
for n,d in razas:
    c=d["campos"]
    comp=c.get('Competencia Practicada') or c.get('Competencias Practicadas') or '—'
    print(f"  {n[0]:14s} [{str(n[1]):12s}] comp={comp[:26]:26s} raciales={[r['nombre']+('/'+r['forma'] if r.get('forma') else '') for r in d['raciales']]}")
json.dump({"especies":[{"nombre":n,**d} for n,d in especies],"razas":[{"nombre":n[0],"especie":n[1],**d} for n,d in razas]},
          open("razas.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
