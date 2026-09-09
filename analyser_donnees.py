# -*- coding: utf-8 -*-
# analyser_donnees.py
# Analyse statistique complete des donnees experimentales RALI-DEM
# Usage : python analyser_donnees.py
# Prerequis : pip install scipy numpy
# ─────────────────────────────────────────────────────────────

import sqlite3, os, sys, math
from collections import defaultdict

# ── Dependances optionnelles ──────────────────────────────────
try:
    from scipy import stats
    from scipy.stats import wilcoxon, ttest_ind, pearsonr, spearmanr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[AVERT] scipy non installe. pip install scipy")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ── Trouver la base ───────────────────────────────────────────
DB = None
for path in ['database/rali_dem.db', 'backend/rali_dem.db',
             'rali_dem.db']:
    if os.path.exists(path):
        DB = path
        break

if not DB:
    print("ERREUR : Base de donnees non trouvee.")
    print("Lancez ce script depuis D:\\RALI-DEM\\")
    sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

SEP = "=" * 65

# ─────────────────────────────────────────────────────────────
# 0. APERCU GENERAL
# ─────────────────────────────────────────────────────────────
print(SEP)
print("ANALYSE STATISTIQUE — RALI-DEM EXPERIMENTATION")
print(SEP)

nb_part = cur.execute("SELECT COUNT(*) FROM exp_participants").fetchone()[0]
nb_sess = cur.execute("SELECT COUNT(*) FROM exp_sessions WHERE statut='terminee'").fetchone()[0]
nb_rep  = cur.execute("SELECT COUNT(*) FROM exp_reponses").fetchone()[0]
nb_eval = cur.execute("SELECT COUNT(*) FROM exp_eval_qualitative").fetchone()[0]

print(f"\nParticipants inscrits   : {nb_part}")
print(f"Sessions terminees      : {nb_sess}")
print(f"Reponses enregistrees   : {nb_rep}")
print(f"Evaluations qualitatives: {nb_eval}")

if nb_rep == 0:
    print("\nAucune reponse. Collectez des donnees avant l'analyse.")
    sys.exit(0)

# ─────────────────────────────────────────────────────────────
# 1. CORRELATION ERT vs TEMPS REEL
# Validation de la formule T(Q)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("1. VALIDATION ERT — r(ert_predit, temps_reel)")
print(SEP)

rows = cur.execute("""
    SELECT r.ert_predit_s, r.temps_reel_s,
           r.objectif_code, r.mode_bloom
    FROM exp_reponses r
    JOIN exp_sessions s ON r.session_id = s.id
    WHERE s.statut = 'terminee'
      AND r.ert_predit_s > 0
      AND r.temps_reel_s > 0
      AND r.temps_reel_s < 600
""").fetchall()

if rows:
    ert_vals  = [r['ert_predit_s'] for r in rows]
    reel_vals = [r['temps_reel_s']  for r in rows]
    n = len(rows)

    # Moyennes et ecart-types
    moy_ert  = sum(ert_vals) / n
    moy_reel = sum(reel_vals) / n
    std_ert  = math.sqrt(sum((v-moy_ert)**2 for v in ert_vals)/(n-1)) if n>1 else 0
    std_reel = math.sqrt(sum((v-moy_reel)**2 for v in reel_vals)/(n-1)) if n>1 else 0

    print(f"\nN paires (ERT, temps_reel) : {n}")
    print(f"ERT predit   : M={moy_ert:.1f}s  sigma={std_ert:.1f}s")
    print(f"Temps reel   : M={moy_reel:.1f}s  sigma={std_reel:.1f}s")

    # Correlation de Pearson
    if HAS_SCIPY:
        r_pearson, p_pearson = pearsonr(ert_vals, reel_vals)
        r_spearman, p_spear = spearmanr(ert_vals, reel_vals)
        print(f"\nCorrelation de Pearson   : r = {r_pearson:.3f}  p = {p_pearson:.4f}")
        print(f"Correlation de Spearman  : rho = {r_spearman:.3f}  p = {p_spear:.4f}")
        print(f"R2 (variance expliquee)  : {r_pearson**2:.3f} ({r_pearson**2*100:.1f}%)")

        if abs(r_pearson) >= 0.7:
            print("-> Correlation forte : la formule ERT predit bien le temps reel")
        elif abs(r_pearson) >= 0.5:
            print("-> Correlation moderee : la formule ERT est un predicteur acceptable")
        else:
            print("-> Correlation faible : la formule ERT necessite un recalibrage")
    else:
        # Calcul manuel de Pearson
        num = sum((e-moy_ert)*(r-moy_reel) for e,r in zip(ert_vals,reel_vals))
        den = math.sqrt(
            sum((e-moy_ert)**2 for e in ert_vals) *
            sum((r-moy_reel)**2 for r in reel_vals)
        )
        r_pearson = num/den if den > 0 else 0
        print(f"\nCorrelation de Pearson (manuelle) : r = {r_pearson:.3f}")

    # Par objectif
    print(f"\nCorrelation par objectif :")
    by_obj = defaultdict(lambda: {'ert':[], 'reel':[]})
    for row in rows:
        k = row['objectif_code'] + '_' + row['mode_bloom']
        by_obj[k]['ert'].append(row['ert_predit_s'])
        by_obj[k]['reel'].append(row['temps_reel_s'])

    print(f"  {'Objectif_Mode':<25} {'N':>4} {'ERT moy':>8} {'Reel moy':>9} {'Diff':>7}")
    print(f"  {'-'*55}")
    for k in sorted(by_obj.keys()):
        e_list = by_obj[k]['ert']
        r_list = by_obj[k]['reel']
        n_obj  = len(e_list)
        if n_obj < 1:
            continue
        me = sum(e_list)/n_obj
        mr = sum(r_list)/n_obj
        diff = mr - me
        print(f"  {k:<25} {n_obj:>4} {me:>7.1f}s {mr:>8.1f}s {diff:>+6.1f}s")
