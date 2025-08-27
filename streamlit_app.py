import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os

st.set_page_config(layout="wide")

# --- CONFIGURATION DES CHEMINS D'ACCÈS ---
# Assurez-vous que ces chemins pointent vers les fichiers de sortie de votre script de monitoring
PATH_TO_MONITORING_FILE = 'monitoring_info.csv'
PATH_TO_INVEST_FILE = 'current_invest.csv'
# -----------------------------------------

# --- INTERFACE UTILISATEUR ---
st.title("📈 Dashboard de Monitoring")
min_date = st.selectbox(
    'Sélectionner la période d\'affichage',
    ['6h', '12h', '1 day', '2 days', '1 week', '2 weeks', '1 month', 'all'],
    index=4 # '1 week' par défaut
)
d = {'6h': 6, '12h': 12, '1 day': 24, '2 days': 48, '1 week': 7*24, '2 weeks': 14*24, '1 month': 30*24, 'all': int(1e6)}
nb_hours = d[min_date]

# --- CHARGEMENT ET PRÉPARATION DES DONNÉES ---

# Vérifier si les fichiers de données existent
if not os.path.exists(PATH_TO_MONITORING_FILE) or not os.path.exists(PATH_TO_INVEST_FILE):
    st.error(f"Fichiers de données introuvables. Assurez-vous que '{PATH_TO_MONITORING_FILE}' et '{PATH_TO_INVEST_FILE}' existent.")
    st.stop()

# Chargement des données de monitoring
try:
    df_monitoring = pd.read_csv(PATH_TO_MONITORING_FILE)
    df_invest = pd.read_csv(PATH_TO_INVEST_FILE)
except Exception as e:
    st.error(f"Erreur lors de la lecture des fichiers CSV : {e}")
    st.stop()

# Nettoyage et conversion des types
df_monitoring['timestamp'] = pd.to_datetime(df_monitoring['timestamp'])
for col in df_monitoring.columns:
    if col != 'timestamp':
        df_monitoring[col] = pd.to_numeric(df_monitoring[col], errors='coerce')

for col in ['usdc_borrowed', 'usdc_invested', 'pending_profit']:
    if col in df_invest.columns:
        df_invest[col] = pd.to_numeric(df_invest[col], errors='coerce')

# Filtrage temporel
df_monitoring = df_monitoring[df_monitoring.timestamp > df_monitoring.timestamp.max() - pd.Timedelta(hours=nb_hours)].copy()

if df_monitoring.empty:
    st.warning("Aucune donnée disponible pour la période sélectionnée.")
    st.stop()

# Normalisation du gain théorique
df_monitoring['gain_theoretical'] = df_monitoring['gain_theoretical'] - df_monitoring['gain_theoretical'].iloc[0]


# --- CALCUL DES MÉTRIQUES ---

# Dernier point de données
last_row = df_monitoring.iloc[-1]

# Gestion des colonnes optionnelles (présentes uniquement en mode MARGIN/SHORT)
usdc_borrowed = last_row.get('usdc_borrowed', 0)
interest_fees_usdc = df_monitoring['interest_fees_usdc'].sum() if 'interest_fees_usdc' in df_monitoring.columns else 0

# Métriques principales
tot_usdc = last_row['tot_usdc']
tot_usdc_initial = df_monitoring['tot_usdc'].iloc[0]
gain_total = tot_usdc - tot_usdc_initial
gain_theoretical = last_row['gain_theoretical']
pending_profit = last_row['pending_profit']
usdc_invested = last_row['usdc_invested']
accuracy = last_row.get('accuracy', 1.0) # Fournir une valeur par défaut
tax = last_row.get('tax', 0.0)
total_fees_usdc = df_monitoring['total_fees_usdc'].sum()
transac_fees_usdc = total_fees_usdc - interest_fees_usdc

# Métriques de risque
usdc_threshold = last_row['usdc_threshold']
max_usdc_seen = df_monitoring['tot_usdc'].max()
remaining = tot_usdc - usdc_threshold
if (max_usdc_seen - usdc_threshold) > 0:
    risk_ratio = (tot_usdc - usdc_threshold) / (max_usdc_seen - usdc_threshold)
else:
    risk_ratio = 1

# Métriques temporelles
last_update_time = pd.to_datetime(last_row['timestamp'])
now_utc = pd.to_datetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
time_delta_minutes = (now_utc - last_update_time).total_seconds() / 60

# --- AFFICHAGE DES INDICATEURS CLÉS (KPIs) ---

col1, col2, col3 = st.columns(3)

# Colonne 1: Statut et Balance
with col1:
    st.subheader("Statut & Balance")
    color_dt = 'green' if time_delta_minutes < 15 else 'red'
    st.markdown(f"**Dernière MàJ :** <font color='{color_dt}'>{last_update_time.strftime('%Y-%m-%d %H:%M:%S')}</font>", unsafe_allow_html=True)
    st.metric("Balance Totale", f"{tot_usdc:,.2f} $", f"{gain_total:,.2f} $ ({((tot_usdc/tot_usdc_initial) - 1):.2%})")

# Colonne 2: Performance
with col2:
    st.subheader("Performance")
    st.metric("Gain Théorique", f"{gain_theoretical:,.2f} $")
    st.metric("Profit en attente", f"{pending_profit:,.2f} $")

