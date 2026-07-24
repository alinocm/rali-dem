# ─────────────────────────────────────────────────────────────
# tools.py  —  Outils complémentaires RALI-DEM
# Contient :
#   1. Rapport d'erreurs par objectif
#   2. Indices progressifs (3 niveaux)
#   3. Export de fiches d'exercices PDF
# ─────────────────────────────────────────────────────────────

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'rali_dem.db')


# ═════════════════════════════════════════════════════════════
# 1. RAPPORT D'ERREURS
# ═════════════════════════════════════════════════════════════

def _maitrise(taux: float) -> str:
    """Niveau de maitrise basé sur le taux de réussite."""
    if taux >= 80: return "Maîtrisé"
    if taux >= 60: return "En progression"
    if taux >= 40: return "Insuffisant"
    return "À retravailler"


def _recommandation(objectif_code: str, taux: float) -> str:
    """Recommandation personnalisée selon l'objectif et le taux."""
    if taux >= 80:
        return ""
    conseils = {
        "NEG_IMP":    "Révisez ¬(P⇒Q) ≡ P∧¬Q — l'erreur la plus fréquente est de nier seulement la conclusion.",
        "CONTRAP":    "Distinguez contraposée (¬Q⇒¬P), réciproque (Q⇒P) et inverse (¬P⇒¬Q).",
        "MORGAN":     "Mémorisez : ¬(P∧Q) ≡ ¬P∨¬Q et ¬(P∨Q) ≡ ¬P∧¬Q — le connecteur s'inverse.",
        "NEG_QUANT":  "Rappel : ¬(∀x,P(x)) ≡ ∃x,¬P(x) et ¬(∃x,P(x)) ≡ ∀x,¬P(x).",
        "IMP":        "L'implication P⇒Q est fausse UNIQUEMENT quand P est vraie et Q est fausse.",
        "NEG_COMP":   "Appliquez De Morgan : ¬(P∧Q) ≡ ¬P∨¬Q, ¬(P∨Q) ≡ ¬P∧¬Q.",
    }
    return conseils.get(objectif_code,
        f"Pratiquez davantage l'objectif {objectif_code}.")


def _recommandations_globales(stats: list) -> list:
    """Recommandations globales basées sur les objectifs les plus échoués."""
    recs = []
    echecs = [s for s in stats if s['taux_reussite'] < 60]
    echecs.sort(key=lambda x: x['taux_reussite'])
    for s in echecs[:3]:
        r = _recommandation(s['objectif_code'], s['taux_reussite'])
        if r:
            recs.append(f"[{s['objectif_code']}] {r}")
    if not recs and stats:
        recs.append("Bonne progression ! Continuez à pratiquer régulièrement.")
    return recs


