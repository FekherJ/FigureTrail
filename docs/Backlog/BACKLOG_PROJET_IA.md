# Backlog — FigureTrail

**Version 1.1 — roadmap de réalisation — 24 octobre 2026 — Fekher Jarrar**

Ce backlog met en œuvre l'architecture décrite dans [docs/architecture/ARCHITECTURE_PROJET_IA.md](../architecture/ARCHITECTURE_PROJET_IA.md), chemin depuis la racine du projet. Les sections B01–B13 définissent les issues, dépendances et preuves de validation. Le dépôt distant [FigureTrail](https://github.com/FekherJ/FigureTrail) est configuré ; l'état du tableau et des issues reste à confirmer. Les identifiants B01 à B13 sont des repères stables ; ils ne présument pas les futurs numéros d'issues GitHub.

**Résultat visé :** une application locale qui retrouve des cellules dans des rapports publics, calcule une variation ou un ratio, puis montre résultat, formule et preuves. Elle utilise un LLM hébergé, un RAG mesuré et une API. Une variante agentique limitée, des garde-fous et des traces complètent le parcours fixe.

## 1. Organisation dans GitHub

Créer un tableau avec trois colonnes : **À faire / En cours / Terminé**. Une seule issue en cours. Chaque bloc Bxx ci-dessous correspond à une issue ; les cases deviennent sa checklist. Conserver les dépendances dans le corps de l'issue.

Champs utiles : priorité `P0` ou `P1`, jalon, estimation en heures. Étiquettes facultatives : `data`, `llm`, `rag`, `api`, `evals`, `agents`, `security`, `observability`, `docs`. Ne pas ajouter de cérémonies ou de sous-tickets si une checklist suffit.

Une issue est terminée lorsque ses critères sont vérifiés et que sa preuve est enregistrée dans le dépôt ou reliée à un commit. Les résultats doivent distinguer appels simulés et appels réels. Une fonctionnalité seulement décrite dans le README n'est pas une fonctionnalité démontrée.

## 2. Plan de livraison et enveloppe de validation

Les estimations initiales représentent **31 heures de réalisation et vérification**, complétées par cinq heures de réserve pour intégration, diagnostic et corrections. L'enveloppe de 36 heures inclut documentation et suivi des issues. Les estimations sont à réviser à partir des résultats des jalons.

Ce chiffrage est ambitieux et provisoire, pas un engagement de livraison. Réestimer après B01 et B03. Si le rythme réel ne tient pas, réduire le corpus, les types de questions ou la finition d'interface ; préserver les P0 et une démonstration limitée de chaque P1. Si cela ne suffit pas, consigner le reste à faire : ne pas déclarer terminé un objectif non réalisé.

| ID | Priorité | Livrable | Dépendances de clôture | Estimation | Jalon |
|---|---|---|---|---:|---|
| B01 | P0 | Dix cas et périmètre vérifiés | Aucune | 2 h | J1 |
| B02 | P0 | Environnement et squelette minimal | B01 | 2 h | J1 |
| B03 | P0 | Premier appel hébergé, schéma et traces | B02 | 2 h | J1 |
| B04 | P0 | Corpus/index préparés sans annotations | B01, B02, B03 | 2 h | J2 |
| B05 | P0 | Recherche lexicale et sémantique mesurée | B04 | 3 h | J2 |
| B06 | P0 | Parcours fixe et calcul avec preuves | B03, B05 | 3 h | J2 |
| B07 | P0 | API documentée et erreurs cohérentes | B06 | 2 h | J2 |
| B08 | P0 | Évaluateur et amélioration comparée | B01, B05, B06 | 3 h | J3 |
| B09 | P0 | Interface de démonstration | B07 | 2 h | J3 |
| B10 | P1 | Agent avec appels d'outils structurés | B07, B08 | 3 h | J4 |
| B11 | P1 | Garde-fous et campagne négative | B09, B10 | 2 h | J4 |
| B12 | P1 | Traces complètes et versions | B07, B10 | 2 h | J4 |
| B13 | P0 | Validation finale et livraison reproductible | B08, B09, B10, B11, B12 | 3 h | J5 |
| Réserve | — | Intégration, diagnostic et corrections | Selon les difficultés | 5 h | Tous |
| **Total projet** | | | | **36 h** | |

