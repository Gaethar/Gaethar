# -*- coding: utf-8 -*-
"""Parser del Manual de Gaethar -> datos.json (regenerable)"""
import re, json, sys, collections, unicodedata

RUTA = sys.argv[1] if len(sys.argv)>1 else "/mnt/project/Gaethar_Completo_en_Revisión_18062026.docx"
txt = open(RUTA, encoding="utf-8").read()
lineas = txt.split("\n")

def limpiar(s): return re.sub(r"\s+"," ",re.sub(r"\*+","",s)).strip()
def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

PN_TEC = {"Básicas":3,"Avanzadas":6,"Maestras":9}
PN_HEC = {"Básicos":2,"Avanzados":4,"Maestros":6}

# ---------- 0. Lista oficial de habilidades ----------
HAB, atr_actual = [], None
for l in lineas[2960:3060]:
    s = limpiar(l)
    m = re.match(r"^Habilidades de \w+ \((FUE|AGI|CON|INT|VOL|CM|CD)\)$", s)
    if m: atr_actual = m.group(1); continue
    if s.isupper(): 
        if HAB: break
        continue
    if atr_actual and s and not s[0].islower() and len(s)<26 and "." not in s:
        HAB.append({"nombre":s,"atributo":atr_actual})
HABSET = {norm(h["nombre"]) for h in HAB}
# alias frecuentes en el texto de clases
ALIAS = {"acrobacias":"Acrobacia","juego de mano":"Juego de Manos"}

# ---------- 1. Técnicas y hechizos ----------
re_tier = re.compile(r"^(?:Técnicas|Hechizos)\s+(Básic[ao]s|Avanzad[ao]s|Maestr[ao]s|Expert[ao]s)\s*$")
re_nom  = re.compile(r"^(.+?)\s*\((Acción Mayor|Acción Menor|Acción Libre|Reacción|Pasiva|Acción)(?:\s+[^)]*)?\)$")
re_cost = re.compile(r"^\((\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñ ]+?)(?:,\s*([A-Z]{2,3}))?\)\s*:?\s*(.*)$")

# líneas donde arranca cada clase (encabezado en MAYÚSCULAS antes de "Recurso:")
CLASES_LN={}
for i,l in enumerate(lineas):
    if re.match(r"^\*{0,2}Recurso:\s*\*{0,2}\s*(.{1,20})\*{0,2}$", l.strip()):
        for k in range(i,max(0,i-160),-1):
            s=lineas[k].strip()
            if s and s==s.upper() and 3<=len(s)<=22 and re.match(r"^[A-ZÁÉÍÓÚÑ ]+$",s):
                CLASES_LN[k]=s.title(); break
LN_MAGIA=next((i for i,l in enumerate(lineas) if l.strip()=="ESCUELAS DE MAGIA"),len(lineas))
# escuelas: encabezado en MAYÚSCULAS seguido de "*Escuela de ...*"
ESCUELAS_LN={}
for i in range(LN_MAGIA,len(lineas)):
    if lineas[i].strip().startswith("*Escuela de"):
        for k in range(i-1,max(LN_MAGIA-1,i-6),-1):
            s=lineas[k].strip()
            if s and s==s.upper() and 3<=len(s)<=18 and re.match(r"^[A-ZÁÉÍÓÚÑ]+$",s):
                ESCUELAS_LN[k]=s.title(); break
ESC_ORD=sorted(ESCUELAS_LN)
def escuela_en(i):
    if i<LN_MAGIA: return None
    e=None
    for k in ESC_ORD:
        if k<=i: e=ESCUELAS_LN[k]
        else: break
    return e
LN_ORD=sorted(CLASES_LN)
def clase_en(i):
    if i>=LN_MAGIA: return None
    c=None
    for k in LN_ORD:
        if k<=i: c=CLASES_LN[k]
        else: break
    return c

