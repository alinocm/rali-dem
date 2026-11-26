# Collecte v2 — mise en œuvre

Branche `corrections-p0`. Cette notice décrit ce qui change, ce qu'il reste
à faire avant la collecte et comment préparer la banque d'items.

## Ce qui change

| Domaine | Avant (collecte 2026) | Maintenant (protocole v2) |
| --- | --- | --- |
| Temps estimés | Un seul (ERT-B), affiché à l'étudiant | ERT-A (Ms Generator V2) et ERT-B, calculés par le serveur, jamais affichés |
| Variables de complexité | Fixées en dur ou modifiées par la page | Calculées par le générateur et enregistrées telles quelles |
| Items | Générés à la volée pour chaque étudiant | 24 items d'une banque validée (communs à tous) + 6 générés, en rotation |
| Mode Bloom / complexité | Compréhension = « moyen », Analyse = « élevé » | Les 15 objectifs dans les 2 modes ; niveau calculé sans le bonus Analyse |
| Options | Cases vides, justifications « erreur : … » | Seulement les options réelles ; même forme de justification pour toutes |
| Écran | Chronomètre, ERT, objectif et mode affichés | Seulement « Question n / 30 » |
| Fiabilité | Réponses perdues, doublons, questions sautées | Nouvel essai automatique, une réponse par question, boutons bloqués après un clic |
| Reprise | Impossible après une coupure | Reprise par le même e-mail ou après rechargement de la page |
| Consentement | Toujours enregistré « oui », texte incomplet | Case réellement transmise, version et date enregistrées |
| Exports | Colonnes décalées (v1) | Sans nom, prénom ni e-mail ; colonnes conformes à l'en-tête |

Les tables existantes sont conservées ; la migration ajoute des colonnes et des
tables au démarrage du serveur, sans toucher aux données de 2026.

## À faire avant la collecte

1. **Consentement** : compléter dans `frontend/experimentation_ui.html` la durée
   de conservation et l'adresse de contact (repérées par `À COMPLÉTER`).
2. **CONTRAP** : confirmer le nombre de négations (1 ou 2) dans
   `NEGATIONS_PAR_OBJECTIF` (`backend/generator.py`).
3. **Railway** : vérifier qu'un volume persistant est monté sur `/data`
   (la base y est créée quand `RAILWAY_ENVIRONMENT` est défini) et prévoir une
   sauvegarde quotidienne du fichier `/data/rali_dem.db`.
4. **Banque d'items** : la préparer et la faire valider (ci-dessous).
5. **Pilote** : faire passer 10 à 15 étudiants, puis vérifier l'export.

## Préparer la banque d'items (administrateur)

1. Générer des candidats : `POST /api/exp/banque/generer?nb_par_combinaison=3`
   (3 candidats pour chacune des 30 combinaisons objectif × mode).
2. Télécharger la fiche de relecture : `GET /api/exp/banque/export`.
3. Les enseignants remplissent la colonne `statut` (`valide` ou `rejete`) et un
   commentaire. Il faut au moins un item `valide` par combinaison ; si
   plusieurs sont validés, le plus ancien est retenu pour tous les étudiants.
4. Renvoyer les décisions : `POST /api/exp/banque/validation` avec
   `{"lignes": [{"code_item": "...", "statut": "valide", "commentaire": "..."}]}`.
5. Contrôler : `GET /api/exp/banque/etat` doit indiquer 30 combinaisons validées.
   Une combinaison sans item validé est servie par le générateur.

## Exports (administrateur)

| Route | Contenu |
| --- | --- |
| `/api/exp/export/reponses` | Une ligne par réponse : item, source, position des options, ERT-A, ERT-B et leurs composantes, temps, temps passé hors de la page |
| `/api/exp/export/items` | Tous les items servis, avec leur texte complet |
| `/api/exp/export/qualitatif` | Questionnaire, une ligne par session |
| `/api/exp/export/v1/...` | Données de la collecte 2026 |

## Réglages (`backend/experimentation.py`)

- `NB_GENERES = 6` : nombre de questions générées par session.
- `FEEDBACK_IMMEDIAT = True` : correction affichée après chaque question
  (point P1 encore à décider).
- `CONSENTEMENT_VERSION` : à changer si le texte du consentement change.

Les coefficients des deux formules sont dans `backend/calculator.py`
(`PARAMS_VERSION`) et ne doivent pas être modifiés pendant une collecte.