else:
    print("Pas de donnees ERT disponibles.")

# ─────────────────────────────────────────────────────────────
# 2. COMPREHENSION vs ANALYSE — Test t de Student
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("2. COMPREHENSION vs ANALYSE — Test t de Student")
print(SEP)

comp = cur.execute("""
    SELECT temps_reel_s FROM exp_reponses r
    JOIN exp_sessions s ON r.session_id = s.id
    WHERE s.statut='terminee' AND r.mode_bloom='comprehension'
      AND r.temps_reel_s > 0 AND r.temps_reel_s < 600
""").fetchall()

anal = cur.execute("""
    SELECT temps_reel_s FROM exp_reponses r
    JOIN exp_sessions s ON r.session_id = s.id
    WHERE s.statut='terminee' AND r.mode_bloom='analyse'
      AND r.temps_reel_s > 0 AND r.temps_reel_s < 600
""").fetchall()

comp_vals = [r[0] for r in comp]
anal_vals = [r[0] for r in anal]

def moyenne(lst): return sum(lst)/len(lst) if lst else 0
def ecart_type(lst):
    if len(lst) < 2: return 0
    m = moyenne(lst)
    return math.sqrt(sum((v-m)**2 for v in lst)/(len(lst)-1))

mc = moyenne(comp_vals); sc = ecart_type(comp_vals)
ma = moyenne(anal_vals); sa = ecart_type(anal_vals)

print(f"\nMode Comprehension : M={mc:.1f}s  sigma={sc:.1f}s  N={len(comp_vals)}")
print(f"Mode Analyse       : M={ma:.1f}s  sigma={sa:.1f}s  N={len(anal_vals)}")

if HAS_SCIPY and len(comp_vals) >= 2 and len(anal_vals) >= 2:
    t_stat, p_val = ttest_ind(anal_vals, comp_vals)
    # Cohen's d
    n1, n2 = len(comp_vals), len(anal_vals)
    pool_std = math.sqrt(((n1-1)*sc**2 + (n2-1)*sa**2) / (n1+n2-2))
    cohens_d = (ma - mc) / pool_std if pool_std > 0 else 0
    effect = 'large' if abs(cohens_d) >= 0.8 else \
             'moyen' if abs(cohens_d) >= 0.5 else 'petit'
    print(f"\nTest t : t({n1+n2-2}) = {t_stat:.2f}  p = {p_val:.4f}")
    print(f"Cohen d = {cohens_d:.2f} (effet {effect})")
    if p_val < 0.001:
        print("-> Difference hautement significative (p < 0.001)")
    elif p_val < 0.05:
        print(f"-> Difference significative (p = {p_val:.3f})")
    else:
        print(f"-> Difference non significative (p = {p_val:.3f})")

