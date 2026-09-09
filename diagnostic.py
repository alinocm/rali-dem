# -*- coding: utf-8 -*-
import sys, os, ast, re, socket
from collections import Counter

print("=" * 55)
print("DIAGNOSTIC RALI-DEM")
print("=" * 55)

print(f"\n[1] Python : {sys.version}")

print("\n[2] Fichiers backend :")
backend = 'backend'
for f in ['main.py','experimentation.py','database.py',
          'generator.py','auth.py']:
    ok = os.path.exists(os.path.join(backend, f))
    print(f"  {'OK' if ok else 'MANQUANT'} {f}")

print("\n[3] Import des modules :")
sys.path.insert(0, backend)
for m in ['database','generator','auth','experimentation']:
    try:
        __import__(m)
        print(f"  OK {m}")
    except Exception as e:
        print(f"  ERREUR {m} : {e}")

print("\n[4] Analyse de main.py :")
try:
    path_main = os.path.join(backend, 'main.py')
    with open(path_main, encoding='utf-8', errors='replace') as f:
        src = f.read()

    # Vérifier encodage déclaré
    l1 = src.split('\n')[0]
    if 'coding' in l1:
        print(f"  OK Encodage declare : {l1.strip()}")
    else:
        print(f"  AVERT Pas de declaration encodage en ligne 1")

    # Syntaxe
    try:
        ast.parse(src)
        print("  OK Syntaxe Python")
    except SyntaxError as e:
        print(f"  ERREUR Syntaxe ligne {e.lineno}: {e.msg}")

    # Doublons de routes
    routes = re.findall(
        r'@app\.(get|post|put|delete)\("([^"]+)"\)', src)
    counts = Counter(routes)
    doublons = [(r,c) for r,c in counts.items() if c>1]
    if doublons:
        print(f"  ERREUR Routes en doublon :")
        for r,c in doublons:
            print(f"     {r[0].upper()} {r[1]} ({c}x)")
    else:
        print(f"  OK Pas de doublon ({len(routes)} routes)")

    # Taille
    print(f"  OK Taille : {len(src)} caracteres")

except Exception as e:
    print(f"  ERREUR : {e}")

print("\n[5] Base de donnees :")
for path in ['database/rali_dem.db','backend/rali_dem.db']:
    if os.path.exists(path):
        import sqlite3
        conn = sqlite3.connect(path)
        cur  = conn.cursor()
        tables = [t[0] for t in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        exp = [t for t in tables if t.startswith('exp_')]
        print(f"  OK {path}")
        for t in exp:
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"     {t} : {n} ligne(s)")
        conn.close()
        break
else:
    print("  ERREUR Base non trouvee")

print("\n[6] Port 8000 :")
s = socket.socket()
try:
    s.bind(('127.0.0.1', 8000))
    s.close()
    print("  OK Port 8000 libre")
except OSError:
    print("  AVERT Port 8000 deja utilise")

print("\n[7] Test rapide application :")
try:
    import urllib.request
    req = urllib.request.urlopen(
        'http://127.0.0.1:8000/api/diagnostic', timeout=3)
    print(f"  OK Application repond (status {req.status})")
except Exception as e:
    print(f"  INFO Application non accessible : {e}")
    print("       (normal si elle n'est pas lancee)")

print("\n" + "=" * 55)
print("FIN DU DIAGNOSTIC")
print("=" * 55)
