import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os

# Configuration de la page pour un layout plus adapté au mobile
st.set_page_config(
    page_title="Cryptoune Dashboard",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# --- INTERFACE UTILISATEUR ---
st.title("📈 Dashboard de Monitoring")
min_date = st.selectbox(
    'Période',
    ['6h', '12h', '1 day', '2 days', '1 week', '2 weeks', '1 month', 'all'],
    index=4 # '1 week' par défaut
)
d = {'6h': 6, '12h': 12, '1 day': 24, '2 days': 48, '1 week': 7*24, '2 weeks': 14*24, '1 month': 30*24, 'all': int(1e6)}
nb_hours = d[min_date]

# --- CHARGEMENT ET PRÉPARATION DES DONNÉES ---
@st.cache_data(ttl=60) # Mise en cache des données pour 1 minute
def load_data():
    try:
        df_mon=pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vSTqIh7BXEaPKj1fukalCyUZE7eydHKVRmtxKy5OuT0mhvUcAnAlpbB8odqbzcv9TT84H-DrxZw-U0v/pub?output=xlsx') 
        df_inv=pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vSTqIh7BXEaPKj1fukalCyUZE7eydHKVRmtxKy5OuT0mhvUcAnAlpbB8odqbzcv9TT84H-DrxZw-U0v/pub?output=xlsx',sheet_name='current_invest') 
        
        # Nettoyage et conversion des types
        df_mon['timestamp'] = pd.to_datetime(df_mon['timestamp'])
        for col in df_mon.columns:
            if col != 'timestamp':
                df_mon[col] = pd.to_numeric(df_mon[col], errors='coerce')
        for col in ['usdc_borrowed', 'usdc_invested', 'pending_profit']:
            if col in df_inv.columns:
                df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce')
        return df_mon, df_inv
    except Exception:
        return None, None

df_monitoring_full, df_invest = load_data()

if df_monitoring_full is None:
    st.error(f"Fichiers de données introuvables ou corrompus. Vérifiez '{PATH_TO_MONITORING_FILE}' et '{PATH_TO_INVEST_FILE}'.")
    st.stop()

# Filtrage temporel
df_monitoring = df_monitoring_full[df_monitoring_full.timestamp > df_monitoring_full.timestamp.max() - pd.Timedelta(hours=nb_hours)].copy()

if df_monitoring.empty:
    st.warning("Aucune donnée disponible pour la période sélectionnée.")
    st.stop()

# Normalisation du gain
df_monitoring['gain_theoretical'] = df_monitoring['gain_theoretical'] - df_monitoring['gain_theoretical'].iloc[0]

# --- CALCUL DES MÉTRIQUES ---
last_row = df_monitoring.iloc[-1]
tot_usdc = last_row['tot_usdc']
tot_usdc_initial = df_monitoring['tot_usdc'].iloc[0]
gain_total = tot_usdc - tot_usdc_initial
usdc_invested = last_row['usdc_invested']
pending_profit = last_row['pending_profit']
usdc_borrowed = last_row.get('usdc_borrowed', 0)
last_update_time = pd.to_datetime(last_row['timestamp'])
now_utc = pd.to_datetime(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
time_delta_minutes = (now_utc - last_update_time).total_seconds() / 60
color_dt = 'green' if time_delta_minutes < 15 else 'red'

# NOUVELLES MÉTRIQUES AJOUTÉES
usdc_threshold = last_row.get('usdc_threshold', 0)
margin = tot_usdc - usdc_threshold
accuracy = last_row.get('accuracy', 1.0)
tax = last_row.get('tax', 0.0)
nb_sharp_signals = last_row.get('nb_sharp_2h_greater_0_99', 0)


# --- AFFICHAGE DES INDICATEURS CLÉS (KPIs) ---
st.caption(f"Dernière mise à jour : <font color='{color_dt}'>{last_update_time.strftime('%H:%M:%S')}</font>", unsafe_allow_html=True)
st.divider()

# Première rangée d'indicateurs
col1, col2, col3 = st.columns(3)
col1.metric("Balance", f"{tot_usdc:,.2f} $", f"{gain_total:,.2f} $")
col2.metric("Investi", f"{usdc_invested:,.0f} $")
col3.metric("En attente", f"{pending_profit:,.2f} $")

# Affichage conditionnel de l'emprunt
if usdc_borrowed > 0:
    st.metric("Emprunté", f"{usdc_borrowed:,.0f} $")

st.divider()

# --- DEUXIÈME RANGÉE D'INDICATEURS (VOS AJOUTS) ---
col4, col5, col6 = st.columns(3)
col4.metric("Marge de Sécurité", f"{margin:,.0f} $", f"Seuil à {usdc_threshold:,.0f} $")
col5.metric("Précision", f"{accuracy:.2%}")
col6.metric("Signaux > 0.99", f"{int(nb_sharp_signals)}")

# La "taxe" est souvent mieux en petit, car c'est un détail plus technique
st.caption(f"Taxe / Slippage moyen : {tax:.3%}")

st.divider()


# --- GRAPHIQUES PRINCIPAUX ---
st.subheader("📈 Évolution des Gains")
fig1, ax1 = plt.subplots(figsize=(7, 3.5)) # Taille adaptée
ax1.plot(df_monitoring['timestamp'], df_monitoring['gain_theoretical'], label=f'Théorique ({last_row["gain_theoretical"]:,.0f}$)')
ax1.plot(df_monitoring['timestamp'], df_monitoring['tot_usdc'] - tot_usdc_initial, label=f'Réel ({gain_total:,.0f}$)')
ax1.set_ylabel('Gain ($)')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend(fontsize='small')
ax1.tick_params(axis='x', labelrotation=45)
fig1.tight_layout()
st.pyplot(fig1, use_container_width=True)

# --- SECTIONS DÉPLIABLES POUR LES DÉTAILS ---

with st.expander("📊 Analyse des positions"):
    # Figure: Répartition par Actif
    st.subheader("Répartition par Actif")
    # S'assurer que le DataFrame n'est pas vide et contient 'asset'
    if not df_invest.empty and 'asset' in df_invest.columns:
        df_plot_invest = df_invest.set_index('asset')
        fig3, ax3 = plt.subplots(figsize=(7, 3.5)) # Taille adaptée
        
        plot_data = df_plot_invest[['usdc_invested']]
        plot_data.plot.bar(ax=ax3, stacked=True, color=['royalblue'])
        if 'pending_profit' in df_plot_invest.columns:
            positive_profits = df_plot_invest[df_plot_invest['pending_profit'] >= 0]
            if not positive_profits.empty:
                positive_profits['pending_profit'].plot.bar(ax=ax3, color='green', label='Profit attente')

            negative_profits = df_plot_invest[df_plot_invest['pending_profit'] < 0]
            if not negative_profits.empty:
                negative_profits['pending_profit'].plot.bar(ax=ax3, color='red', label='Perte attente')
        
        ax3.set_ylabel('Montant ($)')
        ax3.grid(True, axis='y', linestyle='--', alpha=0.6)
        ax3.legend(fontsize='small')
        fig3.tight_layout()
        st.pyplot(fig3, use_container_width=True)
    else:
        st.info("Aucune position ouverte à afficher.")


    # Figure: Evolution des Investissements
    st.subheader("Historique des Investissements")
    fig2, ax2 = plt.subplots(figsize=(7, 3.5)) # Taille adaptée
    ax2.plot(df_monitoring['timestamp'], df_monitoring['usdc_invested'], label=f'Investi', color='royalblue')
    if 'usdc_borrowed' in df_monitoring.columns:
        ax2.plot(df_monitoring['timestamp'], df_monitoring['usdc_borrowed'], label=f'Emprunté', color='grey')
    ax2.set_ylabel('Montant ($)')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(fontsize='small')
    ax2.tick_params(axis='x', labelrotation=45)
    fig2.tight_layout()
    st.pyplot(fig2, use_container_width=True)

with st.expander("📉 Analyse du marché et des frais"):
    # Figure: Performance vs Marché
    st.subheader("Performance vs Marché")
    df_monitoring['btc_change'] = 100 * (df_monitoring['price_btc'] / df_monitoring['price_btc'].iloc[0] - 1)
    df_monitoring['real_profit_pct'] = 100 * (df_monitoring['tot_usdc'] / tot_usdc_initial - 1)
    
    fig4, ax4 = plt.subplots(figsize=(7, 3.5)) # Taille adaptée
    ax4.plot(df_monitoring['timestamp'], df_monitoring['btc_change'], label=f"BTC ({df_monitoring['btc_change'].iloc[-1]:.2f}%)", color='orange')
    ax4.plot(df_monitoring['timestamp'], df_monitoring['real_profit_pct'], label=f"Profit Réel ({df_monitoring['real_profit_pct'].iloc[-1]:.2f}%)", color='red')
    ax4.set_ylabel('Variation (%)')
    ax4.grid(True, linestyle='--', alpha=0.6)
    ax4.legend(fontsize='small')
    ax4.tick_params(axis='x', labelrotation=45)
    fig4.tight_layout()
    st.pyplot(fig4, use_container_width=True)

    # Affichage conditionnel des graphiques de frais
    if 'interest_fees_usdc' in df_monitoring.columns:
        st.subheader("Analyse des Frais (Mode MARGIN)")
        total_fees = df_monitoring['total_fees_usdc'].sum()
        interest_fees = df_monitoring['interest_fees_usdc'].sum()
        
        fig6, ax6 = plt.subplots(figsize=(7, 3.5)) # Taille adaptée
        ax6.plot(df_monitoring['timestamp'], df_monitoring['total_fees_usdc'].cumsum(), label=f'Totaux ({total_fees:.2f}$)')
        ax6.plot(df_monitoring['timestamp'], df_monitoring['interest_fees_usdc'].cumsum(), label=f'Intérêt ({interest_fees:.2f}$)')
        ax6.plot(df_monitoring['timestamp'], (df_monitoring['total_fees_usdc']-df_monitoring['interest_fees_usdc']).cumsum(), label=f'Transaction ({(total_fees - interest_fees):.2f}$)')
        ax6.set_ylabel('Frais Cumulés ($)')
        ax6.grid(True, linestyle='--', alpha=0.6)
        ax6.legend(fontsize='small')
        ax6.tick_params(axis='x', labelrotation=45)
        fig6.tight_layout()
        st.pyplot(fig6, use_container_width=True)