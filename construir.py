# -*- coding: utf-8 -*-
"""Une los tres parsers en datos.json (sin descripciones)."""
import json, subprocess, sys, hashlib, datetime, re

M = sys.argv[1] if len(sys.argv)>1 else "/mnt/project/Gaethar_Completo_en_Revisión_18062026.docx"
for s in ("parser.py","razas.py","trasfondos.py"):
    subprocess.run([sys.executable,s,M],capture_output=True)

crudo = json.load(open("crudo.json",encoding="utf-8"))
raz   = json.load(open("razas.json",encoding="utf-8"))
tra   = json.load(open("trasfondos.json",encoding="utf-8"))

def campo(c,*claves):
    for k in claves:
        if k in c: return c[k]
    return None
def eleccionLibre(t):
    m=re.search(r"\+\s*(\d+)\s+a\s+(\d+)\s+Atributos?\s+de\s+tu\s+[Ee]lecci",t or "")
    return {"valor":int(m.group(1)),"cantidad":int(m.group(2))} if m else None
def bonos(t):
    if not t: return {}
    t=re.sub(r"C\.\s*M\.?","CM",t,flags=re.I); t=re.sub(r"C\.\s*D\.?","CD",t,flags=re.I)
    out={}
    for n,a in re.findall(r"\+\s*(\d+)\s*(FUE|AGI|CON|INT|VOL|CM|CD|Afinidad Mágica)",t,re.I):
        out[a.upper().replace("AFINIDAD MÁGICA","AM")]=int(n)
    return out
def comps(c):
    """competencias practicadas/entrenadas declaradas en un bloque de especie o raza"""
    out=[]
    for k,niv in (("Competencias Practicadas","Practicado"),("Competencia Practicada","Practicado"),
                  ("Competencias Entrenadas","Entrenado"),("Competencia Entrenada","Entrenado"),
                  ("Profesión Practicada","Practicado"),("Profesión Entrenada","Entrenado")):
        if k in c:
            for p in re.split(r"\s+[ye]\s+|,\s*",c[k]):
                p=p.strip(" .")
                if p: out.append({"nombre":p,"nivel":niv,"profesion":"Profesión" in k})
    return out

especies=[]
for e in raz["especies"]:
    c=e["campos"]
    especies.append({"nombre":e["nombre"],
        "bonosAtributo":bonos(campo(c,"Bonificación de Atributos","Bonificación")),
        "bonosALibreEleccion":eleccionLibre(campo(c,"Bonificación de Atributos","Bonificación")),
        "competencias":comps(c),
        "movimiento":campo(c,"Movimiento"),
        "tamano":(campo(c,"Tamaño") or ("Mediano" if e["nombre"]=="Deorcyn" else None)),
        "idiomas":campo(c,"Idiomas"),
        "recursoRacial":campo(c,"Recurso Racial"),
        "debilidad":campo(c,"Debilidad Racial"),
        "penalizacionAtributo":{},   # las debilidades raciales ya no restan atributos
        "raciales":[{k:v for k,v in r.items() if not k.startswith("_")} for r in e["raciales"]]})

razas=[]
for r in raz["razas"]:
    c=r["campos"]
    razas.append({"nombre":r["nombre"],"especie":r["especie"],
        "bonosAtributo":bonos(campo(c,"Bonificación de Atributos","Bonificación")),
        "competencias":comps(c),
        "movimiento":campo(c,"Movimiento"),
        "raciales":[{k:v for k,v in x.items() if not k.startswith("_")} for x in r["raciales"]]})

espec=crudo.get("especializaciones",{})
# ── escuela base por clase, acceso extra por subclase/especialización, descuentos de PN ──
import unicodedata as _u
LINEAS=open(M,encoding="utf-8").read().split("\n")
def _lim(s): return re.sub(r"\s+"," ",re.sub(r"\*+","",s)).strip()
ESCUELAS_TXT=["Arcana","Astromancia","Belomancia","Criomancia","Encantamiento","Ilusión",
              "Luminaria","Naturaleza","Piromancia","Umbría","Voltaica"]
def escuelas_en(t):
    return [e for e in ESCUELAS_TXT if re.search(r"\b"+e+r"\b",t or "",re.I)]