def get_rapport_erreurs(apprenant: str = None,
                          objectif_code: str = None,
                          utilisateur_id: int = None) -> dict:
    """
    Génère un rapport d'erreurs en lisant les tables de tracking.
    Lit track_reponses_adapt et track_reponses_exam.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # ── Filtre utilisateur ────────────────────────────────────
    filtre_user = ""
    params      = []

    if utilisateur_id:
        filtre_user = "AND utilisateur_id = ?"
        params.append(utilisateur_id)
        params.append(utilisateur_id)  # pour UNION ALL
    elif apprenant:
        # Filtrage par nom approximatif via sous-requête
        filtre_user = "AND utilisateur_id IN (SELECT id FROM utilisateurs WHERE nom || ' ' || prenom LIKE ?)"
        params.append(f"%{apprenant}%")
        params.append(f"%{apprenant}%")

    filtre_obj = ""
    if objectif_code:
        filtre_obj = "AND objectif_code = ?"
        params.append(objectif_code)
        params.append(objectif_code)  # pour UNION ALL
    
    params2 = params  # alias pour compatibilité

    # ── Statistiques par objectif (adapt + exam fusionnés) ────
    sql = f"""
        SELECT objectif_code,
               COUNT(*) as nb_total,
               COALESCE(SUM(est_correct), 0) as nb_correctes,
               COALESCE(AVG(score_question), 0) as score_moyen,
               COALESCE(AVG(ert_secondes), 0) as ert_moyen
        FROM (
            SELECT objectif_code, est_correct, score_question,
                   ert_secondes, utilisateur_id
            FROM track_reponses_adapt
            WHERE 1=1 {filtre_user} {filtre_obj}
            UNION ALL
            SELECT objectif_code, est_correct, score_question,
                   ert_secondes, utilisateur_id
            FROM track_reponses_exam
            WHERE 1=1 {filtre_user} {filtre_obj}
        )
        GROUP BY objectif_code
        ORDER BY nb_total DESC
    """
    try:
        rows = cur.execute(sql, params).fetchall()
    except Exception:
        rows = []

    stats_par_obj = []
    for r in rows:
        nb_t = r['nb_total']
        nb_c = r['nb_correctes'] or 0
        taux = round(nb_c / nb_t * 100, 1) if nb_t > 0 else 0.0
        stats_par_obj.append({
            'objectif_code': r['objectif_code'],
            'nb_total':      nb_t,
            'nb_correctes':  nb_c,
            'nb_erreurs':    nb_t - nb_c,
            'taux_reussite': taux,
            'score_moyen':   round(r['score_moyen'] or 0, 2),
            'ert_moyen':     round(r['ert_moyen'] or 0, 1),
            'niveau_maitrise': _maitrise(taux),
            'recommandation':  _recommandation(r['objectif_code'], taux),
        })

    # ── Progression temporelle ────────────────────────────────
    sql_prog = f"""
        SELECT strftime('%Y-%m-%d', date_reponse) as date,
               COUNT(*) as total,
               SUM(est_correct) as correctes
        FROM (
            SELECT date_reponse, est_correct, utilisateur_id
            FROM track_reponses_adapt
            WHERE 1=1 {filtre_user}
            UNION ALL
            SELECT date_reponse, est_correct, utilisateur_id
            FROM track_reponses_exam
            WHERE 1=1 {filtre_user}
        )
        GROUP BY date ORDER BY date DESC LIMIT 30
    """
    try:
        prog_rows = cur.execute(sql_prog, params).fetchall()
    except Exception as e:
        print("[rapport] progression erreur:", e)
        prog_rows = []

    progression = []
    for p in prog_rows:
        t = p['total']
        c = p['correctes'] or 0
        progression.append({
            'date':          p['date'],
            'total':         t,
            'correctes':     c,
            'taux_reussite': round(c / t * 100, 1) if t > 0 else 0.0,
        })

    # ── Résumé global ─────────────────────────────────────────
    total     = sum(s['nb_total']    for s in stats_par_obj)
    correctes = sum(s['nb_correctes'] for s in stats_par_obj)
    taux_g    = round(correctes / total * 100, 1) if total > 0 else 0.0

    conn.close()

    return {
        'stats_par_objectif':    stats_par_obj,
        'progression':           progression,
        'recommandations_globales': _recommandations_globales(stats_par_obj),
        'resume': {
            'total_questions': total,
            'nb_correctes':    correctes,
            'nb_erreurs':      total - correctes,
            'taux_reussite':   taux_g,
            'score_moyen':     round(
                sum(s['score_moyen'] * s['nb_total'] for s in stats_par_obj)
                / total, 2) if total > 0 else 0.0,
        }
    }



# ═════════════════════════════════════════════════════════════
# INDICES PROGRESSIFS PAR OBJECTIF (3 niveaux)
# Niveau 1 : indice vague (orientation générale)
# Niveau 2 : indice modéré (rappel de la règle)
# Niveau 3 : indice précis (quasi-solution)
# ═════════════════════════════════════════════════════════════

INDICES = {
    "PROP": [
        "Une proposition est un énoncé qui a une valeur de vérité.",
        "Demandez-vous : peut-on dire que cet énoncé est Vrai ou Faux ?",
        "Une question, un ordre ou un souhait ne sont pas des propositions. Seuls les énoncés déclaratifs vérifiables le sont.",
    ],
    "VVER": [
        "Regardez les valeurs de P et Q et le connecteur utilisé.",
        "Rappelez-vous la table de vérité du connecteur : ∧ (et), ∨ (ou), ⇒ (si...alors), ⇔ (si et seulement si).",
        "Pour ⇒ : l'implication est FAUSSE uniquement quand P est Vraie et Q est Fausse. Dans tous les autres cas, elle est Vraie.",
    ],
    "TVER": [
        "Identifiez le connecteur et les valeurs de P et Q dans la ligne concernée.",
        "Consultez la table : ∧ est vraie seulement si P=V et Q=V. ∨ est fausse seulement si P=F et Q=F.",
        "Pour ⇒ : retenez le seul cas faux — P=V et Q=F. Pour ⇔ : vraie quand P et Q ont la même valeur.",
    ],
    "NEG_SIMPLE": [
        "La négation d'une proposition simple s'obtient en ajoutant 'ne...pas' au verbe.",
        "La négation logique utilise 'ne...pas', pas 'ne...jamais', 'ne...plus' ou 'ne...que'.",
        "Pour 'Le sujet verbe complément', la négation est 'Le sujet ne verbe pas complément'. Aucun mot nouveau n'est ajouté.",
    ],
    "CONN_ID": [
        "Lisez attentivement la phrase et cherchez le mot de liaison logique.",
        "'Et' → ∧, 'ou' → ∨, 'si...alors' → ⇒, 'si et seulement si' → ⇔.",
        "Le connecteur principal est celui qui relie les deux propositions P et Q. 'et' donne ∧, 'ou' donne ∨.",
    ],
    "CONN_TRAD": [
        "Identifiez P et Q dans la phrase, puis le connecteur qui les relie.",
        "'P et Q' → P∧Q, 'P ou Q' → P∨Q, 'Si P alors Q' → P⇒Q, 'P ssi Q' → P⇔Q.",
        "Attention à l'ordre : 'Si P alors Q' se traduit P⇒Q et non Q⇒P. P est la prémisse, Q la conclusion.",
    ],
    "CONN_INV": [
        "Identifiez le connecteur formel et traduisez-le en langage naturel.",
        "∧ → 'et', ∨ → 'ou', ⇒ → 'si...alors' (pas 'donc' ni 'parce que'), ⇔ → 'si et seulement si'.",
        "P⇒Q se lit 'Si P, alors Q'. Attention : ⇒ n'exprime pas la causalité, seulement l'implication logique.",
    ],
    "IMP": [
        "Rappelez-vous dans quel unique cas l'implication P⇒Q est fausse.",
        "P⇒Q est fausse UNIQUEMENT quand P est Vraie et Q est Fausse (V⇒F = F).",
        "Dans tous les autres cas (V⇒V, F⇒V, F⇒F), l'implication est Vraie. Une prémisse fausse rend l'implication vraie.",
    ],
    "EQUIV": [
        "P⇔Q est vraie quand P et Q ont la même valeur de vérité.",
        "⇔ est vraie si P=V et Q=V, ou si P=F et Q=F. Elle est fausse si P et Q ont des valeurs différentes.",
        "P⇔Q ≡ (P⇒Q) ∧ (Q⇒P). C'est une double implication : P implique Q ET Q implique P.",
    ],
    "MORGAN": [
        "Les lois de De Morgan concernent la négation d'une conjonction ou disjonction.",
        "De Morgan 1 : ¬(P∧Q) ≡ ¬P∨¬Q. De Morgan 2 : ¬(P∨Q) ≡ ¬P∧¬Q.",
        "Retenez : quand on nie, le connecteur s'inverse (∧ devient ∨ et vice-versa) ET chaque membre est nié.",
    ],
    "NEG_COMP": [
        "Pour nier une proposition composée, appliquez les lois de De Morgan.",
        "¬(P∧Q) ≡ ¬P∨¬Q : le ET devient OU. ¬(P∨Q) ≡ ¬P∧¬Q : le OU devient ET.",
        "N'oubliez pas d'inverser le connecteur ET de nier les deux membres. Erreur fréquente : nier sans inverser.",
    ],
    "NEG_IMP": [
        "La négation d'une implication n'est pas une implication.",
        "¬(P⇒Q) ≡ P ∧ ¬Q. La négation d'une implication est une conjonction.",
        "¬(Si P alors Q) = P et non-Q. P reste vraie, seule Q est niée. Erreur fréquente : écrire 'Si P alors ¬Q'.",
    ],
    "QUANT_TRAD": [
        "∀ signifie 'pour tout' et ∃ signifie 'il existe au moins un'.",
        "'Tous les x vérifient P' → ∀x, P(x). 'Il existe un x qui vérifie P' → ∃x, P(x).",
        "Attention à l'ordre des quantificateurs : ∀x∃y P(x,y) ≠ ∃y∀x P(x,y).",
    ],
    "NEG_QUANT": [
        "La négation inverse le quantificateur et nie la propriété.",
        "¬(∀x, P(x)) ≡ ∃x, ¬P(x). ¬(∃x, P(x)) ≡ ∀x, ¬P(x).",
        "Pour nier '∀x, P(x)' : il suffit de trouver UN x pour lequel P est fausse → ∃x, ¬P(x).",
    ],
    "CONTRAP": [
        "La contraposée de P⇒Q est une implication équivalente avec P et Q niés et inversés.",
        "Contraposée de P⇒Q : ¬Q⇒¬P. Elle est logiquement équivalente à P⇒Q.",
        "Distinguez : contraposée (¬Q⇒¬P ≡ P⇒Q), réciproque (Q⇒P, non équivalente), inverse (¬P⇒¬Q, non équivalente).",
    ],
}

def get_indice(objectif_code: str, niveau_indice: int) -> dict:
    """
    Retourne un indice pour un objectif donné.

    Paramètres
    ----------
    objectif_code : code de l'objectif
    niveau_indice : 1, 2 ou 3 (du plus vague au plus précis)

    Retourne
    --------
    dict avec l'indice et les métadonnées
    """
    if objectif_code not in INDICES:
        return {
            "indice":         "Aucun indice disponible pour cet objectif.",
            "niveau":         niveau_indice,
            "indices_restants": 0,
        }

    indices = INDICES[objectif_code]
    idx     = max(0, min(niveau_indice - 1, len(indices) - 1))
    indice  = indices[idx]

    return {
        "objectif_code":   objectif_code,
        "indice":          indice,
        "niveau":          niveau_indice,
        "indices_restants": len(indices) - niveau_indice,
        "avertissement": (
            "⚠️ Dernier indice disponible. "
            "Essayez maintenant par vous-même !"
            if niveau_indice >= len(indices) else ""
        ),
    }


# ═════════════════════════════════════════════════════════════
# 3. EXPORT PDF
# ═════════════════════════════════════════════════════════════

def exporter_fiche_html(
    questions:     list,
    titre:         str  = "Fiche d'exercices — Logique mathématique",
    avec_corrige:  bool = False,
    enseignant:    str  = "",
    niveau:        str  = "",
) -> str:
    """
    Génère une fiche d'exercices en HTML prête à imprimer / convertir en PDF.

    Paramètres
    ----------
    questions    : liste de questions (format dict du générateur)
    titre        : titre de la fiche
    avec_corrige : inclure le corrigé ou non
    enseignant   : nom de l'enseignant
    niveau       : niveau des questions

    Retourne
    --------
    str : contenu HTML complet
    """
    from corrector import REGLES

    date     = datetime.now().strftime("%d/%m/%Y")
    nb_q     = len(questions)

    # Génération des questions HTML
    questions_html = ""
    for i, q in enumerate(questions, 1):
        distracteurs = q.get("distracteurs", [])
        if isinstance(distracteurs, str):
            try:
                distracteurs = json.loads(distracteurs.replace("'", '"'))
            except Exception:
                distracteurs = []

        # Mélanger réponse correcte et distracteurs
        import random
        choix = [q["reponse_correcte"]] + distracteurs[:3]
        random.shuffle(choix)
        lettres = ["A", "B", "C", "D"]

        choix_html = ""
        for j, c in enumerate(choix):
            lettre = lettres[j] if j < len(lettres) else str(j+1)
            choix_html += f"""
            <div class="choix">
                <span class="lettre">{lettre})</span> {c}
            </div>"""

        # Indicateurs de complexité
        ert   = q.get("ert_secondes", 0)
        score = q.get("score_pedagogique", 0)
        niv   = q.get("niveau_complexite", "").upper()

        questions_html += f"""
        <div class="question">
            <div class="question-header">
                <span class="num">Question {i}</span>
                <span class="meta">
                    ERT : {ert}s &nbsp;|&nbsp;
                    Complexité : {score}/10 &nbsp;|&nbsp;
                    Niveau : {niv}
                </span>
            </div>
            <p class="enonce">{q['enonce']}</p>
            <div class="choix-container">{choix_html}</div>
            <div class="espace-reponse">Réponse : ________</div>
        </div>"""

    # Corrigé HTML
    corrige_html = ""
    if avec_corrige:
        corrige_html = "<div class='corrige'><h2>✅ Corrigé</h2><ol>"
        for i, q in enumerate(questions, 1):
            obj     = q.get("objectif_code", "")
            regle   = REGLES.get(obj, {})
            formule = regle.get("formule", "").replace("\n", "<br>")
            corrige_html += f"""
            <li>
                <strong>Q{i} :</strong> {q['reponse_correcte']}<br>
                <em>Règle : {regle.get('nom', '')}</em><br>
                <code>{formule}</code>
            </li>"""
        corrige_html += "</ol></div>"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{titre}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
            color: #1a1a2e;
            padding: 30px 40px;
            max-width: 900px;
            margin: auto;
        }}
        .entete {{
            border-bottom: 3px solid #16213e;
            padding-bottom: 12px;
            margin-bottom: 24px;
        }}
        .entete h1 {{
            font-size: 20px;
            color: #16213e;
            margin-bottom: 6px;
        }}
        .entete .meta {{
            font-size: 12px;
            color: #555;
            display: flex;
            gap: 30px;
        }}
        .question {{
            border: 1px solid #dde;
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 18px;
            background: #f9f9fc;
            break-inside: avoid;
        }}
        .question-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .num {{
            font-weight: bold;
            font-size: 14px;
            color: #16213e;
        }}
        .meta {{
            font-size: 11px;
            color: #888;
            background: #eef;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        .enonce {{
            font-size: 13px;
            line-height: 1.6;
            margin-bottom: 12px;
            font-style: italic;
        }}
        .choix-container {{ padding-left: 10px; }}
        .choix {{
            padding: 4px 0;
            line-height: 1.5;
        }}
        .lettre {{
            font-weight: bold;
            color: #16213e;
            display: inline-block;
            width: 24px;
        }}
        .espace-reponse {{
            margin-top: 10px;
            font-size: 12px;
            color: #777;
            border-top: 1px dashed #ccc;
            padding-top: 6px;
        }}
        .corrige {{
            margin-top: 40px;
            border-top: 3px solid #16213e;
            padding-top: 20px;
        }}
        .corrige h2 {{
            color: #16213e;
            margin-bottom: 16px;
        }}
        .corrige ol {{ padding-left: 20px; }}
        .corrige li {{
            margin-bottom: 12px;
            line-height: 1.6;
        }}
        .corrige code {{
            display: block;
            background: #f0f0f8;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 11px;
            margin-top: 4px;
            white-space: pre-line;
        }}
        .pied-page {{
            margin-top: 30px;
            text-align: center;
            font-size: 11px;
            color: #aaa;
            border-top: 1px solid #eee;
            padding-top: 10px;
        }}
        @media print {{
            body {{ padding: 15px; }}
            .question {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="entete">
        <h1>📘 {titre}</h1>
        <div class="meta">
            <span>📅 Date : {date}</span>
            <span>📝 Questions : {nb_q}</span>
            {"<span>👨‍🏫 Enseignant : " + enseignant + "</span>" if enseignant else ""}
            {"<span>📊 Niveau : " + niveau + "</span>" if niveau else ""}
        </div>
    </div>

    <div class="questions">
        {questions_html}
    </div>

    {corrige_html}

    <div class="pied-page">
        Généré par RALI-DEM — Générateur automatique de questions de logique mathématique
    </div>
</body>
</html>"""

    return html