# etiquetas de especialización por clase (Sendas, Maestrías, Círculos, Juramentos, Escuelas de Mando...)
especializaciones={}
re_esp=re.compile(r"^-\s*\*\*(.+?)\*\*\s*:")
for i,l in enumerate(lineas):
    if i>=LN_MAGIA: break
    s=limpiar(l)
    # etiqueta: línea suelta en Título, 4-26 chars, seguida en <=3 líneas de viñetas "- **X**:"
    if not (s and 4<=len(s)<=26 and s[0].isupper() and not s.startswith(("*","-","|","("))): continue
    if s.startswith(("Técnicas","Hechizos","Subclases","Equipo","Descripción","Mecánicas","Rol ","Cultura","Historia","Orígenes","Percepción","Una nota")): continue
    lst=[]; magias={}
    for k in range(i+1,min(i+40,len(lineas))):
        t=lineas[k].strip()
        if not t: continue
        m=re_esp.match(t)
        if m: lst.append(limpiar(m.group(1))); continue
        mm=re.match(r"^-\s*Magia\s+(Principal|Secundaria|Complementaria)\s*:?\s*(.+?)\.?$",limpiar(t),re.I)
        if mm and lst:
            magias.setdefault(lst[-1],{})[mm.group(1).capitalize()]=[
                x.strip(" .") for x in re.split(r"\s+[yo]\s+|,\s*",mm.group(2)) if x.strip(" .")]
            continue
        if t.startswith("-"): continue          # otra sub-viñeta: seguir
        if lst: break
        if k>i+3: break
    cl=clase_en(i)
    if cl and len(lst)>=2 and cl not in especializaciones:
        especializaciones[cl]={"etiqueta":s,"opciones":lst,**({"magias":magias} if magias else {})}

entradas, tier, subclase, _clase_prev = [], None, None, None
for i,l in enumerate(lineas):
    s=l.strip()
    _c=clase_en(i)
    if _c!=_clase_prev:          # al cambiar de clase se limpia la subclase
        subclase=None; _clase_prev=_c
    if i>=LN_MAGIA: subclase=None
    if limpiar(s)=="Subclases": subclase="__esperando__"; continue
    # nombre de subclase: línea suelta en Título justo antes de un bloque de tiers
    if subclase is not None and re_tier.match(limpiar(lineas[i+1].strip() if i+1<len(lineas) else "")) is None:
        pass
    mt=re_tier.match(limpiar(s)) if not s.startswith("**") else None
    if mt:
        t0=mt.group(1)
        tier=("Maestras" if t0.endswith("as") else "Maestros") if t0.startswith("Expert") else t0
        continue
    # detectar encabezado de subclase: línea corta en Título seguida (en <=4 líneas) de "Técnicas Básicas"
    if subclase is not None and s and len(s)<=28 and not s.startswith(("*","-","|","(")) and s[0].isupper():
        sig=[]
        for x in lineas[i+1:i+12]:
            if limpiar(x): sig.append(limpiar(x))
            if len(sig)>=3: break
        if any(x.startswith("Técnicas Básicas") for x in sig) or any(x.startswith("Hechizos Básicos") for x in sig):
            subclase=limpiar(s); continue
    mn=re_nom.match(limpiar(s)) if s.startswith("**") else None
    if not mn and s.startswith("**") and tier:
        # entrada sin tipo de acción: se valida por su línea de costo en P.N.
        c=limpiar(s)
        if 3<=len(c)<=40 and not c.endswith(":"):
            for j in range(i+1,min(i+4,len(lineas))):
                t=lineas[j].strip()
                if not t: continue
                mcost=re.match(r"^\((?:(\d+)\s*(?:P\.?\s*N\.?|[A-Za-zÁÉÍÓÚáéíóúñ ]+?)|(Pasiva))\s*(?:,[^)]*)?\)\s*:",t)
                if mcost:
                    acc="Pasiva" if mcost.group(2) else "Especial"
                    mn=type("M",(),{"group":lambda self,k,_c=c,_a=acc:{1:_c,2:_a}[k]})()
                break
    if not (mn and tier): continue
    costo=recurso=salv=None
    for j in range(i+1,min(i+4,len(lineas))):
        t=lineas[j].strip()
        if not t: continue
        mc=re_cost.match(t)
        if mc: costo,recurso,salv=int(mc.group(1)),limpiar(mc.group(2)),mc.group(3)
        break
    es_hechizo = tier in PN_HEC
    entradas.append({"nombre":mn.group(1).strip(),"accion":mn.group(2),
        "clase":clase_en(i),
        "escuela":escuela_en(i),
        "subclase":subclase if subclase and subclase!="__esperando__" else None,
        "tipo":"hechizo" if es_hechizo else "tecnica","tier":tier,
        "pn":(PN_HEC if es_hechizo else PN_TEC)[tier],
        "costo":costo,"recurso":recurso,"salvacion":salv,"_linea":i})

