# 🏠 Dashboard Immobilier DVF

Un dashboard **Streamlit** interactif pour explorer les transactions immobilières en France à partir des données ouvertes **DVF** (*Demandes de Valeurs Foncières*, publiées par l'État). Filtrez par région, département, type de bien, visualisez les prix au m², et localisez les transactions sur carte.

Projet Master 1 — Data Visualization, Efrei Paris.

![Aperçu — ventes par mois](img/sales_by_month.png)

## ✨ Fonctionnalités

| Page | Description |
|---|---|
| 🏠 **Accueil** | Présentation du projet |
| 📊 **Visualisations générales** | Fréquence des mutations, tendance mensuelle, répartition par type de bien, prix moyen par département/région, carte des transactions — de 2019 à 2024 |
| 🔎 **Votre exploration** | Filtres interactifs (type de mutation, type de bien, région/département, nb. de pièces), nuage de points prix/surface, carte vue d'ensemble ou détaillée |
| 🧠 **Estimation / Prédiction** | Estimation du prix de vente d'une maison ou d'un appartement (type, surface, nb. de pièces, commune) via un modèle pré-entraîné sur les ventes les plus récentes (marché actuel) |

## 📂 Structure du projet

```
project_st.py          # application Streamlit
train_model.py          # script d'entraînement hors-ligne du modèle de prédiction
model/
  └── price_model.joblib   # modèle pré-entraîné, chargé par l'app (inclus)
project.ipynb           # notebook d'exploration et de nettoyage (données 2019)
dvf_test.ipynb          # notebook de test (imputation KNN)
data/
  └── departements-france.csv   # table de référence département/région (incluse)
```

## 📥 Données

Les jeux de données de transactions sont trop volumineux pour être versionnés ici. Télécharge les années nécessaires et place-les dans `data/` :

- **2019-2020** (historique) — depuis [data.gouv.fr — Demandes de valeurs foncières](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/) :
  - `data/full_2019.csv`
  - `data/sampled_2020_by_dep.csv`
- **2021-2024** (historique récent + entraînement du modèle) — depuis le dépôt officiel [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/) (fichier `full.csv.gz` de chaque année, à décompresser) :
  - `data/dvf_2021.csv`, `data/dvf_2022.csv`, `data/dvf_2023.csv`, `data/dvf_2024.csv`

Seule `data/departements-france.csv` (table de référence, quelques Ko) est versionnée.

Le module de prédiction n'a besoin que du modèle déjà entraîné (`model/price_model.joblib`, inclus dans le repo) — pas des CSV bruts, sauf si tu veux le ré-entraîner (voir ci-dessous).

## 🧠 Ré-entraîner le modèle de prédiction

Le modèle est entraîné hors-ligne sur les deux années les plus récentes (marché actuel), avec un signal de prix par commune (lissé vers la médiane départementale pour les petites communes) :

```bash
python train_model.py
```

Nécessite `data/dvf_2023.csv` et `data/dvf_2024.csv` (voir ci-dessus). Régénère `model/price_model.joblib`.

## 🚀 Lancer le projet

```bash
pip install -r requirements.txt
streamlit run project_st.py
```
