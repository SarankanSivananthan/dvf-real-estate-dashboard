# 🏠 DVF Real Estate Dashboard

An interactive **Streamlit** dashboard for exploring French real estate transactions from the open **DVF** dataset (*Demandes de Valeurs Foncières*, published by the French government): 2019-2024 visualizations, filtered exploration, and a price estimation module trained on the current market.

Master 1 project — Data Visualization, Efrei Paris.

![Preview — sales by month](img/sales_by_month.png)

## Contents

- [Features](#-features)
- [How the prediction module works](#-how-the-prediction-module-works)
- [Project structure](#-project-structure)
- [Data](#-data)
- [Retraining the model](#-retraining-the-prediction-model)
- [Running the project](#-running-the-project)

## ✨ Features

### 🏠 Home
Project introduction.

### 📊 General Visualizations
A market overview for a chosen year (2019-2024 slider):

- **Mutation frequency** — breakdown by transaction type (Sale, Off-plan sale, Exchange, Expropriation...)
- **Monthly trend** — number of sales per month, to spot seasonality
- **Property type breakdown** — House, Apartment, Outbuilding, Land, Commercial premises (pie chart)
- **Median price by department** — Houses and Apartments only, sorted horizontal bars, departments with fewer than 20 sampled sales excluded (too little data to be a reliable statistic)
- **Median price per m² by region** — sorted in descending order
- **Mutation density map** — a heatmap on a real map background (OpenStreetMap)
- **2019-2024 evolution** — median price per m² by year (House vs. Apartment), behind a button since it loads all 6 years of data on first click (a few minutes), then stays cached for the session

Prices shown use the **median** rather than the mean: the raw DVF data contains outlier values (see below) that would otherwise skew a mean.

### 🔎 Your Exploration
Filtered exploration for a chosen year:

- Filters: transaction type, property type, regions, departments, number of rooms
- Histogram of transactions by month for the current filters
- Median price per m² by department (on the current selection)
- Price vs. surface scatter plot (point size = number of rooms)
- Map of the filtered transactions — overview (`st.map`) or detailed (interactive map with tooltips)

### 🧠 Estimation / Prediction
Estimates the sale price of a house or apartment from its type, commune, surface, and number of rooms, using a pre-trained machine learning model. Full details below.

## 🧠 How the prediction module works

The prediction module is **trained offline** by [`train_model.py`](train_model.py), and the result is shipped in the repo (`model/price_model.joblib`, ~3MB): the app only **loads and runs it** — it never retrains anything at runtime. Here is a full breakdown of how the model is built.

### 1. Source data

The two most recent, complete DVF years available: **2023 and 2024** (~7.3 million raw rows combined), downloaded from the official [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/) repository.

**Why only 2 years, instead of the full 2019-2024 history?** The goal of this module is to estimate a price **relative to today's market**. Blending several years without correcting for real-estate price inflation would bias the estimate toward dated prices. Sticking to the most recent years avoids that bias without adding the complexity of a price-trend correction.

### 2. Data cleaning

Out of 7.3M raw rows, a series of filters narrows the dataset down to **1,378,860 usable rows**:

| Filter | Why |
|---|---|
| `nature_mutation == 'Vente'` | Excludes exchanges, expropriations, auctions — keep only regular sales |
| `type_local ∈ {Maison, Appartement}` | Excludes land and commercial premises, whose price dynamics are unrelated |
| **Bulk-sale deduplication** (see box below) | Fixes a major artifact in the DVF data |
| `surface_reelle_bati` between 9 and 500 m² | Excludes data-entry errors (zero or absurd surfaces) |
| `nombre_pieces_principales` between 1 and 12 | Same |
| `valeur_fonciere` between €10,000 and €2,000,000 | Excludes non-representative extreme values |
| `code_commune` present | Required for the per-commune price signal (next step) |

> **🐛 The bulk-sale bug.** DVF sometimes records a transaction covering multiple housing units (e.g. a whole apartment building sold in one deal) by repeating the **full transaction value on every unit's row**, instead of splitting it. One real case hit while building this project: a sale in Bourges where 1,105 rows each showed €54,257,152 — the value of the *entire block*, not of one unit. Left uncorrected, a handful of rows like this can wreck any price statistic for their department. The fix: for each transaction (`id_mutation`), count how many Maison/Appartement rows it contains — if more than one, the transaction is excluded (`nombre_lots` alone isn't enough: it's a per-row lot count, unrelated to how many rows share one transaction). The same fix is applied both here and in the visualization pipeline (`process()` in `project_st.py`).

### 3. Feature engineering — the commune price signal

The model uses 5 features:

| Feature | Description |
|---|---|
| `type_local` | House or Apartment (one-hot encoded) |
| `surface_reelle_bati` | Living area (m²) |
| `nombre_pieces_principales` | Number of rooms |
| `annee_mutation` | 2023 or 2024, to capture any short-term trend |
| `price_signal` | **Median price per m² observed in the property's commune**, for its property type |

The `price_signal` is what really makes the difference: the department alone (96 possible values) is far too coarse a grid for France (e.g. Paris's 7th and 19th arrondissements don't share anything close to the same market, yet both are just "Paris"). The commune (~35,000 possible values) captures location far better.

**The problem with raw commune data**: some communes have very few sales in the sample (sometimes just one), making their local median unreliable. A **Bayesian shrinkage** toward the department median is applied:

```
price_signal = (n × commune_median + k × department_median) / (n + k)
```

where `n` = number of observed sales in the commune, and `k = 15` (smoothing constant). A commune with many sales (large `n`) keeps close to its own median; a commune with few sales gets pulled toward the more reliable department median. If a commune has zero sales in the training data, the signal falls back entirely to the department median (`dept_fallback`).

**Avoiding data leakage**: this lookup is computed **only on the training split** (after the train/test split), then applied as-is to the test data. Computing it on the full dataset before splitting would let each test row indirectly "see" its own target value through its commune's median — inflating the measured R² artificially.

### 4. Training

- **Split**: 80% train / 20% test, random (`random_state=42` for reproducibility)
- **Target**: `log(1 + valeur_fonciere)` rather than the raw price — real estate prices are strongly right-skewed (a few very expensive sales), and working in log-space stabilizes training. `expm1` (the inverse) is applied to convert back to euros at prediction time.
- **Model**: [`HistGradientBoostingRegressor`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) (scikit-learn) — a histogram-based gradient boosting regressor, fast even on over a million rows (~50 seconds to train) and generally stronger than a random forest on this kind of tabular data.
  - `max_iter=300`, `learning_rate=0.08`, `max_depth=8`, `l2_regularization=1.0`
- **Preprocessing**: `type_local` one-hot encoded via a `ColumnTransformer`; the other features pass through unchanged (`remainder='passthrough'`)

### 5. Evaluation

Measured on the 20% test split (never seen during training), converted back to euros (`expm1`):

| Metric | Value | Meaning |
|---|---|---|
| **R²** | **0.70** | The model explains 70% of the variance in sale prices — a solid score for this kind of data: DVF contains neither floor, condition, view, nor amenities, which account for a good part of the remaining price variation |
| **MAE** | **≈ €60,175** | On average, the estimate is off from the actual sale price by about €60,000 |

Both metrics are recomputed every time `train_model.py` runs and displayed directly in the app (caption under the Prediction page title), so they always stay in sync with the actually-loaded model.

### 6. At runtime (in the app)

1. The user picks: property type → department → commune (list filtered by department) → surface → number of rooms
2. The app looks up the `price_signal` for the chosen commune (falling back to the department if not found)
3. The model predicts `log(1 + price)` from the 5 features, then it's converted back to euros
4. The estimated price and price per m² are displayed

Loading `price_model.joblib` (`joblib.load`) is cached (`st.cache_resource`): near-instant from the first visit to the page onward.

### Known limitations

- The estimate is **indicative only**: it doesn't account for exact address, floor, condition, or amenities (balcony, parking, view...)
- The commune signal can be weakly discriminative for very low-volume communes (falls back to department)
- Not a substitute for a professional appraisal

## 📂 Project structure

```
project_st.py           # Streamlit application (4 pages)
train_model.py           # offline training script for the prediction model
model/
  └── price_model.joblib    # pre-trained model + commune lookup (included, ~3MB)
project.ipynb            # exploration and cleaning notebook (2019 data)
dvf_test.ipynb           # scratch/test notebook (KNN imputation, abandoned)
data/
  └── departements-france.csv   # department/region reference table (included)
```

## 📥 Data

The transaction datasets are too large to version here (hundreds of MB to a few GB per year). Download the years you need and place them in `data/`:

- **2019-2020** (historical) — from [data.gouv.fr — Demandes de valeurs foncières](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/):
  - `data/full_2019.csv`
  - `data/sampled_2020_by_dep.csv`
- **2021-2024** (recent history + model training) — from the official [files.data.gouv.fr/geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/) repository (each year's `full.csv.gz`, to be decompressed):
  - `data/dvf_2021.csv`, `data/dvf_2022.csv`, `data/dvf_2023.csv`, `data/dvf_2024.csv`

Only `data/departements-france.csv` (reference table, a few KB) is versioned.

**The prediction module needs none of these CSVs** to run in the app — the already-trained model (`model/price_model.joblib`) is included in the repo. The raw CSVs are only needed for the visualization pages, or if you want to retrain the model yourself.

## 🧠 Retraining the prediction model

```bash
python train_model.py
```

Requires `data/dvf_2023.csv` and `data/dvf_2024.csv` (see above). Regenerates `model/price_model.joblib` with up-to-date R²/MAE metrics, printed to the console and automatically picked up by the app.

## 🚀 Running the project

```bash
pip install -r requirements.txt
streamlit run project_st.py
```
