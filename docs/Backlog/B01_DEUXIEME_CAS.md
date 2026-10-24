# B01 — Cas de référence : variation relative

**24 octobre 2026 — Vérifié contre les sources FinQA ; B01 : 10 cas / 10, faisabilité des données terminée.**

Objectif : préparer des réponses de référence fiables pour mesurer ensuite la recherche de preuves et la sélection de cellules par le LLM. Ces vérifications ne constituent pas encore une évaluation de l'application.

## Question et sources

Cas : `FBHS/2017/page_23.pdf-2` ; contexte : `FBHS/2017/page_23.pdf`.

Question originale : **what was the percentage growth in sales of cabinets from 2016 to 2017**.

Quelle a été la croissance en pourcentage des ventes de la division Cabinets entre 2016 et 2017 ? Le passage `pre_text[22]` décrit les ventes nettes annuelles par division pour les trois derniers exercices. Ce sont des valeurs historiques, sans mention de prévision dans ce passage.

Coordonnées à partir de zéro :

| Rôle | Cellule | Ligne | En-tête | Valeur | Unité et échelle |
|---|---|---|---|---:|---|
| Nouveau | `table[1][1]` | cabinets | 2017 | 2467,1 | millions de dollars, symbole `$` |
| Ancien / base | `table[1][2]` | cabinets | 2016 | 2397,8 | millions de dollars, symbole `$` |

`table[0][0]` indique « in millions » ; les deux cellules portent `$`. Le contexte sélectionné ne donne pas de code ISO de devise : aucun code USD n'est ajouté par supposition. Aucune conversion n'est nécessaire puisque les deux valeurs ont la même unité et la même échelle.

Les cellules correspondantes de `table_ori` valent `$2,467.1` et `$2,397.8`, sous les en-têtes `<i>2017</i>` et `<i>2016</i>`. Le symbole monétaire et les séparateurs de milliers sont retirés avant conversion en `Decimal` ; les valeurs numériques concordent.

La ligne et ses en-têtes fournissent les preuves numériques ; `pre_text[22]` établit la nature annuelle des ventes. La colonne 2015 et les lignes Plumbing, Doors et Security ne sont pas les opérandes de cette question.

## Formule et réponse

```text
variation relative = 100 × (nouveau − ancien) / ancien
                   = 100 × (2467,1 − 2397,8) / 2397,8
                   = 2,890149303528234214696805405… %
affichage selon la précision de la référence : 2,9 %
```

Base positive : 2397,8. La hausse absolue est de 69,3 millions ; elle n'est pas la réponse en pourcentage. Diviser par 2467,1 utiliserait la mauvaise base. Il s'agit d'une variation relative, pas d'une différence entre deux taux exprimée en points de pourcentage.

FinQA conserve `answer = "2.9%"`, mais `exe_ans = 0.0289` est **un ratio décimal**, contrairement au premier cas où `exe_ans` était déjà un pourcentage. Les annotations originales sont conservées sans modification. Comparer le ratio calculé à `exe_ans` avec une tolérance absolue de `0.000005` ; en pourcentage, cela correspond à `0.0005` point. Vérifier également l'affichage à une décimale. La convention doit être explicitement enregistrée lors de la préparation du futur jeu d'évaluation.

Le programme annoté `subtract(2467.1, 2397.8), divide(#0, 2397.8)` est une donnée de référence, jamais du code exécuté. `gold_inds` désigne `table_1` ; le contexte de période est vérifié séparément.

## Séparation, doublon et limites

- Source complète autorisée : `data/samples/finqa-b01-growth-source.json` ; uniquement `filename`, `pre_text`, `post_text`, `table`, `table_ori`. Aucun filtrage sur la bonne ligne.
- Question et annotations : `evals/cases/finqa-b01-growth-reference.json`, exclusivement pour l'évaluation.
- `FBHS/2017/page_23.pdf-1` partage exactement les mêmes champs sources. Dédupliquer ce contexte avant indexation et grouper ses questions ensemble lors de la séparation développement/final. Les deux cas détaillés proviennent de rapports différents.
- Aucun conflit numérique constaté entre les deux versions des cellules utilisées. Le contexte contient des artefacts textuels, par exemple `2019s` pour des apostrophes : ne pas prétendre que tout le document est nettoyé.
- Vérification sur les textes et tableaux FinQA distribués, sans inspection du PDF original. La notice et l'empreinte du téléchargement restent celles de `data/FINQA_PROVENANCE.md`.

## Contrôle reproductible

```powershell
python3.14.exe -X utf8 scripts/inspect_finqa.py --case growth
python3.14.exe -X utf8 scripts/inspect_finqa.py --case growth --check
```

La première commande régénère les deux exports séparés ; la seconde les vérifie sans écriture. La commande existante sans option conserve le premier cas. Le vérificateur hors ligne utilise `assert` : ne pas exécuter avec `-O`.

Contrôles : empreinte du brut, libellés/périodes, valeurs des deux tableaux, base positive, calcul depuis les cellules, ratio/arrondi, liste positive des champs sources et correspondance des exports. Aucun appel LLM/API : **0 €** pour cette étape.

## Conventions de référence et suivi

Un résultat de référence doit préciser son unité, sa convention et sa tolérance. Un nombre correct accompagné des mauvaises années ou d'une réponse de référence mal normalisée peut fausser une évaluation.

Les deux familles prévues ont maintenant chacune un premier exemple vérifié : ratio en pourcentage et variation relative. La vérification des dix cas et la revue des doublons/distracteurs sont maintenant consignées dans le [rapport B01](../verification/B01_VERIFICATION_DONNEES.md). B01 est terminé pour la faisabilité des données ; aucun score RAG/LLM n'est annoncé.
