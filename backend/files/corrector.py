# ─────────────────────────────────────────────────────────────
# corrector.py  —  Correction automatique RALI-DEM
# Fournit pour chaque question :
#   - le résultat (correct / incorrect)
#   - la règle logique utilisée
#   - la preuve mathématique détaillée
#   - un conseil personnalisé si mauvaise réponse
# ─────────────────────────────────────────────────────────────


# ═════════════════════════════════════════════════════════════
# RÈGLES LOGIQUES PAR OBJECTIF
# Chaque règle contient :
#   - nom       : nom de la règle
#   - formule   : écriture formelle
#   - explication : description en langage naturel
#   - exemple   : illustration simple
# ═════════════════════════════════════════════════════════════

REGLES = {

    "PROP": {
        "nom":        "Définition d'une proposition logique",
        "formule":    "P est une proposition ⟺ P a une valeur de vérité (V ou F)",
        "explication": (
            "Une proposition logique est un énoncé déclaratif qui est "
            "soit VRAI soit FAUX, mais jamais les deux à la fois. "
            "Les questions, les ordres et les phrases ambiguës "
            "ne sont pas des propositions."
        ),
        "exemple": (
            "✓ « Le soleil est une étoile » → proposition (Vraie)\n"
            "✓ « 2 + 2 = 5 » → proposition (Fausse)\n"
            "✗ « Fermez la porte ! » → ordre, pas une proposition\n"
            "✗ « Est-ce qu'il viendra ? » → question, pas une proposition"
        ),
    },

    "VVER": {
        "nom":        "Valeur de vérité d'une proposition composée",
        "formule":    (
            "P ∧ Q : vraie ssi P et Q sont vraies\n"
            "P ∨ Q : vraie ssi au moins l'une est vraie\n"
            "P ⇒ Q : fausse ssi P est vraie et Q est fausse\n"
            "P ⇔ Q : vraie ssi P et Q ont la même valeur"
        ),
        "explication": (
            "La valeur de vérité d'une proposition composée dépend "
            "des valeurs de ses composantes et du connecteur utilisé. "
            "Le cas le plus important à retenir : une implication P ⇒ Q "
            "n'est fausse QUE lorsque P est vraie et Q est fausse."
        ),
        "exemple": (
            "P = V, Q = F :\n"
            "  P ∧ Q = F   (les deux doivent être vraies)\n"
            "  P ∨ Q = V   (au moins une est vraie)\n"
            "  P ⇒ Q = F   (seul cas où l'implication est fausse)\n"
            "  P ⇔ Q = F   (valeurs différentes)"
        ),
    },

    "TVER": {
        "nom":        "Table de vérité",
        "formule":    (
            "┌───┬───┬───────┬───────┬───────┬───────┐\n"
            "│ P │ Q │ P ∧ Q │ P ∨ Q │ P ⇒ Q │ P ⇔ Q │\n"
            "├───┼───┼───────┼───────┼───────┼───────┤\n"
            "│ V │ V │   V   │   V   │   V   │   V   │\n"
            "│ V │ F │   F   │   V   │   F   │   F   │\n"
            "│ F │ V │   F   │   V   │   V   │   F   │\n"
            "│ F │ F │   F   │   F   │   V   │   V   │\n"
            "└───┴───┴───────┴───────┴───────┴───────┘"
        ),
        "explication": (
            "La table de vérité liste toutes les combinaisons possibles "
            "des valeurs de P et Q, et la valeur résultante pour chaque "
            "connecteur. À mémoriser absolument : l'implication P ⇒ Q "
            "est vraie dans 3 cas sur 4 — elle n'est fausse que quand "
            "P est vraie et Q est fausse."
        ),
        "exemple": (
            "Pour P ⇒ Q (lire : « Si P alors Q ») :\n"
            "  V ⇒ V = V  (la promesse est tenue)\n"
            "  V ⇒ F = F  (la promesse est brisée ← seul cas faux)\n"
            "  F ⇒ V = V  (promesse vacuement tenue)\n"
            "  F ⇒ F = V  (promesse vacuement tenue)"
        ),
    },

    "NEG_SIMPLE": {
        "nom":        "Négation d'une proposition simple",
        "formule":    "¬P est vraie ⟺ P est fausse",
        "explication": (
            "La négation d'une proposition P, notée ¬P ou non(P), "
            "inverse sa valeur de vérité. Si P est vraie, ¬P est fausse, "
            "et inversement. En langage naturel, on insère « ne... pas » "
            "autour du verbe."
        ),
        "exemple": (
            "P  = « L'étudiant comprend ce cours »\n"
            "¬P = « L'étudiant ne comprend pas ce cours »\n\n"
            "Table de vérité :\n"
            "  P = V  →  ¬P = F\n"
            "  P = F  →  ¬P = V"
        ),
    },

    "CONN_ID": {
        "nom":        "Identification des connecteurs logiques",
        "formule":    (
            "ET  → ∧  (conjonction)\n"
            "OU  → ∨  (disjonction)\n"
            "SI...ALORS → ⇒  (implication)\n"
            "SI ET SEULEMENT SI → ⇔  (équivalence)"
        ),
        "explication": (
            "Les connecteurs logiques permettent de combiner des propositions. "
            "Chaque expression du langage naturel correspond à un symbole formel. "
            "Il faut repérer le connecteur PRINCIPAL, c'est-à-dire celui qui "
            "porte sur l'ensemble de la proposition."
        ),
        "exemple": (
            "« Le médecin examine le patient ET prescrit un traitement »\n"
            "  → connecteur principal : ∧ (ET)\n\n"
            "« Si l'étudiant travaille, alors il réussit »\n"
            "  → connecteur principal : ⇒ (implication)"
        ),
    },

    "CONN_TRAD": {
        "nom":        "Traduction du langage naturel vers le formel",
        "formule":    (
            "« P et Q »              → P ∧ Q\n"
            "« P ou Q »              → P ∨ Q\n"
            "« Si P, alors Q »       → P ⇒ Q\n"
            "« P si et seulement Q » → P ⇔ Q"
        ),
        "explication": (
            "Pour traduire une phrase en formule logique :\n"
            "1. Identifier les propositions élémentaires (P, Q, ...)\n"
            "2. Identifier le connecteur principal\n"
            "3. Écrire la formule avec les symboles correspondants"
        ),
        "exemple": (
            "Phrase : « Le professeur explique ce cours et l'étudiant prend des notes »\n"
            "  P = « Le professeur explique ce cours »\n"
            "  Q = « L'étudiant prend des notes »\n"
            "  Formule : P ∧ Q"
        ),
    },

    "CONN_INV": {
        "nom":        "Traduction du formel vers le langage naturel",
        "formule":    (
            "P ∧ Q → « P et Q »\n"
            "P ∨ Q → « P ou Q »\n"
            "P ⇒ Q → « Si P, alors Q »\n"
            "P ⇔ Q → « P si et seulement si Q »"
        ),
        "explication": (
            "Pour traduire une formule logique en phrase naturelle :\n"
            "1. Remplacer chaque variable par son énoncé correspondant\n"
            "2. Remplacer chaque symbole par son expression naturelle\n"
            "3. Vérifier que la phrase est grammaticalement correcte"
        ),
        "exemple": (
            "Formule : P ⇒ Q\n"
            "  P = « L'avocat connaît ce dossier »\n"
            "  Q = « Il plaide correctement »\n"
            "  Traduction : « Si l'avocat connaît ce dossier, alors il plaide correctement »"
        ),
    },

    "IMP": {
        "nom":        "Implication logique (P ⇒ Q)",
        "formule":    (
            "P ⇒ Q est FAUSSE uniquement quand P = V et Q = F\n"
            "Dans tous les autres cas, P ⇒ Q est VRAIE\n\n"
            "Équivalences importantes :\n"
            "  P ⇒ Q  ≡  ¬P ∨ Q\n"
            "  P ⇒ Q  ≡  ¬Q ⇒ ¬P  (contraposée)"
        ),
        "explication": (
            "L'implication P ⇒ Q se lit « Si P, alors Q ». "
            "Elle exprime que la vérité de P garantit la vérité de Q. "
            "Attention : si P est fausse, l'implication est toujours vraie, "
            "quelle que soit la valeur de Q (promesse vacuement satisfaite)."
        ),
        "exemple": (
            "« Si il pleut, alors je prends un parapluie » (P ⇒ Q)\n\n"
            "  Il pleut (V) et je prends un parapluie (V) → V ⇒ V = V ✓\n"
            "  Il pleut (V) et je ne prends pas (F)       → V ⇒ F = F ✗\n"
            "  Il ne pleut pas (F) et je prends (V)       → F ⇒ V = V ✓\n"
            "  Il ne pleut pas (F) et je ne prends pas (F)→ F ⇒ F = V ✓"
        ),
    },

    "EQUIV": {
        "nom":        "Équivalence logique (P ⇔ Q)",
        "formule":    (
            "P ⇔ Q  ≡  (P ⇒ Q) ∧ (Q ⇒ P)\n"
            "P ⇔ Q est vraie ⟺ P et Q ont la même valeur de vérité"
        ),
        "explication": (
            "L'équivalence P ⇔ Q signifie que P et Q sont vraies ou "
            "fausses simultanément. C'est une double implication : "
            "P implique Q ET Q implique P. "
            "En langage naturel : « P si et seulement si Q »."
        ),
        "exemple": (
            "P ⇔ Q  ≡  (P ⇒ Q) ∧ (Q ⇒ P)\n\n"
            "  P = V, Q = V → (V⇒V) ∧ (V⇒V) = V ∧ V = V\n"
            "  P = V, Q = F → (V⇒F) ∧ (F⇒V) = F ∧ V = F\n"
            "  P = F, Q = V → (F⇒V) ∧ (V⇒F) = V ∧ F = F\n"
            "  P = F, Q = F → (F⇒F) ∧ (F⇒F) = V ∧ V = V"
        ),
    },

    "MORGAN": {
        "nom":        "Lois de De Morgan",
        "formule":    (
            "¬(P ∧ Q)  ≡  ¬P ∨ ¬Q\n"
            "¬(P ∨ Q)  ≡  ¬P ∧ ¬Q\n\n"
            "Moyen mnémotechnique :\n"
            "  La négation entre dans la parenthèse\n"
            "  ET devient OU, OU devient ET"
        ),
        "explication": (
            "Les lois de De Morgan permettent de distribuer la négation "
            "sur une conjonction ou une disjonction. "
            "Règle 1 : nier un ET donne un OU de négations. "
            "Règle 2 : nier un OU donne un ET de négations. "
            "Le connecteur s'inverse toujours."
        ),
        "exemple": (
            "Exemple 1 (loi 1) :\n"
            "  P = « L'étudiant réussit l'examen »\n"
            "  Q = « L'étudiant rend le devoir »\n"
            "  ¬(P ∧ Q) = ¬P ∨ ¬Q\n"
            "  = « L'étudiant ne réussit pas l'examen OU ne rend pas le devoir »\n\n"
            "Exemple 2 (loi 2) :\n"
            "  ¬(P ∨ Q) = ¬P ∧ ¬Q\n"
            "  = « L'étudiant ne réussit pas l'examen ET ne rend pas le devoir »"
        ),
    },

    "NEG_COMP": {
        "nom":        "Négation d'une proposition composée",
        "formule":    (
            "¬(P ∧ Q)  ≡  ¬P ∨ ¬Q      [De Morgan 1]\n"
            "¬(P ∨ Q)  ≡  ¬P ∧ ¬Q      [De Morgan 2]\n"
            "¬(P ⇒ Q)  ≡  P ∧ ¬Q       [négation implication]\n"
            "¬(P ⇔ Q)  ≡  P ⊕ Q        [ou exclusif]"
        ),
        "explication": (
            "Pour nier une proposition composée, on applique la règle "
            "qui correspond au connecteur principal :\n"
            "• Si c'est un ET (∧) → appliquer De Morgan 1\n"
            "• Si c'est un OU (∨) → appliquer De Morgan 2\n"
            "• Si c'est une implication (⇒) → P ∧ ¬Q\n"
            "• Si c'est une équivalence (⇔) → (P ∧ ¬Q) ∨ (¬P ∧ Q)"
        ),
        "exemple": (
            "¬(P ∧ Q) avec P = « Le médecin diagnostique » et Q = « prescrit »\n"
            "  Étape 1 : identifier le connecteur → ∧ (ET)\n"
            "  Étape 2 : appliquer De Morgan 1\n"
            "  Résultat : ¬P ∨ ¬Q\n"
            "  = « Le médecin ne diagnostique pas OU ne prescrit pas »"
        ),
    },

    "NEG_IMP": {
        "nom":        "Négation d'une implication",
        "formule":    (
            "¬(P ⇒ Q)  ≡  P ∧ ¬Q\n\n"
            "Preuve :\n"
            "  P ⇒ Q   ≡  ¬P ∨ Q\n"
            "  ¬(P ⇒ Q) ≡  ¬(¬P ∨ Q)\n"
            "             ≡  ¬(¬P) ∧ ¬Q    [De Morgan]\n"
            "             ≡  P ∧ ¬Q        [double négation]"
        ),
        "explication": (
            "La négation d'une implication est souvent mal comprise. "
            "¬(P ⇒ Q) ne signifie PAS « Si P, alors non(Q) ». "
            "La règle correcte est : P ∧ ¬Q, c'est-à-dire "
            "« P est vraie ET Q est fausse ». "
            "C'est exactement le seul cas où l'implication est fausse."
        ),
        "exemple": (
            "« Si l'étudiant travaille, alors il réussit »\n"
            "  P = « L'étudiant travaille »\n"
            "  Q = « L'étudiant réussit »\n\n"
            "  ¬(P ⇒ Q) = P ∧ ¬Q\n"
            "  = « L'étudiant travaille ET il ne réussit pas »\n\n"
            "  Erreur fréquente : « Si l'étudiant ne travaille pas, alors... »\n"
            "  → Ce serait la négation de P seulement, pas de l'implication !"
        ),
    },

    "QUANT_TRAD": {
        "nom":        "Traduction des quantificateurs",
        "formule":    (
            "∀x, P(x)  ←→  « Tous les x vérifient P »\n"
            "∃x, P(x)  ←→  « Il existe au moins un x qui vérifie P »\n\n"
            "Traduction formelle :\n"
            "  « Tous les A sont B »    → ∀x, A(x) ⇒ B(x)\n"
            "  « Il existe un A qui B » → ∃x, A(x) ∧ B(x)"
        ),
        "explication": (
            "Le quantificateur universel ∀ (pour tout) affirme que "
            "la propriété est vraie pour TOUS les éléments. "
            "Le quantificateur existentiel ∃ (il existe) affirme qu'il "
            "existe AU MOINS UN élément qui vérifie la propriété. "
            "Attention à l'ordre des quantificateurs : il est important !"
        ),
        "exemple": (
            "« Tous les étudiants comprennent ce cours »\n"
            "  → ∀x, Etudiant(x) ⇒ Comprend(x, cours)\n"
            "  Notation simplifiée : ∀x, P(x)\n\n"
            "« Il existe un étudiant qui comprend ce cours »\n"
            "  → ∃x, Etudiant(x) ∧ Comprend(x, cours)\n"
            "  Notation simplifiée : ∃x, P(x)"
        ),
    },

    "NEG_QUANT": {
        "nom":        "Négation des quantificateurs",
        "formule":    (
            "¬(∀x, P(x))  ≡  ∃x, ¬P(x)\n"
            "¬(∃x, P(x))  ≡  ∀x, ¬P(x)\n\n"
            "En langage naturel :\n"
            "  ¬(Tous les x...) = Il existe au moins un x qui ne...\n"
            "  ¬(Il existe un x...) = Tous les x ne..."
        ),
        "explication": (
            "Pour nier une proposition quantifiée, on échange "
            "les quantificateurs ET on nie la propriété :\n"
            "• ∀ devient ∃, et P devient ¬P\n"
            "• ∃ devient ∀, et P devient ¬P\n"
            "Le quantificateur s'inverse toujours, comme le connecteur "
            "s'inverse dans De Morgan."
        ),
        "exemple": (
            "Exemple 1 :\n"
            "  P : « Tous les médecins connaissent ce principe »\n"
            "  ∀x, P(x)\n"
            "  ¬(∀x, P(x)) = ∃x, ¬P(x)\n"
            "  = « Il existe au moins un médecin qui ne connaît pas ce principe »\n\n"
            "Exemple 2 :\n"
            "  P : « Il existe un étudiant qui réussit cet examen »\n"
            "  ∃x, P(x)\n"
            "  ¬(∃x, P(x)) = ∀x, ¬P(x)\n"
            "  = « Tous les étudiants ne réussissent pas cet examen »"
        ),
    },

    "CONTRAP": {
        "nom":        "Raisonnement par contraposée",
        "formule":    (
            "P ⇒ Q  ≡  ¬Q ⇒ ¬P\n\n"
            "Preuve :\n"
            "  P ⇒ Q   ≡  ¬P ∨ Q\n"
            "  ¬Q ⇒ ¬P ≡  ¬(¬Q) ∨ ¬P  =  Q ∨ ¬P  =  ¬P ∨ Q  ✓"
        ),
        "explication": (
            "La contraposée de « Si P, alors Q » est « Si non(Q), alors non(P) ». "
            "Ces deux formulations sont LOGIQUEMENT ÉQUIVALENTES : "
            "elles ont exactement la même table de vérité. "
            "Ne pas confondre avec :\n"
            "  • La réciproque : Q ⇒ P (non équivalente en général)\n"
            "  • L'inverse : ¬P ⇒ ¬Q (non équivalente en général)"
        ),
        "exemple": (
            "Original   : « Si l'étudiant travaille (P), alors il réussit (Q) »\n"
            "Contraposée: « Si l'étudiant ne réussit pas (¬Q), alors il ne travaille pas (¬P) »\n\n"
            "Réciproque (non équivalente) : « Si l'étudiant réussit, alors il travaille »\n"
            "Inverse (non équivalente)    : « Si l'étudiant ne travaille pas, alors il ne réussit pas »\n\n"
            "Vérification par table de vérité :\n"
            "  P=V, Q=V : P⇒Q = V  et  ¬Q⇒¬P = F⇒F = V  ✓\n"
            "  P=V, Q=F : P⇒Q = F  et  ¬Q⇒¬P = V⇒F = F  ✓\n"
            "  P=F, Q=V : P⇒Q = V  et  ¬Q⇒¬P = F⇒V = V  ✓\n"
            "  P=F, Q=F : P⇒Q = V  et  ¬Q⇒¬P = V⇒V = V  ✓"
        ),
    },
}