Les dépendances indiquent ce qui est nécessaire pour terminer, pas pour commencer à réfléchir ou écrire quelques lignes. Évaluations et traces commencent immédiatement : B08 formalise les premiers contrôles, B12 complète les traces commencées dans B03. API et UI minimales peuvent être amorcées avant leur clôture.

Les jalons correspondent à des résultats, pas à cinq semaines fixes :

- **J1 — Faisabilité :** données vérifiables et accès LLM compatible avec les contraintes.
- **J2 — Chaîne P0 :** recherche → LLM → calcul → API, avec premiers résultats évalués.
- **J3 — Qualité visible :** comparaison mesurée et interface de preuve.
- **J4 — P1 démontrés :** agent limité, garde-fous et observabilité.
- **J5 — Démonstration :** versions figées, essais finaux, limites et reproduction.

Ordre conseillé : B01 → B02 → B03 → B04 → B05 → B06 → B07 → B08 → B09 → B10 → B11 → B12 → B13. Valider J1 avant la chaîne P0 ; réestimer les tâches après l'essai fournisseur B03.

**Enveloppe de validation :** 20 € d'usage API et 5 € de réserve, sous un plafond cumulé strictement inférieur à 30 €. Choix du fournisseur et dépenses non engagés. Les essais, embeddings, évaluations et erreurs comptent tous. Avant une campagne, estimer sa consommation et réduire le nombre de répétitions si nécessaire. Vérifier séparément l'accès API, les tarifs et la facturation fournisseur.

### Adoption progressive du blueprint

Le [blueprint technique](../architecture/AI_PROJECT_BLUEPRINT.md) complète l'architecture sans ajouter de tickets, d'heures ou de technologies obligatoires. Commencer par constater l'état réel ; conserver ce qui convient et corriger uniquement les écarts utiles au jalon. L'arborescence cible ne doit pas être créée à l'avance.

| Étape existante | Recommandations à vérifier au moment utile |
|---|---|
| B02 | Structure actuelle, exclusions Git, environnement reproductible et `/health`. uv/Ruff retenus ; ne pas imposer une migration vers `src/`. |
| B03 | Contrat LLM, validation, appels bornés, erreurs, coût et premières traces. |
| B04 à B08 | Provenance, corpus sans annotations, cohérence des index, récupération, calcul déterministe et évaluations communes au service. |
| B09 à B12 | Affichage sûr des preuves, outils bornés, cas négatifs et traces complètes. |
| B13 | Contrôles automatisés sans secrets, reproduction de la démo et résultats/limites mesurés. |

Le blueprint ne prouve pas à lui seul une fonctionnalité. B01 est vérifié ; le socle technique local B02 est validé, avec un remote GitHub configuré et un tableau d'issues restant à confirmer. Les autres étapes restent à réaliser.

## 3. Issues prêtes à reprendre

### B01 — Valider dix questions, leurs preuves et le périmètre

**Priorité : P0 · Étiquettes : data, evals · Jalon : J1 · Estimation : 2 h · Dépendances : aucune**

Objectif : valider des références numériques à deux cellules avec contexte explicite, sans dépendance à l'OCR ou à une reconstruction financière implicite.

- [x] Lire un petit échantillon FinQA et sélectionner dix questions compréhensibles : variation relative et ratio en pourcentage sur deux cellules, avec dénominateur positif.
- [x] Pour chacune, relever question, contexte, cellules, unités, périodes, formule, résultat attendu et provenance ; recalculer et vérifier les preuves sources.
- [x] Examiner les doublons de contexte et prévoir des documents distracteurs pour la recherche.
- [x] Lire les conditions d'utilisation/attribution à conserver avec les données ; noter le périmètre retenu et les exclusions.

**Critères d'acceptation :** dix cas relus, calculables sans convention implicite, avec preuves identifiables. Aucun exemple ou chiffre inventé. Sources et annotations ont des destinations distinctes. Si le sous-ensemble ne convient pas, consigner ce qui bloque et réduire les types de calcul avant B04.

