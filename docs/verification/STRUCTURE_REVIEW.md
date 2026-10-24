# FigureTrail — Revue de structure

**24 octobre 2026 — Périmètre : l'ensemble des fichiers locaux du projet à l'issue de B01.**

## Conclusion

La structure constitue une base cohérente pour ce projet d'apprentissage et de portfolio : documentation, sources, références d'évaluation et code de contrôle ont des responsabilités distinctes. Elle est adaptée au stade B01. La qualité du futur système IA devra ensuite être démontrée par son implémentation et ses évaluations.

Cette revue contrôle l'organisation du dépôt, les chemins, les exclusions Git et la reproduction des vérifications existantes. Elle ne constitue pas un audit de sécurité de production ni une validation de fonctionnalités IA encore absentes.

## Changements effectués

| Point observé | Correction |
|---|---|
| Rapports de preuve isolés à la racine | Déplacement des deux fichiers B01 dans `docs/verification/`. |
| Références vers l'ancien emplacement | Mise à jour de README, AGENTS, backlog, fiches B01, provenance et rapport. |
| README accumulant anciennes consignes de démarrage | Présentation recentrée sur le projet, son état réel, sa structure et les commandes reproductibles. |
| Vérification sur une nouvelle copie avant génération des sources ignorées par Git | Instructions dans l'ordre : obtenir le brut, générer les dix exports, lancer les contrôles. |
| Architecture indiquant encore dix cas à sélectionner | Statut B01 actualisé ; ajout des preuves dans l'arborescence documentée. |
| Rapports contenant les bonnes réponses | Exclusion de `docs/verification/` de l'inférence explicitée, comme pour `evals/`. |
| Conventions d'édition non partagées | Ajout de `.editorconfig`, sans reformater les données ou le code existants. |
| Dossiers temporaires possibles si un test est interrompu | Ajout de `/tests/.b01-*/` à `.gitignore`. |

## Responsabilité de chaque emplacement

| Emplacement depuis la racine | Contenu | Versionnement / usage |
|---|---|---|
| `README.md` | Présentation, état réel, commandes et points d'entrée | À versionner. |
| `AGENTS.md` | Consignes de développement et limites de l'étape | À versionner ; ne remplace pas la documentation du produit. |
| `docs/architecture/` | Architecture cible, contrats et frontières | À versionner ; conception distincte de l'implémentation. |
| `docs/Backlog/` | Travail, critères et notes des premiers exemples | À versionner ; casse existante conservée. |
| `docs/verification/` | Conclusions et preuves datées par jalon, Markdown et JSON | À versionner ; exclu de l'inférence car contient des réponses. |
| `scripts/` | Préparation et inspection locales | À versionner ; lit les références pour les vérifier, hors service d'inférence. |
| `tests/` | Tests automatisés ciblés | À versionner ; données temporaires de test ignorées. |
| `evals/cases/` | Questions, cellules attendues, résultats et tolérances | À versionner ; jamais chargé comme corpus d'inférence. |
| `data/raw/` | Téléchargement original avec annotations | Local, ignoré par Git, hors inférence. |
| `data/samples/` | Sources complètes générées, champs autorisés seulement | Local, ignoré par Git ; reproductible depuis le brut et le script. |
| `data/FINQA_PROVENANCE.md`, `data/FINQA_LICENSE.txt` | Attribution, empreinte et notice des données | À versionner. La notice des données ne vaut pas licence du code. |

Pour les prochaines étapes : ajouter `app/` pour le service réel, `prompts/` pour les prompts effectivement utilisés et `evals/results/` pour les résultats mesurés de campagnes IA. Le découpage cible est décrit dans [l'architecture](../architecture/ARCHITECTURE_PROJET_IA.md). Ces répertoires seront créés avec leur contenu utile.

## Contrôles exécutés

- Génération puis contrôle de **10 cas sur une copie sans exports sources préexistants** : réussis sous Python 3.14.5.
- **3 tests négatifs réussis**, sans modification de la logique Python.
- **28 liens Markdown locaux contrôlés**, y compris existence et casse des chemins : aucun lien cassé.
- Règles `.gitignore` vérifiées avec Git sur **13 chemins à exclure** et **10 chemins à conserver**.
- Empreintes du fichier brut, du manifeste et du script conformes à l'instantané B01.
- Aucun ancien chemin de dossier de rapports dans les documents actifs ; les données et références numériques sont préservées.

La copie de reproduction utilise le fichier brut local dont l'empreinte est vérifiée, afin de tester la génération sans retélécharger les données. Le téléchargement réseau lui-même n'est pas retesté. Les tests d'exclusion Git sont exécutés dans un dépôt temporaire ; aucun dépôt n'est initialisé dans FigureTrail pendant cette revue.

Les vérifications B01 restent décrites dans le [rapport de données](B01_VERIFICATION_DONNEES.md), avec leurs [résultats exacts](B01_VERIFICATION_RESULTS.json). Le déplacement ne modifie ni les résultats numériques ni les empreintes du code et du manifeste. Le JSON B01 reste un instantané de cette vérification de données ; cette revue documente l'évolution des chemins.

## Points restant à réaliser

| Étape | Travail nécessaire |
|---|---|
| B02 | Dépôt Git, environnement isolé, configuration des dépendances et versions réellement testées, vérification FTS5 et premier endpoint de santé. |
| B03 | Configuration sans secrets, fournisseur et modèle réels, sortie structurée, première trace avec durée et consommation. |
| B04–B08 | Corpus/index sans annotations, traitement des conflits de tableaux, recherche et évaluations avec cas réservés. |
| B10–B12 | Boucle d'outils bornée, contrôles et tests de sécurité, traces et versions. |
| Préparation de publication | Intégration continue, revue des fichiers suivis, licence du code à choisir et démarrage reproductible complet. |

Le choix d'un dossier ne démontre pas à lui seul ces capacités. Les objectifs P0/P1 et leurs preuves de réalisation restent ceux du [backlog](../Backlog/BACKLOG_PROJET_IA.md). Aucun appel LLM ni achat n'a été effectué pendant cette réorganisation.
