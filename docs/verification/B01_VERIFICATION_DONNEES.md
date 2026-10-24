# FigureTrail — Rapport de vérification des dix exemples B01

**24 octobre 2026 — Faisabilité des données vérifiée : 10 exemples sur 10.**

Vérification réalisée par l'assistant, à la demande de l'apprenant. Ce rapport documente les sources effectivement lues, les calculs refaits et les limites constatées. La relecture des documents n'est pas présentée comme un travail manuel réalisé par l'apprenant.

## 1. Conclusion et objectif de cette étape

Les dix exemples sont calculables depuis deux cellules, avec une base strictement positive et des preuves d'unité, d'échelle et de période. Les deux tableaux fournis par FinQA concordent sur les vingt cellules utilisées. Cinq exemples sont des ratios en pourcentage et cinq des variations relatives, dont une baisse. Les dix contextes appartiennent à dix rapports distincts.

**B01 peut être clôturé pour son périmètre de faisabilité des données.** Le projet reste une application à construire : aucun LLM, RAG, API ou agent n'a été évalué ici. Le jalon J1 complet attend notamment l'essai hébergé de B03. Les défauts de normalisation identifiés devront être traités en B04 avant toute indexation.

Ces exemples servent de références : nous connaissons les preuves et le résultat avant de demander au futur système de les retrouver. Les utiliser pour préparer des essais de développement ne constitue ni un entraînement de modèle ni une mesure de performance sur des cas réservés.

## 2. Méthode et provenance