# ═════════════════════════════════════════════════════════════
# CONSEILS PAR TYPE D'ERREUR
# ═════════════════════════════════════════════════════════════

CONSEILS_ERREUR = {
    "NEG_SIMPLE": (
        "💡 Conseil : la négation insère simplement « ne... pas » "
        "autour du verbe principal. Ne modifiez pas le reste de la phrase."
    ),
    "NEG_COMP": (
        "💡 Conseil : repérez d'abord le connecteur principal (ET ou OU), "
        "puis appliquez la loi de De Morgan correspondante. "
        "ET devient OU, OU devient ET — et chaque proposition est niée."
    ),
    "NEG_IMP": (
        "💡 Conseil : ¬(P ⇒ Q) n'est PAS « Si P, alors ¬Q ». "
        "La bonne réponse est P ∧ ¬Q : "
        "P reste vraie et Q devient fausse."
    ),
    "NEG_QUANT": (
        "💡 Conseil : le quantificateur s'inverse toujours. "
        "¬∀ devient ∃, et ¬∃ devient ∀. "
        "N'oubliez pas de nier aussi la propriété P."
    ),
    "MORGAN": (
        "💡 Conseil : De Morgan en deux règles simples — "
        "¬(P ∧ Q) = ¬P ∨ ¬Q et ¬(P ∨ Q) = ¬P ∧ ¬Q. "
        "Le connecteur s'inverse et chaque terme est nié."
    ),
    "CONTRAP": (
        "💡 Conseil : la contraposée de (P ⇒ Q) est (¬Q ⇒ ¬P). "
        "On inverse ET on nie les deux propositions. "
        "Ne pas confondre avec la réciproque (Q ⇒ P) "
        "qui n'est pas équivalente."
    ),
    "IMP": (
        "💡 Conseil : l'implication P ⇒ Q n'est fausse "
        "QUE quand P est vraie et Q est fausse. "
        "Dans tous les autres cas, elle est vraie — "
        "notamment quand P est fausse (quelle que soit Q)."
    ),
    "EQUIV": (
        "💡 Conseil : P ⇔ Q est vraie quand P et Q ont "
        "la même valeur de vérité (toutes deux vraies ou toutes deux fausses). "
        "C'est une double implication : (P⇒Q) et (Q⇒P) simultanément."
    ),
    "TVER": (
        "💡 Conseil : référez-vous à la table de vérité complète. "
        "Le point le plus délicat est l'implication : "
        "elle n'est fausse QUE pour P=V et Q=F."
    ),
    "VVER": (
        "💡 Conseil : calculez d'abord la valeur de chaque "
        "proposition élémentaire, puis appliquez le connecteur. "
        "Pour l'implication, retenez : V⇒F = F, tous les autres cas = V."
    ),
    "CONN_TRAD": (
        "💡 Conseil : identifiez d'abord le connecteur principal "
        "dans la phrase (et, ou, si...alors, si et seulement si), "
        "puis traduisez avec le symbole correspondant (∧, ∨, ⇒, ⇔)."
    ),
    "CONN_INV": (
        "💡 Conseil : remplacez chaque symbole par son expression "
        "naturelle et reconstituez la phrase. "
        "⇒ se traduit toujours par « Si..., alors... »."
    ),
    "CONN_ID": (
        "💡 Conseil : cherchez le mot-clé du connecteur : "
        "« et » → ∧, « ou » → ∨, "
        "« si...alors » → ⇒, "
        "« si et seulement si » → ⇔."
    ),
    "QUANT_TRAD": (
        "💡 Conseil : « Tous les... » correspond à ∀ (pour tout) "
        "et « Il existe au moins un... » correspond à ∃ (il existe). "
        "La propriété P(x) représente ce que vérifie x."
    ),
    "PROP": (
        "💡 Conseil : une proposition doit être un énoncé déclaratif "
        "dont on peut dire qu'il est vrai ou faux. "
        "Les questions, ordres et opinions non vérifiables "
        "ne sont pas des propositions."
    ),
}


