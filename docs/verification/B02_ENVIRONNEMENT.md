# B02 — Validation de l'environnement et du socle HTTP

**24 octobre 2026 — environnement local et contrat de santé vérifiés.**

## Périmètre

Le socle comprend l'application FastAPI, le contrat Pydantic de `/health`, l'environnement Python isolé et les commandes de vérification. L'organisation existante des données, références, tests et documents est conservée. Les modules d'analyse, retrieval et outils seront ajoutés selon la roadmap.

`GET /health` renvoie HTTP 200 et `{"status":"ok","corpus_version":null}`. Il indique la disponibilité du processus ; aucun corpus n'est encore chargé. Le schéma OpenAPI décrit uniquement `/health`. L'application ne charge pas les scripts de préparation ou les annotations d'évaluation.

## Versions vérifiées

| Composant | Version |
|---|---|
| CPython, Windows 64 bits | 3.14.5 |
| uv | 0.11.14 |
| FastAPI | 0.162.0 |
| Pydantic | 2.14.1 |
| Uvicorn | 0.54.0 |
| NumPy | 2.5.4 |
| SQLite, FTS5 disponible | 3.50.4 |
| Ruff | 0.17.2 |

`pyproject.toml` décrit les dépendances et les règles de code ; `uv.lock` conserve les versions résolues et les empreintes des distributions. `package = false` correspond à une application exécutée depuis le dépôt. La compatibilité vérifiée porte sur Python 3.14 et Windows.

Les paquets sont installés dans `.venv/` depuis PyPI sous forme précompilée. La création explicite de l'environnement avec Python ne demande ni activation PowerShell ni installation de pip. `.gitattributes` conserve les octets JSON et normalise les autres fichiers texte en LF ; les empreintes des références restent vérifiables entre copies.

## Reproduction

Depuis la racine, avec le brut et les exports préparés selon [README](../../README.md) :

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Appeler `Invoke-RestMethod http://127.0.0.1:8000/health` dans un autre terminal. Le contrat JSON est servi sur `/openapi.json` ; `/docs` fournit la documentation interactive FastAPI, dont les ressources de navigateur peuvent demander Internet. Arrêter le serveur avec Ctrl+C.

## Résultats observés

- Environnement créé et synchronisé avec le lockfile ; 16 paquets installés et dépendances compatibles.
- SQLite FTS5 : création, insertion et recherche en mémoire réussies ; produit scalaire NumPy conforme.
- HTTP réel : réponse 200 et contrat attendu pour `/health`, schéma OpenAPI valide.
- Les routes de données brutes, références d'évaluation et analyses non implémentées renvoient 404.
- Dix cas B01 conformes et trois tests négatifs réussis dans l'environnement du projet.
- Lint Ruff et contrôle de format des trois fichiers du socle réussis.
- Exclusions Git contrôlées pour l'environnement, les caches, secrets et données générées ; code, références et notices suivis.
- Aucun appel de modèle nécessaire aux vérifications. Le serveur de contrôle est arrêté après les essais.

Le point de santé mesure la disponibilité du processus. Il ne constitue pas un contrôle de disponibilité d'un fournisseur, de qualité de retrieval ou d'exactitude de réponse LLM. Les résultats courants de revue du dépôt et les contrôles de liens sont consignés dans la [revue de structure](STRUCTURE_REVIEW.md).

## Prochaine étape

B03 doit établir l'accès à un fournisseur hébergé, le contrat de sélection de cellules, les limites d'appel, le suivi d'usage et les premières mesures coût/latence. Aucun fournisseur ou modèle n'est encore configuré. Les tâches de suivi GitHub restent décrites dans le backlog, séparément de la validation technique du socle.

Sources : [uv : structure et lockfile](https://docs.astral.sh/uv/concepts/projects/layout/), [synchronisation verrouillée](https://docs.astral.sh/uv/concepts/projects/sync/), [FastAPI et OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [Ruff](https://docs.astral.sh/ruff/configuration/), [SQLite FTS5](https://sqlite.org/fts5.html), [attributs Git](https://git-scm.com/docs/gitattributes).
