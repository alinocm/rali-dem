# ─────────────────────────────────────────────────────────────
# stats.py  —  Module de statistiques RALI-DEM
#
# Statistiques calculées :
#   • Par apprenant : taux de réussite, ERT moyen,
#     distribution Bloom, progression temporelle
#   • Par cohorte : distribution scores, objectifs difficiles,
#     évolution collective
#   • Corrélations inter-objectifs (matrice de Pearson)
#   • Exports : JSON, CSV, SPSS (.sav via pyreadstat)
# ─────────────────────────────────────────────────────────────

import os
import json
import sqlite3
import math
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get('RALI_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db'))
# Ordre pédagogique des 15 objectifs
OBJECTIFS_ORDRE = [
    'PROP', 'VVER', 'TVER', 'NEG_SIMPLE',
    'CONN_ID', 'CONN_TRAD', 'CONN_INV',
    'IMP', 'EQUIV', 'MORGAN',
    'NEG_COMP', 'NEG_IMP',
    'QUANT_TRAD', 'NEG_QUANT', 'CONTRAP',
]

OBJECTIFS_NOMS = {
    'PROP':       'Identifier une proposition',
    'VVER':       'Valeur de vérité',
    'TVER':       'Table de vérité',
    'NEG_SIMPLE': 'Négation simple',
    'CONN_ID':    'Identifier les connecteurs',
    'CONN_TRAD':  'Traduction LN → formel',
    'CONN_INV':   'Traduction formel → LN',
    'IMP':        'Implication logique',
    'EQUIV':      'Équivalence logique',
    'MORGAN':     'Lois de De Morgan',
    'NEG_COMP':   'Négation d\'une proposition composée',
    'NEG_IMP':    'Négation d\'une implication',
    'QUANT_TRAD': 'Traduction avec quantificateurs',
    'NEG_QUANT':  'Négation des quantificateurs',
    'CONTRAP':    'Raisonnement par contraposée',
}


# ═════════════════════════════════════════════════════════════
# CONNEXION
# ═════════════════════════════════════════════════════════════

def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═════════════════════════════════════════════════════════════
# UTILITAIRES STATISTIQUES
# ═════════════════════════════════════════════════════════════

def _moyenne(valeurs: list) -> float:
    if not valeurs:
        return 0.0
    return round(sum(valeurs) / len(valeurs), 2)


def _ecart_type(valeurs: list) -> float:
    if len(valeurs) < 2:
        return 0.0
    m = _moyenne(valeurs)
    variance = sum((x - m) ** 2 for x in valeurs) / (len(valeurs) - 1)
    return round(math.sqrt(variance), 2)


def _correlation_pearson(x: list, y: list) -> float:
    """Calcule le coefficient de corrélation de Pearson entre x et y."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x, y = x[:n], y[:n]
    mx, my = _moyenne(x), _moyenne(y)
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den_x = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 3)


def _percentile(valeurs: list, p: float) -> float:
    """Calcule le p-ième percentile d'une liste de valeurs."""
    if not valeurs:
        return 0.0
    tri = sorted(valeurs)
    idx = (p / 100) * (len(tri) - 1)
    lo  = int(idx)
    hi  = lo + 1
    if hi >= len(tri):
        return round(tri[lo], 2)
    return round(tri[lo] + (idx - lo) * (tri[hi] - tri[lo]), 2)


def _distribution(valeurs: list, tranches: list) -> dict:
    """
    Distribue les valeurs dans des tranches.
    tranches = [(label, min, max), ...]
    """
    result = {t[0]: 0 for t in tranches}
    for v in valeurs:
        for label, lo, hi in tranches:
            if lo <= v < hi:
                result[label] += 1
                break
        else:
            # Dernière tranche inclut la borne supérieure
            result[tranches[-1][0]] += 1
    return result


# ═════════════════════════════════════════════════════════════
# TABLEAU DE BORD ADMINISTRATEUR
# ═════════════════════════════════════════════════════════════

