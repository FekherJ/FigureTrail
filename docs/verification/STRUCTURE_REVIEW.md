# FigureTrail — Revue de structure et de documentation

**24 octobre 2026 — périmètre : dépôt existant et socle local B02.**

## Organisation retenue

La structure sépare application, préparation des données, tests, références d'évaluation et preuves de vérification. Elle conserve les chemins existants et permet l'ajout progressif des capacités prévues sans migration de packaging ni modules vides.

| Emplacement | Responsabilité | Règle |
|---|---|---|
| `app/` | API et contrats applicatifs | Point de santé implémenté ; service d'analyse à construire |
| `scripts/` | Préparation et vérification locale | Commandes relançables avec chemins relatifs |
| `tests/` | Tests automatisés | Vérifications des erreurs et frontières de données |
| `evals/cases/` | Références et manifeste | Aucun chargement par le service d'inférence |
| `data/` | Sources locales et provenance | Brut/exports générés ignorés ; notice et provenance suivies |
| `docs/architecture/` | Conception et contrats cibles | Distinction explicite avec le code disponible |
| `docs/Backlog/` | Roadmap et critères d'acceptation | Identifiants B01–B13 stables |
| `docs/verification/` | Preuves, mesures et limites | Exclu de l'ingestion d'inférence |

Les rapports sont regroupés sous `docs/verification/`. Les conventions d'édition, exclusions Git et attributs de fins de ligne restent à la racine. Aucun déplacement de fichiers ou changement de casse supplémentaire n'est nécessaire.

## Conventions de documentation

README présente la finalité du service, les capacités implémentées, l'installation, les contrôles et les références techniques. Architecture et backlog décrivent les décisions, dépendances et critères de validation. Les rapports décrivent la méthode, les données effectivement vérifiées et les limites de mesure.

La présentation reste centrée sur le produit et ses preuves. Les métadonnées de revue conservent l'assistance IA et les contrôles déterministes comme provenance ; aucune revue humaine indépendante ou fonctionnalité non vérifiée n'est attribuée au projet.

## Vérifications

- **47 fichiers de projet examinés**, hors métadonnées Git, environnement et caches ; 18 fichiers adaptés, sans ajout ni suppression de fichier.
- **40 liens Markdown locaux valides**, existence et casse contrôlées.
- Dix cas de référence et trois tests négatifs réussis ; valeurs, cellules, unités, périodes, opérations, tolérances et annotations FinQA originales inchangées.
- Lint Ruff réussi et format des trois fichiers du socle conforme.
- Modifications Python limitées aux docstrings et au message de refus de `-O` ; structure syntaxique fonctionnelle vérifiée identique après retrait de ces textes.
- Dépendances, lockfile, licences, données sources, conventions Git et logique applicative conservés.
- Identifiants B01–B13, priorités, dépendances, estimations et schémas Mermaid conservés ; statut du remote GitHub actualisé, tableau d'issues non déclaré configuré.
- Métadonnées de revue normalisées avec provenance assistée par IA conservée ; empreintes du manifeste et du vérificateur cohérentes avec l'instantané.
- Aucun appel LLM, nouvelle dépendance, changement d'historique Git ou publication distante effectué par cette revue.

Les chiffres de B01 restent des résultats de contrôle de données, pas des scores LLM/RAG. Les références originales FinQA, le téléchargement et les exports sources sont conservés. Les empreintes du manifeste et du vérificateur sont actualisées dans l'instantané pour refléter uniquement la normalisation des métadonnées et du message de diagnostic.

## Suite de réalisation

| Étape | Critères à établir |
|---|---|
| B03 | Fournisseur/modèles, contrat structuré, coût/latence et premières traces |
| B04–B08 | Corpus/index sans annotations, conflits de tableaux traités, recherche et évaluations réservées |
| B09–B12 | Interface de preuves, outils bornés, contrôles de sécurité et observabilité |
| B13 | Validation finale, reproduction et documentation de livraison |

La [roadmap](../Backlog/BACKLOG_PROJET_IA.md) conserve son périmètre. Les preuves de données sont détaillées dans le [rapport B01](B01_VERIFICATION_DONNEES.md) et l'[instantané associé](B01_VERIFICATION_RESULTS.json). Le [rapport B02](B02_ENVIRONNEMENT.md) décrit le socle HTTP et les versions vérifiées.