# Colonne 3: Position et Risque
with col3:
    st.subheader("Position & Risque")
    st.metric("Total Investi", f"{usdc_invested:,.0f} $")
    # Affichage conditionnel de l'emprunt
    if 'usdc_borrowed' in last_row and last_row['usdc_borrowed'] > 0:
        st.metric("Total Emprunté", f"{usdc_borrowed:,.0f} $")
    
    color_remaining = 'green' if risk_ratio > 0.66 else 'orange' if risk_ratio > 0.33 else 'red'
    st.markdown(f"**Marge restante :** <font color='{color_remaining}'>{remaining:,.0f} $</font>", unsafe_allow_html=True)


# --- GRAPHIQUES ---
st.divider()
fig_col1, fig_col2 = st.columns(2)

with fig_col1:
    # Figure 1: Evolution des Gains
    st.subheader("Évolution des Gains")
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(df_monitoring['timestamp'], df_monitoring['gain_theoretical'], label=f'Gain Théorique ({gain_theoretical:,.0f}$)')
    ax1.plot(df_monitoring['timestamp'], df_monitoring['tot_usdc'] - tot_usdc_initial, label=f'Gain Réel (Balance, {gain_total:,.0f}$)')
    ax1.set_ylabel('Gain ($)')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    ax1.tick_params(axis='x', labelrotation=45)
    fig1.tight_layout()
    st.pyplot(fig1)

    # Figure: Evolution des Investissements
    st.subheader("Évolution des Investissements")
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(df_monitoring['timestamp'], df_monitoring['usdc_invested'], label=f'Investi ({usdc_invested:,.0f}$)', color='royalblue')
    # Affichage conditionnel de l'emprunt
    if 'usdc_borrowed' in df_monitoring.columns:
        ax2.plot(df_monitoring['timestamp'], df_monitoring['usdc_borrowed'], label=f'Emprunté ({usdc_borrowed:,.0f}$)', color='grey')
    ax2.set_ylabel('Montant ($)')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
    ax2.tick_params(axis='x', labelrotation=45)
    fig2.tight_layout()
    st.pyplot(fig2)


with fig_col2:
    # Figure 3: Répartition par Actif
    st.subheader("Répartition par Actif")
    # Préparation des données pour le bar chart
    df_plot_invest = df_invest.set_index('asset')
    cols_to_plot = ['usdc_invested']
    colors = ['royalblue']
    if 'usdc_borrowed' in df_plot_invest.columns:
        cols_to_plot.append('usdc_borrowed')
        colors.append('grey')

    fig3, ax3 = plt.subplots(figsize=(8, 4))
    df_plot_invest[cols_to_plot].plot.bar(ax=ax3, stacked=False, color=colors)
    
    # Ajout du profit/perte en attente par-dessus
    if 'pending_profit' in df_plot_invest.columns:
        df_plot_invest[df_plot_invest['pending_profit'] >= 0]['pending_profit'].plot.bar(ax=ax3, color='green', label='Profit en attente')
        df_plot_invest[df_plot_invest['pending_profit'] < 0]['pending_profit'].plot.bar(ax=ax3, color='red', label='Perte en attente')

    ax3.set_ylabel('Montant ($)')
    ax3.grid(True, axis='y', linestyle='--', alpha=0.6)
    ax3.legend()
    fig3.tight_layout()
    st.pyplot(fig3)

    # Figure 4: Performance vs Marché
    st.subheader("Performance vs Marché")
    df_monitoring['btc_change'] = 100 * (df_monitoring['price_btc'] / df_monitoring['price_btc'].iloc[0] - 1)
    df_monitoring['real_profit_pct'] = 100 * (df_monitoring['tot_usdc'] / tot_usdc_initial - 1)
    
    fig4, ax4 = plt.subplots(figsize=(8, 4))
    ax4.plot(df_monitoring['timestamp'], df_monitoring['btc_change'], label=f"BTC ({df_monitoring['btc_change'].iloc[-1]:.2f}%)", color='orange')
    ax4.plot(df_monitoring['timestamp'], df_monitoring['real_profit_pct'], label=f"Profit Réel ({df_monitoring['real_profit_pct'].iloc[-1]:.2f}%)", color='red')
    ax4.set_ylabel('Variation (%)')
    ax4.grid(True, linestyle='--', alpha=0.6)
    ax4.legend()
    ax4.tick_params(axis='x', labelrotation=45)
    fig4.tight_layout()
    st.pyplot(fig4)


# Affichage conditionnel des graphiques de frais
if 'interest_fees_usdc' in df_monitoring.columns:
    st.divider()
    st.subheader("Analyse des Frais (Mode MARGIN)")
    fig6, ax6 = plt.subplots(figsize=(8, 4))
    ax6.plot(df_monitoring['timestamp'], df_monitoring['total_fees_usdc'].cumsum(), label=f'Frais Totaux ({total_fees_usdc:.2f}$)')
    ax6.plot(df_monitoring['timestamp'], df_monitoring['interest_fees_usdc'].cumsum(), label=f'Frais d\'Intérêt ({interest_fees_usdc:.2f}$)')
    ax6.plot(df_monitoring['timestamp'], (df_monitoring['total_fees_usdc']-df_monitoring['interest_fees_usdc']).cumsum(), label=f'Frais de Transaction ({transac_fees_usdc:.2f}$)')
    ax6.set_ylabel('Frais Cumulés ($)')
    ax6.grid(True, linestyle='--', alpha=0.6)
    ax6.legend()
    ax6.tick_params(axis='x', labelrotation=45)
    fig6.tight_layout()
    st.pyplot(fig6)