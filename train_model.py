"""
Offline training script for the price estimation model used by the
"Estimation - Prediction" page of project_st.py.

Trains on the most recent full years of DVF sales (current market),
so the estimate reflects today's prices rather than a multi-year blend.

Usage:
    python train_model.py

Expects the source DVF CSVs (not versioned, see README) at:
    ../DataViz_Project/dvf_recent/dvf_2023.csv
    ../DataViz_Project/dvf_recent/dvf_2024.csv
    data/departements-france.csv

Writes the trained artifact to:
    model/price_model.joblib
"""
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_DIR = "/Volumes/TOSHIBA EXT/stockage_M1/DataViz_Project/dvf_recent"
TRAIN_YEARS = [2023, 2024]
COMMUNE_SMOOTHING = 15  # higher = more shrinkage toward department median for small communes


def load_years(years):
    frames = []
    for year in years:
        df = pd.read_csv(f"{DATA_DIR}/dvf_{year}.csv", low_memory=False)
        df["annee_mutation"] = year
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def clean(df, df_dept):
    df["code_departement"] = df["code_departement"].astype(str)
    df["code_departement"] = df["code_departement"].apply(lambda c: "0" + c if len(c) == 1 else c)
    df_dept = df_dept.copy()
    df_dept["code_departement"] = df_dept["code_departement"].astype(str)
    df = df.merge(df_dept, on="code_departement", how="left")

    # DVF records the full transaction value on every row of a bulk sale
    # (e.g. a whole apartment building sold as one mutation, split into one
    # row per unit) instead of splitting it per unit. Excluding mutations
    # that contain more than one Maison/Appartement row avoids those rows
    # wrecking any price statistic (nombre_lots does NOT catch this — it's
    # a per-row lot count, unrelated to how many rows share one mutation).
    residential = df["type_local"].isin(["Maison", "Appartement"])
    residential_units_per_mutation = df[residential].groupby("id_mutation").size()
    single_unit_mutation = df["id_mutation"].map(residential_units_per_mutation).fillna(0) <= 1

    mask = (
        (df["nature_mutation"] == "Vente")
        & residential
        & single_unit_mutation
        & df["surface_reelle_bati"].between(9, 500)
        & df["nombre_pieces_principales"].between(1, 12)
        & df["valeur_fonciere"].between(10_000, 2_000_000)
        & df["code_commune"].notna()
    )
    data = df.loc[mask].copy()
    data["prix_m_carre"] = data["valeur_fonciere"] / data["surface_reelle_bati"]
    return data


def build_commune_lookup(data):
    dept_median = data.groupby(["code_departement", "type_local"])["prix_m_carre"].median()

    grouped = data.groupby(["code_commune", "type_local"])["prix_m_carre"]
    commune_stats = grouped.agg(["median", "count"]).reset_index()

    commune_dept = data[["code_commune", "code_departement"]].drop_duplicates("code_commune")
    commune_stats = commune_stats.merge(commune_dept, on="code_commune", how="left")

    commune_stats["dept_median"] = commune_stats.apply(
        lambda r: dept_median.get((r["code_departement"], r["type_local"]), r["median"]), axis=1
    )
    commune_stats["price_signal"] = (
        commune_stats["count"] * commune_stats["median"]
        + COMMUNE_SMOOTHING * commune_stats["dept_median"]
    ) / (commune_stats["count"] + COMMUNE_SMOOTHING)

    lookup = commune_stats.set_index(["code_commune", "type_local"])["price_signal"].to_dict()
    dept_fallback = dept_median.to_dict()
    return lookup, dept_fallback


def attach_price_signal(data, lookup, dept_fallback):
    signal_df = pd.Series(lookup, name="price_signal").rename_axis(["code_commune", "type_local"]).reset_index()
    data = data.merge(signal_df, on=["code_commune", "type_local"], how="left")

    fallback_df = pd.Series(dept_fallback, name="dept_signal").rename_axis(["code_departement", "type_local"]).reset_index()
    data = data.merge(fallback_df, on=["code_departement", "type_local"], how="left")

    data["price_signal"] = data["price_signal"].fillna(data["dept_signal"])
    return data.drop(columns=["dept_signal"])


def main():
    print("Loading DVF data...")
    t0 = time.time()
    raw = load_years(TRAIN_YEARS)
    df_dept = pd.read_csv("data/departements-france.csv")
    print(f"  {len(raw):,} raw rows in {time.time() - t0:.1f}s")

    data = clean(raw, df_dept)
    print(f"  {len(data):,} rows after cleaning")

    train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

    print("Building commune price lookup (from training split only, to avoid leakage)...")
    lookup, dept_fallback = build_commune_lookup(train_data)

    train_data = attach_price_signal(train_data, lookup, dept_fallback).dropna(subset=["price_signal"])
    test_data = attach_price_signal(test_data, lookup, dept_fallback).dropna(subset=["price_signal"])

    feature_cols = ["type_local", "surface_reelle_bati", "nombre_pieces_principales", "annee_mutation", "price_signal"]
    X_train, y_train = train_data[feature_cols], np.log1p(train_data["valeur_fonciere"])
    X_test, y_test = test_data[feature_cols], np.log1p(test_data["valeur_fonciere"])

    preprocessor = ColumnTransformer([
        ("categorical", OneHotEncoder(handle_unknown="ignore"), ["type_local"]),
    ], remainder="passthrough")

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.08, max_depth=8, l2_regularization=1.0, random_state=42,
        )),
    ])

    print("Training model...")
    t1 = time.time()
    model.fit(X_train, y_train)
    print(f"  trained in {time.time() - t1:.1f}s")

    predictions = model.predict(X_test)
    r2 = r2_score(np.expm1(y_test), np.expm1(predictions))
    mae = mean_absolute_error(np.expm1(y_test), np.expm1(predictions))
    print(f"R2 (price space): {r2:.3f}")
    print(f"MAE (price space): {mae:,.0f}")

    communes = (
        data[["code_commune", "nom_commune", "code_departement", "nom_departement"]]
        .drop_duplicates("code_commune")
        .sort_values(["nom_departement", "nom_commune"])
        .reset_index(drop=True)
    )

    artifact = {
        "model": model,
        "commune_lookup": lookup,
        "dept_fallback": dept_fallback,
        "communes": communes,
        "train_years": TRAIN_YEARS,
        "r2": r2,
        "mae": mae,
    }
    joblib.dump(artifact, "model/price_model.joblib")
    print("Saved model/price_model.joblib")


if __name__ == "__main__":
    main()