**Preuve à conserver :** fiche de faisabilité et premiers cas de développement annotés côté évaluation. Le rapport doit compter uniquement les cas effectivement vérifiés.

**Point de conception :** L'évaluation sépare pertinence des preuves, sélection de cellules et exactitude numérique.

**État local au 24 octobre 2026 : terminé pour la faisabilité des données, revue assistée des sources et recalcul déterministe.** Dix cas relus/recalculés, dix contextes et groupes de rapport distincts, conventions de référence explicites, doublons audités, trois distracteurs identifiés et notice conservée. [Rapport et limites](../verification/B01_VERIFICATION_DONNEES.md). Contrôles exécutés : dix cas et trois tests négatifs réussis, sans appel LLM. Aucun ticket GitHub distant n'a été créé ou clôturé. Le jalon J1 complet attend B03.

### B02 — Établir l'environnement et le socle HTTP

**Priorité : P0 · Étiquettes : api, data · Jalon : J1 · Estimation : 2 h · Dépendances : B01**

Objectif : établir un environnement reproductible et un socle HTTP vérifiable.

- [x] Relire architecture et backlog, vérifier la structure actuelle et initialiser le dépôt Git local.
- [x] Configurer le dépôt distant GitHub et le suivi de la branche `main`.
- [ ] Configurer le tableau GitHub et les issues de réalisation ; statut à confirmer.
- [x] Créer un environnement Python, installer FastAPI/Pydantic/Uvicorn et NumPy ; vérifier SQLite FTS5 sur le runtime Windows choisi.
- [x] Ajouter les fichiers de configuration sans secrets, exclusions Git et instructions de démarrage ; fixer les versions effectivement testées.
- [x] Charger un cas, afficher ses données sources séparément de ses références et démarrer un `/health` sans appel IA.

**Critères d'acceptation :** environnement et démarrage documentés, exemple lu correctement, clé absente du suivi Git. FTS5 fonctionne ou une décision de remplacement minimale est consignée ; pas de développement d'un moteur SQL/recherche maison.

**Preuve à conserver :** premier commit, instructions Windows et exemple de sortie. Ce ticket ne demande pas de créer tous les modules de l'architecture vides.

**Point de conception :** Configuration, sources d'inférence et références d'évaluation ont des responsabilités distinctes.

**État au 24 octobre 2026 : socle local B02 validé ; remote GitHub configuré, tableau d'issues à confirmer.** Voir le [rapport B02](../verification/B02_ENVIRONNEMENT.md) pour les versions, commandes, vérifications et limites. Aucune fonctionnalité LLM/RAG n'est annoncée comme réalisée ; B03 reste à commencer.

### B03 — Valider un LLM hébergé, son contrat et son coût

**Priorité : P0 · Étiquettes : llm, observability, security · Jalon : J1 · Estimation : 2 h · Dépendances : B02**

Objectif : écarter tôt un modèle trop lent ou inaccessible et obtenir un vrai appel contrôlé.

- [ ] Vérifier accès, tarifs, sorties structurées, embeddings et tool calling d'un fournisseur ; choisir un modèle génératif et un modèle d'embedding compatibles avec le budget.
- [ ] Faire un appel réel sur un cas source : opération et références de cellules, ou abstention ; valider le schéma côté Python.
- [ ] Centraliser les appels dans un module, sans multi-fournisseur. Désactiver les retries cachés ; appliquer sortie bornée, timeout et suivi de consommation.
- [ ] Créer un `run_id` et enregistrer modèle, version de prompt, durée, tokens, coût estimé et erreur éventuelle. Vérifier aussi un échec simulé sans frais.

**Critères d'acceptation :** résultat réel inspecté ; aucun opérande pris directement d'un nombre généré. Latence/coût mesurés et jugés acceptables selon une limite écrite avant de poursuivre. Les erreurs et consommations inconnues restent explicites. La clé n'apparaît ni dans le navigateur ni dans les traces.

**Preuve à conserver :** trace expurgée de secrets, configuration du modèle et décision datée coût/latence. Aucun objectif chiffré de performance n'est annoncé comme atteint avant mesure.