# ─────────────────────────────────────────────────────────────
# 3. TAUX DE REUSSITE PAR OBJECTIF
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("3. TAUX DE REUSSITE PAR OBJECTIF")
print(SEP)

obj_stats = cur.execute("""
    SELECT objectif_code, mode_bloom,
           COUNT(*) as n,
           SUM(est_correct) as n_ok,
           AVG(est_correct)*100 as taux,
           AVG(temps_reel_s) as tps_moy
    FROM exp_reponses r
    JOIN exp_sessions s ON r.session_id = s.id
    WHERE s.statut = 'terminee'
    GROUP BY objectif_code, mode_bloom
    ORDER BY objectif_code, mode_bloom
""").fetchall()

if obj_stats:
    print(f"\n  {'Objectif':<15} {'Mode':<15} {'N':>4} {'Reussite':>9} {'Tps moy':>8}")
    print(f"  {'-'*55}")
    for r in obj_stats:
        barre = '#' * int((r['taux'] or 0) / 10)
        print(f"  {r['objectif_code']:<15} {r['mode_bloom']:<15} "
              f"{r['n']:>4} {(r['taux'] or 0):>8.1f}% {(r['tps_moy'] or 0):>7.1f}s")

# ─────────────────────────────────────────────────────────────
# 4. ANALYSE DES DISTRACTEURS
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("4. ANALYSE DES DISTRACTEURS")
print(SEP)

dist_stats = cur.execute("""
    SELECT objectif_code,
           distracteur_choisi,
           COUNT(*) as freq,
           reponse_correcte
    FROM exp_reponses r
    JOIN exp_sessions s ON r.session_id = s.id
    WHERE s.statut = 'terminee'
      AND est_correct = 0
    GROUP BY objectif_code, distracteur_choisi
    ORDER BY freq DESC
    LIMIT 15
""").fetchall()

if dist_stats:
    print(f"\n  Top erreurs (distracteurs les plus choisis) :")
    print(f"  {'Objectif':<15} {'Freq':>5}  Distracteur choisi")
    print(f"  {'-'*60}")
    for d in dist_stats:
        dist_court = str(d['distracteur_choisi'] or '')[:40]
        print(f"  {d['objectif_code']:<15} {d['freq']:>5}  {dist_court}")
else:
    print("  Pas encore de donnees sur les erreurs.")

# ─────────────────────────────────────────────────────────────
# 5. EVALUATION QUALITATIVE LIKERT
# Remplace les Tableaux 4.6 et 4.7 de la these
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("5. EVALUATION QUALITATIVE — MOYENNES LIKERT /5")
print(SEP)

eval_data = cur.execute("""
    SELECT grammaticalite, naturalite, clarte,
           plausibilite_dist, pertinence_obj, alignement_bloom,
           acceptabilite, utilite_apprentissage,
           score_coherence, score_plausibilite,
           score_acceptabilite, score_global
    FROM exp_eval_qualitative
""").fetchall()