# escuela base: la técnica "Hechizos Básicos" de cada clase dice de qué escuela
RE_COMPRA=re.compile(r"\(\d+\s*P\.?\s*N\.?\)\s*:\s*(?:Elige|Puedes seleccionar|Puedes comprar)\s+1\s+Hechizo",re.I)
escuelaBase={}; escuelaSubclase={}
for e in crudo["entradas"]:
    ln=e.get("_linea")
    if ln is None or not e["clase"]: continue
    for j in range(ln+1,min(ln+4,len(LINEAS))):
        t=_lim(LINEAS[j])
        if not t: continue
        if RE_COMPRA.search(t):
            m=re.search(r"de la escuela(?:\s+de)?\s+([A-ZÁÉÍÓÚ][a-záéíóúñ]+)",t)
            if m and m.group(1) in ESCUELAS_TXT:
                if e["subclase"]: escuelaSubclase.setdefault((e["clase"],e["subclase"]),m.group(1))
                else: escuelaBase.setdefault(e["clase"],m.group(1))
            elif re.search(r"lista de Hechizos Principales",t):
                escuelaBase.setdefault(e["clase"],"__disciplina__")
        break

# acceso adicional otorgado por texto de especialización o por una técnica pasiva
accesoExtra={}   # (clase, nombre_opcion) -> [escuelas]
for cl,esp in espec.items():
    for i,l in enumerate(LINEAS):
        m=re.match(r"^-\s*\*\*(.+?)\*\*\s*:\s*(.+)$",l.strip())
        if not m: continue
        op=_lim(m.group(1))
        if op not in esp["opciones"]: continue
        txt=m.group(2)
        esc=[]
        for pat in (r"acceso a la [Mm]agia\s+([A-ZÁÉÍÓÚ][a-záéíóúñ]+)",
                    r"hechizos de la escuela(?:\s+de)?\s+([A-ZÁÉÍÓÚ][a-záéíóúñ]+)"):
            esc+=[x for x in re.findall(pat,txt) if x in ESCUELAS_TXT]
        if esc: accesoExtra[cl+"|"+op]=sorted(set(esc))
# técnicas que dan acceso (p.ej. Hechicero Innato del Guardian de la Convergencia)
accesoTecnica={}
for e in crudo["entradas"]:
    ln=e.get("_linea")
    if ln is None or not e["clase"]: continue
    for j in range(ln+1,min(ln+4,len(LINEAS))):
        t=_lim(LINEAS[j])
        if not t: continue
        m=re.search(r"[Pp]uedes aprender [Hh]echizos de la escuela(?:\s+de)?\s+([A-ZÁÉÍÓÚ][a-záéíóúñ]+)",t)
        if m and m.group(1) in ESCUELAS_TXT: accesoTecnica[e["tipo"]+"|"+e["nombre"]]=[m.group(1)]
        break

# descuentos de P.N. declarados por técnicas pasivas
descuentos={}
for e in crudo["entradas"]:
    ln=e.get("_linea")
    if ln is None: continue
    for j in range(ln+1,min(ln+4,len(LINEAS))):
        t=_lim(LINEAS[j])
        if not t: continue
        m=re.search(r"[Aa]prender [Hh]echizos?\s+(.*?)cuesta[n]?\s+(\d+)\s*P\.?\s*N\.?\s*menos",t)
        if m:
            ambito,monto=m.group(1),int(m.group(2))
            esc=escuelas_en(ambito)
            if not esc:
                mg=(espec.get(e["clase"],{}).get("magias") or {}).get(e["subclase"] or "",{})
                esc=(mg.get("Principal") or {}).get("escuelas") if isinstance(mg.get("Principal"),dict) else (mg.get("Principal") or [])
                esc=esc or escuelas_en(e["subclase"] or "")
            # Los descuentos de disciplina aplican a TODOS los tiers en las 5 subclases del Mago.
            # El manual solo menciona un tier en el Ilusionista, pero es una inconsistencia
            # de redacción, no una regla distinta: se normaliza aquí.
            descuentos[e["tipo"]+"|"+e["nombre"]]={"monto":monto,"escuelas":esc,"tiers":[]}
        break

# normalizar magias: "(solo 1 de ellas)" → elección
for cl,e in espec.items():
    for op,mg in (e.get("magias") or {}).items():
        for tipo,lst in list(mg.items()):
            eleccion=any("solo 1" in x.lower() for x in lst)
            lst=[re.sub(r"\s*\(.*?\)","",x).strip() for x in lst]
            mg[tipo]={"escuelas":lst,"eligeUna":eleccion or (tipo=="Complementaria")}