**Point de conception :** Un schéma valide ne garantit pas la pertinence des cellules ni l'exactitude de la réponse.

### B04 — Préparer un corpus versionné, sans fuite de réponses

**Priorité : P0 · Étiquettes : data, rag, security · Jalon : J2 · Estimation : 2 h · Dépendances : B01, B02, B03**

Objectif : transformer des textes/tableaux publics en preuves récupérables.

- [ ] Préparer un petit corpus avec distracteurs ; dédupliquer, attribuer `report_id`, `source_id` et `cell_id`, conserver les nombres d'origine.
- [ ] Construire les segments de texte/lignes de tableau en préservant libellés, en-têtes, périodes, unités et contexte. Ne pas inventer une entreprise ou une unité manquante.
- [ ] Créer SQLite/FTS5 et les embeddings du corpus ; enregistrer vecteurs, correspondance des segments et manifeste de versions/hashes.
- [ ] Séparer physiquement les références ; ajouter un contrôle de fuite et un contrôle d'alignement index/vecteurs/corpus.

**Critères d'acceptation :** préparation relançable ; aucun champ de réponse, programme ou bonne preuve dans le corpus d'inférence. Tous les identifiants résolvent une source réelle. Index incohérent refusé au chargement ; traces préservées lors d'une reconstruction.

**Preuve à conserver :** commande de préparation, exemple anonymisé seulement si nécessaire, manifeste et résultats des contrôles. Conserver uniquement les sources publiques autorisées dans ce dépôt.

**Point de conception :** La segmentation préserve ensemble nombres, libellés, périodes et unités.

### B05 — Construire et mesurer la recherche de preuves

**Priorité : P0 · Étiquettes : rag, evals · Jalon : J2 · Estimation : 3 h · Dépendances : B04**

Objectif : un RAG qui retrouve réellement des preuves parmi plusieurs contextes.

- [ ] Implémenter la recherche FTS5/BM25 et l'affichage des meilleurs segments avec leurs scores et cellules.
- [ ] Ajouter la recherche sémantique : embeddings de question, vecteurs normalisés, cosinus NumPy et filtrage de périmètre avant sélection finale.
- [ ] Mesurer rappel des preuves et récupération de toutes les preuves nécessaires sur les dix cas de travail ; inspecter au moins deux échecs ou cas difficiles.
- [ ] Garder le même corpus et les mêmes questions pour comparer lexical/sémantique ; consigner le choix provisoire.

**Critères d'acceptation :** recherche sur un corpus avec distracteurs ; aucun identifiant du document correct injecté depuis les annotations. Toute restriction vient du périmètre utilisateur déclaré. Les références de test ne servent qu'au calcul des métriques. Scores et sources restent inspectables.

**Preuve à conserver :** tableau de comparaison et exemples de preuves retrouvées/manquées, avec version du corpus et paramètre `k`.

**Point de conception :** La similarité est un signal de classement ; sa pertinence se mesure contre les références.

### B06 — Assembler le parcours fixe et le calcul vérifiable

**Priorité : P0 · Étiquettes : llm, rag, security · Jalon : J2 · Estimation : 3 h · Dépendances : B03, B05**

Objectif : question → recherche → sélection structurée par le LLM → calcul par le code → preuves.

- [ ] Écrire le service d'analyse fixe : une recherche puis au maximum un appel génératif ; utiliser les seuls segments retrouvés.
- [ ] Valider opération et références de cellules accessibles ; relire les nombres depuis le corpus et calculer avec `Decimal`.
- [ ] Appliquer les formules variation/ratio, contrôles d'unités, périodes, échelles et dénominateur. Construire les preuves affichées depuis ces données.
- [ ] Gérer les états succès, information insuffisante, demande non supportée, blocage et erreur ; enregistrer les premiers résultats évalués.

**Critères d'acceptation :** calcul correct sur les cas contrôlés, absence d'`eval` ou de code/SQL généré exécuté. Référence inconnue, unité ambiguë, division par zéro et sortie invalide ne deviennent pas des succès. Les vérifications ciblées couvrent formules, mauvaise référence et cas incomplet. Aucun score global n'est déduit de ces seuls contrôles.

