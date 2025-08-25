import pandas as pd
import os
import matplotlib.pyplot as plt

def generate_scores_between_dates(df, start_date, end_date, output_dir):
    # Conversion des dates en datetime
    df['Date'] = pd.to_datetime(df['Date'])

    # Filtrage entre les deux dates
    mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
    df_filtered = df[mask].copy()

    if df_filtered.empty:
        print("Aucune donnée dans cet intervalle de dates.")
        return

    # Nettoyage des colonnes
    df_filtered['Mat'] = df_filtered['Mat'].astype(str).str.strip().str.upper()
    df_filtered['Nom_Emp'] = df_filtered['Nom_Emp'].astype(str).str.strip().str.title()

    # Colonnes d'origine attendues
    original_score_cols = [
        'score_duree_annuel',
        'score_production_annuel',
        'score_global_annuel'
    ]

    # Noms renommés pour la période
    renamed_score_cols = {
        'score_duree_annuel': 'score_duree_periode',
        'score_production_annuel': 'score_production_periode',
        'score_global_annuel': 'score_global_periode'
    }

    # Vérification des colonnes manquantes
    missing_cols = [col for col in original_score_cols if col not in df_filtered.columns]
    if missing_cols:
        print(f"⚠️ Colonnes manquantes : {missing_cols}")
        return

    # Remplissage des NaN
    df_filtered[original_score_cols] = df_filtered[original_score_cols].fillna(0)

    # Moyenne par employé
    df_scores = df_filtered.groupby(['Mat', 'Nom_Emp'])[original_score_cols].mean().reset_index()

    # Renommage des colonnes
    df_scores.rename(columns=renamed_score_cols, inplace=True)

    # Tri par score global
    df_scores = df_scores.sort_values(by='score_global_periode', ascending=False)

    # Nom dynamique du fichier
    start_str = pd.to_datetime(start_date).strftime('%Y-%m-%d')
    end_str = pd.to_datetime(end_date).strftime('%Y-%m-%d')
    output_filename = f"scores_{start_str}_to_{end_str}.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # Export Excel
    df_scores.to_excel(output_path, index=False)
    print(f"✅ Export réussi : {output_path}")

import matplotlib.pyplot as plt
import pandas as pd

def plot_employee_scores_daily(df, matricule, date_debut, date_fin):
    # Filtrer par matricule et période
    mask = (df['Mat'] == matricule) & (df['Date'] >= date_debut) & (df['Date'] <= date_fin)
    df_emp = df.loc[mask].copy()
    
    if df_emp.empty:
        print(f"Aucune donnée trouvée pour l'employé {matricule} entre {date_debut} et {date_fin}.")
        return None
    
    # S'assurer que 'Date' est datetime
    df_emp['Date'] = pd.to_datetime(df_emp['Date'])
    
    # Regrouper par date pour calculer la moyenne journalière des scores
    df_daily = df_emp.groupby('Date').agg({
        'score_duree': 'mean',
        'score_production_journalier': 'mean',
        'score_global_journalier': 'mean'
    }).reset_index()
    
    # Créer une figure et des axes
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

    # Retourner la figure pour Streamlit
    return fig



import pandas as pd
import altair as alt

def calculer_rendement_usine(df, date_debut, date_fin, w_d=0.3, w_p=0.5, w_g=0.2):
    """
    Calcule et trace le rendement global de l'usine sur une période donnée.
    Retourne un graphique Altair interactif pour Streamlit.
    """
    # Vérification des poids
    assert abs(w_d + w_p + w_g - 1.0) < 1e-6, "Les poids doivent avoir une somme de 1."

    # Conversion de la colonne Date
    df['Date'] = pd.to_datetime(df['Date'])

    # Filtrage par période
    mask = (df['Date'] >= pd.to_datetime(date_debut)) & (df['Date'] <= pd.to_datetime(date_fin))
    df_filtered = df.loc[mask].copy()

    if df_filtered.empty:
        return None

    # Calcul du score combiné
    df_filtered['score_combine'] = (
        w_d * df_filtered['score_duree'] +
        w_p * df_filtered['score_production_journalier'] +
        w_g * df_filtered['score_global_journalier']
    )

    # Moyenne quotidienne
    rendement_journalier = df_filtered.groupby('Date')['score_combine'].mean().reset_index()

    # Graphique Altair
    chart = alt.Chart(rendement_journalier).mark_line(point=True).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('score_combine:Q', title='Score global moyen'),
        tooltip=['Date:T', 'score_combine:Q']
    ).properties(
        title=f"Rendement global de l'usine ({date_debut} → {date_fin})",
        width=800,
        height=400
    ).interactive()  # permet zoom/hover

    return chart