clases=[{"nombre":n,"recurso":c["recurso"],"bonosAtributo":c["bonosAtributo"],
         "competencias":c["competencias"],"otrasCompetencias":c["otrasCompetencias"],
         "especializacion":espec.get(n),
         "subclases":sorted({e["subclase"] for e in crudo["entradas"] if e["clase"]==n and e["subclase"]})}
        for n,c in crudo["clases"].items()]

entradas=[{k:v for k,v in e.items() if not k.startswith("_")} for e in crudo["entradas"]]

# ════════════════════════════════════════════════════════════════════
#  AJUSTES — correcciones que aún NO están en el manual.
#  Cuando actualices el manual, borra la entrada correspondiente de aquí.
# ════════════════════════════════════════════════════════════════════
AJUSTES_CLASE={
  "Guerrero":{"bonosAtributo":{"FUE":5,"CM":5}},          # antes: CM+5, CD+5
  "Pícaro":{"competencias":{"Juego de Manos":"Practicado",# antes: Entrenado
                            "Forzar Cerraduras":"Entrenado"}},  # antes: Practicado
}
for c in clases:
    aj=AJUSTES_CLASE.get(c["nombre"])
    if not aj: continue
    if "bonosAtributo" in aj: c["bonosAtributo"]=aj["bonosAtributo"]
    for hab,niv in (aj.get("competencias") or {}).items():
        for x in c["competencias"]:
            if x["habilidad"]==hab: x["nivel"]=niv

# ── Nombres en singular ──
SINGULAR={"Humanos":"Humano","Elfos":"Elfo","Enanos":"Enano","Medianos":"Mediano",
          "Orcos":"Orco","Ogros de Clan":"Ogro de Clan",
          "Kalethianos":"Kalethiano","Valenianos":"Valeniano","Nodrimianos":"Nodrimiano"}
for e in especies: e["nombre"]=SINGULAR.get(e["nombre"],e["nombre"])
for r in razas:
    r["nombre"]=SINGULAR.get(r["nombre"],r["nombre"])
    r["especie"]=SINGULAR.get(r["especie"],r["especie"])
escuelaBase={SINGULAR.get(k,k):v for k,v in escuelaBase.items()}

# ── Entradas "Personalizado" (no vienen del manual) ──
tras_lista=sorted(tra["trasfondos"],key=lambda x:x["nombre"].lower())
tras_lista.append({"nombre":"Personalizado","bonosAtributo":{},"competencias":[],
  "beneficios":["Trasfondo libre: define con tu DM la historia, el bono y las competencias."],
  "bonosALibreEleccion":{"valor":10,"cantidad":1},"personalizado":True})

def_lista=sorted(tra["defectos"],key=lambda x:x["nombre"].lower())
def_lista.append({"nombre":"Personalizado","efecto":"Defecto libre: acuérdalo con tu DM.",
                  "personalizado":True})

datos={
 "version":datetime.date.today().isoformat(),
 "fuente":"Manual de Gaethar (revisión 18-06-2026)",
 "nota":"Paquete sin descripciones. Consulta el manual para el efecto de cada entrada.",
 "habilidades":crudo["habilidades"],
 "nivelesCompetencia":["Sin Practicar","Practicado","Entrenado","Experto"],
 "costosPN":{"tecnica":{"Básicas":3,"Avanzadas":6,"Maestras":9},
             "hechizo":{"Básicos":2,"Avanzados":4,"Maestros":6}},
 "especies":especies,"razas":razas,"clases":clases,
 "escuelasMagia":sorted({e["escuela"] for e in crudo["entradas"] if e["escuela"]}),
 "escuelaBase":escuelaBase,"escuelaSubclase":{k[0]+"|"+k[1]:v for k,v in escuelaSubclase.items()},
 "accesoExtra":accesoExtra,"accesoTecnica":accesoTecnica,"descuentosPN":descuentos,
 "estilosCombate":crudo.get("estilosCombate",[]),
 "trasfondos":tras_lista,"defectos":def_lista,"dotes":tra["dotes"],
 "entradas":entradas}

json.dump(datos,open("datos.json","w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
import os
print("datos.json →", round(os.path.getsize("datos.json")/1024,1),"KB")
for k in ("especies","razas","clases","trasfondos","defectos","dotes","entradas","habilidades","escuelasMagia","estilosCombate"):
    print(f"  {k:14s} {len(datos[k])}")
print("  raciales      ", sum(len(x['raciales']) for x in especies)+sum(len(x['raciales']) for x in razas))
faltan=[(x["nombre"],k) for x in especies for k in ("movimiento","tamano","recursoRacial") if not x[k]]
print("\ncampos vacíos en especies:", faltan or "ninguno")