**Preuve à conserver :** exécution réelle complète et vérifications relançables ; au moins un résultat avec formule et deux sources de cellules, et un état sans réponse chiffrée.

**Point de conception :** Le modèle sélectionne l'opération et les cellules ; le code valide les données et calcule.

### B07 — Exposer une API documentée, avec contrats et erreurs

**Priorité : P0 · Étiquettes : api, security · Jalon : J2 · Estimation : 2 h · Dépendances : B06**

Objectif : rendre le service utilisable et testable indépendamment de l'interface.

- [ ] Exposer `/reports`, `POST /analyses` et la relecture `GET /analyses/{run_id}` ; conserver `/health` et la documentation OpenAPI.
- [ ] Définir les schémas de requête/résultat et codes d'erreur ; préserver le `run_id` lors d'une erreur après création d'exécution.
- [ ] Valider taille de question, périmètre et mode ; limiter à une analyse active et appliquer une durée maximale.
- [ ] Contrôler liaison locale, origine et JSON ; vérifier un succès, une entrée invalide, une exécution inconnue et une panne fournisseur simulée.

**Critères d'acceptation :** contrat cohérent dans `/docs`, résultat consultable sans nouvel appel IA, erreurs techniques distinctes des états métier. Pas de clé exposée, CORS permissif ou accès à des chemins libres. Une entrée invalide ne déclenche pas d'appel payant.

**Preuve à conserver :** exemples de requêtes/réponses et contrôle ciblé du contrat HTTP.

**Point de conception :** L'information insuffisante est un état métier distinct d'une panne technique.

### B08 — Formaliser les évaluations et démontrer une amélioration

**Priorité : P0 · Étiquettes : evals, rag · Jalon : J3 · Estimation : 3 h · Dépendances : B01, B05, B06**

Objectif : mesurer les forces/faiblesses et empêcher une démonstration fondée sur quelques exemples choisis.

- [ ] Formaliser l'évaluateur autour du même service que l'API ; lui seul charge résultats et preuves attendus, après réception de la sortie d'analyse.
- [ ] Étendre si possible vers 20 cas de développement et réserver 10 cas finaux par groupe documentaire ; garder le nombre réel si la préparation prend plus de temps.
- [ ] Définir tolérances, conventions de pourcentage, métriques de recherche/exactitude/unités/abstention, revue de preuves, latence/coût et catégories d'erreur.
- [ ] Comparer les deux recherches dans le parcours fixe ; corriger une faiblesse observée, puis mesurer à nouveau sur les cas de développement.

**Critères d'acceptation :** commande reproductible, versions et effectifs publiés, erreurs conservées dans les résultats. Cas finaux non utilisés pour régler les variantes. Pas de filtre documentaire déduit des bonnes réponses. Une amélioration est mesurée, ou l'absence de gain est expliquée. Le système n'est pas évalué seulement sur sa validité JSON.

**Preuve à conserver :** rapports avant/après, règles de notation et au moins une analyse détaillée d'erreur. Consigner avant les essais finaux les seuils chiffrés retenus et les raisons de leur choix.

**Point de conception :** Les contrôles de calcul, de retrieval et de bout en bout utilisent des mesures distinctes.

### B09 — Créer une interface qui montre les preuves

**Priorité : P0 · Étiquettes : api, docs · Jalon : J3 · Estimation : 2 h · Dépendances : B07**

Objectif : une démonstration compréhensible rapidement, sous forme de fiche d'analyse.

- [ ] Servir une page depuis FastAPI : question, périmètre, lancement, état d'attente et résultat.
- [ ] Afficher valeurs d'origine, unités/périodes, formule, résultat et preuves lisibles avec leurs en-têtes de tableau.
- [ ] Afficher clairement les cas non résolus et erreurs ; proposer la relecture d'une exécution et une section de détails techniques.
- [ ] Échapper le contenu des sources et vérifier le parcours dans le navigateur, y compris un texte contenant des balises.

**Critères d'acceptation :** une personne comprend le besoin et peut suivre le calcul jusqu'aux sources. Le navigateur appelle l'API applicative, sans clé fournisseur. Pas de conversation à maintenir ni de refonte graphique ; une page suffit.