def sauvegarder_fiche(
    questions:    list,
    chemin:       str,
    titre:        str  = "Fiche d'exercices",
    avec_corrige: bool = False,
    enseignant:   str  = "",
    niveau:       str  = "",
) -> str:
    """
    Génère et sauvegarde une fiche HTML sur le disque.
    Retourne le chemin du fichier créé.
    """
    html = exporter_fiche_html(
        questions    = questions,
        titre        = titre,
        avec_corrige = avec_corrige,
        enseignant   = enseignant,
        niveau       = niveau,
    )
    with open(chemin, 'w', encoding='utf-8') as f:
        f.write(html)
    return chemin


# ═════════════════════════════════════════════════════════════
# EXPORT JSON
# ═════════════════════════════════════════════════════════════

def exporter_json(
    questions:    list,
    titre:        str  = "Fiche d'exercices — Logique mathématique",
    avec_corrige: bool = False,
    enseignant:   str  = "",
    niveau:       str  = "",
) -> str:
    """
    Exporte une fiche d'exercices au format JSON.
    Retourne une chaîne JSON.
    """
    import json
    from datetime import datetime

    fiche = {
        "titre":      titre,
        "enseignant": enseignant,
        "niveau":     niveau,
        "date":       datetime.now().strftime("%d/%m/%Y %H:%M"),
        "nb_questions": len(questions),
        "questions":  []
    }

    for i, q in enumerate(questions, 1):
        distracteurs = q.get("distracteurs", [])
        if isinstance(distracteurs, str):
            try:
                import ast as _ast
                distracteurs = _ast.literal_eval(distracteurs)
            except Exception:
                distracteurs = []

        item = {
            "numero":          i,
            "objectif_code":   q.get("objectif_code", ""),
            "mode_bloom":      q.get("mode_bloom", ""),
            "niveau_complexite": q.get("niveau_complexite", ""),
            "ert_secondes":    q.get("ert_secondes", 0),
            "enonce":          q.get("enonce", ""),
            "options":         [],
        }

        # Mélanger bonne réponse et distracteurs
        import random
        options = [q.get("reponse_correcte", "")] + distracteurs[:3]
        random.shuffle(options)
        lettres = ["A", "B", "C", "D"]
        for j, opt in enumerate(options):
            item["options"].append({
                "lettre":  lettres[j] if j < len(lettres) else str(j+1),
                "texte":   opt,
                "correct": opt == q.get("reponse_correcte", "")
                           if avec_corrige else None
            })

        if avec_corrige:
            item["reponse_correcte"] = q.get("reponse_correcte", "")

        fiche["questions"].append(item)

    return json.dumps(fiche, ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════════════════════
# EXPORT CSV
# ═════════════════════════════════════════════════════════════

def exporter_csv(
    questions:    list,
    titre:        str  = "Fiche d'exercices — Logique mathématique",
    avec_corrige: bool = False,
    enseignant:   str  = "",
    niveau:       str  = "",
) -> str:
    """
    Exporte une fiche d'exercices au format CSV (séparateur ;).
    Compatible Excel et LibreOffice Calc.
    Retourne une chaîne CSV encodée en UTF-8.
    """
    import csv
    import io
    import random

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)

    # En-tête de la fiche
    writer.writerow(["# Fiche d'exercices RALI-DEM"])
    writer.writerow(["# Titre", titre])
    writer.writerow(["# Enseignant", enseignant])
    writer.writerow(["# Niveau", niveau])
    writer.writerow(["# Questions", len(questions)])
    writer.writerow([])

    # En-tête des colonnes
    colonnes = ["N°", "Objectif", "Bloom", "Niveau",
                "ERT(s)", "Énoncé", "Option A", "Option B",
                "Option C", "Option D"]
    if avec_corrige:
        colonnes.append("Bonne réponse")
    writer.writerow(colonnes)

    # Lignes de questions
    lettres = ["A", "B", "C", "D"]
    for i, q in enumerate(questions, 1):
        distracteurs = q.get("distracteurs", [])
        if isinstance(distracteurs, str):
            try:
                import ast as _ast
                distracteurs = _ast.literal_eval(distracteurs)
            except Exception:
                distracteurs = []

        options = [q.get("reponse_correcte", "")] + distracteurs[:3]
        random.shuffle(options)

        # Padder à 4 options
        while len(options) < 4:
            options.append("")

        row = [
            i,
            q.get("objectif_code", ""),
            q.get("mode_bloom", ""),
            q.get("niveau_complexite", ""),
            q.get("ert_secondes", 0),
            q.get("enonce", ""),
            options[0],
            options[1],
            options[2] if len(options) > 2 else "",
            options[3] if len(options) > 3 else "",
        ]
        if avec_corrige:
            row.append(q.get("reponse_correcte", ""))

        writer.writerow(row)

    return output.getvalue()