- Fichier local vérifié : `data/raw/finqa-dev.json`, 883 entrées.
- SHA-256 : `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51`.
- Source : [FinQA, dataset/dev.json](https://github.com/czyssrs/FinQA/blob/main/dataset/dev.json), Chen et al., FinQA, EMNLP 2021.
- Corpus de cette revue : uniquement les textes et tableaux distribués dans FinQA ; aucun PDF original inspecté, aucune ingestion OCR.
- Sélection raisonnée de cas simples, non aléatoire et non représentative de tout FinQA ; annotations consultées pour la curation, jamais pour une recherche d'inférence.
- Relecture du contexte pour identifier le bon indicateur, le segment, les années et le caractère réalisé, prévisionnel ou pro forma.
- Lecture des valeurs dans `table`, contrôle numérique contre `table_ori`, calcul indépendant avec `Decimal`, comparaison aux annotations originales et à leur précision d'affichage.
- Champs sources autorisés exclusivement : `filename`, `pre_text`, `post_text`, `table`, `table_ori`. Toutes les lignes du contexte sont conservées, sans sélection fondée sur les bonnes preuves.
- Aucune exécution des programmes FinQA ni de code généré ; aucun appel LLM ou API : **0 €** pour cette étape.
- Vérification exécutée sous Python **3.14.5** ; bibliothèque standard uniquement.

La notice MIT du dépôt FinQA, copyright 2021 Zhiyu Chen, a été lue dans `data/FINQA_LICENSE.txt`. Conserver cette notice et l'attribution avec les extraits ; `data/FINQA_PROVENANCE.md` conserve l'origine et l'empreinte. Cette lecture de la notice du dépôt n'est pas une vérification indépendante des droits de chaque document financier sous-jacent. Aucun PDF complet n'est redistribué.

## 3. Résultats des dix exemples

Les résultats affichés suivent la précision de l'annotation d'origine. La référence numérique canonique conserve le résultat calculé, sans l'arrondir prématurément.

| Cas | Identifiant FinQA | Famille | Résultat affiché | Vérification |
|---|---|---|---:|---|
| C01 | `DVN/2007/page_58.pdf-2` | Ratio % | 24.69% | Conforme |
| C02 | `FBHS/2017/page_23.pdf-2` | Variation % | 2.9% | Conforme |
| C03 | `PKG/2009/page_65.pdf-4` | Ratio % | 56% | Conforme |
| C04 | `UNP/2008/page_77.pdf-1` | Ratio % | 14.3% | Conforme |
| C05 | `INTC/2013/page_29.pdf-3` | Ratio % | 35.8% | Conforme |
| C06 | `ZBH/2017/page_53.pdf-1` | Ratio % | 4.392% | Conforme |
| C07 | `LMT/2012/page_47.pdf-3` | Variation % | 3.2% | Conforme |
| C08 | `MAS/2018/page_35.pdf-3` | Variation % | 1.4% | Conforme |
| C09 | `ETR/2004/page_213.pdf-4` | Variation % | 5.5% | Conforme |
| C10 | `ETR/2017/page_26.pdf-4` | Variation % | -7.4% | Conforme |

## 4. Preuves et calcul détaillés par cas

Les coordonnées commencent à zéro. Les extraits indiqués ci-dessous sont présents dans les champs sources cités. Les questions d'application sont des reformulations explicites en anglais ; les questions FinQA d'origine restent conservées séparément, sans modification.

### C01 — Part du Canada dans la production totale estimée

- **Question d'origine :** what percentage of the total oil and gas mmboe comes from canada?
- **Question explicite pour l'application :** In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?
- **Contexte :** `DVN/2007/page_58.pdf` ; Prévision de production pour 2008.
- **Unité commune :** MMBoe ; échelle : million de barils équivalent pétrole.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| numerator | `table[3][4]` | 60 | Estimation 2008 |
| denominator | `table[5][4]` | 243 | Estimation 2008 |

**Calcul :** `100 * 60 / 243` = **24.69135802469135802469135802 %**, affichage **24.69%**.

**Preuves de contexte contrôlées :**

- `table[0][4]` contient : « total ( mmboe ) ».
- `table[3][0]` contient : « canada ».
- `table[5][0]` contient : « total ».
- `pre_text[30]` contient : « estimates of oil , gas and ngl production for 2008 ».
- `pre_text[33]` contient : « midpoint ».

**Référence FinQA :** `answer = 24.69%` ; `exe_ans = 24.69136` exprimé en **percent**. L'écart dans cette unité est `0.00000197530864197530864198`, dans la tolérance `0.000005`.

- 2007 est l'année du rapport, pas celle des valeurs : prévisions 2008.
- La colonne Total inclut les NGLs ; conserver ce périmètre tabulé.
- Anomalie hors opérandes : table[4][3] = 2014, table_ori[4][3] = tiret. La bloquer/normaliser explicitement en B04.
- Source complète : `data/samples/finqa-b01-source.json` ; annotations originales : `evals/cases/finqa-b01-reference.json`.

### C02 — Croissance des ventes de Cabinets

- **Question d'origine :** what was the percentage growth in sales of cabinets from 2016 to 2017
- **Question explicite pour l'application :** For FBHS, what was the percentage growth in annual Cabinets segment net sales from 2016 to 2017?
- **Contexte :** `FBHS/2017/page_23.pdf` ; Ventes annuelles historiques.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| new | `table[1][1]` | 2467.1 | Exercice 2017 |
| old | `table[1][2]` | 2397.8 | Exercice 2016 |

**Calcul :** `100 * (2467.1 - 2397.8) / 2397.8` = **2.890149303528234214696805405 %**, affichage **2.9%**.

**Preuves de contexte contrôlées :**

- `table[0][0]` contient : « in millions ».
- `table[0][1]` contient : « 2017 ».
- `table[0][2]` contient : « 2016 ».
- `table[1][0]` contient : « cabinets ».
- `pre_text[22]` contient : « annual net sales for each of the last three fiscal years ».

**Référence FinQA :** `answer = 2.9%` ; `exe_ans = 0.0289` exprimé en **ratio**. L'écart dans cette unité est `0.00000149303528234214696805405`, dans la tolérance `0.000005`.

- Utiliser la division Cabinets, pas les ventes totales ou Plumbing.
- Le symbole $ est explicite ; aucun code ISO de devise n'est ajouté par supposition.
- Source complète : `data/samples/finqa-b01-growth-source.json` ; annotations originales : `evals/cases/finqa-b01-growth-reference.json`.

### C03 — Part des engagements d'achat exigibles après 2014

- **Question d'origine :** what percentage of total purchase commitments are due after 2014?
- **Question explicite pour l'application :** In PKG's 2009 purchase commitments schedule, what percentage of the total is due after 2014?
- **Contexte :** `PKG/2009/page_65.pdf` ; Échéancier d'engagements futurs du rapport 2009.
- **Unité commune :** dollar ($) ; échelle : millier.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| numerator | `table[6][1]` | 25048 | Après 2014 : thereafter |
| denominator | `table[7][1]` | 44572 | Total de l'échéancier 2010 et suivants |

**Calcul :** `100 * 25048 / 44572` = **56.19671542672529839361033833 %**, affichage **56%**.

**Preuves de contexte contrôlées :**

- `table[0][1]` contient : « in thousands ».
- `table[5][0]` contient : « 2014 ».
- `table[6][0]` contient : « thereafter ».
- `table[7][0]` contient : « total ».
- `pre_text[0]` contient : « purchase commitments ».
- `pre_text[1]` contient : « total purchase commitments ».

**Référence FinQA :** `answer = 56%` ; `exe_ans = 0.56197` exprimé en **ratio**. L'écart dans cette unité est `0.0000028457327470160638966167`, dans la tolérance `0.000005`.

- Thereafter signifie après la dernière année explicite 2014 ; ne pas inclure 2014.
- Les engagements futurs ne sont pas des achats déjà réalisés.
- Source complète : `data/samples/finqa-b01-03-source.json` ; annotations originales : `evals/cases/finqa-b01-03-reference.json`.

### C04 — Part des salaires et congés à payer dans les dettes courantes

- **Question d'origine :** as of december 31 , 2008 what was the percent of the total accounts payable and other liabilities that was accrued wages and vacation
- **Question explicite pour l'application :** For Union Pacific at December 31, 2008, what percentage of total accounts payable and other current liabilities was accrued wages and vacation?
- **Contexte :** `UNP/2008/page_77.pdf` ; Solde historique au 31 décembre 2008.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| numerator | `table[2][1]` | 367 | 31 décembre 2008 |
| denominator | `table[8][1]` | 2560 | 31 décembre 2008 |

**Calcul :** `100 * 367 / 2560` = **14.3359375 %**, affichage **14.3%**.

**Preuves de contexte contrôlées :**

- `table[0][0]` contient : « millions of dollars ».
- `table[0][1]` contient : « 2008 ».
- `table[2][0]` contient : « accrued wages and vacation ».
- `table[8][0]` contient : « total accounts payable and other current liabilities ».
- `pre_text[15]` contient : « accounts payable and other current liabilities ».

**Référence FinQA :** `answer = 14.3%` ; `exe_ans = 0.14336` exprimé en **ratio**. L'écart dans cette unité est `6.25E-7`, dans la tolérance `0.000005`.

- La question abrège le libellé ; le dénominateur est le total des passifs courants du tableau, pas seulement Accounts payable.
- Ne pas utiliser la colonne 2007.
- Source complète : `data/samples/finqa-b01-04-source.json` ; annotations originales : `evals/cases/finqa-b01-04-reference.json`.

### C05 — Part des surfaces détenues situées hors États-Unis

- **Question d'origine :** what is the percent of the square feet in owned facilities in other countries?
- **Question explicite pour l'application :** For Intel at December 28, 2013, what percentage of the total square footage of owned facilities was in other countries?
- **Contexte :** `INTC/2013/page_29.pdf` ; Surfaces des installations au 28 décembre 2013.
- **Unité commune :** pied carré ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| numerator | `table[1][2]` | 16.7 | 28 décembre 2013 |
| denominator | `table[1][3]` | 46.6 | 28 décembre 2013 |

**Calcul :** `100 * 16.7 / 46.6` = **35.83690987124463519313304721 %**, affichage **35.8%**.

**Preuves de contexte contrôlées :**

- `table[0][0]` contient : « square feet in millions ».
- `table[0][2]` contient : « othercountries ».
- `table[0][3]` contient : « total ».
- `table[1][0]` contient : « owned facilities ».
- `pre_text[3]` contient : « as of december 28 , 2013 ».

**Référence FinQA :** `answer = 35.8%` ; `exe_ans = 0.35837` exprimé en **ratio**. L'écart dans cette unité est `9.012875536480686695279E-7`, dans la tolérance `0.000005`.

- Le dénominateur est le total Owned facilities 46,6, pas Total facilities 54,9.
- Unité de surface ; aucune conversion en monnaie. Les exposants des libellés sont des appels de note.
- Source complète : `data/samples/finqa-b01-05-source.json` ; annotations originales : `evals/cases/finqa-b01-05-reference.json`.

### C06 — Marge nette sur les chiffres pro forma 2015

- **Question d'origine :** what is the company's net earnings as a percent of net sales in 2015 ? ( net profit margin )
- **Question explicite pour l'application :** Using Zimmer Biomet's unaudited pro forma figures for the year ended December 31, 2015, what were net earnings as a percentage of net sales?
- **Contexte :** `ZBH/2017/page_53.pdf` ; Données pro forma non auditées, année terminée le 31 décembre 2015.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| numerator | `table[2][1]` | 330.2 | Année terminée le 31 décembre 2015, pro forma |
| denominator | `table[1][1]` | 7517.8 | Année terminée le 31 décembre 2015, pro forma |

**Calcul :** `100 * 330.2 / 7517.8` = **4.392242411343744180478331427 %**, affichage **4.392%**.

**Preuves de contexte contrôlées :**

- `table[0][1]` contient : « 2015 ( in millions ) ».
- `table[2][0]` contient : « net earnings ».
- `table[1][0]` contient : « net sales ».
- `pre_text[34]` contient : « unaudited pro forma financial information ».
- `pre_text[36]` contient : « pro forma financial information ( unaudited ) ».
- `post_text[0]` contient : « comparative purposes only ».

**Référence FinQA :** `answer = 4.392%` ; `exe_ans = 0.04392` exprimé en **ratio**. L'écart dans cette unité est `0.00000242411343744180478331427`, dans la tolérance `0.000005`.

- Rapport identifié 2017 mais valeurs portant sur 2015.
- Préciser pro forma non audité : ne pas présenter ces valeurs comme des résultats historiques consolidés sans retraitement.
- Le calcul porte sur les valeurs fournies ; aucune reconstitution comptable de la fusion.
- Source complète : `data/samples/finqa-b01-06-source.json` ; annotations originales : `evals/cases/finqa-b01-06-reference.json`.

### C07 — Croissance du résultat opérationnel de Space Systems en 2011

- **Question d'origine :** what is the growth rate in operating profit for space systems in 2011?
- **Question explicite pour l'application :** For Lockheed Martin Space Systems, what was the percentage change in operating profit from 2010 to 2011?
- **Contexte :** `LMT/2012/page_47.pdf` ; Résultats annuels historiques du segment Space Systems.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| new | `table[2][2]` | 1063 | Exercice 2011 |
| old | `table[2][3]` | 1030 | Exercice 2010 |

**Calcul :** `100 * (1063 - 1030) / 1030` = **3.203883495145631067961165049 %**, affichage **3.2%**.

**Preuves de contexte contrôlées :**

- `table[0][2]` contient : « 2011 ».
- `table[0][3]` contient : « 2010 ».
- `table[2][0]` contient : « operating profit ».
- `table[1][1]` contient : « $ ».
- `pre_text[16]` contient : « space systems 2019 operating results included the following ( in millions ) ».

**Référence FinQA :** `answer = 3.2%` ; `exe_ans = 0.03204` exprimé en **ratio**. L'écart dans cette unité est `0.00000116504854368932038834951`, dans la tolérance `0.000005`.

- Interprétation annuelle de growth in 2011 : 2011 comparé à 2010 ; la question d'origine ne précise pas explicitement la base.
- Les paragraphes initiaux parlent de MST et d'une baisse : ce n'est pas le segment Space Systems du tableau.
- La colonne 2012 ne sert pas à la variation en 2011.
- Source complète : `data/samples/finqa-b01-07-source.json` ; annotations originales : `evals/cases/finqa-b01-07-reference.json`.

### C08 — Croissance du résultat opérationnel publié de 2017 à 2018

- **Question d'origine :** what was the percentage growth in the operating profit as reported from 2017 to 2018
- **Question explicite pour l'application :** For Masco, what was the percentage growth in operating profit as reported from 2017 to 2018?
- **Contexte :** `MAS/2018/page_35.pdf` ; Résultat annuel historique, as reported.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| new | `table[1][1]` | 1211 | Exercice 2018 |
| old | `table[1][2]` | 1194 | Exercice 2017 |

**Calcul :** `100 * (1211 - 1194) / 1194` = **1.423785594639865996649916248 %**, affichage **1.4%**.

**Preuves de contexte contrôlées :**

- `table[0][1]` contient : « 2018 ».
- `table[0][2]` contient : « 2017 ».
- `table[1][0]` contient : « operating profit as reported ».
- `pre_text[10]` contient : « dollars in millions ».

**Référence FinQA :** `answer = 1.4%` ; `exe_ans = 0.01424` exprimé en **ratio**. L'écart dans cette unité est `0.00000214405360134003350083752`, dans la tolérance `0.000005`.

- Choisir as reported, pas as adjusted ni les lignes de marge déjà en pourcentage.
- Anomalies hors opérandes : table[3][2] et [3][3] = 2014, mais table_ori contient des tirets. À traiter en B04.
- Source complète : `data/samples/finqa-b01-08-source.json` ; annotations originales : `evals/cases/finqa-b01-08-reference.json`.

### C09 — Croissance du net revenue d'Entergy Louisiana de 2002 à 2003

- **Question d'origine :** what is the growth rate in net revenue in 2003 for entergy louisiana , inc.?
- **Question explicite pour l'application :** For Entergy Louisiana, what was the percentage change in the reported net revenue measure from 2002 to 2003?
- **Contexte :** `ETR/2004/page_213.pdf` ; Mesure annuelle historique net revenue / marge brute définie dans le rapport.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| new | `table[7][1]` | 973.7 | Exercice 2003 |
| old | `table[1][1]` | 922.9 | Exercice 2002 |

**Calcul :** `100 * (973.7 - 922.9) / 922.9` = **5.504388341098710586195687507 %**, affichage **5.5%**.

**Preuves de contexte contrôlées :**

- `table[0][1]` contient : « in millions ».
- `table[7][0]` contient : « 2003 net revenue ».
- `table[1][0]` contient : « 2002 net revenue ».
- `pre_text[0]` contient : « entergy louisiana ».
- `pre_text[5]` contient : « 2003 compared to 2002 net revenue ».
- `pre_text[6]` contient : « comparing 2003 to 2002 ».

**Référence FinQA :** `answer = 5.5%` ; `exe_ans = 0.05504` exprimé en **ratio**. L'écart dans cette unité est `0.00000388341098710586195687507`, dans la tolérance `0.000005`.

- Net revenue est ici une mesure de marge brute définie dans pre_text[5], pas gross operating revenues.
- Ne pas utiliser les variations intermédiaires du tableau comme valeurs annuelles ; le rapport 2004 décrit ici 2003/2002.
- Source complète : `data/samples/finqa-b01-09-source.json` ; annotations originales : `evals/cases/finqa-b01-09-reference.json`.

### C10 — Baisse du net revenue d'Entergy Wholesale Commodities en 2016

- **Question d'origine :** what is the growth rate in net revenue in 2016?
- **Question explicite pour l'application :** For Entergy Wholesale Commodities, what was the signed percentage change in net revenue from 2015 to 2016?
- **Contexte :** `ETR/2017/page_26.pdf` ; Mesure annuelle historique du segment Entergy Wholesale Commodities.
- **Unité commune :** dollar ($) ; échelle : million.

| Rôle | Cellule | Valeur | Période / périmètre |
|---|---|---:|---|
| new | `table[8][1]` | 1542 | Exercice 2016 |
| old | `table[1][1]` | 1666 | Exercice 2015 |

**Calcul :** `100 * (1542 - 1666) / 1666` = **-7.442977190876350540216086435 %**, affichage **-7.4%**.

**Preuves de contexte contrôlées :**

- `table[0][1]` contient : « in millions ».
- `table[8][0]` contient : « 2016 net revenue ».
- `table[1][0]` contient : « 2015 net revenue ».
- `pre_text[8]` contient : « entergy wholesale commodities ».
- `post_text[0]` contient : « decreased by approximately $ 124 million in 2016 ».

**Référence FinQA :** `answer = -7.4%` ; `exe_ans = -0.07443` exprimé en **ratio**. L'écart dans cette unité est `2.2809123649459783913565E-7`, dans la tolérance `0.000005`.

- Le résultat est négatif malgré le mot growth ; conserver le signe.
- La question ne donne pas les années de base ni le segment : le contexte explicite une comparaison 2016/2015 de ce segment.
- Ne pas confondre ce segment avec Entergy Louisiana dans l'autre rapport retenu.
- Source complète : `data/samples/finqa-b01-10-source.json` ; annotations originales : `evals/cases/finqa-b01-10-reference.json`.

## 5. Normalisation des réponses et points de vigilance

**Convention explicite par cas.** C01 stocke `exe_ans` en pourcentage ; C02 à C10 le stockent en ratio décimal. Pour ces neuf cas, multiplier par 100 avant de comparer à un résultat exprimé en pourcentage. La tolérance native de `0.000005` correspond alors à `0.0005` point de pourcentage ; pour C01 elle reste `0.000005` point. Ce sont des contrôles des annotations arrondies, pas les seuils définitifs du futur produit.

**Évaluation numérique future.** Utiliser `expected_percent` calculé depuis les cellules dans le manifeste de revue, puis fixer les tolérances d'évaluation du système avant les mesures. Un affichage arrondi conforme ne suffit pas : C03 affiche 56 %, mais sa référence calculée vaut environ 56,196715 %. Toujours contrôler également les bonnes périodes, cellules et unités.

**Défauts hors opérandes.** C01 contient une conversion erronée de tiret en `2014`. C08 en contient deux, dans la ligne Kichler pour 2017 et 2016. Ces cellules n'affectent pas les calculs relus, mais restent présentes dans les sources complètes. B04 devra utiliser une règle traçable confrontant les tableaux, représenter un tiret comme valeur absente et tester les conflits, avant de les rendre récupérables. Ne pas remplacer tous les nombres 2014 : certains sont de vraies années.

**Contexte obligatoire.** C06 est pro forma non audité ; C01 est prévisionnel ; C03 porte sur des paiements futurs. Le nom du fichier ne suffit pas à identifier l'année d'une valeur. Pour les montants libellés $, aucun code ISO de devise absent du contexte n'est inventé. L'échelle monétaire commune est explicite dans les preuves.

**Questions adaptées.** Certaines questions d'origine omettent l'entreprise ou la base annuelle. Les questions d'application du manifeste explicitent ces éléments, notamment C07 et C10, et la nature pro forma de C06. Cela définit un benchmark adapté, distinct du benchmark FinQA d'origine. La recherche devra partir de la question, sans `report_id` caché issu des bonnes réponses ; une demande réellement ambiguë devra être clarifiée ou signalée.

## 6. Doublons, groupes et distracteurs

Audit des 883 entrées : **299 contextes exacts distincts**, **299 noms de fichiers distincts**, **272 groupes de contexte associés à plusieurs questions**. L'empreinte du contexte compare tous les champs sources sauf `filename`, afin de détecter aussi un contenu identique sous un autre nom.

Les dix exemples choisis ont dix empreintes de contexte différentes et dix groupes de rapport différents (`entreprise/année`). Les variantes de même page ne deviennent pas des documents indépendants. L'identifiant de rapport et les rapprochements de contenu doivent rester groupés pour éviter une séparation développement/final trompeuse.

| Cas choisi | Questions du même fichier dans dev.json | Questions partageant exactement le contexte |
|---|---:|---:|
| C01 | 2 | 2 |
| C02 | 2 | 2 |
| C03 | 4 | 4 |
| C04 | 3 | 3 |
| C05 | 4 | 4 |
| C06 | 1 | 1 |
| C07 | 4 | 4 |
| C08 | 3 | 3 |
| C09 | 4 | 4 |
| C10 | 4 | 4 |

Les identifiants complets de ces rapprochements figurent dans `docs/verification/B01_VERIFICATION_RESULTS.json`. Une égalité exacte ne détecte pas toutes les quasi-duplicatas ; le groupe de rapport est une protection supplémentaire. Les dix cas sont tous de développement : aucune partition finale réservée n'est constituée ici.

**Trois distracteurs identifiés pour B04**, distincts entre eux et des dix contextes :

- `AES/2017/page_157.pdf-1` (`AES/2017/page_157.pdf`) : Autre entreprise, revenus 2017/2016/2015 ; années et montants similaires.
- `LMT/2015/page_56.pdf-4` (`LMT/2015/page_56.pdf`) : Même entreprise LMT, autre rapport et autres années ; tableau de net sales / operating profit.
- `UNP/2007/page_65.pdf-1` (`UNP/2007/page_65.pdf`) : Autre échéancier de paiements futurs ; peut concurrencer celui des engagements PKG.

Ce sont des candidats de corpus vérifiés pour leur présence et leur distinction, pas trois cas de calcul supplémentaires relus. B04 doit préparer leurs sources seules, vérifier leur qualité et les inclure dans le même index que les dix contextes cibles. Les lignes voisines et années non demandées dans les tableaux constituent également des distracteurs internes. Aucun score de recherche n'est encore disponible.

## 7. Candidats écartés de cette sélection

Cette liste consigne les problèmes effectivement observés pendant la sélection, sans affirmer que ces cas sont inutilisables dans tout autre périmètre.

| Candidat | Motif de non-sélection pour B01 |
|---|---|
| `HOLX/2015/page_98.pdf-2` | Montants $ et prévisions clairs, mais l'échelle monétaire n'est pas explicitée dans le contexte FinQA fourni. Ne pas inventer millions. |
| `LLY/2018/page_63.pdf-1` | Les cellules Inventories correspondent, mais aucune échelle du tableau n'est explicitée dans ce contexte. |
| `PM/2017/page_99.pdf-1` | Le calcul des cellules donne environ −13,3773 %, qui s'arrondit à −13,4 % à une décimale ; la réponse texte est −13,3 %. |
| `UNP/2006/page_37.pdf-2` | Programme annoté mélangeant 3,2 et 2242 ; les valeurs pertinentes ne forment pas deux cellules comparables dans l'unité attendue. Hors périmètre sans conversion/reconstruction. |
| `LMT/2006/page_37.pdf-1` | La question évoque le total du trimestre, alors que le dénominateur annoté 929400 est la ligne décembre. Périmètre du total incohérent. |
| `PM/2015/page_85.pdf-1` | Réponse texte positive 3,4 % alors que le programme produit une variation négative ; les deux valeurs de dette ne sont pas dans les cellules du tableau sélectionné. |

## 8. Séparation des données et fichiers livrés

- `data/raw/finqa-dev.json` : brut avec annotations, local et exclu de l'inférence/Git.
- `data/samples/*-source.json` : dix contextes complets limités aux cinq champs autorisés ; locaux et ignorés par Git.
- `evals/cases/*-reference.json` : annotations FinQA originales inchangées, exclusivement pour l'évaluation.
- `evals/cases/finqa-b01-reviewed.json` : questions adaptées, coordonnées, unités, périodes, opérations, résultats et conventions de cette revue ; **jamais dans l'index ou le prompt d'inférence**.
- `scripts/inspect_finqa.py` : lecture et contrôles relançables, sans dépendance externe.
- `tests/test_b01_verification.py` : trois contrôles négatifs.
- `docs/verification/B01_VERIFICATION_DONNEES.md` : ce rapport.
- `docs/verification/B01_VERIFICATION_RESULTS.json` : résultats exacts, empreintes, doublons et candidats distracteurs.

**Le dossier `docs/verification/` contient des réponses et coordonnées attendues. Il appartient à la documentation d'évaluation ; il doit être exclu de toute ingestion d'inférence**, au même titre que `evals/`. Une future préparation de corpus utilise une liste positive de sources, jamais tous les Markdown/JSON du dépôt.

## 9. Reproduire les contrôles

Depuis la racine du projet, dans PowerShell :

```powershell
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all --check
python3.14.exe -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
```

Résultat observé : dix cas conformes et trois tests négatifs réussis. Les tests injectent une mauvaise année, une confusion ratio/pourcentage et une réponse dans un export source : ces trois erreurs sont rejetées. Ces contrôles concernent la préparation des références, pas encore les garde-fous du futur LLM.

Pour régénérer les vingt exports depuis le brut dont l'empreinte est vérifiée :

```powershell
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all
```

Sans option, la commande conserve le premier cas ; `--case growth` conserve le second ; `--case case03` à `case10` sélectionne les suivants. `--check` ne réécrit aucun export. Ne pas utiliser `-O` : le script refuse ce mode qui désactive les assertions. Le manifeste et le fichier brut doivent être présents ; le README indique comment obtenir le brut.

Les instantanés JSON/Markdown de `docs/verification/` sont datés de cette revue. Les commandes ci-dessus recontrôlent les données ; elles ne régénèrent pas automatiquement le rapport narratif. Si données, manifeste ou code changent, refaire la revue et mettre à jour les instantanés.

## 10. Limites et prochaine étape

Le contrôle confirme les dix exemples sélectionnés dans FinQA, pas la vérité indépendante des rapports originaux ni la qualité de tout le dataset. Aucune vérification des PDFs, aucun test sur des cas réservés, aucune mesure de généralisation, aucun coût/temps de réponse de modèle et aucun gain de recrutement ne sont démontrés.

Prochaine action du backlog : **B02**, préparer le dépôt et l'environnement minimal et vérifier SQLite FTS5. Puis **B03**, choisir et tester un LLM hébergé avec sortie structurée et mesurer latence/consommation avant une campagne. Fournisseur et modèle restent non choisis ; aucun achat n'a été effectué. Ne pas commencer B04 sans traiter les conflits de tableau identifiés et conserver les références hors du corpus.

À comprendre pour la suite : le modèle proposera l'opération et les identifiants des cellules ; le code calculera. Les références préparées ici permettront de vérifier séparément la récupération des preuves, le choix des cellules et le résultat numérique.
