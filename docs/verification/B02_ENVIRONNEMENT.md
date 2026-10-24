# B02 — Environnement et API minimale

**Vérification du 24 octobre 2026. Socle technique local validé ; organisation distante GitHub encore à effectuer.**

## Résultat et périmètre

La structure existante convient au jalon : `docs/architecture/`, `docs/Backlog/`, `docs/verification/`, `scripts/`, `tests/`, `data/` et `evals/` sont conservés. Seul `app/` est ajouté pour une API réelle. Aucun module d'analyse, répertoire de prompts vide, framework d'agents, base distante ou migration `src/` n'est introduit.

Le point de santé est `GET /health` → HTTP 200, `{"status":"ok","corpus_version":null}`. Il indique la disponibilité du processus, sans promettre la disponibilité d'un corpus ou d'un fournisseur. L'API n'importe ni le script de préparation ni les références d'évaluation. Le schéma OpenAPI ne comporte que `/health`. Le serveur de vérification est arrêté après le contrôle.

## Choix et versions réellement testés

| Élément | Version / rôle |
|---|---|
| Windows, Python | CPython 3.14.5, 64 bits ; `.python-version` fixe la version testée |
| uv | 0.11.14 ; environnement `.venv/`, résolution et synchronisation |
| FastAPI | 0.162.0 ; route HTTP et documentation OpenAPI |
| Pydantic | 2.14.1 ; contrat typé de réponse |
| Uvicorn | 0.54.0 ; serveur local |
| NumPy | 2.5.4 ; produit scalaire vérifié, préparation du futur essai sémantique |
| SQLite | 3.50.4 ; module standard, FTS5 testé avec insertion et recherche |
| Ruff | 0.17.2 ; lint et format des nouveaux fichiers |

`pyproject.toml` décrit les dépendances et règles de code ; `uv.lock` conserve les versions résolues et les empreintes des distributions. Le projet reste une application locale sans paquet à publier (`package = false`). Le développement cible actuellement Python 3.14 ; aucune compatibilité avec d'autres versions n'est revendiquée.

La bibliothèque standard peut créer l'environnement avant `uv sync` : cela évite une restriction Windows rencontrée par l'assistant lors de la création des lanceurs. L'installation a ensuite été effectuée avec les permissions nécessaires, sans changement du PATH global. Les installations utilisent les distributions précompilées de PyPI (`--no-build`) ; pas de compilation locale de dépendances natives.

`.gitattributes` impose LF pour le texte et laisse les octets JSON inchangés, car les preuves B01 incluent des empreintes de JSON existants. Cela évite qu'une conversion automatique Git des fins de ligne invalide ces empreintes. Aucun fichier B01 n'est reformatté. Les règles Ruff E4/E7/E9/F sont explicites ; le format est appliqué progressivement aux nouveaux fichiers.

## Reproduire

Depuis la racine, les instructions complètes sont dans [README](../../README.md). Aucune activation de script PowerShell, clé API ou variable de fournisseur n'est requise :

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

Les données B01 sont déjà présentes sur cette machine. Sur une copie neuve, suivre d'abord le téléchargement et la génération B01 documentés dans README. Dans un autre terminal, appeler `Invoke-RestMethod http://127.0.0.1:8000/health` ; arrêter le serveur avec Ctrl+C. `/docs` utilise la documentation interactive par défaut de FastAPI, dont les ressources de navigateur peuvent demander Internet ; `/health` et `/openapi.json` sont servis localement.

## Vérifications exécutées

- Environnement recréé dans le projet puis synchronisé avec le lockfile : réussite ; 16 paquets installés, dépendances compatibles.
- SQLite FTS5 : création d'une table en mémoire, insertion et recherche réussies. NumPy : produit scalaire attendu obtenu.
- HTTP réel : `/health` renvoie 200 avec le contrat attendu ; schéma `/openapi.json` valide. Les chemins de données brutes, références et analyses non implémentées renvoient 404.
- **10 cas B01 et 3 tests négatifs réussis** dans le nouvel environnement, sans réécriture des exports.
- Ruff : lint réussi sur le code ; trois nouveaux fichiers conformes au format.
- **39 liens Markdown locaux valides**, avec contrôle de casse.
- Git : **36 fichiers suivis**, sept chemins locaux/secrets contrôlés comme ignorés ; aucun secret détecté par les motifs ciblés examinés. Ce contrôle ne constitue pas une détection exhaustive de secrets.
- **35 fichiers préexistants inchangés**, y compris toutes les données, références, le code et les preuves B01. Empreintes du manifeste, de l'instantané et du script conservées dans les objets Git malgré les différences de fins de ligne.
- Aucun appel de modèle, coût API, publication ou création distante GitHub.

## Git et reste à faire

Le dépôt Git local contient un premier commit du socle vérifié, avec l'identité Git déjà configurée et son adresse GitHub de non-divulgation. Aucune identité n'est inventée ni configuration globale modifiée. Les données brutes, exports sources, environnement et caches sont exclus ; les références, preuves, code, `pyproject.toml` et `uv.lock` restent suivis.

La publication distante et le tableau GitHub restent à effectuer par l'utilisateur, comme prévu dans les échanges précédents. Aucun dépôt distant, ticket ou tableau n'est annoncé comme créé. La licence générale du code reste à choisir ; la notice FinQA est conservée.

La suite technique est B03 : vérifier un fournisseur/modèle, coût, latence, sortie structurée, appels bornés et première trace. Aucun LLM, RAG, index documentaire, embedding ou agent n'est encore implémenté. Aucun appel de modèle ni dépense API n'a été effectué en B02. Le socle local n'est pas une preuve de performance IA ou de préparation à la production.

## Ce qu'il faut comprendre

1. L'environnement isole les dépendances ; le lockfile permet de retrouver les mêmes versions.
2. FastAPI reçoit une requête HTTP, Pydantic définit le contrat, Uvicorn écoute sur l'interface locale.
3. Le point de santé ne lit pas les références : le calcul et le RAG seront des fonctions distinctes, construites et évaluées plus tard.

Sources techniques : [uv : structure et lockfile](https://docs.astral.sh/uv/concepts/projects/layout/), [uv : synchronisation verrouillée](https://docs.astral.sh/uv/concepts/projects/sync/), [FastAPI : premiers pas et OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [Ruff : configuration](https://docs.astral.sh/ruff/configuration/), [SQLite FTS5](https://sqlite.org/fts5.html), [Git : attributs de texte](https://git-scm.com/docs/gitattributes).
