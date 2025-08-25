import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

def calculate_global_scores(df, alpha=0.4, min_working_days=3):
    """
    Calcule les scores globaux de performance à partir d'un DataFrame d'activité,
    avec détection des fraudes basée sur des seuils min et max pour Qte/h.

    Args:
        df (pd.DataFrame): Données d'activité avec colonnes attendues.
        alpha (float): Coefficient pour pondérer les scores (non utilisé ici).
        min_working_days (int): Nombre minimum de jours travaillés (non utilisé ici).

    Returns:
        pd.DataFrame: DataFrame enrichi avec les scores calculés et indicateur de fraude.
    """

    # -----------------------------
    # 1. Ajouter Mois et Année
    # -----------------------------
    df['Mois'] = df['Date'].dt.month
    df['Année'] = df['Date'].dt.year

    # a. Temps de travail par jour
    travail_par_jour = df.groupby(['Mat', 'Date'])['Travail_en_minutes'].sum().reset_index()

    # b. Nombre de couples Opération/Produit par jour
    nb_operations = df.groupby(['Mat', 'Date']).apply(
        lambda x: x[['Opération', 'Produit']].drop_duplicates().shape[0]
    ).reset_index(name='nb_op_produit')

    # c. Fusion
    daily_duration = travail_par_jour.merge(nb_operations, on=['Mat', 'Date'])
    daily_duration['Duree_totale_jour'] = daily_duration['Travail_en_minutes'] + 60 * daily_duration['nb_op_produit']
    df = df.merge(daily_duration[['Mat', 'Date', 'Duree_totale_jour']], on=['Mat', 'Date'], how='left')

    # -----------------------------
    # 2. Durée mensuelle
    # -----------------------------
    monthly_duration = df.groupby(['Mat', 'Année', 'Mois']).agg(
        mean_duration=('Duree_totale_jour', 'mean')
    ).reset_index()
    monthly_duration['score_duree_mensuel'] = monthly_duration.groupby(['Année', 'Mois'])['mean_duration'].transform(
        lambda x: MinMaxScaler((0, 100)).fit_transform(x.fillna(0).values.reshape(-1, 1)).flatten()
    )
    df = df.merge(monthly_duration, on=['Mat', 'Année', 'Mois'], how='left')

    # -----------------------------
    # 3. Durée annuelle
    # -----------------------------
    annual_duration = df.groupby(['Mat', 'Année']).agg(
        mean_duration=('Duree_totale_jour', 'mean')
    ).reset_index()
    annual_duration['score_duree_annuel'] = annual_duration.groupby('Année')['mean_duration'].transform(
        lambda x: MinMaxScaler((0, 100)).fit_transform(x.fillna(0).values.reshape(-1, 1)).flatten()
    )
    df = df.merge(annual_duration[['Mat', 'Année', 'score_duree_annuel']], on=['Mat', 'Année'], how='left')

    # -----------------------------
    # 4. Nettoyage
    # -----------------------------
    df = df[df['Travail_en_minutes'] > 0].copy()

    # -----------------------------
    # 5. Qte/h
    # -----------------------------
    df['Qte/h'] = np.where(
        (df['Travail_en_minutes'] + 60) > 0,
        (df['Qte_Prod'] * 60) / (df['Travail_en_minutes'] + 60),
        np.nan
    )

    # -----------------------------
    # 6. Exclusivité
    # -----------------------------
    couple_counts = df.groupby(['Opération', 'Produit'])['Mat'].nunique().reset_index(name='nb_employes')
    df = df.merge(couple_counts, on=['Opération', 'Produit'], how='left')
    df['exclusif'] = df['nb_employes'] == 1

    # -----------------------------
    # 7. Seuils de performance
    # -----------------------------
    group_stats = df.groupby(['Opération', 'Produit']).agg(
        count=('Qte/h', 'size'),
        mean=('Qte/h', 'mean'),
        std=('Qte/h', 'std')
    ).reset_index()
    group_stats['cv'] = group_stats['std'] / group_stats['mean'].replace(0, np.nan)
    group_stats['Seuil_bon_rendement'] = group_stats.apply(
        lambda row: np.nan if pd.isna(row['mean']) or row['mean'] == 0 else
        row['mean'] * 1.8 if row['count'] < 10 else
        row['mean'] * 1.3 if row['cv'] > 0.4 else
        row['mean'] * 1.1,
        axis=1
    )
    df = df.merge(group_stats[['Opération', 'Produit', 'Seuil_bon_rendement']], on=['Opération', 'Produit'], how='left')

    # -----------------------------
    # 8. Seuils pour exclusifs (p90)
    # -----------------------------
    exclusifs_couples = couple_counts[couple_counts['nb_employes'] == 1][['Opération', 'Produit']]
    df_exclusifs = df.merge(exclusifs_couples, on=['Opération', 'Produit'], how='inner')
    p90_table = df_exclusifs.groupby(['Opération', 'Produit'])['Qte/h'].quantile(0.90).reset_index()
    p90_table.rename(columns={'Qte/h': 'Seuil_p90'}, inplace=True)
    df = df.merge(p90_table, on=['Opération', 'Produit'], how='left')

    # -----------------------------
    # 9. Seuil final
    # -----------------------------
    df['Seuil_utilise'] = df.apply(
        lambda row: row['Seuil_p90'] if row['exclusif'] and not pd.isna(row['Seuil_p90']) else row['Seuil_bon_rendement'],
        axis=1
    )

    # -----------------------------
    # 10. Détection de fraude (seuil min / max)
    # -----------------------------
    seuils_fraude = df.groupby(['Opération', 'Produit'])['Qte/h'].agg(
        q10=lambda x: x.quantile(0.10),
        q90=lambda x: x.quantile(0.90)
    ).reset_index()
    seuils_fraude['Seuil_min'] = seuils_fraude['q10'] * 0.5  # tolérance bas
    seuils_fraude['Seuil_max'] = seuils_fraude['q90'] * 1.5  # tolérance haut

    df = df.merge(seuils_fraude[['Opération', 'Produit', 'Seuil_min', 'Seuil_max']],
                  on=['Opération', 'Produit'], how='left')

    # Flag fraude
    df['fraude'] = (df['Qte/h'] < df['Seuil_min']) | (df['Qte/h'] > df['Seuil_max'])

    # -----------------------------
    # 11. Score de production journalier
    # -----------------------------
    df['score_production_journalier'] = ((df['Qte/h'] / df['Seuil_utilise']) * 100).clip(upper=100)

    # -----------------------------
    # 12. Score de durée journalier
    # -----------------------------
    normalized_durations = daily_duration.copy()
    normalized_durations['score_duree'] = normalized_durations.groupby('Date')['Duree_totale_jour'].transform(
        lambda x: MinMaxScaler((0, 100)).fit_transform(x.values.reshape(-1, 1)).flatten()
    )
    df = df.merge(normalized_durations[['Mat', 'Date', 'score_duree']], on=['Mat', 'Date'], how='left')

    # -----------------------------
    # 13. Scores mensuels et annuels (production)
    # -----------------------------
    df['score_production_mensuel'] = df.groupby(['Mat', 'Année', 'Mois'])['score_production_journalier'].transform('mean').clip(upper=100)
    df['score_production_annuel'] = df.groupby(['Mat', 'Année'])['score_production_journalier'].transform('mean').clip(upper=100)

    # -----------------------------
    # 14. Scores globaux
    # -----------------------------
    df['score_global_journalier'] = (0.7 * df['score_production_journalier'] + 0.3 * df['score_duree']).clip(upper=100)
    df['score_global_mensuel'] = (0.7 * df['score_production_mensuel'] + 0.3 * df['score_duree_mensuel']).clip(upper=100)
    df['score_global_annuel'] = (0.7 * df['score_production_annuel'] + 0.3 * df['score_duree_annuel']).clip(upper=100)

    return df
