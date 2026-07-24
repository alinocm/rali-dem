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

def get_rapport_erreurs(apprenant: str = None, objectif_code: str = None) -> dict:
    """
    Génère un rapport d'erreurs détaillé.

    Analyse :
    - Quels objectifs posent le plus de problèmes
    - Quels distracteurs sont les plus souvent choisis
    - Évolution des performances dans le temps
    - Recommandations personnalisées
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ── Statistiques globales par objectif ────────────────────
    q_base = '''
        SELECT
            h.objectif_code,
            COUNT(*) as nb_total,
            SUM(h.est_correct) as nb_correctes,
            AVG(h.score_question) as score_moyen,
            AVG(h.ert_secondes) as ert_moyen
        FROM historique_adaptatif h
        WHERE 1=1
    '''
    params = []
    if apprenant:
        q_base += '''
            AND h.session_id IN (
                SELECT id FROM sessions_adaptatives WHERE apprenant = ?
            )
        '''
        params.append(apprenant)
    if objectif_code:
        q_base += ' AND h.objectif_code = ?'
        params.append(objectif_code)

    q_base += ' GROUP BY h.objectif_code ORDER BY nb_total DESC'
    cursor.execute(q_base, params)
    stats_objectifs = []

    for row in cursor.fetchall():
        r = dict(row)
        nb    = r["nb_total"]
        bonnes = r["nb_correctes"] or 0
        taux  = round(bonnes / nb * 100, 1) if nb > 0 else 0

        # Distracteurs les plus souvent choisis pour cet objectif
        cursor.execute('''
            SELECT reponse_apprenant, COUNT(*) as nb
            FROM historique_adaptatif
            WHERE objectif_code = ? AND est_correct = 0
            GROUP BY reponse_apprenant
            ORDER BY nb DESC
            LIMIT 3
        ''', (r["objectif_code"],))
        erreurs_frequentes = [dict(e) for e in cursor.fetchall()]

        stats_objectifs.append({
            "objectif_code":    r["objectif_code"],
            "nb_tentatives":    nb,
            "nb_correctes":     bonnes,
            "taux_reussite":    taux,
            "score_moyen":      round(r["score_moyen"] or 0, 2),
            "ert_moyen":        round(r["ert_moyen"] or 0, 1),
            "niveau_maitrise":  _maitrise(taux),
            "erreurs_frequentes": erreurs_frequentes,
            "recommandation":   _recommandation(taux, r["objectif_code"]),
        })

    # ── Évolution temporelle (7 derniers jours) ───────────────
    cursor.execute('''
        SELECT
            DATE(date_reponse) as jour,
            COUNT(*) as nb,
            SUM(est_correct) as bonnes
        FROM historique_adaptatif
        WHERE date_reponse >= DATE("now", "-7 days")
        GROUP BY DATE(date_reponse)
        ORDER BY jour
    ''')
    evolution = []
    for row in cursor.fetchall():
        r    = dict(row)
        nb   = r["nb"]
        bon  = r["bonnes"] or 0
        taux = round(bon / nb * 100, 1) if nb > 0 else 0
        evolution.append({
            "jour":  r["jour"],
            "nb":    nb,
            "taux":  taux,
        })

    # ── Points forts et points faibles ───────────────────────
    points_forts  = [s for s in stats_objectifs if s["taux_reussite"] >= 80]
    points_faibles= [s for s in stats_objectifs if s["taux_reussite"] < 60]

    conn.close()

    return {
        "apprenant":       apprenant or "tous",
        "date_rapport":    datetime.now().strftime("%d/%m/%Y %H:%M"),
        "stats_objectifs": stats_objectifs,
        "evolution":       evolution,
        "points_forts":    [s["objectif_code"] for s in points_forts],
        "points_faibles":  [s["objectif_code"] for s in points_faibles],
        "recommandations_globales": _recommandations_globales(stats_objectifs),
    }


def _maitrise(taux: float) -> str:
    if taux >= 80: return "✅ Maîtrisé"
    if taux >= 60: return "⚠️ En cours d'acquisition"
    return "❌ À retravailler"


def _recommandation(taux: float, code: str) -> str:
    NOMS = {
        "NEG_SIMPLE": "la négation simple",
        "NEG_COMP":   "la négation composée",
        "NEG_IMP":    "la négation d'implication",
        "NEG_QUANT":  "la négation des quantificateurs",
        "MORGAN":     "les lois de De Morgan",
        "CONTRAP":    "la contraposée",
        "IMP":        "l'implication",
        "EQUIV":      "l'équivalence",
        "QUANT_TRAD": "la traduction des quantificateurs",
        "CONN_TRAD":  "la traduction LN→formel",
        "CONN_INV":   "la traduction formel→LN",
        "CONN_ID":    "l'identification des connecteurs",
        "TVER":       "les tables de vérité",
        "VVER":       "les valeurs de vérité",
        "PROP":       "les propositions logiques",
    }
    nom = NOMS.get(code, code)
    if taux >= 80:
        return f"Continuez à pratiquer {nom} pour maintenir ce niveau."
    if taux >= 60:
        return f"Révisez les règles de {nom} et faites plus d'exercices."
    return f"Reprenez le cours sur {nom} et pratiquez les exercices de base."


def _recommandations_globales(stats: list) -> list:
    recs = []
    faibles = [s for s in stats if s["taux_reussite"] < 60]
    if faibles:
        for s in faibles[:3]:
            recs.append(s["recommandation"])
    if not recs:
        recs.append("Excellent travail ! Continuez à pratiquer régulièrement.")
    return recs


# ═════════════════════════════════════════════════════════════
# 2. INDICES PROGRESSIFS
# ═════════════════════════════════════════════════════════════

# Indices en 3 niveaux pour chaque objectif
INDICES = {

    "NEG_SIMPLE": [
        "💡 Indice 1 : La négation d'une proposition P s'obtient en ajoutant « ne... pas » autour du verbe.",
        "💡 Indice 2 : Identifiez le verbe principal dans la proposition, puis insérez « ne » avant et « pas » après.",
        "💡 Indice 3 : La bonne réponse commence par le même sujet que la proposition originale, suivi de « ne [verbe] pas ».",
    ],

    "NEG_COMP": [
        "💡 Indice 1 : Repérez le connecteur principal : est-ce ET (∧) ou OU (∨) ?",
        "💡 Indice 2 : Appliquez De Morgan : ¬(P∧Q) = ¬P∨¬Q  et  ¬(P∨Q) = ¬P∧¬Q. Le connecteur s'inverse !",
        "💡 Indice 3 : Si la proposition contient ET, la négation contiendra OU (et vice versa). Niez ensuite chaque partie.",
    ],

    "NEG_IMP": [
        "💡 Indice 1 : La négation de « Si P, alors Q » n'est PAS « Si P, alors non Q ».",
        "💡 Indice 2 : Appliquez la règle : ¬(P⇒Q) ≡ P ∧ ¬Q. P reste vraie, Q devient fausse.",
        "💡 Indice 3 : La bonne réponse est : « [P] ET [négation de Q] ». P est gardé intact, seul Q est nié.",
    ],

    "NEG_QUANT": [
        "💡 Indice 1 : Pour nier un quantificateur, on échange ∀ et ∃.",
        "💡 Indice 2 : ¬(∀x P(x)) = ∃x ¬P(x)  et  ¬(∃x P(x)) = ∀x ¬P(x). Le quantificateur s'inverse ET la propriété se nie.",
        "💡 Indice 3 : Si la proposition dit « Tous les X... », la négation dit « Il existe au moins un X qui ne... pas ».",
    ],

    "MORGAN": [
        "💡 Indice 1 : Identifiez si vous avez un ET (∧) ou un OU (∨) entre les deux propositions.",
        "💡 Indice 2 : De Morgan 1 : ¬(P∧Q) = ¬P∨¬Q  |  De Morgan 2 : ¬(P∨Q) = ¬P∧¬Q.",
        "💡 Indice 3 : Inversez le connecteur (ET↔OU) et niez chacune des deux propositions séparément.",
    ],

    "CONTRAP": [
        "💡 Indice 1 : La contraposée de « Si P, alors Q » utilise les négations de P et Q.",
        "💡 Indice 2 : La contraposée est « Si ¬Q, alors ¬P ». Attention : on inverse ET on nie les deux propositions.",
        "💡 Indice 3 : Commencez par « Si [négation de Q], alors [négation de P] ». Ce n'est pas la réciproque (Si Q alors P) !",
    ],

    "IMP": [
        "💡 Indice 1 : L'implication P⇒Q est fausse UNIQUEMENT quand P est vraie et Q est fausse.",
        "💡 Indice 2 : Vérifiez les valeurs de P et Q indiquées dans la question, puis consultez la table.",
        "💡 Indice 3 : Table de l'implication : V⇒V=V, V⇒F=F, F⇒V=V, F⇒F=V. Seul V⇒F donne F.",
    ],

    "EQUIV": [
        "💡 Indice 1 : P⇔Q est vraie quand P et Q ont la même valeur de vérité.",
        "💡 Indice 2 : P⇔Q ≡ (P⇒Q) ∧ (Q⇒P). C'est une double implication.",
        "💡 Indice 3 : La bonne réponse doit exprimer « Si P alors Q » ET « Si Q alors P » simultanément.",
    ],

    "TVER": [
        "💡 Indice 1 : Regardez le connecteur dans la formule (∧, ∨, ⇒ ou ⇔).",
        "💡 Indice 2 : Repérez les valeurs de P et Q dans la question, puis cherchez la ligne correspondante.",
        "💡 Indice 3 : Table complète — ⇒ : V⇒V=V, V⇒F=F, F⇒V=V, F⇒F=V. La seule ligne fausse est V⇒F.",
    ],

    "VVER": [
        "💡 Indice 1 : Notez les valeurs de P et Q données dans l'énoncé.",
        "💡 Indice 2 : Appliquez la règle du connecteur : ∧ (les deux V), ∨ (au moins un V), ⇒ (F seulement si V⇒F).",
        "💡 Indice 3 : Pour l'implication P⇒Q, si P est Fausse, le résultat est toujours Vrai, quelle que soit Q.",
    ],

    "CONN_TRAD": [
        "💡 Indice 1 : Repérez le mot-clé du connecteur : « et », « ou », « si...alors », « si et seulement si ».",
        "💡 Indice 2 : Correspondances — et→∧, ou→∨, si...alors→⇒, si et seulement si→⇔.",
        "💡 Indice 3 : Identifiez P (première proposition) et Q (deuxième), puis écrivez P [symbole] Q.",
    ],

    "CONN_INV": [
        "💡 Indice 1 : Identifiez le symbole du connecteur dans la formule.",
        "💡 Indice 2 : Correspondances inverses — ∧→et, ∨→ou, ⇒→si...alors, ⇔→si et seulement si.",
        "💡 Indice 3 : Remplacez P et Q par les phrases données et le symbole par son expression naturelle.",
    ],

    "CONN_ID": [
        "💡 Indice 1 : Cherchez le mot qui relie les deux parties de la phrase.",
        "💡 Indice 2 : Les mots-clés sont : « et » (∧), « ou » (∨), « si...alors » (⇒), « si et seulement si » (⇔).",
        "💡 Indice 3 : Le connecteur principal est celui qui porte sur l'ensemble de la proposition, pas sur un détail.",
    ],

    "QUANT_TRAD": [
        "💡 Indice 1 : Repérez si la phrase dit « Tous les... » ou « Il existe au moins un... ».",
        "💡 Indice 2 : « Tous les » correspond à ∀ (pour tout) et « Il existe au moins un » correspond à ∃ (il existe).",
        "💡 Indice 3 : La formule est ∀x, P(x) ou ∃x, P(x) où P(x) représente la propriété vérifiée par x.",
    ],

    "PROP": [
        "💡 Indice 1 : Une proposition est un énoncé qui peut être vrai ou faux.",
        "💡 Indice 2 : Éliminez les questions et les ordres — ils ne sont jamais des propositions.",
        "💡 Indice 3 : Cherchez l'énoncé déclaratif dont on peut établir clairement la valeur de vérité (V ou F).",
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
                    Score : {score}/10 &nbsp;|&nbsp;
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
