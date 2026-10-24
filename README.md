# FigureTrail

Retrouver des chiffres dans des rapports publics, calculer une variation ou un ratio et montrer les preuves : cellules, périodes, unités et formule.

**État au 24 octobre 2026 : B01 vérifié ; socle local B02 opérationnel.** Dix cas FinQA sont vérifiés. Un environnement verrouillé et une API minimale `/health` fonctionnent. Le LLM hébergé, le RAG, l'API d'analyse et l'agent restent à construire. L'organisation distante GitHub reste à effectuer.

## Ce qui fonctionne

- Préparation reproductible de dix contextes sources, séparés des réponses attendues.
- Vérification des cellules, unités, périodes et calculs avec `Decimal`.
- Audit des doublons de contexte et identification de trois candidats distracteurs.
- Dix contrôles de cas et trois tests négatifs : mauvaise année, confusion ratio/pourcentage et réponse présente dans un export source.
- Environnement isolé, dépendances verrouillées, contrôles SQLite FTS5/NumPy et endpoint de santé sans appel IA.

Ces contrôles valident les exemples sélectionnés dans les textes/tableaux FinQA. Aucun PDF original n'a été inspecté et aucun score LLM/RAG n'a été mesuré. Aucun appel LLM ni dépense API n'est nécessaire pour cette étape.

## Organisation actuelle

```text
FigureTrail/
  app/                  # __init__.py et main.py : API minimale
  docs/
    architecture/       # conception et schémas Mermaid
    Backlog/            # tâches B01 à B13 et notes des premières séances
    verification/       # rapports de vérification et résultats justificatifs
  scripts/              # commandes locales de préparation et de contrôle
  tests/                # tests automatisés des contrôles existants
  evals/cases/          # références et manifeste de revue ; jamais en inférence
  data/
    raw/                # téléchargement original, ignoré par Git
    samples/            # contextes sources générés, ignorés par Git
    FINQA_PROVENANCE.md
    FINQA_LICENSE.txt
  AGENTS.md             # consignes pour l'assistance au développement
  .editorconfig         # conventions d'édition
  .gitignore            # données locales, secrets et fichiers générés
  .gitattributes        # fins de ligne ; préservation des octets JSON
  .python-version       # Python testé
  pyproject.toml        # dépendances et configuration Ruff
  uv.lock               # versions résolues, à conserver dans Git
  README.md
```

Les autres modules seront ajoutés avec leur première fonctionnalité. `.venv/` et les caches restent locaux et ignorés par Git. La [conception cible](docs/architecture/ARCHITECTURE_PROJET_IA.md) les distingue de l'état actuel.

## Démarrer B02 sur Windows

Prérequis vérifiés : **Python 3.14.5 et uv 0.11.14**. Depuis la racine du projet :

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La création explicite par Python fonctionne aussi dans l'environnement Windows restreint de cette vérification. uv installe les paquets dans `.venv/`, sans activation PowerShell. `--locked` refuse de modifier silencieusement les versions ; `--no-build` exige des distributions précompilées. Internet est nécessaire au premier téléchargement. Voir les [versions et preuves B02](docs/verification/B02_ENVIRONNEMENT.md).

Si uv n'est pas reconnu dans VS Code, ouvrir un nouveau terminal. Sur cette machine, remplacer si nécessaire `uv` par `& "$env:USERPROFILE\.local\bin\uv.exe"`. Sélectionner l'interpréteur `.venv\Scripts\python.exe` du projet dans VS Code.

Dans un deuxième terminal :

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Réponse : `{"status":"ok","corpus_version":null}`. `ok` signifie que le processus répond ; `null` indique qu'aucun corpus n'est chargé. Le schéma est disponible sur `/openapi.json`, sa documentation interactive sur `/docs`. Arrêter le serveur avec **Ctrl+C**. Aucune clé ni configuration de fournisseur n'est nécessaire en B02 ; leur ajout appartient à B03.

