"""
installer.py — Script d'installation automatique RALI-DEM
Lance ce script depuis la racine du projet D:\RALI-DEM
pour mettre à jour tous les fichiers backend automatiquement.

Usage : python installer.py
"""
import os
import sys
import shutil
import urllib.request

# ── Fichiers à télécharger depuis les outputs ──────────────
# Ce script copie les fichiers depuis le dossier courant
# (là où tu as placé les fichiers téléchargés)

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
if not os.path.exists(BACKEND_DIR):
    # Si lancé depuis D:\RALI-DEM directement
    BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')

FILES = [
    'corrector.py',
    'adaptive.py',
    'exam.py',
    'tools.py',
    'generator.py',
]

print("=== Installation RALI-DEM ===\n")
print(f"Dossier backend : {os.path.abspath(BACKEND_DIR)}\n")

src_dir = os.path.dirname(os.path.abspath(__file__))

for fname in FILES:
    src  = os.path.join(src_dir, fname)
    dest = os.path.join(BACKEND_DIR, fname)
    if os.path.exists(src):
        shutil.copy2(src, dest)
        print(f"  ✅ {fname} installé")
    else:
        print(f"  ⚠️  {fname} introuvable dans {src_dir}")

print("\n=== Vérification des imports ===\n")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

checks = [
    ('corrector', ['corriger']),
    ('adaptive',  ['init_tables_adaptatives', 'creer_session',
                   'enregistrer_reponse', 'terminer_session']),
    ('exam',      ['init_tables_examen', 'creer_examen',
                   'soumettre_reponse', 'get_bulletin']),
    ('tools',     ['get_rapport_erreurs', 'get_indice',
                   'exporter_fiche_html']),
    ('generator', ['generer_question']),
]

all_ok = True
for module, funcs in checks:
    try:
        mod = __import__(module)
        missing = [f for f in funcs if not hasattr(mod, f)]
        if missing:
            print(f"  ❌ {module}.py — fonctions manquantes : {missing}")
            all_ok = False
        else:
            print(f"  ✅ {module}.py — OK ({len(funcs)} fonctions vérifiées)")
    except ImportError as e:
        print(f"  ❌ {module}.py — Erreur import : {e}")
        all_ok = False

print()
if all_ok:
    print("✅ Tous les fichiers sont correctement installés !")
    print("\nTu peux maintenant lancer :")
    print("  python backend/main.py")
else:
    print("⚠️  Certains fichiers ont des problèmes.")
    print("Assure-toi que tous les fichiers .py sont dans le même dossier que installer.py")