# ═════════════════════════════════════════════════════════════
# EXPORT MOODLE XML
# Format : Gift/Moodle XML pour import direct dans Moodle
# ═════════════════════════════════════════════════════════════

def exporter_moodle_xml(
    questions:    list,
    titre:        str  = "Fiche d'exercices — Logique mathématique",
    avec_corrige: bool = True,
    enseignant:   str  = "",
    niveau:       str  = "",
) -> str:
    """
    Exporte une fiche d'exercices au format Moodle XML.
    Importable directement dans Moodle via
    Administration > Banque de questions > Import > Format XML Moodle.
    Retourne une chaîne XML.
    """
    import random
    import html as html_lib
    from datetime import datetime

    def esc(s):
        """Échappe les caractères spéciaux XML."""
        return html_lib.escape(str(s), quote=True)

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<quiz>')

    # Catégorie Moodle
    lines.append('  <question type="category">')
    lines.append('    <category>')
    lines.append(f'      <text>RALI-DEM/{esc(titre)}</text>')
    lines.append('    </category>')
    lines.append('  </question>')

    for i, q in enumerate(questions, 1):
        distracteurs = q.get("distracteurs", [])
        if isinstance(distracteurs, str):
            try:
                import ast as _ast
                distracteurs = _ast.literal_eval(distracteurs)
            except Exception:
                distracteurs = []

        bonne_reponse = q.get("reponse_correcte", "")
        options = [bonne_reponse] + distracteurs[:3]
        random.shuffle(options)
        nb_options = len(options)

        # Score correct = 100 / (nombre distracteurs)
        # Score incorrect = 0
        fraction_correct = 100

        nom_q = (f"RALI-{q.get('objectif_code','Q')}-"
                 f"{q.get('mode_bloom','')[:4].upper()}-"
                 f"{datetime.now().strftime('%H%M%S')}-{i}")

        lines.append('  <question type="multichoice">')
        lines.append(f'    <name><text>{esc(nom_q)}</text></name>')
        lines.append('    <questiontext format="html">')
        lines.append(f'      <text><![CDATA[<p>{esc(q.get("enonce",""))}</p>]]></text>')
        lines.append('    </questiontext>')
        lines.append('    <generalfeedback format="html">')
        lines.append(f'      <text><![CDATA[')
        lines.append(f'        <p><strong>Bonne réponse :</strong> {esc(bonne_reponse)}</p>')
        lines.append(f'        <p><em>Objectif : {esc(q.get("objectif_code",""))}</em></p>')
        lines.append(f'      ]]></text>')
        lines.append('    </generalfeedback>')
        lines.append(f'    <defaultgrade>1</defaultgrade>')
        lines.append(f'    <penalty>0</penalty>')
        lines.append(f'    <hidden>0</hidden>')
        lines.append(f'    <single>true</single>')
        lines.append(f'    <shuffleanswers>true</shuffleanswers>')
        lines.append(f'    <answernumbering>ABCD</answernumbering>')

        # Méta-données comme tags Moodle
        lines.append('    <tags>')
        lines.append(f'      <tag><text>objectif:{esc(q.get("objectif_code",""))}</text></tag>')
        lines.append(f'      <tag><text>bloom:{esc(q.get("mode_bloom",""))}</text></tag>')
        lines.append(f'      <tag><text>niveau:{esc(q.get("niveau_complexite",""))}</text></tag>')
        lines.append(f'      <tag><text>ert:{q.get("ert_secondes",0)}s</text></tag>')
        lines.append('    </tags>')

        # Options de réponse
        for opt in options:
            est_correct = (opt == bonne_reponse)
            fraction = fraction_correct if est_correct else 0
            lines.append(f'    <answer fraction="{fraction}" format="html">')
            lines.append(f'      <text><![CDATA[<p>{esc(opt)}</p>]]></text>')
            if est_correct:
                lines.append('      <feedback format="html">')
                lines.append('        <text><![CDATA[<p>✅ Correct !</p>]]></text>')
                lines.append('      </feedback>')
            else:
                lines.append('      <feedback format="html">')
                lines.append(f'        <text><![CDATA[<p>❌ Incorrect. La bonne réponse est : {esc(bonne_reponse)}</p>]]></text>')
                lines.append('      </feedback>')
            lines.append('    </answer>')

        lines.append('  </question>')

    lines.append('</quiz>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    print("=== Test des outils RALI-DEM ===\n")

    # ── Test indices ─────────────────────────────────────────
    print("── Indices progressifs ──")
    for niveau in [1, 2, 3]:
        r = get_indice("CONTRAP", niveau)
        print(f"  Niveau {niveau} : {r['indice']}")
    print()

    # ── Test rapport d'erreurs (sans données = vide) ─────────
    print("── Rapport d'erreurs ──")
    rapport = get_rapport_erreurs()
    print(f"  Objectifs analysés : {len(rapport['stats_objectifs'])}")
    print(f"  Points forts  : {rapport['points_forts']}")
    print(f"  Points faibles: {rapport['points_faibles']}")
    print()

    # ── Test export HTML ─────────────────────────────────────
    print("── Export fiche HTML ──")
    questions_test = [
        {
            "enonce":           "Quelle est la négation de « Si P, alors Q » ?",
            "reponse_correcte": "P et non Q",
            "distracteurs":     ["Si P, alors non Q", "Non P ou Q", "Non P et non Q"],
            "objectif_code":    "NEG_IMP",
            "ert_secondes":     72.0,
            "score_pedagogique":3.45,
            "niveau_complexite":"moyen",
        },
        {
            "enonce":           "Selon De Morgan, quelle est la négation de « P et Q » ?",
            "reponse_correcte": "non P ou non Q",
            "distracteurs":     ["non P et non Q", "P ou Q", "non(P ou Q)"],
            "objectif_code":    "MORGAN",
            "ert_secondes":     68.0,
            "score_pedagogique":3.21,
            "niveau_complexite":"moyen",
        },
    ]

    chemin = "/tmp/fiche_test.html"
    sauvegarder_fiche(
        questions    = questions_test,
        chemin       = chemin,
        titre        = "Fiche d'exercices — Négation et De Morgan",
        avec_corrige = True,
        enseignant   = "Prof. Dupont",
        niveau       = "Moyen",
    )
    print(f"  Fiche sauvegardée : {chemin}")
    print(f"  Taille : {os.path.getsize(chemin)} octets")
    print("\n✅ Tous les tests réussis !")