# 🏠 Dashboard Immobilier DVF

Un dashboard **Streamlit** interactif pour explorer les transactions immobilières en France à partir des données ouvertes **DVF** (*Demandes de Valeurs Foncières*, publiées par l'État) : visualisations sur 2019-2024, exploration filtrée, et un module d'estimation de prix entraîné sur le marché actuel.

Projet Master 1 — Data Visualization, Efrei Paris.

![Aperçu — ventes par mois](img/sales_by_month.png)

## Sommaire

- [Fonctionnalités](#-fonctionnalités)
- [Comment fonctionne le module de prédiction](#-comment-fonctionne-le-module-de-prédiction)
- [Structure du projet](#-structure-du-projet)
- [Données](#-données)
- [Ré-entraîner le modèle](#-ré-entraîner-le-modèle-de-prédiction)
- [Lancer le projet](#-lancer-le-projet)

## ✨ Fonctionnalités

### 🏠 Accueil
Présentation du projet.

### 📊 Visualisations générales
Vue d'ensemble du marché pour une année choisie (slider 2019-2024) :

- **Fréquence des mutations** — répartition par nature de transaction (Vente, Vente en l'état futur d'achèvement, Échange, Expropriation...)
- **Tendance mensuelle** — nombre de ventes par mois, pour repérer la saisonnalité
- **Répartition par type de bien** — Maison, Appartement, Dépendance, Terrain, Local commercial (camembert)
- **Prix médian par département** — Maison/Appartement uniquement, barres horizontales triées, départements avec moins de 20 ventes échantillonnées exclus (statistique non fiable sur trop peu de données)
- **Prix au m² médian par région** — trié par ordre décroissant
- **Carte de densité des mutations** — heatmap sur fond de carte réel (OpenStreetMap)
- **Évolution 2019-2024** — prix médian au m² par année (Maison vs Appartement), derrière un bouton car cela charge les 6 années de données au premier clic (quelques minutes), puis reste en cache pour la session

Les prix affichés utilisent la **médiane** plutôt que la moyenne : les données DVF brutes contiennent des valeurs aberrantes (voir plus bas) qui fausseraient une moyenne.

### 🔎 Votre exploration
Exploration filtrée pour une année choisie :

- Filtres : type de mutation, type de bien, régions, départements, nombre de pièces
- Histogramme des transactions par mois selon les filtres
- Prix au m² médian par département (sur la sélection)
- Nuage de points prix / surface (taille des points = nombre de pièces)
- Carte des transactions filtrées — vue d'ensemble (`st.map`) ou détaillée (carte interactive avec info-bulles)

### 🧠 Estimation / Prédiction
Estime le prix de vente d'une maison ou d'un appartement à partir de son type, sa commune, sa surface et son nombre de pièces, via un modèle de machine learning pré-entraîné. Détails complets ci-dessous.

## 🧠 Comment fonctionne le module de prédiction

Le module de prédiction est **entraîné hors-ligne** par [`train_model.py`](train_model.py) et le résultat est embarqué dans le repo (`model/price_model.joblib`, ~3 Mo) : l'application ne fait que le **charger et l'exécuter**, elle ne ré-entraîne jamais rien au runtime. Voici le détail de chaque étape de la construction du modèle.

### 1. Données sources

Les deux années DVF les plus récentes et complètes disponibles : **2023 et 2024** (~7.3 millions de lignes brutes cumulées), téléchargées depuis le dépôt officiel [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/).

**Pourquoi seulement 2 ans, et pas tout l'historique 2019-2024 ?** L'objectif du module est d'estimer un prix **par rapport au marché actuel**. Mélanger plusieurs années sans corriger l'inflation immobilière biaiserait l'estimation vers des prix datés. Se limiter aux années les plus récentes évite ce biais sans complexifier le modèle avec un indice de correction des prix.

### 2. Nettoyage des données

Sur les 7.3M lignes brutes, plusieurs filtres successifs réduisent le jeu de données à **1 378 860 lignes exploitables** :

| Filtre | Pourquoi |
|---|---|
| `nature_mutation == 'Vente'` | Exclut les échanges, expropriations, adjudications — on ne veut que des ventes classiques |
| `type_local ∈ {Maison, Appartement}` | Exclut terrains et locaux commerciaux, dont la dynamique de prix n'a rien à voir |
| **Déduplication des ventes en bloc** (voir encadré ci-dessous) | Corrige un artefact majeur des données DVF |
| `surface_reelle_bati` entre 9 et 500 m² | Exclut les erreurs de saisie (surfaces nulles ou absurdes) |
| `nombre_pieces_principales` entre 1 et 12 | Idem |
| `valeur_fonciere` entre 10 000 € et 2 000 000 € | Exclut les valeurs extrêmes non représentatives |
| `code_commune` renseigné | Nécessaire pour le signal de prix par commune (étape suivante) |

> **🐛 Le bug des ventes en bloc.** DVF enregistre parfois une transaction portant sur plusieurs logements (ex : un immeuble entier vendu en une fois) en répétant la **valeur totale de la transaction sur chaque ligne/logement**, au lieu de la répartir. Un seul cas réel rencontré en construisant ce projet : une vente à Bourges où 1105 lignes affichaient chacune 54 257 152 € — la valeur du *bloc entier*, pas d'un logement. Sans correction, ce genre de ligne fait exploser n'importe quelle statistique de prix pour son département. La correction : on compte, pour chaque transaction (`id_mutation`), le nombre de lignes Maison/Appartement qu'elle contient — si plus d'une, la transaction est exclue (`nombre_lots` ne suffit pas : c'est un compteur par ligne, pas par transaction). Cette même correction est appliquée à la fois ici et dans le pipeline des visualisations (`process()` dans `project_st.py`).

### 3. Feature engineering — le signal de prix par commune

Le modèle utilise 5 variables :

| Variable | Description |
|---|---|
| `type_local` | Maison ou Appartement (encodé en one-hot) |
| `surface_reelle_bati` | Surface habitable (m²) |
| `nombre_pieces_principales` | Nombre de pièces |
| `annee_mutation` | 2023 ou 2024, pour capter une éventuelle tendance à court terme |
| `price_signal` | **Prix médian au m² observé dans la commune du bien**, pour son type de bien |

Le `price_signal` est ce qui fait vraiment la différence : le département seul (96 valeurs possibles) est une maille bien trop grossière pour la France (ex : le 7ème arrondissement de Paris et le 19ème n'ont pas du tout le même marché, mais tous deux sont "Paris"). La commune (~35 000 valeurs) capture bien mieux la localisation.

**Problème avec la commune brute** : certaines communes ont très peu de ventes dans l'échantillon (parfois une seule), rendant leur médiane locale peu fiable. On applique donc un **lissage bayésien** vers la médiane du département :

```
price_signal = (n × médiane_commune + k × médiane_département) / (n + k)
```

où `n` = nombre de ventes observées dans la commune, et `k = 15` (constante de lissage). Une commune avec beaucoup de ventes (`n` grand) garde sa propre médiane ; une commune avec peu de ventes est automatiquement tirée vers la médiane, plus fiable, de son département. Si une commune n'a aucune vente dans les données d'entraînement, le signal retombe entièrement sur la médiane départementale (`dept_fallback`).

**Éviter la fuite de données (data leakage)** : ce calcul est effectué **uniquement sur les données d'entraînement** (après le split train/test), puis appliqué tel quel aux données de test. Si on l'avait calculé sur l'ensemble des données avant de séparer train/test, chaque ligne de test aurait indirectement "vu" sa propre valeur cible via la médiane de sa commune — le R² mesuré aurait été artificiellement gonflé.

### 4. Entraînement

- **Split** : 80 % train / 20 % test, aléatoire (`random_state=42` pour la reproductibilité)
- **Cible** : `log(1 + valeur_fonciere)` plutôt que le prix brut — les prix immobiliers sont fortement asymétriques (quelques ventes très chères), et travailler en log stabilise l'apprentissage. On applique `expm1` (l'inverse) pour revenir en euros au moment de la prédiction.
- **Modèle** : [`HistGradientBoostingRegressor`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) (scikit-learn) — un gradient boosting par histogrammes, rapide même sur plus d'un million de lignes (~50 secondes d'entraînement) et généralement plus performant qu'une forêt aléatoire sur ce type de données tabulaires.
  - `max_iter=300`, `learning_rate=0.08`, `max_depth=8`, `l2_regularization=1.0`
- **Prétraitement** : `type_local` encodé en one-hot via un `ColumnTransformer` ; les autres variables passent telles quelles (`remainder='passthrough'`)

### 5. Évaluation

Mesurée sur les 20 % de données de test (jamais vues pendant l'entraînement), en repassant en euros (`expm1`) :

| Métrique | Valeur | Interprétation |
|---|---|---|
| **R²** | **0.70** | Le modèle explique 70 % de la variance des prix de vente — bon score pour ce type de données : DVF ne contient ni l'étage, ni l'état du bien, ni la vue, ni les prestations, qui expliquent une bonne partie du prix restant |
| **MAE** | **≈ 60 175 €** | En moyenne, l'estimation s'écarte du prix réel de vente d'environ 60 000 € |

Ces deux métriques sont recalculées à chaque exécution de `train_model.py` et affichées directement dans l'app (caption sous le titre de la page Prédiction), pour rester toujours synchronisées avec le modèle réellement chargé.

### 6. À l'exécution (dans l'app)

1. L'utilisateur choisit : type de bien → département → commune (liste filtrée par département) → surface → nombre de pièces
2. L'app récupère le `price_signal` de la commune choisie dans le lookup (avec repli département si absent)
3. Le modèle prédit `log(1 + prix)` à partir des 5 features, puis on repasse en euros
4. Affichage du prix estimé et du prix au m²

Le chargement de `price_model.joblib` (`joblib.load`) est mis en cache (`st.cache_resource`) : quasi instantané dès le premier accès à la page.

### Limites assumées

- Estimation **indicative** : ne tient pas compte de l'adresse exacte, de l'étage, de l'état du bien, des prestations (balcon, parking, vue...)
- Le signal de commune peut être peu discriminant pour les communes très peu vendues (repli département)
- Ne remplace pas une estimation professionnelle

## 📂 Structure du projet

```
project_st.py           # application Streamlit (4 pages)
train_model.py           # entraînement hors-ligne du modèle de prédiction
model/
  └── price_model.joblib    # modèle pré-entraîné + lookup communes (inclus, ~3 Mo)
project.ipynb            # notebook d'exploration et de nettoyage (données 2019)
dvf_test.ipynb           # notebook de test (imputation KNN, abandonné)
data/
  └── departements-france.csv   # table de référence département/région (incluse)
```

## 📥 Données

Les jeux de données de transactions sont trop volumineux pour être versionnés ici (des centaines de Mo à plusieurs Go par année). Télécharge les années nécessaires et place-les dans `data/` :

- **2019-2020** (historique) — depuis [data.gouv.fr — Demandes de valeurs foncières](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/) :
  - `data/full_2019.csv`
  - `data/sampled_2020_by_dep.csv`
- **2021-2024** (historique récent + entraînement du modèle) — depuis le dépôt officiel [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/) (fichier `full.csv.gz` de chaque année, à décompresser) :
  - `data/dvf_2021.csv`, `data/dvf_2022.csv`, `data/dvf_2023.csv`, `data/dvf_2024.csv`

Seule `data/departements-france.csv` (table de référence, quelques Ko) est versionnée.

**Le module de prédiction n'a besoin d'aucun de ces CSV** pour fonctionner dans l'app — le modèle déjà entraîné (`model/price_model.joblib`) est inclus dans le repo. Les CSV ne sont nécessaires que pour les pages de visualisation, ou si tu veux ré-entraîner le modèle toi-même.

## 🧠 Ré-entraîner le modèle de prédiction

```bash
python train_model.py
```

Nécessite `data/dvf_2023.csv` et `data/dvf_2024.csv` (voir ci-dessus). Régénère `model/price_model.joblib` avec les métriques R²/MAE à jour, affichées dans la console et automatiquement reprises par l'app.

## 🚀 Lancer le projet

```bash
pip install -r requirements.txt
streamlit run project_st.py
```
