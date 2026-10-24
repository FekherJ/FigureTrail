# B01 — Cas de référence : ratio en pourcentage

**24 octobre 2026 — Cas vérifié contre les textes et tableaux FinQA ; B01 : 10 références vérifiées.**

Références : [backlog](BACKLOG_PROJET_IA.md), [architecture](../architecture/ARCHITECTURE_PROJET_IA.md), [provenance et licence](../../data/FINQA_PROVENANCE.md).

## Question et périmètre

Cas public : `DVN/2007/page_58.pdf-2`, troisième entrée de `dev.json`.

Question originale : **what percentage of the total oil and gas mmboe comes from canada?**

Lecture en français : quelle part du volume total de production exprimé en MMBoe provient du Canada ? Le tableau inclut pétrole, gaz et liquides de gaz naturel (NGLs). La question abrège ce périmètre : on utilise la colonne Total existante, sans reconstruire un total pétrole + gaz différent.

Le premier exemple physique du fichier (`V/2008/page_17.pdf-1`) demandait une moyenne monétaire par transaction, hors des deux familles retenues. Nous avons choisi un ratio en pourcentage à deux cellules, sans prétendre constituer un échantillon représentatif.

## Cellules et contexte

Coordonnées Python **à partir de zéro** : ligne 0 = en-têtes, colonne 0 = libellés.

| Rôle | Cellule | Ligne | Colonne | Valeur | Unité | Période |
|---|---|---|---|---:|---|---|
| Numérateur | `table[3][4]` | Canada | Total (MMBoe) | 60 | MMBoe | Estimation 2008 |
| Dénominateur | `table[5][4]` | Total | Total (MMBoe) | 243 | MMBoe | Estimation 2008 |

MMBoe désigne des millions de barils équivalent pétrole. Les deux opérandes ont la même unité et la même échelle : elles s'annulent dans le ratio. Ne pas additionner directement les colonnes pétrole en MMBbls et gaz en Bcf. La documentation financière de Devon explique la conversion énergétique et l'inclusion des NGLs ([rapport annuel, note 1](https://media.corporate-ir.net/media_files/irol/67/67097/reports/AR2007/08_02_01.htm)). Notre calcul utilise seulement la colonne totale fournie dans FinQA.

Preuves à retrouver dans le fichier source local :

- `table[0][4]` et `table_ori[0][4]` : en-tête et unité.
- `table[3][0]`, `table[3][4]`, `table[5][0]`, `table[5][4]` : libellés et valeurs, opérandes identiques dans `table_ori`.
- `pre_text[16]` : section d'estimations pour 2008.
- `pre_text[27]` : exclusion des opérations d'Afrique de l'Ouest dans les prévisions qui suivent.
- `pre_text[30]` : production estimée pour 2008 ; `[31]` donne une fourchette et `[33]` précise que le tableau se situe au milieu de celle-ci. On utilise le total tabulé 243, sans lui substituer un milieu recalculé.

L'année 2007 dans l'identifiant du rapport n'est donc pas la période des opérandes. Ce sont des prévisions, pas une production réalisée. Le PDF original n'a pas été vérifié ; le contrôle porte sur les textes et tableaux distribués par FinQA.

## Calcul et référence

```text
part = 100 × volume Canada / volume total
     = 100 × 60 / 243
     = 24,691358024691358… %
affichage à deux décimales : 24,69 %
```

Le dénominateur est positif. Sans multiplication par 100, le ratio vaut environ 0,2469 ; la sortie est un pourcentage, pas un volume ni une variation entre deux années.

Les [annotations séparées](../../evals/cases/finqa-b01-reference.json) donnent `answer = 24.69%`, `exe_ans = 24.69136` et `program = divide(60, 243), multiply(#0, const_100)`. Ce programme est une donnée, jamais du code exécuté. La tolérance pour cet `exe_ans` arrondi est **0,000005 point de pourcentage** ; l'affichage à deux décimales doit également correspondre.

Les bonnes preuves annotées désignent `table_3`, `table_5` et `text_34` (unités). Notre relecture ajoute les passages établissant la période et le caractère prévisionnel : les annotations seules n'expliquent pas tout le contexte.

## Anomalie et limites

`table[4][3]` contient `2014`, tandis que `table_ori[4][3]` contient un tiret. Cette cellule International/NGLs n'est pas utilisée ici. Le script la signale sans correction automatique. Avant B04, il faudra traiter cette anomalie : une normalisation peut transformer un symbole en nombre trompeur.

Un cas de développement examiné, aucun score global. Aucun corpus de recherche, distracteur, appel LLM, test d'abstention ou partition finale par groupe documentaire n'existe encore. Les références de ce vérificateur ne doivent jamais alimenter le futur service d'analyse.

## Contrôles et reproduction

Depuis la racine : `python3.14.exe -X utf8 scripts/inspect_finqa.py`.

- Résolution des chemins depuis le script et vérification des libellés, coordonnées et en-têtes des cellules.
- `SOURCE_FIELDS` autorise seulement les champs sources. Exclure uniquement `answer` laisserait fuir les programmes, bonnes preuves ou résultats de recherche préparés.
- `Decimal` lit les nombres depuis les chaînes des cellules ; l'arrondi d'affichage reste distinct du calcul.
- Les `assert` contrôlent ce cas et l'export écrit sur disque. Ils sont réservés au contrôle hors ligne ; les validations de l'API nécessitent des exceptions explicites. Ne pas utiliser l'option `-O`, qui les désactive.

Exécution observée : contrôles passés, deux fichiers séparés créés, résultat conforme. Dépense LLM/API : **0 €**.

## Couverture et suivi

Le [cas de variation relative](B01_DEUXIEME_CAS.md) complète la couverture des deux opérations. La méthode combine revue assistée des sources et recalcul déterministe ; elle ne constitue pas une revue humaine indépendante.

Les dix références, doublons et candidats distracteurs sont consignés dans le [rapport B01](../verification/B01_VERIFICATION_DONNEES.md). B01 est validé pour la faisabilité des données ; le socle local B02 est vérifié et la prochaine étape technique est B03. Les références restent séparées du futur corpus d'inférence.