def get_tableau_bord() -> dict:
    """
    Retourne les indicateurs clés pour le tableau de bord admin.
    """
    conn = _connexion()

    # ── Apprenants ────────────────────────────────────────────
    nb_apprenants = conn.execute(
        "SELECT COUNT(*) FROM utilisateurs WHERE role='apprenant'"
    ).fetchone()[0]

    nb_actifs_7j = conn.execute("""
        SELECT COUNT(DISTINCT utilisateur_id)
        FROM track_reponses_adapt
        WHERE date_reponse >= datetime('now', '-7 days')
    """).fetchone()[0]

    # ── Sessions ──────────────────────────────────────────────
    nb_sessions_adapt = conn.execute(
        "SELECT COUNT(*) FROM track_sessions_adapt WHERE terminee=1"
    ).fetchone()[0]

    nb_sessions_exam = conn.execute(
        "SELECT COUNT(*) FROM track_sessions_exam WHERE termine=1"
    ).fetchone()[0]

    # ── Questions répondues ───────────────────────────────────
    nb_rep_adapt = conn.execute(
        "SELECT COUNT(*) FROM track_reponses_adapt"
    ).fetchone()[0]

    nb_rep_exam = conn.execute(
        "SELECT COUNT(*) FROM track_reponses_exam"
    ).fetchone()[0]

    total_reponses = nb_rep_adapt + nb_rep_exam

    # ── Taux de réussite global ───────────────────────────────
    correctes_adapt = conn.execute(
        "SELECT COALESCE(SUM(est_correct),0) FROM track_reponses_adapt"
    ).fetchone()[0]

    correctes_exam = conn.execute(
        "SELECT COALESCE(SUM(est_correct),0) FROM track_reponses_exam"
    ).fetchone()[0]

    taux_global = round(
        (correctes_adapt + correctes_exam) / total_reponses * 100, 1
    ) if total_reponses > 0 else 0.0

    # ── ERT moyen global ──────────────────────────────────────
    ert_adapt = conn.execute(
        "SELECT COALESCE(AVG(ert_secondes),0) FROM track_reponses_adapt"
    ).fetchone()[0]

    ert_exam = conn.execute(
        "SELECT COALESCE(AVG(ert_secondes),0) FROM track_reponses_exam"
    ).fetchone()[0]

    ert_global = round(
        (ert_adapt * nb_rep_adapt + ert_exam * nb_rep_exam)
        / total_reponses, 1
    ) if total_reponses > 0 else 0.0

    # ── Note moyenne aux examens ──────────────────────────────
    note_moy = conn.execute(
        "SELECT COALESCE(AVG(note_sur_20),0) FROM track_sessions_exam WHERE termine=1"
    ).fetchone()[0]

    # ── Objectif le plus échoué ───────────────────────────────
    obj_echec = conn.execute("""
        SELECT objectif_code,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               ROUND(100.0 * SUM(est_correct) / COUNT(*), 1) as taux
        FROM (
            SELECT objectif_code, est_correct FROM track_reponses_adapt
            UNION ALL
            SELECT objectif_code, est_correct FROM track_reponses_exam
        )
        GROUP BY objectif_code
        ORDER BY taux ASC
        LIMIT 1
    """).fetchone()

    # ── Objectif le mieux maîtrisé ────────────────────────────
    obj_maitrise = conn.execute("""
        SELECT objectif_code,
               ROUND(100.0 * SUM(est_correct) / COUNT(*), 1) as taux
        FROM (
            SELECT objectif_code, est_correct FROM track_reponses_adapt
            UNION ALL
            SELECT objectif_code, est_correct FROM track_reponses_exam
        )
        GROUP BY objectif_code
        ORDER BY taux DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return {
        "apprenants": {
            "total":          nb_apprenants,
            "actifs_7_jours": nb_actifs_7j,
        },
        "sessions": {
            "adaptatives": nb_sessions_adapt,
            "examens":     nb_sessions_exam,
            "total":       nb_sessions_adapt + nb_sessions_exam,
        },
        "reponses": {
            "total":         total_reponses,
            "taux_reussite": taux_global,
            "ert_moyen":     ert_global,
        },
        "examens": {
            "note_moyenne":  round(note_moy, 2),
        },
        "objectifs": {
            "plus_echoue":   dict(obj_echec) if obj_echec else None,
            "mieux_maitrise": dict(obj_maitrise) if obj_maitrise else None,
        },
        "date_calcul": datetime.now().isoformat(),
    }


# ═════════════════════════════════════════════════════════════
# STATISTIQUES PAR OBJECTIF (cohorte)
# ═════════════════════════════════════════════════════════════

def get_stats_objectifs() -> list:
    """
    Retourne les statistiques de réussite pour chaque objectif
    sur l'ensemble de la cohorte.
    """
    conn = _connexion()

    rows = conn.execute("""
        SELECT objectif_code,
               mode_bloom,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen,
               AVG(score_question) as score_moyen
        FROM (
            SELECT objectif_code, mode_bloom,
                   est_correct, ert_secondes, score_question
            FROM track_reponses_adapt
            UNION ALL
            SELECT objectif_code, mode_bloom,
                   est_correct, ert_secondes, score_question
            FROM track_reponses_exam
        )
        GROUP BY objectif_code, mode_bloom
        ORDER BY objectif_code, mode_bloom
    """).fetchall()

    conn.close()

    # Organiser par objectif
    par_objectif = {}
    for r in rows:
        code  = r['objectif_code']
        bloom = r['mode_bloom']
        if code not in par_objectif:
            par_objectif[code] = {
                'objectif_code': code,
                'nom':           OBJECTIFS_NOMS.get(code, code),
                'total':         0,
                'correctes':     0,
                'taux_reussite': 0.0,
                'ert_moyen':     0.0,
                'score_moyen':   0.0,
                'par_bloom':     {},
            }
        n   = r['total']
        cor = r['correctes'] or 0
        par_objectif[code]['total']     += n
        par_objectif[code]['correctes'] += cor
        par_objectif[code]['par_bloom'][bloom] = {
            'total':         n,
            'correctes':     cor,
            'taux_reussite': round(cor / n * 100, 1) if n > 0 else 0.0,
            'ert_moyen':     round(r['ert_moyen'] or 0, 1),
            'score_moyen':   round(r['score_moyen'] or 0, 2),
        }

    # Calculer les totaux
    for code, d in par_objectif.items():
        n   = d['total']
        cor = d['correctes']
        d['taux_reussite'] = round(cor / n * 100, 1) if n > 0 else 0.0
        # ERT moyen pondéré
        erts = []
        for b in d['par_bloom'].values():
            erts.extend([b['ert_moyen']] * b['total'])
        d['ert_moyen']   = round(sum(erts) / len(erts), 1) if erts else 0.0
        d['score_moyen'] = round(
            sum(b['score_moyen'] * b['total']
                for b in d['par_bloom'].values()) / n, 2
        ) if n > 0 else 0.0

    # Trier selon l'ordre pédagogique
    result = []
    for code in OBJECTIFS_ORDRE:
        if code in par_objectif:
            result.append(par_objectif[code])
    # Ajouter les objectifs non listés
    for code, d in par_objectif.items():
        if code not in OBJECTIFS_ORDRE:
            result.append(d)

    return result


# ═════════════════════════════════════════════════════════════
# STATISTIQUES PAR APPRENANT
# ═════════════════════════════════════════════════════════════

def get_stats_apprenant(utilisateur_id: int) -> dict:
    """
    Statistiques détaillées d'un apprenant spécifique.
    """
    conn = _connexion()

    # Infos utilisateur
    user = conn.execute(
        """SELECT nom, prenom, email, niveau, institution
           FROM utilisateurs WHERE id=?""",
        (utilisateur_id,)
    ).fetchone()

    if not user:
        conn.close()
        raise ValueError(f"Utilisateur {utilisateur_id} introuvable.")

    # Résultats par objectif
    rows = conn.execute("""
        SELECT objectif_code, mode_bloom,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen,
               AVG(score_question) as score_moyen,
               MIN(date_reponse) as premiere,
               MAX(date_reponse) as derniere
        FROM (
            SELECT objectif_code, mode_bloom, est_correct,
                   ert_secondes, score_question, date_reponse
            FROM track_reponses_adapt WHERE utilisateur_id=?
            UNION ALL
            SELECT objectif_code, mode_bloom, est_correct,
                   ert_secondes, score_question, date_reponse
            FROM track_reponses_exam WHERE utilisateur_id=?
        )
        GROUP BY objectif_code, mode_bloom
    """, (utilisateur_id, utilisateur_id)).fetchall()

    # Progression temporelle (par semaine)
    progression = conn.execute("""
        SELECT strftime('%Y-%W', date_reponse) as semaine,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen
        FROM (
            SELECT date_reponse, est_correct, ert_secondes
            FROM track_reponses_adapt WHERE utilisateur_id=?
            UNION ALL
            SELECT date_reponse, est_correct, ert_secondes
            FROM track_reponses_exam WHERE utilisateur_id=?
        )
        GROUP BY semaine
        ORDER BY semaine
    """, (utilisateur_id, utilisateur_id)).fetchall()

    # Notes aux examens
    examens = conn.execute("""
        SELECT titre, note_sur_20, mention,
               nb_questions, nb_correctes,
               date_examen, duree_secondes
        FROM track_sessions_exam
        WHERE utilisateur_id=? AND termine=1
        ORDER BY date_examen
    """, (utilisateur_id,)).fetchall()

    conn.close()

    # Organiser résultats par objectif
    par_objectif = {}
    total_q = total_c = 0
    for r in rows:
        code  = r['objectif_code']
        bloom = r['mode_bloom']
        if code not in par_objectif:
            par_objectif[code] = {
                'objectif_code': code,
                'nom':           OBJECTIFS_NOMS.get(code, code),
                'total':         0,
                'correctes':     0,
                'taux_reussite': 0.0,
                'ert_moyen':     0.0,
                'par_bloom':     {},
            }
        n   = r['total']
        cor = r['correctes'] or 0
        par_objectif[code]['total']     += n
        par_objectif[code]['correctes'] += cor
        total_q += n
        total_c += cor
        par_objectif[code]['par_bloom'][bloom] = {
            'total':         n,
            'correctes':     cor,
            'taux_reussite': round(cor / n * 100, 1) if n > 0 else 0.0,
            'ert_moyen':     round(r['ert_moyen'] or 0, 1),
        }

    for d in par_objectif.values():
        n = d['total']
        d['taux_reussite'] = round(d['correctes'] / n * 100, 1) if n > 0 else 0.0

    # Notes examens
    notes = [e['note_sur_20'] for e in examens]

    return {
        "utilisateur": dict(user),
        "resume": {
            "total_questions":   total_q,
            "total_correctes":   total_c,
            "taux_reussite":     round(total_c / total_q * 100, 1) if total_q > 0 else 0.0,
            "nb_examens":        len(examens),
            "note_moy_examens":  _moyenne(notes),
            "note_max_examens":  max(notes) if notes else 0.0,
            "note_min_examens":  min(notes) if notes else 0.0,
            "ecart_type_notes":  _ecart_type(notes),
        },
        "par_objectif":  list(par_objectif.values()),
        "progression":   [dict(p) for p in progression],
        "examens":       [dict(e) for e in examens],
    }


# ═════════════════════════════════════════════════════════════
# STATISTIQUES COHORTE
# ═════════════════════════════════════════════════════════════

def get_stats_cohorte(
    niveau:      Optional[str] = None,
    institution: Optional[str] = None,
) -> dict:
    """
    Statistiques agrégées sur l'ensemble des apprenants.
    Filtrable par niveau ou institution.
    """
    conn = _connexion()

    # Filtre
    filtres_sql = "WHERE u.role='apprenant'"
    params      = []
    if niveau:
        filtres_sql += " AND u.niveau=?"
        params.append(niveau)
    if institution:
        filtres_sql += " AND u.institution=?"
        params.append(institution)

    # Distribution des notes aux examens
    notes_rows = conn.execute(f"""
        SELECT se.note_sur_20, se.mention
        FROM track_sessions_exam se
        JOIN utilisateurs u ON se.utilisateur_id = u.id
        {filtres_sql} AND se.termine=1
    """, params).fetchall()

    notes = [r['note_sur_20'] for r in notes_rows]

    tranches_notes = [
        ('0-5',   0,  5),
        ('5-10',  5,  10),
        ('10-14', 10, 14),
        ('14-16', 14, 16),
        ('16-18', 16, 18),
        ('18-20', 18, 20.01),
    ]
    dist_notes = _distribution(notes, tranches_notes)

    # Distribution des mentions
    mentions = {}
    for r in notes_rows:
        m = r['mention']
        mentions[m] = mentions.get(m, 0) + 1

    # Taux de réussite par objectif (cohorte)
    obj_rows = conn.execute(f"""
        SELECT r.objectif_code,
               COUNT(*) as total,
               SUM(r.est_correct) as correctes
        FROM (
            SELECT ra.objectif_code, ra.est_correct, ra.utilisateur_id
            FROM track_reponses_adapt ra
            UNION ALL
            SELECT re.objectif_code, re.est_correct, re.utilisateur_id
            FROM track_reponses_exam re
        ) r
        JOIN utilisateurs u ON r.utilisateur_id = u.id
        {filtres_sql}
        GROUP BY r.objectif_code
        ORDER BY correctes * 1.0 / total ASC
    """, params).fetchall()

    taux_par_obj = []
    for r in obj_rows:
        n = r['total']
        c = r['correctes'] or 0
        taux_par_obj.append({
            'objectif_code': r['objectif_code'],
            'nom':           OBJECTIFS_NOMS.get(r['objectif_code'], ''),
            'total':         n,
            'correctes':     c,
            'taux_reussite': round(c / n * 100, 1) if n > 0 else 0.0,
        })

    # ERT par niveau Bloom
    ert_bloom = conn.execute(f"""
        SELECT r.mode_bloom,
               AVG(r.ert_secondes) as ert_moyen,
               COUNT(*) as total
        FROM (
            SELECT ra.mode_bloom, ra.ert_secondes, ra.utilisateur_id
            FROM track_reponses_adapt ra
            UNION ALL
            SELECT re.mode_bloom, re.ert_secondes, re.utilisateur_id
            FROM track_reponses_exam re
        ) r
        JOIN utilisateurs u ON r.utilisateur_id = u.id
        {filtres_sql}
        GROUP BY r.mode_bloom
    """, params).fetchall()

    conn.close()

    return {
        "filtres": {"niveau": niveau, "institution": institution},
        "notes_examens": {
            "valeurs":       notes,
            "moyenne":       _moyenne(notes),
            "ecart_type":    _ecart_type(notes),
            "mediane":       _percentile(notes, 50),
            "p25":           _percentile(notes, 25),
            "p75":           _percentile(notes, 75),
            "distribution":  dist_notes,
            "mentions":      mentions,
        },
        "taux_par_objectif":  taux_par_obj,
        "ert_par_bloom":      [dict(r) for r in ert_bloom],
        "nb_examens_total":   len(notes),
    }


# ═════════════════════════════════════════════════════════════
# MATRICE DE CORRÉLATIONS INTER-OBJECTIFS (Pearson)
# ═════════════════════════════════════════════════════════════

def get_matrice_correlations() -> dict:
    """
    Calcule la matrice de corrélation de Pearson entre objectifs.
    Pour chaque apprenant, on calcule son taux de réussite
    par objectif, puis on corrèle les vecteurs de taux.

    Interprétation :
      r > 0.7  → forte corrélation positive (maîtriser A aide à maîtriser B)
      r < -0.3 → corrélation négative (difficultés croisées)
    """
    conn = _connexion()

    # Taux de réussite par (apprenant, objectif)
    rows = conn.execute("""
        SELECT utilisateur_id, objectif_code,
               COUNT(*) as total,
               SUM(est_correct) as correctes
        FROM (
            SELECT utilisateur_id, objectif_code, est_correct
            FROM track_reponses_adapt
            UNION ALL
            SELECT utilisateur_id, objectif_code, est_correct
            FROM track_reponses_exam
        )
        GROUP BY utilisateur_id, objectif_code
    """).fetchall()

    conn.close()

    # Construire un dictionnaire {user_id: {objectif: taux}}
    donnees = {}
    for r in rows:
        uid  = r['utilisateur_id']
        code = r['objectif_code']
        taux = round(r['correctes'] / r['total'] * 100, 1) if r['total'] > 0 else 0.0
        if uid not in donnees:
            donnees[uid] = {}
        donnees[uid][code] = taux

    # Garder uniquement les apprenants ayant répondu à au moins 2 objectifs
    apprenants = [uid for uid, d in donnees.items() if len(d) >= 2]

    # Liste des objectifs présents
    objectifs_presents = sorted(set(
        code for d in donnees.values() for code in d.keys()
    ), key=lambda c: OBJECTIFS_ORDRE.index(c) if c in OBJECTIFS_ORDRE else 99)

    # Construire les vecteurs par objectif
    def vecteur(code):
        return [
            donnees[uid].get(code, None)
            for uid in apprenants
        ]

    # Calculer la matrice (ignorer les None)
    matrice = {}
    for code_i in objectifs_presents:
        matrice[code_i] = {}
        v_i = vecteur(code_i)
        for code_j in objectifs_presents:
            v_j = vecteur(code_j)
            # Garder les paires où les deux ont une valeur
            paires = [(v_i[k], v_j[k])
                      for k in range(len(apprenants))
                      if v_i[k] is not None and v_j[k] is not None]
            if len(paires) < 2:
                matrice[code_i][code_j] = None
            else:
                xi, yi = zip(*paires)
                matrice[code_i][code_j] = _correlation_pearson(
                    list(xi), list(yi)
                )

    # Identifier les paires fortement corrélées
    correlations_fortes = []
    for i, ci in enumerate(objectifs_presents):
        for j, cj in enumerate(objectifs_presents):
            if i >= j:
                continue
            r = matrice[ci].get(cj)
            if r is not None and abs(r) >= 0.5:
                correlations_fortes.append({
                    'objectif_1': ci,
                    'objectif_2': cj,
                    'correlation': r,
                    'interpretation': (
                        'Forte corrélation positive' if r >= 0.7
                        else 'Corrélation positive modérée' if r >= 0.5
                        else 'Corrélation négative modérée'
                    )
                })

    correlations_fortes.sort(key=lambda x: -abs(x['correlation']))

    return {
        "objectifs":           objectifs_presents,
        "nb_apprenants":       len(apprenants),
        "matrice":             matrice,
        "correlations_fortes": correlations_fortes,
    }


# ═════════════════════════════════════════════════════════════
# PROGRESSION TEMPORELLE (cohorte)
# ═════════════════════════════════════════════════════════════

def get_progression_temporelle(granularite: str = 'semaine') -> list:
    """
    Retourne l'évolution du taux de réussite moyen dans le temps.
    granularite : 'jour' | 'semaine' | 'mois'
    """
    formats = {
        'jour':    '%Y-%m-%d',
        'semaine': '%Y-%W',
        'mois':    '%Y-%m',
    }
    fmt = formats.get(granularite, '%Y-%W')

    conn = _connexion()
    rows = conn.execute(f"""
        SELECT strftime('{fmt}', date_reponse) as periode,
               COUNT(*) as total,
               SUM(est_correct) as correctes,
               AVG(ert_secondes) as ert_moyen,
               COUNT(DISTINCT utilisateur_id) as nb_apprenants
        FROM (
            SELECT date_reponse, est_correct,
                   ert_secondes, utilisateur_id
            FROM track_reponses_adapt
            UNION ALL
            SELECT date_reponse, est_correct,
                   ert_secondes, utilisateur_id
            FROM track_reponses_exam
        )
        GROUP BY periode
        ORDER BY periode
    """).fetchall()
    conn.close()

    result = []
    for r in rows:
        n = r['total']
        c = r['correctes'] or 0
        result.append({
            'periode':       r['periode'],
            'total':         n,
            'correctes':     c,
            'taux_reussite': round(c / n * 100, 1) if n > 0 else 0.0,
            'ert_moyen':     round(r['ert_moyen'] or 0, 1),
            'nb_apprenants': r['nb_apprenants'],
        })
    return result


# ═════════════════════════════════════════════════════════════
# EXPORTS
# ═════════════════════════════════════════════════════════════

def exporter_stats_json(type_stats: str = 'cohorte',
                         utilisateur_id: Optional[int] = None) -> str:
    """Export JSON des statistiques."""
    if type_stats == 'apprenant' and utilisateur_id:
        data = get_stats_apprenant(utilisateur_id)
    elif type_stats == 'objectifs':
        data = get_stats_objectifs()
    elif type_stats == 'correlations':
        data = get_matrice_correlations()
    elif type_stats == 'progression':
        data = get_progression_temporelle()
    else:
        data = {
            "tableau_bord":  get_tableau_bord(),
            "cohorte":       get_stats_cohorte(),
            "objectifs":     get_stats_objectifs(),
            "progression":   get_progression_temporelle(),
        }
    return json.dumps(data, ensure_ascii=False, indent=2)


def exporter_stats_csv(type_stats: str = 'objectifs') -> str:
    """Export CSV des statistiques (compatible Excel)."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)

    writer.writerow([f"# Export statistiques RALI-DEM — {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
    writer.writerow([])

    if type_stats == 'objectifs':
        stats = get_stats_objectifs()
        writer.writerow([
            'Code objectif', 'Nom', 'Total réponses', 'Correctes',
            'Taux de réussite (%)', 'ERT moyen (s)', 'Score moyen /10'
        ])
        for s in stats:
            writer.writerow([
                s['objectif_code'], s['nom'],
                s['total'], s['correctes'],
                s['taux_reussite'], s['ert_moyen'], s['score_moyen']
            ])

    elif type_stats == 'apprenants':
        conn = _connexion()
        users = conn.execute("""
            SELECT u.id, u.nom, u.prenom, u.email, u.niveau, u.institution,
                   u.date_creation, u.derniere_connexion,
                   COUNT(DISTINCT sa.id) as nb_sessions_adapt,
                   COUNT(DISTINCT se.id) as nb_examens,
                   COALESCE(AVG(se.note_sur_20), 0) as note_moy
            FROM utilisateurs u
            LEFT JOIN track_sessions_adapt sa ON sa.utilisateur_id=u.id AND sa.terminee=1
            LEFT JOIN track_sessions_exam se ON se.utilisateur_id=u.id AND se.termine=1
            WHERE u.role='apprenant'
            GROUP BY u.id
        """).fetchall()
        conn.close()

        writer.writerow([
            'ID', 'Nom', 'Prénom', 'Email', 'Niveau', 'Institution',
            'Date inscription', 'Dernière connexion',
            'Sessions adaptatives', 'Examens', 'Note moyenne /20'
        ])
        for u in users:
            writer.writerow([
                u['id'], u['nom'], u['prenom'], u['email'],
                u['niveau'], u['institution'],
                u['date_creation'][:10] if u['date_creation'] else '',
                u['derniere_connexion'][:10] if u['derniere_connexion'] else '',
                u['nb_sessions_adapt'], u['nb_examens'],
                round(u['note_moy'], 2)
            ])

    elif type_stats == 'reponses_brutes':
        conn = _connexion()
        rows = conn.execute("""
            SELECT r.utilisateur_id, u.nom, u.prenom, u.niveau, u.institution,
                   r.objectif_code, r.mode_bloom, r.niveau_complexite,
                   r.est_correct, r.ert_secondes, r.score_question,
                   r.date_reponse, 'adaptatif' as source
            FROM track_reponses_adapt r
            JOIN utilisateurs u ON r.utilisateur_id=u.id
            UNION ALL
            SELECT r.utilisateur_id, u.nom, u.prenom, u.niveau, u.institution,
                   r.objectif_code, r.mode_bloom, r.niveau_complexite,
                   r.est_correct, r.ert_secondes, r.score_question,
                   r.date_reponse, 'examen' as source
            FROM track_reponses_exam r
            JOIN utilisateurs u ON r.utilisateur_id=u.id
            ORDER BY date_reponse
        """).fetchall()
        conn.close()

        writer.writerow([
            'ID apprenant', 'Nom', 'Prénom', 'Niveau', 'Institution',
            'Objectif', 'Mode Bloom', 'Niveau complexité',
            'Correct (1=oui)', 'ERT (s)', 'Score /10',
            'Date réponse', 'Source'
        ])
        for r in rows:
            writer.writerow(list(r))

    return output.getvalue()


def exporter_stats_spss(type_stats: str = 'reponses') -> bytes:
    """
    Export au format SPSS (.sav) via pyreadstat.
    Retourne les bytes du fichier .sav.
    Nécessite : pip install pyreadstat
    """
    try:
        import pyreadstat
    except ImportError:
        raise ImportError(
            "pyreadstat n'est pas installé. "
            "Exécutez : pip install pyreadstat"
        )
    import tempfile
    import pandas as pd

    conn = _connexion()

    if type_stats == 'reponses':
        rows = conn.execute("""
            SELECT r.utilisateur_id,
                   u.niveau, u.institution,
                   r.objectif_code, r.mode_bloom,
                   r.niveau_complexite, r.est_correct,
                   r.ert_secondes, r.score_question,
                   r.date_reponse, 1 as source_adaptatif
            FROM track_reponses_adapt r
            JOIN utilisateurs u ON r.utilisateur_id=u.id
            UNION ALL
            SELECT r.utilisateur_id,
                   u.niveau, u.institution,
                   r.objectif_code, r.mode_bloom,
                   r.niveau_complexite, r.est_correct,
                   r.ert_secondes, r.score_question,
                   r.date_reponse, 0 as source_adaptatif
            FROM track_reponses_exam r
            JOIN utilisateurs u ON r.utilisateur_id=u.id
        """).fetchall()
        conn.close()

        colonnes = [
            'utilisateur_id', 'niveau', 'institution',
            'objectif_code', 'mode_bloom', 'niveau_complexite',
            'est_correct', 'ert_secondes', 'score_question',
            'date_reponse', 'source_adaptatif'
        ]

    elif type_stats == 'examens':
        rows = conn.execute("""
            SELECT se.utilisateur_id, u.nom, u.prenom,
                   u.niveau, u.institution,
                   se.nb_questions, se.nb_correctes,
                   se.note_sur_20, se.mention,
                   se.duree_secondes, se.date_examen
            FROM track_sessions_exam se
            JOIN utilisateurs u ON se.utilisateur_id=u.id
            WHERE se.termine=1
        """).fetchall()
        conn.close()
        colonnes = [
            'utilisateur_id', 'nom', 'prenom',
            'niveau', 'institution',
            'nb_questions', 'nb_correctes',
            'note_sur_20', 'mention',
            'duree_secondes', 'date_examen'
        ]

    # Créer DataFrame
    df = pd.DataFrame([list(r) for r in rows], columns=colonnes)

    # Étiquettes SPSS pour les variables
    etiquettes = {
        'utilisateur_id':    'Identifiant apprenant',
        'objectif_code':     'Code objectif pédagogique',
        'mode_bloom':        'Mode Bloom (comprehension/analyse)',
        'niveau_complexite': 'Niveau de complexité (faible/moyen/eleve)',
        'est_correct':       'Réponse correcte (1=oui, 0=non)',
        'ert_secondes':      'Temps de réponse estimé (secondes)',
        'score_question':    'Score de la question (/10)',
        'note_sur_20':       'Note à l\'examen (/20)',
        'duree_secondes':    'Durée de la session (secondes)',
        'source_adaptatif':  'Source (1=adaptatif, 0=examen)',
    }

    # Écrire le fichier .sav
    with tempfile.NamedTemporaryFile(suffix='.sav', delete=False) as f:
        chemin = f.name

    pyreadstat.write_sav(
        df, chemin,
        column_labels=etiquettes
    )

    with open(chemin, 'rb') as f:
        contenu = f.read()

    os.unlink(chemin)
    return contenu


# ═════════════════════════════════════════════════════════════
# TEST
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, sys

    DB_PATH = os.path.join(tempfile.gettempdir(), 'rali_test_tracking.db')

    # Vérifier que la base de test existe
    if not os.path.exists(DB_PATH):
        print("⚠️  Lancez d'abord le test de tracking.py pour créer la base")
        sys.exit(1)

    print("=== Test stats.py ===\n")

    # 1. Tableau de bord
    tb = get_tableau_bord()
    print(f"1. Tableau de bord ✅")
    print(f"   Apprenants: {tb['apprenants']['total']}")
    print(f"   Sessions adapt: {tb['sessions']['adaptatives']}")
    print(f"   Taux global: {tb['reponses']['taux_reussite']}%")
    print(f"   Note moy examens: {tb['examens']['note_moyenne']}/20")

    # 2. Stats objectifs
    obj = get_stats_objectifs()
    print(f"\n2. Stats objectifs ✅ — {len(obj)} objectifs")
    for o in obj[:3]:
        print(f"   [{o['objectif_code']}] taux: {o['taux_reussite']}%")

    # 3. Stats apprenant
    conn = sqlite3.connect(DB_PATH)
    uid = conn.execute(
        "SELECT id FROM utilisateurs WHERE email='test@test.cm'"
    ).fetchone()
    conn.close()
    if uid:
        sa = get_stats_apprenant(uid[0])
        print(f"\n3. Stats apprenant ✅")
        print(f"   Taux réussite: {sa['resume']['taux_reussite']}%")
        print(f"   Note moy examens: {sa['resume']['note_moy_examens']}/20")

    # 4. Stats cohorte
    co = get_stats_cohorte()
    print(f"\n4. Stats cohorte ✅")
    print(f"   Nb examens: {co['nb_examens_total']}")
    if co['notes_examens']['valeurs']:
        print(f"   Moyenne notes: {co['notes_examens']['moyenne']}/20")
        print(f"   Médiane: {co['notes_examens']['mediane']}/20")

    # 5. Matrice corrélations
    mat = get_matrice_correlations()
    print(f"\n5. Matrice corrélations ✅")
    print(f"   {mat['nb_apprenants']} apprenants, "
          f"{len(mat['objectifs'])} objectifs")
    if mat['correlations_fortes']:
        c = mat['correlations_fortes'][0]
        print(f"   Corrélation max: {c['objectif_1']} ↔ "
              f"{c['objectif_2']} = {c['correlation']}")

    # 6. Progression temporelle
    prog = get_progression_temporelle('semaine')
    print(f"\n6. Progression temporelle ✅ — {len(prog)} semaine(s)")
    for p in prog:
        print(f"   {p['periode']}: {p['taux_reussite']}% "
              f"({p['nb_apprenants']} apprenants)")

    # 7. Export JSON
    j = exporter_stats_json('objectifs')
    print(f"\n7. Export JSON ✅ — {len(j)} caractères")

    # 8. Export CSV objectifs
    c = exporter_stats_csv('objectifs')
    print(f"8. Export CSV objectifs ✅ — {len(c.splitlines())} lignes")

    # 9. Export CSV apprenants
    ca = exporter_stats_csv('apprenants')
    print(f"9. Export CSV apprenants ✅ — {len(ca.splitlines())} lignes")

    # 10. Export CSV réponses brutes
    cr = exporter_stats_csv('reponses_brutes')
    print(f"10. Export CSV réponses brutes ✅ — {len(cr.splitlines())} lignes")

    print("\n✅ Tous les tests passent !")