**Preuve à conserver :** captures ou courte séquence montrant un succès sourcé et une information insuffisante.

**Point de conception :** Le résultat reste vérifiable jusqu'aux valeurs sources et à la formule.

### B10 — Ajouter un agent limité avec de appels d'outils structurés

**Priorité : P1 · Étiquettes : agents, llm, evals · Jalon : J4 · Estimation : 3 h · Dépendances : B07, B08**

Objectif : implémenter une sélection d'outils bornée et mesurer son apport par rapport au parcours fixe.

- [ ] Déclarer les outils `search_evidence`, `read_evidence` et `calculate` avec des paramètres structurés, reliés aux fonctions existantes.
- [ ] Laisser le modèle choisir les outils et la prochaine action ; appliquer un périmètre immuable, quatre appels génératifs, six appels d'outils dont deux recherches au maximum.
- [ ] Arrêter sur calcul valide, abstention ou limite ; refuser outil inconnu, cellule non accessible ou texte final chiffré sans calcul validé.
- [ ] Comparer avec le parcours fixe sur les mêmes cas de développement et le même retriever : qualité, erreurs, outils, latence et coût.

**Critères d'acceptation :** au moins une trace réelle montre plusieurs décisions d'outils du modèle. Les outils utilisent les mêmes validations que le fixe. Les limites sont vérifiées en code, y compris avec une réponse modèle simulée qui tente de les dépasser. Aucun framework d'agents ou système multi-agent requis.

**Preuve à conserver :** trace expurgée, tableau comparatif et décision motivée sur le mode par défaut. Ne pas inventer de gain : conserver le fixe si les mesures le justifient.

**Point de conception :** L'agent choisit les prochaines actions ; le programme applique les permissions et plafonds.

### B11 — Tester injections, permissions et cas impossibles

**Priorité : P1 · Étiquettes : security, evals · Jalon : J4 · Estimation : 2 h · Dépendances : B09, B10**

Objectif : éprouver les garde-fous déjà présents, pas les ajouter seulement en fin de projet.

- [ ] Préparer environ dix cas de robustesse : instruction hostile dans une source, accès hors périmètre, outil inconnu, cellule inventée, mauvais format, limites d'appels et HTML hostile.
- [ ] Ajouter/relire les cas de preuve réellement manquante avec variantes identifiées du corpus, en vérifiant les doublons.
- [ ] Vérifier sans frais les branches de permission et d'erreur avec des réponses simulées ; exécuter quelques cas d'injection avec le vrai modèle dans l'enveloppe prévue.
- [ ] Corriger tout contournement de permission observé et conserver les limites du dispositif.

**Critères d'acceptation :** aucune action interdite observée n'est acceptée comme réussite ; résultat sans preuve refusé, boucle arrêtée au plafond, source HTML inactive. Distinguer test applicatif déterministe, comportement du modèle et cas non testés. Zéro violation observée n'est pas présenté comme une garantie générale de sécurité.

**Preuve à conserver :** liste des attaques/cas, résultat attendu/observé, défauts corrigés et reste à faire.

**Point de conception :** Les instructions au modèle ne remplacent pas les autorisations exécutées en code.

### B12 — Rendre chaque exécution explicable et versionnée

**Priorité : P1 · Étiquettes : observability, data · Jalon : J4 · Estimation : 2 h · Dépendances : B07, B10**

Objectif : compléter les traces de B03 pour diagnostiquer qualité, coût et échecs.

- [ ] Relier événements, recherches, outils et appels IA au `run_id` ; enregistrer versions code/prompts/corpus/index/configuration et modèle demandé/retourné si disponible.
- [ ] Consolider durées, tokens et coûts estimés avec tarif daté, y compris erreurs ; conserver `null` quand la consommation est inconnue.
- [ ] Exporter une synthèse JSON/CSV ou une requête SQL et afficher les détails utiles dans l'interface.
- [ ] Modifier la version d'un corpus de test et vérifier qu'un ancien résultat reste consultable, identifié comme ancien et recalculable explicitement.

