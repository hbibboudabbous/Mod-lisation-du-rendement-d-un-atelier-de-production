import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from cleaning_data import (
    load_and_clean_data,
    filter_critical_data,
    identify_exclusive_operations,
    exclude_employees_based_on_exclusive_couples,
    filter_by_presence_days
)
from calcul import calculate_global_scores
from functions import generate_scores_between_dates

OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def process_dataframe(df, output_dir, seuil_pointages=1, seuil_jours=3):
    os.makedirs(output_dir, exist_ok=True)

    st.write(f"👥 Après nettoyage : {df['Mat'].nunique()} employés")
    
    df = filter_critical_data(df)
    st.write(f"🔍 Après filtrage critique : {df['Mat'].nunique()} employés")

    exclusive_list, exclusive_data = identify_exclusive_operations(df)
    st.write(f"⚠️ Nombre opérations exclusives : {len(exclusive_list)}")

    df, df_exclus = exclude_employees_based_on_exclusive_couples(df, exclusive_list, seuil_pointages)
    st.write(f"🚫 Après exclusion employés exclusives : {df['Mat'].nunique()} employés")

    df, df_absents = filter_by_presence_days(df, seuil_jours)
    st.write(f"📉 Après filtrage par jours de présence : {df['Mat'].nunique()} employés")

    df['Mois'] = df['Date'].dt.month
    df['Année'] = df['Date'].dt.year

    df = calculate_global_scores(df)

    df.to_excel(os.path.join(output_dir, "filtredwithscores.xlsx"), index=False)

    start_date = "2024-01-01"
    end_date = "2024-12-31"
    generate_scores_between_dates(df, start_date, end_date, output_dir)

    return df


def plot_employee_scores_daily(df, matricule, date_debut, date_fin):
    mask = (df['Mat'] == matricule) & (df['Date'] >= pd.to_datetime(date_debut)) & (df['Date'] <= pd.to_datetime(date_fin))
    df_emp = df.loc[mask].copy()
    
    if df_emp.empty:
        st.warning(f"Aucune donnée trouvée pour l'employé {matricule} entre {date_debut} et {date_fin}.")
        return None
    
    df_emp['Date'] = pd.to_datetime(df_emp['Date'])
    df_daily = df_emp.groupby('Date').agg({
        'score_duree': 'mean',
        'score_production_journalier': 'mean',
        'score_global_journalier': 'mean'
    }).reset_index()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df_daily['Date'], df_daily['score_duree'], label='Score Durée Journalier', marker='o', color='red')
    ax.plot(df_daily['Date'], df_daily['score_production_journalier'], label='Score Production Journalier', marker='o', color='green')
    ax.plot(df_daily['Date'], df_daily['score_global_journalier'], label='Score Global Journalier', marker='o', color='blue')

    ax.set_title(f"Scores journaliers pour l'employé {matricule}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    
    return fig


# ---------------------------
# Interface Streamlit
# ---------------------------
# ---------------------------
# Interface Streamlit
# ---------------------------
st.title("📊 Analyse des employés")

# Uploader un fichier
uploaded_file = st.file_uploader("Uploader un fichier Excel ou CSV", type=["xlsx", "csv"])

# Paramètres
seuil_pointages = st.slider("Seuil pointages", min_value=1, max_value=10, value=1)
seuil_jours = st.slider("Seuil jours de présence", min_value=1, max_value=30, value=3)

if uploaded_file is not None:
    # Lire le fichier correctement
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type == "csv":
        df = pd.read_csv(uploaded_file, parse_dates=["Date"])
    else:
        df = pd.read_excel(uploaded_file, parse_dates=["Date"])

    # Traitement
    df_result = process_dataframe(df, OUTPUT_FOLDER, seuil_pointages, seuil_jours)
    st.success(f"✅ Traitement terminé - {df_result['Mat'].nunique()} employés retenus")

    # Aperçu
    st.subheader("Aperçu des données traitées")
    st.dataframe(df_result.head(10))

    # Sélection de la période
    date_debut = st.date_input("Date début", pd.to_datetime("2024-01-01"))
    date_fin = st.date_input("Date fin", pd.to_datetime("2024-06-30"))

    # Filtrer la période
    mask = (df_result['Date'] >= pd.to_datetime(date_debut)) & (df_result['Date'] <= pd.to_datetime(date_fin))
    df_periode = df_result.loc[mask]

    # Calculer le score moyen global par employé
    scores_moyens = df_periode.groupby('Mat')['score_global_journalier'].mean().reset_index()

    # Identifier 5 meilleurs et 5 moins performants
    top5 = scores_moyens.nlargest(5, 'score_global_journalier')['Mat'].tolist()
    bottom5 = scores_moyens.nsmallest(5, 'score_global_journalier')['Mat'].tolist()

    st.subheader("📈 Meilleurs et 📉 Moins performants")

    # Afficher les graphiques
    for mat in top5 + bottom5:
        st.write(f"**Employé {mat}**")
        fig = plot_employee_scores_daily(df_result, mat, str(date_debut), str(date_fin))
        if fig:
            st.pyplot(fig)
