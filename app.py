import streamlit as st
import pandas as pd
import io
import os
import altair as alt
from pathlib import Path

# Import de tes fonctions
from cleaning_data import (
    load_and_clean_data,
    filter_critical_data,
    identify_exclusive_operations,
    exclude_employees_based_on_exclusive_couples,
    filter_by_presence_days
)
from calcul import calculate_global_scores
from functions import (
    generate_scores_between_dates,
    plot_employee_scores_daily,
    calculer_rendement_usine
)

# --- Config ---
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
st.set_page_config(page_title="SOPEM Performance", layout="wide", page_icon="📈")

# --- Sidebar navigation ---
st.sidebar.title("Navigation")
pages = [
    "1️⃣ Import & Période",
    "2️⃣ Evolution scores employés",
    "3️⃣ Rendement usine",
    "4️⃣ Recherche employé"
]
page = st.sidebar.radio("Aller à :", pages)

# --- Mise en cache du traitement du fichier ---
@st.cache_data
def process_file(uploaded_file):
    df = load_and_clean_data(uploaded_file)
    df = filter_critical_data(df)
    exclusive_list, _ = identify_exclusive_operations(df)
    df, _ = exclude_employees_based_on_exclusive_couples(df, exclusive_list)
    df, _ = filter_by_presence_days(df)
    return calculate_global_scores(df)

# --- Vérification colonnes obligatoires ---
def validate_dataframe(df):
    required_cols = {"Mat", "Date", "score_global_journalier"}
    if not required_cols.issubset(df.columns):
        st.error(f"Le fichier doit contenir les colonnes : {required_cols}")
        st.stop()

# --------------------- PAGE 1 : Import & Période ---------------------
if page == pages[0]:
    st.title("📂 Importer un fichier & choisir la période")
    uploaded_file = st.file_uploader("Choisissez un fichier (.csv ou .xlsx)", type=["csv", "xlsx"])

    if uploaded_file:
        with st.spinner("Traitement du fichier..."):
            df = process_file(uploaded_file)
            validate_dataframe(df)
            st.session_state.df = df

        st.success(f"✅ {df['Mat'].nunique()} employés retenus après filtrage")
        st.dataframe(df.head(20), use_container_width=True)

        # --- Sélection période ---
        st.markdown("---")
        st.subheader("📅 Sélection de la période d'étude")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date début", pd.to_datetime("2024-01-01"))
        with col2:
            end_date = st.date_input("Date fin", pd.to_datetime("2024-12-31"))

        st.session_state.start_date = start_date
        st.session_state.end_date = end_date

        # --- Génération du fichier des scores entre dates ---
        if st.button("📤 Générer le fichier Excel des scores"):
            output_buffer = io.BytesIO()
            generate_scores_between_dates(df, start_date, end_date, output_buffer)
            output_buffer.seek(0)
            st.download_button(
                label="⬇️ Télécharger le fichier des scores",
                data=output_buffer,
                file_name="scores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- Téléchargement du DataFrame complet ---
        st.markdown("---")
        st.subheader("💾 Télécharger le DataFrame complet")
        output_df_buffer = io.BytesIO()
        with pd.ExcelWriter(output_df_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Data_Complet")
        output_df_buffer.seek(0)

        st.download_button(
            label="⬇️ Télécharger le DataFrame complet",
            data=output_df_buffer,
            file_name="df_complet.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("Veuillez charger un fichier pour commencer.")

# --------------------- PAGE 2 : Evolution scores employés ---------------------
elif page == pages[1]:
    st.title("📈 Evolution du score global des employés")

    if "df" in st.session_state:
        df = st.session_state.df
        start_date, end_date = st.session_state.start_date, st.session_state.end_date
        st.info(f"Période sélectionnée : {start_date} → {end_date}")

        mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
        df_periode = df.loc[mask]

        scores_moyens = df_periode.groupby('Mat')['score_global_journalier'].mean().reset_index()
        scores_moyens = scores_moyens.sort_values(by='score_global_journalier', ascending=False)
        st.dataframe(scores_moyens, use_container_width=True)

        top10 = scores_moyens.head(10)['Mat'].tolist()
        selected_mats = st.multiselect("👥 Sélectionner employés à afficher", scores_moyens['Mat'].tolist(), top10)

        if selected_mats:
            chart = alt.Chart(df_periode[df_periode['Mat'].isin(selected_mats)]).mark_line().encode(
                x='Date:T',
                y='score_global_journalier:Q',
                color='Mat:N',
                tooltip=['Mat', 'Date', 'score_global_journalier']
            ).properties(width=800, height=400)
            st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Veuillez d'abord importer un fichier et choisir une période dans la page 1.")

# --------------------- PAGE 3 : Rendement usine ---------------------
elif page == pages[2]:
    st.title("🏭 Rendement global de l'usine")

    if "df" in st.session_state:
        df = st.session_state.df
        start_date, end_date = st.session_state.start_date, st.session_state.end_date
        st.info(f"Période sélectionnée : {start_date} → {end_date}")

        chart = calculer_rendement_usine(df, pd.to_datetime(start_date), pd.to_datetime(end_date))
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("⚠️ Aucun rendement trouvé sur cette période.")
    else:
        st.warning("Veuillez d'abord importer un fichier et choisir une période dans la page 1.")

# --------------------- PAGE 4 : Recherche employé ---------------------
elif page == pages[3]:
    st.title("🔎 Recherche d'un employé")

    if "df" in st.session_state:
        df = st.session_state.df
        start_date, end_date = st.session_state.start_date, st.session_state.end_date
        st.info(f"Période sélectionnée : {start_date} → {end_date}")

        matricule = st.text_input("Entrer le matricule employé")
        if matricule:
            fig = plot_employee_scores_daily(df, matricule, pd.to_datetime(start_date), pd.to_datetime(end_date))
            if fig:
                st.pyplot(fig)
            else:
                st.warning("Aucune donnée pour ce matricule sur la période.")

            st.markdown("#### Tâches effectuées par cet employé sur la période")
            mask = (df['Mat'] == matricule) & (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
            df_emp = df.loc[mask]
            if not df_emp.empty:
                st.dataframe(df_emp[['Date', 'Opération', 'Produit', 'Qte_Prod', 'Travail_en_minutes']], use_container_width=True)
            else:
                st.info("Aucune tâche trouvée pour cet employé sur la période.")
    else:
        st.warning("Veuillez d'abord importer un fichier et choisir une période dans la page 1.")
