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

## Décisions prises (26/11/2026)

- Conservation des données : 5 ans après la fin de la thèse ; contact : alinocm@gmail.com.
- CONTRAP compte 1 négation (pas de double négation au sens du protocole).
- Pas de correction pendant la session (`FEEDBACK_IMMEDIAT = False`) :
  l'étudiant voit seulement « Réponse enregistrée ».

## À faire avant la collecte

1. **Sauvegarder les données 2026** : télécharger les trois exports v1 depuis la
   page administrateur **avant** tout redéploiement (la base actuelle n'est pas
   sur un volume et sera effacée).
2. **Railway** : attacher un volume persistant monté sur `/data` au service
   `web` (la base y est créée quand `RAILWAY_ENVIRONMENT` est défini) et prévoir
   une sauvegarde régulière.
3. **Sécurité** : définir la variable `RALI_SECRET_KEY` sur Railway (longue
   valeur aléatoire), puis changer le mot de passe administrateur avec le
   bouton « Changer mon mot de passe » sous le nom de l'utilisateur connecté.
4. **Banque d'items** : la préparer et la faire valider (ci-dessous).
5. **Pilote** : faire passer 10 à 15 étudiants, puis vérifier l'export.

## Préparer la banque d'items

Tout se fait dans la page administrateur, menu **Expérimentation**, carte
« Banque d'items ».

1. **Générer les candidats** (3 par combinaison par défaut, soit 90 items).
2. **Télécharger la fiche** `banque_items_relecture.csv` et l'ouvrir dans Excel
   (séparateur `;`). Les enseignants écrivent `valide` ou `rejete` dans la
   colonne `statut` (les accents et les majuscules sont acceptés) et, si
   besoin, un commentaire. Ne pas modifier `code_item`.
3. **Envoyer la fiche remplie**, enregistrée au format CSV. On peut l'envoyer
   plusieurs fois ; les lignes non reconnues sont signalées.
4. Le compteur doit indiquer **30 / 30 combinaisons validées**. Pour les
   combinaisons restantes, utiliser « Seulement les combinaisons sans item
   validé », puis recommencer les étapes 2 et 3.

Si plusieurs items sont validés pour une combinaison, le plus ancien est
retenu. Dès qu'un item retenu a été présenté à un étudiant, sa combinaison est
verrouillée (🔒) : on ne peut plus la changer, pour que tous les étudiants
reçoivent le même item. Les items du pilote sont donc ceux de la collecte.

Les mêmes opérations restent possibles par l'API (`/api/exp/banque/generer`,
`/export`, `/validation`, `/validation_csv`, `/etat`).

## Exports (administrateur)

| Route | Contenu |
| --- | --- |
| `/api/exp/export/reponses` | Une ligne par réponse : item, source, position des options, ERT-A, ERT-B et leurs composantes, temps, temps passé hors de la page |
| `/api/exp/export/items` | Tous les items servis, avec leur texte complet |
| `/api/exp/export/qualitatif` | Questionnaire, une ligne par session |
| `/api/exp/export/v1/...` | Données de la collecte 2026 |

## Réglages (`backend/experimentation.py`)

- `NB_GENERES = 6` : nombre de questions générées par session.
- `FEEDBACK_IMMEDIAT = False` : aucune correction pendant la session.
- `CONSENTEMENT_VERSION` : à changer si le texte du consentement change.

Les coefficients des deux formules sont dans `backend/calculator.py`
(`PARAMS_VERSION`) et ne doivent pas être modifiés pendant une collecte.
