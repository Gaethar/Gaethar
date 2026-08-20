# -*- coding: utf-8 -*-
"""Reglas de Gaethar: apilamiento de competencias y multiclase. Verificación."""
NIV=["Sin Practicar","Practicado","Entrenado","Experto"]   # manual, cap. Competencias: cuatro niveles
def ix(n): return NIV.index(n)

def apilar(otorgamientos):
    """1er otorgamiento: su valor tal cual (puede ser Maestro).
       Cada otorgamiento posterior: max(actual+1, otorgado), tope Experto."""
    if not otorgamientos: return NIV[0]
    base = max(ix(o) for o in otorgamientos)          # el mayor otorgamiento manda
    extra = len(otorgamientos) - 1                    # cada duplicado sube 1
    return NIV[max(base, min(base + extra, ix("Experto")))]  # tope Experto, nunca baja

def mc_nivel(nivel_original, nivel_en_clase):
    """Multiclase: todo llega Practicado; a nivel 3 se restaura lo Entrenado,
       a nivel 5 lo Experto. Nunca supera su valor original."""
    if nivel_en_clase < 1: return None
    tope = ix(nivel_original)
    if   nivel_en_clase >= 5: permitido = ix("Experto")
    elif nivel_en_clase >= 3: permitido = ix("Entrenado")
    else:                     permitido = ix("Practicado")
    return NIV[min(tope, permitido)]

print("— APILAMIENTO —")
casos=[(["Practicado","Practicado"],"Entrenado"),
       (["Practicado","Practicado","Practicado"],"Experto"),
       (["Entrenado","Practicado"],"Experto"),
       (["Entrenado","Entrenado"],"Experto"),
       (["Practicado","Entrenado"],"Experto"),
       (["Practicado"],"Practicado"),
       (["Entrenado","Entrenado","Practicado"],"Experto"),
       (["Experto"],"Experto"),(["Experto","Practicado"],"Experto"),(["Experto","Entrenado","Practicado"],"Experto"),(["Practicado","Practicado","Practicado","Practicado"],"Experto")]
for ent,esp in casos:
    got=apilar(ent); print(("  ✓" if got==esp else "  ✗"),"+".join(ent),"→",got,"" if got==esp else f"(esperado {esp})")

print("\n— MULTICLASE (competencia original → por nivel en la clase nueva) —")
print("  nivel:      1           3           5")
for orig in ["Practicado","Entrenado","Experto"]:
    fila=[mc_nivel(orig,n) for n in (1,3,5)]
    print(f"  {orig:11s} "+"  ".join(f"{x:11s}" for x in fila))

print("\n— COMBINADO: Pícaro 1º + multiclase Guerrero —")
# Pícaro da Acrobacia Practicado; Guerrero da Acrobacia Entrenado (original)
for n in (1,3,5):
    mc=mc_nivel("Entrenado",n)
    print(f"  Guerrero nv{n}: Pícaro(Practicado) + MC({mc}) → {apilar(['Practicado',mc])}")
