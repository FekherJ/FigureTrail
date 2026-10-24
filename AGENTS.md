# FigureTrail — Consignes de travail

## Contexte et documents de référence

- Nom affiché : **FigureTrail** ; nom technique : `figuretrail` (Windows, PowerShell, VS Code). La racine est le dossier contenant ce fichier et README.md. Utiliser des chemins relatifs à cette racine dans le code pour garder le projet portable.
- Lire [README.md](README.md), [l'architecture](docs/architecture/ARCHITECTURE_PROJET_IA.md) et [le backlog](docs/Backlog/BACKLOG_PROJET_IA.md) avant de modifier le projet.
- Conserver les dossiers réels `docs/architecture/` et `docs/Backlog/`, y compris leur casse. Les preuves sont regroupées dans `docs/verification/`. La documentation est regroupée sous `docs/` ; les autres dossiers restent à la racine.
- Préserver les fichiers et changements existants. Créer uniquement les fichiers utiles à l'étape en cours.
- Consulter le [blueprint technique](docs/architecture/AI_PROJECT_BLUEPRINT.md) comme complément à l'architecture. Appliquer ses recommandations dans l'ordre B02 à B13 décrit au backlog ; conserver ce qui convient déjà et justifier les adaptations par un besoin actuel. L'arborescence cible n'est pas une liste de fichiers à créer. uv et Ruff ont été retenus en B02 : dépendances dans `pyproject.toml`, versions exactes dans `uv.lock`, commandes dans README. Ne pas ajouter d'autres outils sans besoin actuel.

## Objectif pédagogique

- Accompagner en français un développeur de niveau Python intermédiaire, peu pratiqué récemment.
- Priorités : LLM/RAG, APIs/architecture et évaluations ; ensuite agents/tool calling, sécurité et observabilité.
- Temps disponible : environ une heure par jour pendant six semaines. Le backlog propose 36 h de projet et une réserve de temps ; réestimer selon le rythme réellement constaté.
- Budget supplémentaire strictement inférieur à 30 €. La proposition de 20 € d'API + 5 € de marge n'est pas une dépense déjà engagée. L'abonnement ChatGPT ne vaut pas crédit API.
- Expliquer les concepts, les choix et le code utile. Avancer par petits changements vérifiables, adaptés à une séance d'une heure.
- Terminer chaque étape par ce qui est réellement obtenu, les vérifications exécutées, les limites, ce qu'il faut comprendre et la prochaine action du backlog. Ne pas annoncer des fonctionnalités ou scores non démontrés.

## Périmètre et séparation des données

- B01 est terminé pour la faisabilité des données : dix cas vérifiés par l'assistant le 24 octobre 2026. Lire `docs/verification/B01_VERIFICATION_DONNEES.md` pour les preuves, limites et suites ; socle local B02 opérationnel, mise en place distante GitHub encore à effectuer, suite technique B03. Lire aussi `docs/verification/B02_ENVIRONNEMENT.md`. Ne pas transformer ce résultat en score LLM/RAG.
- Aucun appel LLM payant à cette étape. Aucun fournisseur ou modèle choisi par anticipation.
- Pour chaque cas, vérifier question, cellules, unités/échelles, périodes, formule, résultat et preuves. Conserver la provenance et distinguer données réalisées et prévisions.
- Les téléchargements bruts contiennent des annotations : ils restent dans `data/raw/` et ne sont jamais des données d'inférence.
- Les sources seules vont dans `data/samples/` à ce stade ; questions/réponses attendues, programmes, bonnes preuves et notes de relecture restent séparés dans `evals/` et la fiche B01 de `docs/Backlog/`.
- `docs/verification/` contient des réponses et coordonnées attendues : il est exclu de toute ingestion d'inférence, comme `evals/`. Le manifeste `evals/cases/finqa-b01-reviewed.json` contient les questions adaptées et conventions explicites ; conserver les questions FinQA originales.
- Le futur corpus/index/prompt ne doit recevoir ni réponses, ni programmes, ni preuves sélectionnées par les annotations. Utiliser une liste explicite de champs source autorisés.
- La sélection manuelle d'un cas de développement ne constitue pas une évaluation de recherche. Plus tard, rechercher sur plusieurs documents avec distracteurs, sans filtre documentaire déduit des bonnes réponses.
- Calculer par code déterministe avec `Decimal`, jamais par `eval` ou exécution de code généré. Les opérandes viennent des cellules sources.
- Garder les secrets, données brutes et traces locales hors de Git. Conserver les conditions et attributions des sources publiques.

## Manière de développer

- Privilégier la bibliothèque standard et le minimum de code lisible. Étendre l'application uniquement avec la fonctionnalité en cours ; ne pas créer de modules vides ou de dépendances pour des étapes futures.
- Vérifier les outils avant de supposer leur disponibilité. Au 24 octobre 2026 : `python3.14.exe` fonctionne (3.14.5), `python` et `py` ne sont pas dans le PATH du terminal utilisé. uv 0.11.14 et Git 2.47.0 sont détectés par l'assistant ; leur visibilité peut différer dans un ancien terminal VS Code. Git est installé dans `C:/Users/fekhe/AppData/Local/Programs/Git/cmd/git.exe`. Ne pas modifier le PATH global. Utiliser l'environnement `.venv/` du projet pour l'application.
- Faire les contrôles proportionnés au changement ; conserver un contrôle relançable pour la séparation des données et le calcul étudié.
- Pas de multi-agent, framework d'agents, service cloud, OCR ou ingestion libre de PDF à ce stade. Suivre les dépendances B01 à B13, en conservant honnêtement le reste à faire.
