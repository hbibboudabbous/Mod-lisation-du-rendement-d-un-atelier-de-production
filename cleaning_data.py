import pandas as pd
import numpy as np
import unicodedata
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
from sklearn.preprocessing import MinMaxScaler

# Cleaning functions
def clean_string(s):
    return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('utf-8') if isinstance(s, str) else s

def clean_mat(val):
    if pd.isna(val): return ""
    if isinstance(val, float) and val.is_integer(): return str(int(val))
    return str(val).strip()

# Data loading and initial cleaning
def load_and_clean_data(file_path):
    if file_path.name.endswith('.csv'):
        df = pd.read_csv(file_path, encoding='ISO-8859-1', sep=';')
    elif file_path.name.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported format. Use .csv or .xlsx")
    
    print(f"Initial row count: {len(df)}")
    df["Opération"] = df["Opération"].apply(clean_string)
    df['Mat'] = df['Mat'].apply(clean_mat)
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    return df

def filter_critical_data(df):
    critical_columns = ['Date', 'Mat', 'Nom_Emp', 'Opération', 'Produit', 'Qte_Prod', 'Travail_en_minutes']
    for col in critical_columns:
        df = df[~df[col].isna()]
    return df
def identify_exclusive_operations(df):
    # Calcul des stats par opération/produit
    op_stats = df.groupby(['Opération', 'Produit']).agg(
        count=('Nom_Emp', 'count'),
        unique_employees=('Nom_Emp', 'nunique'),
        exclusive_employee=('Nom_Emp', lambda x: x.mode()[0])
    ).reset_index()
    
    # Récupérer le matricule correspondant à l'employé exclusif
    def get_mat(row):
        op, prod, emp = row['Opération'], row['Produit'], row['exclusive_employee']
        # Filtrer le DataFrame initial pour retrouver le matricule de cet employé
        mat = df[(df['Opération'] == op) & (df['Produit'] == prod) & (df['Nom_Emp'] == emp)]['Mat'].mode()
        return mat.iloc[0] if not mat.empty else None

    op_stats['exclusive_mat'] = op_stats.apply(get_mat, axis=1)

    # Filtrer pour les opérations avec un seul employé unique
    exclusive_ops = op_stats[op_stats['unique_employees'] == 1]

    # Créer la liste avec matricule (Mat)
    exclusive_list = [
        (row['Opération'], row['Produit'], row['exclusive_mat'])
        for _, row in exclusive_ops.iterrows()
    ]

    # Extraire toutes les lignes du DataFrame pour ces exclusives
    if not exclusive_list:
        return [], pd.DataFrame()

    conditions = [((df['Opération'] == op) & (df['Produit'] == prod)) for op, prod, _ in exclusive_list]
    combined_condition = conditions[0]
    for cond in conditions[1:]:
        combined_condition |= cond

    exclusive_data = df[combined_condition].copy()
    return exclusive_list, exclusive_data

def exclude_employees_based_on_exclusive_couples(df, exclusive_list, seuil_pointages=1):
    df_exclusives = df[df.apply(lambda row: (row['Mat'], row['Opération']) in exclusive_list, axis=1)].copy()

    # Nombre de pointages exclusifs par employé
    nb_pointages_exclusifs = df_exclusives.groupby('Mat').size().reset_index(name='nb_pointages_exclusifs')

    # Nombre total de pointages par employé
    nb_pointages_total = df.groupby('Mat').size().reset_index(name='nb_pointages_total')

    # Fusionner pour calculer les pourcentages
    stats = nb_pointages_total.merge(nb_pointages_exclusifs, on='Mat', how='left')
    stats['nb_pointages_exclusifs'] = stats['nb_pointages_exclusifs'].fillna(0)
    stats['pct_pointages_exclusifs'] = 100 * stats['nb_pointages_exclusifs'] / stats['nb_pointages_total']

    # Ajouter au DataFrame original
    df = df.merge(stats[['Mat', 'nb_pointages_exclusifs', 'pct_pointages_exclusifs']], on='Mat', how='left')
    df[['nb_pointages_exclusifs', 'pct_pointages_exclusifs']] = df[['nb_pointages_exclusifs', 'pct_pointages_exclusifs']].fillna(0)

    return df, df_exclusives


def filter_by_presence_days(df, seuil_jours=3):
    """
    Supprime les employés ayant moins de `seuil_jours` de présence distincts dans la colonne Date.
    """
    # Compter le nombre de jours de présence uniques
    presence_counts = df.groupby('Mat')['Date'].nunique().reset_index()
    presence_counts.columns = ['Mat', 'jours_presence']

    # Garder ceux qui ont >= seuil_jours
    mats_valides = presence_counts[presence_counts['jours_presence'] >= seuil_jours]['Mat']

    # Garder les données de ces employés
    df_filtered = df[df['Mat'].isin(mats_valides)].copy()
    df_exclus = df[~df['Mat'].isin(mats_valides)].copy()

    return df_filtered, df_exclus
