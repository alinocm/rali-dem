# -*- coding: utf-8 -*-
# verifier_experimentation.py
# Verification complete du module d'experimentation
# Usage : python verifier_experimentation.py

import sqlite3, os, csv, io, sys

print("=" * 60)
print("VERIFICATION MODULE EXPERIMENTATION RALI-DEM")
print("=" * 60)

# ── Trouver la base ───────────────────────────────────────────
DB = None
for path in ['database/rali_dem.db', 'backend/rali_dem.db']:
    if os.path.exists(path):
        DB = path
        break

if not DB:
    print("\nERREUR : Base de donnees non trouvee")
    sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"\nBase : {DB}")

# ── 1. Tables ─────────────────────────────────────────────────
print("\n[1] Tables experimentation :")
tables = ['exp_participants', 'exp_sessions',
          'exp_reponses', 'exp_eval_qualitative']
ok_tables = True
for t in tables:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  OK {t} : {n} ligne(s)")
        if n == 0:
            print(f"     -> Table vide : faites une session de test")
    except Exception as e:
        print(f"  ERREUR {t} : {e}")
        ok_tables = False

# ── 2. Participants ───────────────────────────────────────────
print("\n[2] Participants :")
parts = cur.execute("""
    SELECT code_anonyme, nom, prenom, email,
           niveau_etudes, etablissement, date_inscription
    FROM exp_participants
    ORDER BY date_inscription DESC
    LIMIT 5
""").fetchall()
if parts:
    for p in parts:
        print(f"  {p['code_anonyme']} | {p['prenom']} {p['nom']}"
              f" | {p['email']} | {p['niveau_etudes']}")
else:
    print("  Aucun participant encore")

# ── 3. Sessions ───────────────────────────────────────────────
print("\n[3] Sessions :")
sess = cur.execute("""
    SELECT s.code_session, s.statut,
           s.nb_questions_faites, s.score_global,
           p.code_anonyme
    FROM exp_sessions s
    JOIN exp_participants p ON s.participant_id = p.id
    ORDER BY s.date_debut DESC LIMIT 5
""").fetchall()
if sess:
    for s in sess:
        print(f"  {s['code_session']} | {s['statut']}"
              f" | {s['nb_questions_faites']} questions"
              f" | score: {s['score_global']}%"
              f" | {s['code_anonyme']}")
else:
    print("  Aucune session encore")

# ── 4. Validation ERT ─────────────────────────────────────────
print("\n[4] Validation ERT (temps reel vs predit) :")
ert_data = cur.execute("""
    SELECT ert_predit_s, temps_reel_s, est_correct,
           objectif_code, mode_bloom
    FROM exp_reponses
    WHERE temps_reel_s > 0 AND ert_predit_s > 0
    LIMIT 100
""").fetchall()

if ert_data:
    n = len(ert_data)
    moy_ert = sum(r['ert_predit_s'] for r in ert_data) / n
    moy_reel = sum(r['temps_reel_s'] for r in ert_data) / n
    taux_ok = sum(r['est_correct'] for r in ert_data) / n * 100

    print(f"  N reponses      : {n}")
    print(f"  ERT moyen predit : {moy_ert:.1f}s")
    print(f"  Temps moyen reel : {moy_reel:.1f}s")
    print(f"  Taux de reussite : {taux_ok:.1f}%")

    # Correlation simple (rang)
    if n >= 2:
        preds  = [r['ert_predit_s'] for r in ert_data]
        reels  = [r['temps_reel_s']  for r in ert_data]
        mean_p = sum(preds)/n
        mean_r = sum(reels)/n
        num = sum((p-mean_p)*(r-mean_r) for p,r in zip(preds,reels))
        den_p = (sum((p-mean_p)**2 for p in preds))**0.5
        den_r = (sum((r-mean_r)**2 for r in reels))**0.5
        if den_p > 0 and den_r > 0:
            corr = num / (den_p * den_r)
            print(f"  Correlation r(ERT, temps_reel) : {corr:.3f}")
        else:
            print("  Correlation : impossible (variance nulle)")
else:
    print("  Pas encore de donnees - faites une session de test")

# ── 5. Distracteurs ───────────────────────────────────────────
print("\n[5] Analyse distracteurs :")
dist = cur.execute("""
    SELECT objectif_code,
           COUNT(*) as total,
           SUM(CASE WHEN est_correct=0 THEN 1 ELSE 0 END) as erreurs,
           distracteur_choisi
    FROM exp_reponses
    WHERE est_correct = 0
    GROUP BY objectif_code
    ORDER BY erreurs DESC
    LIMIT 5
""").fetchall()
if dist:
    print("  Objectifs avec le plus d'erreurs :")
    for d in dist:
        print(f"  {d['objectif_code']} : {d['erreurs']} erreur(s)")
else:
    print("  Pas encore d'erreurs enregistrees")

# ── 6. Evaluation qualitative ─────────────────────────────────
print("\n[6] Evaluations qualitatives :")
eval_data = cur.execute("""
    SELECT AVG(grammaticalite) as gram,
           AVG(naturalite) as nat,
           AVG(clarte) as cla,
           AVG(plausibilite_dist) as plau,
           AVG(pertinence_obj) as pert,
           AVG(alignement_bloom) as bloom,
           AVG(acceptabilite) as acc,
           AVG(utilite_apprentissage) as util,
           AVG(score_global) as global,
           COUNT(*) as n
    FROM exp_eval_qualitative
""").fetchone()

if eval_data and eval_data['n'] > 0:
    n = eval_data['n']
    print(f"  N evaluations : {n}")
    print(f"  Coherence linguistique :")
    print(f"    Grammaticalite : {eval_data['gram']:.2f}/5")
    print(f"    Naturalite     : {eval_data['nat']:.2f}/5")
    print(f"    Clarte         : {eval_data['cla']:.2f}/5")
    print(f"  Plausibilite pedagogique :")
    print(f"    Distracteurs   : {eval_data['plau']:.2f}/5")
    print(f"    Pertinence obj.: {eval_data['pert']:.2f}/5")
    print(f"    Alignement Bloom:{eval_data['bloom']:.2f}/5")
    print(f"  Acceptabilite :")
    print(f"    Acceptabilite  : {eval_data['acc']:.2f}/5")
    print(f"    Utilite appr.  : {eval_data['util']:.2f}/5")
    print(f"  SCORE GLOBAL    : {eval_data['global']:.2f}/5")
else:
    print("  Pas encore d'evaluations")
    print("  -> Completez une session jusqu'a la fin (formulaire Likert)")

conn.close()

# ── Résumé ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESUME")
print("=" * 60)
print("Pour une experimentation valide, vous avez besoin de :")
print("  - 60 a 120 participants")
print("  - 60 a 120 sessions terminees")
print("  - 1800 a 3600 reponses (30 par session)")
print("  - 60 a 120 evaluations qualitatives")
print("\nPartagez le lien Railway avec vos etudiants :")
print("  https://web-production-a77a3.up.railway.app/experimentation")