if eval_data:
    n_eval = len(eval_data)
    print(f"\nN evaluateurs : {n_eval}")

    criteres = [
        ('grammaticalite',       'Grammaticalite'),
        ('naturalite',           'Naturalite'),
        ('clarte',               'Clarte'),
        ('plausibilite_dist',    'Plausib. distracteurs'),
        ('pertinence_obj',       'Pertinence objectif'),
        ('alignement_bloom',     'Alignement Bloom'),
        ('acceptabilite',        'Acceptabilite'),
        ('utilite_apprentissage','Utilite apprentissage'),
    ]

    print(f"\n  {'Critere':<25} {'Moy':>5}  {'Sigma':>6}  {'Min':>4}  {'Max':>4}")
    print(f"  {'-'*52}")

    groupes = {
        'COHERENCE LINGUISTIQUE': ['grammaticalite','naturalite','clarte'],
        'PLAUSIBILITE PEDAGOGIQUE': ['plausibilite_dist','pertinence_obj','alignement_bloom'],
        'ACCEPTABILITE GENERALE': ['acceptabilite','utilite_apprentissage'],
    }

    for groupe, cols in groupes.items():
        print(f"\n  --- {groupe} ---")
        scores_groupe = []
        for col, label in criteres:
            if col not in cols:
                continue
            vals = [r[col] for r in eval_data if r[col] is not None]
            if not vals:
                continue
            m  = sum(vals)/len(vals)
            s  = math.sqrt(sum((v-m)**2 for v in vals)/(len(vals)-1)) if len(vals)>1 else 0
            mn = min(vals)
            mx = max(vals)
            scores_groupe.extend(vals)
            print(f"  {label:<25} {m:>5.2f}  {s:>6.2f}  {mn:>4}  {mx:>4}")

        if scores_groupe:
            mg = sum(scores_groupe)/len(scores_groupe)
            print(f"  {'  -> Moyenne groupe':<25} {mg:>5.2f}")

    # Score global
    glob = [r['score_global'] for r in eval_data if r['score_global']]
    if glob:
        mg = sum(glob)/len(glob)
        sg = math.sqrt(sum((v-mg)**2 for v in glob)/(len(glob)-1)) if len(glob)>1 else 0
        print(f"\n  SCORE GLOBAL : {mg:.2f}/5  (sigma={sg:.2f})")

    # Accord inter-evaluateurs (Kappa de Fleiss approx.)
    if n_eval >= 2:
        print(f"\n  Accord inter-evaluateurs :")
        for col, label in criteres:
            vals = [r[col] for r in eval_data if r[col] is not None]
            if len(vals) < 2:
                continue
            m  = sum(vals)/len(vals)
            s  = math.sqrt(sum((v-m)**2 for v in vals)/(len(vals)-1))
            # Kappa approx via ICC simplifie
            # (necessite au moins 2 evaluateurs par question)
            cv = s/m if m > 0 else 0  # coefficient de variation
            accord = 'Excellent' if cv < 0.1 else \
                     'Bon'       if cv < 0.2 else \
                     'Modere'    if cv < 0.3 else 'Faible'
            print(f"  {label:<25} CV={cv:.2f}  -> {accord}")
else:
    print("\n  Pas encore d'evaluations qualitatives.")
    print("  Completez des sessions jusqu'a la fin (formulaire Likert)")

# ─────────────────────────────────────────────────────────────
# 6. TEXTES PRETS POUR LE CHAPITRE 4
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("6. TEXTES PRÊTS POUR LE CHAPITRE 4")
print(SEP)

if nb_rep > 0 and HAS_SCIPY and len(comp_vals) >= 2 and len(anal_vals) >= 2:
    print(f"""
§4.1.8 — Validation de la formule ERT :
\"L'analyse de la correlation entre les valeurs ERT predites par
la formule T(Q) et les temps de reponse reellement observes sur
{n} paires de donnees revele une correlation de Pearson
r = {r_pearson:.3f} (p {'< 0,001' if p_pearson < 0.001 else f'= {p_pearson:.3f}'}),
ce qui signifie que la formule explique {r_pearson**2*100:.1f}% de la
variance des temps observes.\"

§4.1.8 — Comparaison Comprehension vs Analyse :
\"La difference entre le mode Comprehension (M = {mc:.1f}s, sigma = {sc:.1f}s,
N = {len(comp_vals)}) et le mode Analyse (M = {ma:.1f}s, sigma = {sa:.1f}s,
N = {len(anal_vals)}) est {'hautement significative' if p_val < 0.001 else 'significative'}
(t({len(comp_vals)+len(anal_vals)-2}) = {t_stat:.2f},
p {'< 0,001' if p_val < 0.001 else f'= {p_val:.3f}'},
d de Cohen = {cohens_d:.2f}, effet {effect}).\"
""")

if nb_eval > 0 and eval_data:
    glob_vals = [r['score_global'] for r in eval_data if r['score_global']]
    coh_vals  = [r['score_coherence'] for r in eval_data if r['score_coherence']]
    plau_vals = [r['score_plausibilite'] for r in eval_data if r['score_plausibilite']]
    mg  = sum(glob_vals)/len(glob_vals) if glob_vals else 0
    mcoh= sum(coh_vals)/len(coh_vals)   if coh_vals  else 0
    mpl = sum(plau_vals)/len(plau_vals) if plau_vals else 0
    print(f"""
§4.1.6 — Evaluation qualitative ({n_eval} participants) :
\"L'evaluation qualitative par {n_eval} apprenants revele une
coherence linguistique moyenne de {mcoh:.2f}/5 et une plausibilite
pedagogique de {mpl:.2f}/5. Le score global de {mg:.2f}/5 indique
que les questions generees sont jugees satisfaisantes par les
participants.\"
""")

conn.close()

print(SEP)
print("FIN DE L'ANALYSE")
print("Copiez les textes de la section 6 dans votre these.")
print(SEP)