# ═════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE DE CORRECTION
# ═════════════════════════════════════════════════════════════

def corriger(
    objectif_code:   str,
    reponse_correcte: str,
    reponse_apprenant: str,
    enonce:          str,
    distracteurs:    list,
    p_phrase:        str = "",
    q_phrase:        str = "",
) -> dict:
    """
    Corrige la réponse d'un apprenant et retourne un feedback complet.

    Paramètres
    ----------
    objectif_code     : code de l'objectif (ex: "NEG_IMP")
    reponse_correcte  : bonne réponse attendue
    reponse_apprenant : réponse donnée par l'apprenant
    enonce            : texte de la question
    distracteurs      : liste des mauvaises réponses proposées
    p_phrase          : proposition P en langage naturel (si disponible)
    q_phrase          : proposition Q en langage naturel (si disponible)

    Retourne
    --------
    dict avec :
        est_correct      : bool
        message          : message principal
        reponse_correcte : la bonne réponse
        regle            : nom de la règle logique
        formule          : formule mathématique
        preuve           : preuve détaillée avec P et Q instanciés
        exemple          : exemple général
        conseil          : conseil si mauvaise réponse
        score_obtenu     : 1 si correct, 0 sinon
    """

    # ── Comparaison (insensible à la casse et aux espaces) ────
    est_correct = (
        reponse_apprenant.strip().lower() ==
        reponse_correcte.strip().lower()
    )

    regle = REGLES.get(objectif_code, {})
    conseil = "" if est_correct else CONSEILS_ERREUR.get(objectif_code, "")

    # ── Preuve instanciée avec P et Q réels ───────────────────
    preuve = _construire_preuve(
        objectif_code, p_phrase, q_phrase, reponse_correcte
    )

    # ── Message principal ─────────────────────────────────────
    if est_correct:
        message = "✅ Bonne réponse ! Vous avez correctement appliqué la règle."
    else:
        message = (
            f"❌ Mauvaise réponse.\n"
            f"Votre réponse : « {reponse_apprenant} »\n"
            f"Bonne réponse : « {reponse_correcte} »"
        )

    return {
        "est_correct":       est_correct,
        "message":           message,
        "reponse_correcte":  reponse_correcte,
        "regle":             regle.get("nom", ""),
        "formule":           regle.get("formule", ""),
        "preuve":            preuve,
        "exemple":           regle.get("exemple", ""),
        "conseil":           conseil,
        "score_obtenu":      1 if est_correct else 0,
    }


