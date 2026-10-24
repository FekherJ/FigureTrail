# Provenance des cas B01 FinQA

- Consultation et téléchargement : 24 octobre 2026.
- Projet : [czyssrs/FinQA](https://github.com/czyssrs/FinQA), associé à **Chen et al., FinQA: A Dataset of Numerical Reasoning over Financial Data, EMNLP 2021**. [Article](https://arxiv.org/abs/2109.00122).
- Fichier : [dataset/dev.json](https://github.com/czyssrs/FinQA/blob/main/dataset/dev.json), 883 entrées ; seules les sources complètes des dix contextes choisis sont exportées.
- URL : `https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json`.
- Identifiant Git du blob annoncé par GitHub : `970f239f591c782b17df420c0d343b780737f3da`.
- SHA-256 téléchargé : `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51`.
- `main` peut évoluer : le script refuse une empreinte différente ; examiner le changement avant de modifier la valeur attendue.
- Cas : `DVN/2007/page_58.pdf-2` ; champ `filename` : `DVN/2007/page_58.pdf`. C'est un repère FinQA, pas un PDF présent dans ce dossier. Le PDF original n'a pas été inspecté pendant cette étape.
- Le dépôt annonce une licence MIT, copyright 2021 Zhiyu Chen. La [notice complète](FINQA_LICENSE.txt), récupérée depuis [LICENSE](https://github.com/czyssrs/FinQA/blob/main/LICENSE), est conservée pour accompagner les extraits et leur redistribution. Aucun PDF financier complet n'est redistribué ici.

Le fichier brut contient des annotations et des champs de recherche préexistants. Il est ignoré par Git et exclu de toute future inférence. La copie source n'autorise que `filename`, `pre_text`, `post_text`, `table`, `table_ori`. Elle conserve toutes les lignes du contexte, sans filtrage sur les bonnes preuves.

La référence dans `evals/cases/` conserve `question`, `answer`, `exe_ans`, `program`, `gold_inds`, l'identifiant et la partition locale `development`. Le script ne lance jamais le programme FinQA. Cette sélection de développement ne réserve aucun cas final et ne mesure aucune qualité de recherche.

## Second cas relu

`FBHS/2017/page_23.pdf-2` ; `filename` : `FBHS/2017/page_23.pdf`, dans le même téléchargement et sous la même notice. Exports : `data/samples/finqa-b01-growth-source.json` et `evals/cases/finqa-b01-growth-reference.json`. Vérification des textes/tableaux FinQA uniquement ; aucun PDF original inspecté.

L'entrée `FBHS/2017/page_23.pdf-1` partage le même contexte source : ne pas créer un second document identique dans le corpus et conserver les questions de ce contexte dans le même groupe lors de la séparation développement/final. Les deux cas B01 choisis appartiennent à des rapports différents.

## Vérification des dix cas B01

Le 24 octobre 2026, dix contextes de développement ont été vérifiés par revue assistée des sources et recalcul déterministe : voir `../docs/verification/B01_VERIFICATION_DONNEES.md`. Le manifeste `../evals/cases/finqa-b01-reviewed.json` conserve les identifiants, questions adaptées, unités, périodes, cellules, résultats attendus et conventions de `exe_ans`. Les dix références originales restent inchangées. Tous les contextes proviennent du même téléchargement ci-dessus.

L'audit compare les champs sources sans filename pour les doublons exacts et prévoit un groupement par entreprise/année du rapport. Dix contextes et dix groupes de rapport distincts sont sélectionnés ; trois candidats distracteurs sont identifiés, sans être encore exportés/indexés. Les détails de rapprochement figurent dans `../docs/verification/B01_VERIFICATION_RESULTS.json`. docs/verification et evals sont exclus du futur corpus d'inférence.