**Critères d'acceptation :** depuis un identifiant, retrouver sources, paramètres, outils, résultat et erreurs sans secret ni chaîne de pensée privée. Reconstruire le corpus ne supprime pas les traces. Une panne d'enregistrement critique bloque la poursuite d'appels payants non suivis.

**Preuve à conserver :** exemple de diagnostic d'échec, export et démonstration du changement de version. Cette observabilité locale n'exige pas d'abonnement.

**Point de conception :** Les traces distinguent recherche, sélection de cellule, calcul et erreur fournisseur.

### B13 — Exécuter les essais finaux et livrer une version reproductible

**Priorité : P0 · Étiquettes : evals, docs · Jalon : J5 · Estimation : 3 h · Dépendances : B08, B09, B10, B11, B12**

Objectif : livrer une version reproductible, accompagnée de résultats mesurés et de décisions techniques documentées.

- [ ] Figer code, prompts, corpus, modèles/configurations et règles de mesure ; estimer la campagne finale avant lancement.
- [ ] Exécuter les variantes fixes et l'agent sur les cas finaux réservés ; publier effectifs, scores, échecs, latences et coûts réellement observés.
- [ ] Vérifier le démarrage dans un environnement Python neuf ; documenter récupération des données, configuration et commandes sans secret. La vérification hors réseau peut utiliser des réponses simulées, clairement identifiées.
- [ ] Finaliser README et schémas correspondant au code ; enregistrer une démonstration courte : réussite sourcée, cas difficile/amélioration et absence de preuve. Ajouter limites, arbitrages et prochaines améliorations fondées sur les erreurs.

**Critères d'acceptation :** une autre personne peut suivre l'installation et comprendre les mesures ; code réel du RAG, API, évaluations et outils présent. Les résultats publiés doivent correspondre aux exécutions enregistrées et au périmètre de déploiement vérifié. Si une comparaison ne peut être exécutée faute de budget/temps, l'indiquer explicitement et publier les seuls résultats obtenus.

**Preuve à conserver :** version de livraison, README, rapport de mesures, exemple requête/réponse, traces expurgées et vidéo ou scénario de démonstration. Indiquer la dépense incrémentale suivie et ses limites de rapprochement avec la facture fournisseur.

**Point de conception :** La livraison documente frontières de confiance, erreurs, comparaisons et arbitrages qualité/coût/latence.

## 4. Vérification de couverture

| Priorité | Capacité | Issues de réalisation | Preuve finale |
|---|---|---|---|
| P0 | LLM et sorties structurées | B03, B06 | Appel réel, sélection de cellules validée, erreurs explicites. |
| P0 | RAG | B04, B05, B06, B08 | Recherche multi-source, preuves et comparaison de retrievers. |
| P0 | APIs et architecture | B02, B07, B09 | OpenAPI, service réutilisé par l'évaluateur, démonstration via API. |
| P0 | AI evals | B01, B08, B13 | Références séparées, cas finaux, mesures et analyse d'erreur. |
| P1 | Agents et tool calling | B10 | Outils réellement choisis par le modèle et comparaison au fixe. |
| P1 | Sécurité et garde-fous | B03, B06, B07, B11 | Contrôles de code, tests négatifs et limites explicites. |
| P1 | LLMOps et observabilité | B03, B12, B13 | Versions, traces, coût/latence, diagnostic et reproduction. |
| Bonus | Pipeline de données et SQL | B01, B04, B12 | Préparation reproductible, SQLite, manifeste et exports. |

## 5. Règles de périmètre

Ne pas ajouter pendant ce cycle : OCR/PDF arbitraires, téléchargement d'URL fourni par l'utilisateur, modèle local lent, fine-tuning, multi-agent, plusieurs fournisseurs, SSO, cloud distribué, tableau de bord complet ou juge LLM systématique.

Ces extensions ne répondent pas aux exigences de la version courante. Tout ajout doit résoudre une faiblesse observée et remplacer une autre tâche dans l'enveloppe disponible.

**Prochaine étape technique : B03.** Le socle de données B01 et l'environnement local B02 sont vérifiés. Valider l'accès fournisseur et le contrat LLM avant la construction du corpus indexé et du parcours d'analyse.
