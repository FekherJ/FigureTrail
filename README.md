# FigureTrail

Analyse chiffrée de rapports publics avec preuves traçables : retrouver les valeurs, identifier leurs unités et périodes, calculer un ratio ou une variation et restituer les cellules sources.

La conception associe recherche documentaire, sélection structurée par LLM et calcul déterministe avec `Decimal`. Le modèle sélectionne les preuves ; les opérandes et le résultat proviennent des données et du code.

## État du projet

**Développement actif — état vérifié au 24 octobre 2026.**

| Composant | État |
|---|---|
| Références de données | 10 cas FinQA vérifiés : cellules, unités, périodes, formules et résultats |
| Reproductibilité | Environnement Python isolé, dépendances verrouillées, contrôles relançables |
| API | `/health`, contrat Pydantic et schéma OpenAPI opérationnels |
| Recherche et analyse | Corpus indexé, retrieval lexical/sémantique et analyse LLM planifiés |
| Outils et exploitation | Agent borné, garde-fous d'analyse et traces d'exécution planifiés |

Les contrôles existants valident les données de référence et le socle HTTP. Les performances LLM/RAG seront mesurées après implémentation ; aucun score de modèle n'est publié à ce stade.

## Installation et démarrage

Configuration vérifiée : **Windows, Python 3.14.5, uv 0.11.14**. Les commandes se lancent depuis la racine du dépôt.

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`uv.lock` fixe les versions résolues. `--locked` refuse une modification implicite du lockfile ; `--no-build` utilise des distributions précompilées. Le premier téléchargement demande Internet. L'activation PowerShell de l'environnement n'est pas nécessaire. Dans VS Code, sélectionner `.venv\Scripts\python.exe`.

Dans un autre terminal :

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

```json
{"status":"ok","corpus_version":null}
```

Le point de santé indique que le processus répond. `corpus_version: null` indique qu'aucun corpus n'est chargé. Le contrat est disponible sur `/openapi.json` et la documentation interactive sur `/docs`. Le serveur écoute sur `127.0.0.1` ; **Ctrl+C** l'arrête. Aucune clé de fournisseur n'est requise pour ce socle.

## Préparation des données

Source : [FinQA](https://github.com/czyssrs/FinQA), textes et tableaux publics accompagnés d'annotations. Sur une nouvelle copie, télécharger le brut puis générer les exports séparés :

```powershell
New-Item -ItemType Directory -Force -Path data/raw | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json' -OutFile data/raw/finqa-dev.json
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all
```

Si le brut est déjà présent, conserver ce fichier et lancer la génération. Son empreinte est vérifiée avant lecture. Une modification de la source nécessite une revue de provenance.

Les exports sources contiennent uniquement `filename`, `pre_text`, `post_text`, `table` et `table_ori`. Les questions, réponses, programmes et preuves annotées restent dans les références d'évaluation. Les dix cas sont des cas de développement ; les rapports PDF originaux n'ont pas été inspectés.

## Vérifications

Après préparation des données :

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
```

Résultats vérifiés : **10 cas conformes et 3 tests négatifs réussis**. Les tests rejettent une mauvaise année, une confusion ratio/pourcentage et une réponse introduite dans un export source. Le script de vérification refuse le mode Python `-O`, qui désactive ses assertions.

Ruff contrôle le lint de l'ensemble du code et le format des fichiers du socle API. Les scripts de contrôle FinQA fonctionnent également avec la bibliothèque standard seule. Les contrôles de données sont distincts des futures évaluations de retrieval et de réponse.

## Organisation

```text
app/                    API et contrats actuellement implémentés
scripts/                Préparation des données et contrôles d'environnement
tests/                  Tests automatisés
evals/cases/            Références ; réservées à l'évaluation
data/                   Sources locales, provenance et notice de licence
docs/architecture/     Conception, contrats et décisions techniques
docs/Backlog/           Roadmap B01–B13 et cas de référence
docs/verification/     Rapports, résultats et limites vérifiés
```

Les données téléchargées, exports générés, traces et `.venv/` restent hors du suivi Git. Les modules applicatifs sont ajoutés avec leur première fonctionnalité, selon la roadmap.

## Principes de conception

- **Preuves avant calcul** : références de cellules, unités et périodes contrôlées ; calcul déterministe.
- **Évaluation indépendante** : annotations et rapports de vérification exclus du corpus d'inférence.
- **Comparaisons mesurées** : référence lexicale, variante sémantique, puis agent borné sur les mêmes conditions.
- **Exécution contrôlée** : permissions des outils, limites d'appels, coûts, erreurs et versions explicites.

La prochaine étape technique est l'intégration d'un fournisseur hébergé avec contrat de sortie, mesure coût/latence et premières traces. Le fournisseur et les modèles restent à sélectionner.

## Documentation

- [Architecture et contrats](docs/architecture/ARCHITECTURE_PROJET_IA.md)
- [Standards techniques](docs/architecture/AI_PROJECT_BLUEPRINT.md) et [revue de conception sourcée](docs/verification/AI_PROJECT_BLUEPRINT_REVIEW.md)
- [Roadmap et critères d'acceptation](docs/Backlog/BACKLOG_PROJET_IA.md)
- [Vérification des données](docs/verification/B01_VERIFICATION_DONNEES.md), [résultats exacts](docs/verification/B01_VERIFICATION_RESULTS.json) et [validation de l'environnement](docs/verification/B02_ENVIRONNEMENT.md)
- [Revue de structure](docs/verification/STRUCTURE_REVIEW.md) et [consignes de contribution](AGENTS.md)
- [Provenance FinQA](data/FINQA_PROVENANCE.md) et [notice de licence](data/FINQA_LICENSE.txt)

La notice FinQA s'applique aux données concernées. La licence générale du code FigureTrail reste à définir avant une distribution sous licence explicite.