Contrôles de code :

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py
```

Le lint couvre le code avec les règles explicites E4/E7/E9/F. Le format porte sur les nouveaux fichiers B02, pour préserver le code B01 associé aux preuves existantes. Ruff ne remplace pas un contrôle de types. Les commandes B01 restent indépendantes des paquets tiers et fonctionnent aussi via `uv run --locked python`.

## Reproduire B01 sur Windows

Prérequis vérifié : **Python 3.14.5**, accessible par `python3.14.exe`. Aucun paquet tiers n'est nécessaire pour B01. Les commandes suivantes se lancent depuis la racine du projet.

Sur une nouvelle copie, télécharger le fichier public une fois :

```powershell
python3.14.exe --version
New-Item -ItemType Directory -Force -Path data/raw | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json' -OutFile data/raw/finqa-dev.json
```

Si le fichier brut est déjà présent, passer directement à la génération. Le script vérifie son empreinte avant toute lecture. Une empreinte différente demande de relire le changement, pas de désactiver le contrôle.

**Générer d'abord les dix exports sources**, puis les vérifier :

```powershell
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all --check
python3.14.exe -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
```

Résultat attendu et observé : **10 cas conformes et 3 tests négatifs réussis**. La génération régénère aussi les dix références originales dans `evals/cases/` à partir du brut vérifié. `--check` ne réécrit aucun export ; il suppose qu'ils ont déjà été générés. Ne pas utiliser `-O`, qui désactive les assertions : le script refuse ce mode.

Sans option, la commande conserve le premier exemple. `--case growth` choisit le deuxième ; `--case case03` à `case10` choisit les suivants.

## Données, références et preuves

- **Sources** : `data/samples/*-source.json`, limitées à `filename`, `pre_text`, `post_text`, `table`, `table_ori`. Toutes les lignes du contexte sont conservées.
- **Références** : [manifeste des dix cas](evals/cases/finqa-b01-reviewed.json) et annotations FinQA originales dans `evals/cases/`. Le manifeste contient aussi les questions adaptées avec entreprise, périodes et périmètre explicites.
- **Preuves** : [rapport B01](docs/verification/B01_VERIFICATION_DONNEES.md), [résultats exacts](docs/verification/B01_VERIFICATION_RESULTS.json) et [revue de structure](docs/verification/STRUCTURE_REVIEW.md).
- **Provenance** : [origine et empreinte du téléchargement](data/FINQA_PROVENANCE.md), [notice FinQA](data/FINQA_LICENSE.txt).

Les réponses attendues, programmes et bonnes preuves dans `evals/` et `docs/verification/` sont exclus de toute future ingestion d'inférence. La préparation du corpus utilisera une liste positive de champs sources. Le fichier brut contient lui aussi des annotations et reste hors de l'inférence.

Des tirets sont normalisés en `2014` dans des cellules inutilisées des contextes DVN et MAS. B04 devra traiter ces conflits avant indexation ; les vingt cellules utilisées par B01 concordent entre les deux tableaux. Les précisions d'affichage et conventions de `exe_ans` sont documentées par cas.

## Architecture et suite

Priorités : **LLM/RAG, API/architecture et évaluations**, puis outils/agent, garde-fous et observabilité. La cible est une application Python locale avec calcul déterministe, un LLM hébergé et des traces inspectables.

- [Architecture et contrats proposés](docs/architecture/ARCHITECTURE_PROJET_IA.md).
- [Blueprint : standards techniques et recommandations](docs/architecture/AI_PROJECT_BLUEPRINT.md).
- [Vérification du blueprint et sources](docs/verification/AI_PROJECT_BLUEPRINT_REVIEW.md).
- [Backlog B01 à B13 et critères d'acceptation](docs/Backlog/BACKLOG_PROJET_IA.md).
- [Consignes de travail](AGENTS.md).

Le blueprint complète l'architecture ; son arborescence est une cible progressive. Le backlog fixe l'ordre et le périmètre. Appliquer les recommandations utiles à chaque étape, conserver les éléments déjà conformes et justifier toute nouvelle dépendance ou réorganisation.

**Suite technique : B03**, choisir et tester un modèle hébergé avec des mesures de coût et de latence. Aucun fournisseur n'est choisi. Le socle B02 et le dépôt Git sont locaux ; la publication et le tableau GitHub restent à effectuer selon le backlog.

Le code comprend la préparation/contrôle des données et le point de santé ; il ne constitue pas encore le service d'analyse décrit dans l'architecture. La licence FinQA conservée concerne la source de données ; aucune licence générale du code FigureTrail n'a encore été choisie.