# ═════════════════════════════════════════════════════════════
# CONSTRUCTION DE LA PREUVE INSTANCIÉE
# ═════════════════════════════════════════════════════════════

def _construire_preuve(
    objectif_code: str,
    p_phrase: str,
    q_phrase: str,
    reponse: str,
) -> str:
    """
    Construit la preuve mathématique avec P et Q remplacés
    par les propositions réelles de la question.
    """

    p = p_phrase or "P"
    q = q_phrase or "Q"

    preuves = {

        "NEG_SIMPLE": (
            f"📐 Application de la règle ¬P :\n\n"
            f"  Proposition : P = « {p} »\n\n"
            f"  Règle       : ¬P inverse la valeur de vérité de P\n\n"
            f"  Application : ¬P = « {reponse} »\n\n"
            f"  Vérification :\n"
            f"    Si P est Vraie  → ¬P est Fausse\n"
            f"    Si P est Fausse → ¬P est Vraie"
        ),

        "NEG_COMP": (
            f"📐 Application des lois de De Morgan :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Règle : ¬(P ∧ Q) ≡ ¬P ∨ ¬Q\n"
            f"          ¬(P ∨ Q) ≡ ¬P ∧ ¬Q\n\n"
            f"  Étape 1 : identifier le connecteur principal\n"
            f"  Étape 2 : inverser le connecteur (∧↔∨)\n"
            f"  Étape 3 : nier chaque proposition\n\n"
            f"  Résultat : « {reponse} »"
        ),

        "NEG_IMP": (
            f"📐 Application de ¬(P ⇒ Q) ≡ P ∧ ¬Q :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Développement :\n"
            f"    P ⇒ Q    ≡  ¬P ∨ Q\n"
            f"    ¬(P ⇒ Q) ≡  ¬(¬P ∨ Q)\n"
            f"             ≡  ¬(¬P) ∧ ¬Q   [De Morgan]\n"
            f"             ≡  P ∧ ¬Q        [double négation]\n\n"
            f"  Application :\n"
            f"    P    = « {p} »\n"
            f"    ¬Q   = (négation de) « {q} »\n"
            f"    P∧¬Q = « {reponse} »"
        ),

        "NEG_QUANT": (
            f"📐 Application de la négation des quantificateurs :\n\n"
            f"  Proposition : « {p} »\n\n"
            f"  Règles :\n"
            f"    ¬(∀x, P(x)) ≡ ∃x, ¬P(x)\n"
            f"    ¬(∃x, P(x)) ≡ ∀x, ¬P(x)\n\n"
            f"  Étape 1 : identifier le quantificateur (∀ ou ∃)\n"
            f"  Étape 2 : inverser le quantificateur (∀↔∃)\n"
            f"  Étape 3 : nier la propriété P(x)\n\n"
            f"  Résultat : « {reponse} »"
        ),

        "MORGAN": (
            f"📐 Application des lois de De Morgan :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Loi 1 : ¬(P ∧ Q) ≡ ¬P ∨ ¬Q\n"
            f"  Loi 2 : ¬(P ∨ Q) ≡ ¬P ∧ ¬Q\n\n"
            f"  Règle de mémorisation :\n"
            f"    → Le connecteur s'inverse (∧ devient ∨ ou vice versa)\n"
            f"    → Chaque proposition est niée\n\n"
            f"  Application : « {reponse} »"
        ),

        "IMP": (
            f"📐 Application de la table de vérité de P ⇒ Q :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Table de vérité de l'implication :\n"
            f"    P=V, Q=V → P⇒Q = V\n"
            f"    P=V, Q=F → P⇒Q = F  ← seul cas faux\n"
            f"    P=F, Q=V → P⇒Q = V\n"
            f"    P=F, Q=F → P⇒Q = V\n\n"
            f"  Résultat pour cette question : {reponse}"
        ),

        "EQUIV": (
            f"📐 Application de P ⇔ Q ≡ (P ⇒ Q) ∧ (Q ⇒ P) :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  P ⇔ Q est vraie ssi P et Q ont la même valeur.\n\n"
            f"  Décomposition :\n"
            f"    P ⇔ Q ≡ (P ⇒ Q) ∧ (Q ⇒ P)\n"
            f"          ≡ (Si {p}, alors {q})\n"
            f"            ET (Si {q}, alors {p})\n\n"
            f"  Résultat : « {reponse} »"
        ),

        "CONTRAP": (
            f"📐 Application de P ⇒ Q ≡ ¬Q ⇒ ¬P :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Étapes de construction de la contraposée :\n"
            f"    Étape 1 : écrire ¬Q = (négation de Q)\n"
            f"    Étape 2 : écrire ¬P = (négation de P)\n"
            f"    Étape 3 : former ¬Q ⇒ ¬P\n\n"
            f"  Vérification par table de vérité :\n"
            f"    P=V,Q=V : P⇒Q=V  et  ¬Q⇒¬P = F⇒F = V  ✓\n"
            f"    P=V,Q=F : P⇒Q=F  et  ¬Q⇒¬P = V⇒F = F  ✓\n"
            f"    P=F,Q=V : P⇒Q=V  et  ¬Q⇒¬P = F⇒V = V  ✓\n"
            f"    P=F,Q=F : P⇒Q=V  et  ¬Q⇒¬P = V⇒V = V  ✓\n\n"
            f"  Contraposée : « {reponse} »"
        ),

        "CONN_TRAD": (
            f"📐 Traduction langage naturel → formule logique :\n\n"
            f"  Phrase : « {p} [connecteur] {q} »\n\n"
            f"  Étape 1 : P = « {p} »\n"
            f"  Étape 2 : Q = « {q} »\n"
            f"  Étape 3 : identifier le connecteur\n"
            f"            (et→∧, ou→∨, si...alors→⇒, ssi→⇔)\n\n"
            f"  Résultat : {reponse}"
        ),

        "CONN_INV": (
            f"📐 Traduction formule logique → langage naturel :\n\n"
            f"  P = « {p} »\n"
            f"  Q = « {q} »\n\n"
            f"  Correspondances :\n"
            f"    ∧ → « et »\n"
            f"    ∨ → « ou »\n"
            f"    ⇒ → « Si..., alors... »\n"
            f"    ⇔ → « ... si et seulement si ... »\n\n"
            f"  Traduction : « {reponse} »"
        ),

        "QUANT_TRAD": (
            f"📐 Traduction avec quantificateurs :\n\n"
            f"  Énoncé : « {p} »\n\n"
            f"  ∀ (pour tout) → « Tous les... »\n"
            f"  ∃ (il existe) → « Il existe au moins un... »\n\n"
            f"  Formule correspondante : {reponse}"
        ),

        "TVER": (
            f"📐 Lecture de la table de vérité :\n\n"
            f"  On cherche la valeur de la formule pour les valeurs données.\n\n"
            f"  Table complète :\n"
            f"  ┌───┬───┬───────┬───────┬───────┬───────┐\n"
            f"  │ P │ Q │ P ∧ Q │ P ∨ Q │ P ⇒ Q │ P ⇔ Q │\n"
            f"  ├───┼───┼───────┼───────┼───────┼───────┤\n"
            f"  │ V │ V │   V   │   V   │   V   │   V   │\n"
            f"  │ V │ F │   F   │   V   │   F   │   F   │\n"
            f"  │ F │ V │   F   │   V   │   V   │   F   │\n"
            f"  │ F │ F │   F   │   F   │   V   │   V   │\n"
            f"  └───┴───┴───────┴───────┴───────┴───────┘\n\n"
            f"  Résultat pour cette question : {reponse}"
        ),

        "VVER": (
            f"📐 Calcul de la valeur de vérité :\n\n"
            f"  Étape 1 : relever les valeurs de P et Q\n"
            f"  Étape 2 : appliquer le connecteur\n\n"
            f"  Rappel pour l'implication (cas le plus délicat) :\n"
            f"    V ⇒ V = V\n"
            f"    V ⇒ F = F  ← seul cas faux\n"
            f"    F ⇒ V = V\n"
            f"    F ⇒ F = V\n\n"
            f"  Résultat : {reponse}"
        ),

        "CONN_ID": (
            f"📐 Identification du connecteur principal :\n\n"
            f"  Correspondances à retenir :\n"
            f"    « et »                  → ∧  (conjonction)\n"
            f"    « ou »                  → ∨  (disjonction)\n"
            f"    « si..., alors... »     → ⇒  (implication)\n"
            f"    « si et seulement si »  → ⇔  (équivalence)\n\n"
            f"  Connecteur identifié : {reponse}"
        ),

        "PROP": (
            f"📐 Vérification qu'un énoncé est une proposition :\n\n"
            f"  Critères d'une proposition logique :\n"
            f"    ✓ Énoncé déclaratif (ni question, ni ordre)\n"
            f"    ✓ Valeur de vérité déterminable (V ou F)\n"
            f"    ✓ Non ambigu\n\n"
            f"  Proposition valide : « {reponse} »\n"
            f"  → Cet énoncé est déclaratif et a une valeur de vérité claire."
        ),
    }

    return preuves.get(
        objectif_code,
        f"📐 Règle appliquée : {REGLES.get(objectif_code, {}).get('formule', '')}"
    )