# ---------- 2. Clases ----------
NIVELES={"practicad":"Practicado","entrenad":"Entrenado","expert":"Experto","maestr":"Maestro"}
re_niv=re.compile(r"\b(practicad[oa]s?|entrenad[oa]s?|expert[oa]s?|maestr[oa]s?)\b",re.I)
clases={}
for idx,l in enumerate(lineas):
    m=re.match(r"^\*{0,2}Recurso:\s*\*{0,2}\s*(.+?)\*{0,2}$", l.strip())
    if not m: continue
    recurso=limpiar(m.group(1))
    if len(recurso)>20: continue           # descarta el glosario
    nombre=None
    for k in range(idx,max(0,idx-140),-1):
        s=lineas[k].strip()
        if s and s==s.upper() and 3<=len(s)<=22 and re.match(r"^[A-ZÁÉÍÓÚÑ ]+$",s):
            nombre=s.title(); break
    if not nombre: continue
    bonos,comps,otras={},[],[]
    for k in range(idx+1,min(idx+20,len(lineas))):
        s=limpiar(lineas[k])
        if s.startswith("Equipo") or s.startswith("Subclases") or s.startswith("Técnicas"): break
        if not s.startswith("-"): continue
        s=s.lstrip("- ").rstrip(" .,")
        sa=re.sub(r"C\.\s*M\.?","CM",s,flags=re.I); sa=re.sub(r"C\.\s*D\.?","CD",sa,flags=re.I)
        ATR=r"(?:FUE|AGI|CON|INT|VOL|CM|CD)"
        pares=re.findall(r"\+\s*(\d+)\s*("+ATR+r")",sa,re.I)
        if not pares: pares=[(n,a) for a,n in re.findall(r"("+ATR+r")\s*\+\s*(\d+)",sa,re.I)]
        if pares:
            for a,v in pares: bonos[v.upper()]=bonos.get(v.upper(),0)+int(a)
            continue
        mn=re_niv.search(s)
        if not mn: continue
        nivel=next(v for k2,v in NIVELES.items() if norm(mn.group(1)).startswith(k2))
        resto=re_niv.sub("",s).strip(" .,")
        halladas=[]
        for pieza in re.split(r"\s+[ye]\s+|,\s*",resto):
            p=pieza.strip(" .")
            if not p: continue
            key=norm(p)
            if key in HABSET: halladas.append(next(h["nombre"] for h in HAB if norm(h["nombre"])==key))
            elif key in ALIAS: halladas.append(ALIAS[key])
        if halladas:
            comps += [{"habilidad":x,"nivel":nivel} for x in halladas]
        else:
            otras.append({"texto":s,"nivel":nivel})   # armas, armaduras, escudos
    clases[nombre]={"recurso":recurso,"bonosAtributo":bonos,"competencias":comps,
                    "otrasCompetencias":otras,"_linea":idx}

print("HABILIDADES oficiales:",len(HAB),"→",[h["nombre"] for h in HAB])
print()
print("TÉCNICAS:",sum(1 for e in entradas if e["tipo"]=="tecnica"),
      " HECHIZOS:",sum(1 for e in entradas if e["tipo"]=="hechizo"))
print("con costo de recurso:",sum(1 for e in entradas if e["costo"] is not None),
      "| pasivas sin costo:",sum(1 for e in entradas if e["accion"]=="Pasiva"))
print()
ESTILOS=[]
_ln=next((i for i,l in enumerate(lineas) if l.strip()=="ESTILOS DE COMBATE"),None)
if _ln:
    for k in range(_ln+1,_ln+120):
        s=limpiar(lineas[k])
        if s in ("CLASES Y TÉCNICAS","DOTES"): break
        if s and 3<=len(s)<=30 and not s.startswith(("-","*","|","(")) and s[0].isupper() and "." not in s and s!=s.upper():
            if s not in ESTILOS: ESTILOS.append(s)
print("ESTILOS DE COMBATE:",len(ESTILOS),ESTILOS)
print()
print("ESPECIALIZACIONES:")
for c,e in especializaciones.items(): print(f"  {c:12s} {e['etiqueta']:18s} {e['opciones']}")
print()
import collections as _c
print("atribución de entradas:")
print("  con clase:",sum(1 for e in entradas if e['clase']),"/",len(entradas),
      "| con subclase:",sum(1 for e in entradas if e['subclase']))
print("  por clase:",dict(_c.Counter(e['clase'] for e in entradas if e['clase'])))
print("  por escuela:",dict(_c.Counter(e['escuela'] for e in entradas if e['escuela'])))
print("  sin atribuir:",sum(1 for e in entradas if not e['clase'] and not e['escuela']))
print()
print("CLASES:",len(clases))
for n,c in clases.items():
    print(f"  {n:12s} {c['recurso']:10s} bonos={c['bonosAtributo']} "
          f"comp={[(x['habilidad'],x['nivel'][:4]) for x in c['competencias']]} otras={len(c['otrasCompetencias'])}")
json.dump({"habilidades":HAB,"entradas":entradas,"clases":clases,"especializaciones":especializaciones,"estilosCombate":ESTILOS},
          open("crudo.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