# ═════════════════════════════════════════════════════════════
# TEST
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Test du correcteur RALI-DEM ===\n")

    # Test 1 — bonne réponse
    r = corriger(
        objectif_code    = "NEG_IMP",
        reponse_correcte  = "le médecin suit cette méthode et la femme ne lit pas ce texte",
        reponse_apprenant = "le médecin suit cette méthode et la femme ne lit pas ce texte",
        enonce           = "Quelle est la négation de : « Si le médecin suit cette méthode, alors la femme lit ce texte » ?",
        distracteurs     = [],
        p_phrase         = "le médecin suit cette méthode",
        q_phrase         = "la femme lit ce texte",
    )
    print(r["message"])
    print(f"\n📏 Règle : {r['regle']}")
    print(f"\n📐 Formule :\n{r['formule']}")
    print(f"\n{r['preuve']}")
    print(f"\n📖 Exemple :\n{r['exemple']}")

    print("\n" + "─"*60 + "\n")

    # Test 2 — mauvaise réponse
    r2 = corriger(
        objectif_code    = "CONTRAP",
        reponse_correcte  = "Si l'ami ne montre pas cette solution, alors le voisin ne vérifie pas ce résultat",
        reponse_apprenant = "Si le voisin ne vérifie pas ce résultat, alors l'ami montre cette solution",
        enonce           = "Laquelle est la contraposée de : « Si le voisin vérifie ce résultat, alors l'ami montre cette solution » ?",
        distracteurs     = [],
        p_phrase         = "le voisin vérifie ce résultat",
        q_phrase         = "l'ami montre cette solution",
    )
    print(r2["message"])
    print(f"\n📏 Règle : {r2['regle']}")
    print(f"\n📐 Formule :\n{r2['formule']}")
    print(f"\n{r2['preuve']}")
    print(f"\n{r2['conseil']}")
