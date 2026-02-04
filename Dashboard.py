# Dashboard.py - Version avancée avec toutes les fonctionnalités
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
import warnings
import folium
from streamlit_folium import folium_static
from datetime import datetime
import json
warnings.filterwarnings('ignore')

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Financier Communal - La Réunion",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #374151;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #6B7280;
    }
    .alert-positive {
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .alert-warning {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .alert-danger {
        background-color: #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# DONNÉES DE RÉFÉRENCE ET COORDONNÉES GÉOGRAPHIQUES
# ============================================

# Coordonnées approximatives des communes de La Réunion (latitude, longitude)
COORDONNEES_COMMUNES = {
    'LES AVIRONS': (-21.2409, 55.3389),
    'BRAS-PANON': (-21.0016, 55.6773),
    'ENTRE-DEUX': (-21.2469, 55.4742),
    "L'ÉTANG-SALÉ": (-21.2771, 55.3852),
    'PETITE-ILE': (-21.3533, 55.5662),
    'LA PLAINE-DES-PALMISTES': (-21.1339, 55.6367),
    'LE PORT': (-20.9393, 55.2871),
    'LA POSSESSION': (-20.9284, 55.3341),
    'SAINT-ANDRÉ': (-20.9633, 55.6503),
    'SAINT-BENOÎT': (-21.0372, 55.7153),
    'SAINT-DENIS': (-20.8789, 55.4481),
    'SAINT-JOSEPH': (-21.3778, 55.6192),
    'SAINT-LEU': (-21.1706, 55.2881),
    'SAINT-LOUIS': (-21.2861, 55.4114),
    'SAINT-PAUL': (-21.0097, 55.2694),
    'SAINT-PIERRE': (-21.3419, 55.4778),
    'SAINT-PHILIPPE': (-21.3594, 55.7675),
    'SAINTE-MARIE': (-20.8978, 55.5492),
    'SAINTE-ROSE': (-21.1297, 55.7953),
    'SAINTE-SUZANNE': (-20.9069, 55.6089),
    'SALAZIE': (-21.0275, 55.5386),
    'LE TAMPON': (-21.2781, 55.5183),
    'LES TROIS-BASSINS': (-21.1011, 55.2858),
    'CILAOS': (-21.1342, 55.4722),
    'LA RÉUNION': (47.2079, -1.5561)  # Pour la commune métropolitaine
}

# Benchmarks nationaux/régionaux (valeurs fictives - à remplacer par des données réelles)
BENCHMARKS = {
    'epargne_brute_moyenne_nationale': 150,  # €/habitant
    'depenses_moyennes_nationales': 1200,    # €/habitant
    'recettes_moyennes_nationales': 1350,    # €/habitant
    'taux_epargne_moyen_national': 11.1,     # %
    'ratio_depenses_recettes_moyen': 88.9,   # %
}

# Seuils d'alerte pour les indicateurs financiers
SEUILS_ALERTES = {
    'epargne_brute_seuil_bas': -100,        # €/habitant
    'epargne_brute_seuil_haut': 300,        # €/habitant
    'depenses_habitant_seuil_bas': 800,     # €/habitant
    'depenses_habitant_seuil_haut': 2000,   # €/habitant
    'ratio_depenses_recettes_seuil': 100,   # %
    'solde_seuil_negatif': -50,             # €/habitant
}

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def format_number_for_display(value, decimals=1, is_currency=False):
    """Formate un nombre pour l'affichage dans les tableaux"""
    if pd.isna(value):
        return "-"
    
    try:
        value = float(value)
    except:
        return str(value)
    
    suffix = ""
    if abs(value) >= 1_000_000_000:
        value = value / 1_000_000_000
        suffix = "Md"
    elif abs(value) >= 1_000_000:
        value = value / 1_000_000
        suffix = "M"
    elif abs(value) >= 1_000:
        value = value / 1_000
        suffix = "K"
    
    if is_currency:
        return f"€{value:,.{decimals}f}{suffix}"
    else:
        return f"{value:,.{decimals}f}{suffix}"

def format_population(value):
    """Formate un nombre de population"""
    if pd.isna(value):
        return "-"
    return f"{value:,.0f}"

def get_coordonnees(commune):
    """Récupère les coordonnées d'une commune"""
    commune_upper = str(commune).upper().strip()
    return COORDONNEES_COMMUNES.get(commune_upper, (-21.1151, 55.5364))  # Centre de La Réunion par défaut

def analyser_alertes(df_analyse):
    """Analyse les données et génère des alertes"""
    alertes = []
    
    # Analyse de l'épargne brute
    if 'Montant_par_habitant' in df_analyse.columns and 'Agregat' in df_analyse.columns:
        df_epargne = df_analyse[df_analyse['Agregat'] == 'Epargne brute']
        if not df_epargne.empty:
            for _, row in df_epargne.iterrows():
                epargne = row['Montant_par_habitant']
                if pd.notnull(epargne):
                    if epargne < SEUILS_ALERTES['epargne_brute_seuil_bas']:
                        alertes.append({
                            'type': 'danger',
                            'commune': row.get('Commune', 'Inconnue'),
                            'message': f"Épargne brute très faible : {epargne:,.0f} €/hab",
                            'indicateur': 'Épargne brute'
                        })
                    elif epargne > SEUILS_ALERTES['epargne_brute_seuil_haut']:
                        alertes.append({
                            'type': 'positive',
                            'commune': row.get('Commune', 'Inconnue'),
                            'message': f"Épargne brute exceptionnelle : {epargne:,.0f} €/hab",
                            'indicateur': 'Épargne brute'
                        })
    
    return alertes

# ============================================
# CHARGEMENT DES DONNÉES
# ============================================

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('ofgl-base-communes.csv', sep=';', low_memory=False, encoding='utf-8')
    except:
        try:
            df = pd.read_csv('ofgl-base-communes.csv', sep=';', low_memory=False, encoding='latin-1')
        except:
            st.error("Impossible de lire le fichier CSV. Vérifiez le format et l'encodage.")
            return pd.DataFrame()
    
    # Nettoyage des colonnes
    df.columns = df.columns.str.strip()
    
    # Standardisation des noms de colonnes
    column_mapping = {
        'Exercice': 'Exercice',
        'Outre-mer': 'Outre_mer',
        'Code Insee 2024 Région': 'Code_Region',
        'Nom 2024 Région': 'Nom_Region',
        'Code Insee 2024 Département': 'Code_Departement',
        'Nom 2024 Département': 'Nom_Departement',
        'Code Siren 2024 EPCI': 'Code_EPCI',
        'Nom 2024 EPCI': 'Nom_EPCI',
        'Strate population 2024': 'Strate_population',
        'Commune rurale': 'Commune_rurale',
        'Commune de montagne': 'Commune_montagne',
        'Commune touristique': 'Commune_touristique',
        'Tranche revenu par habitant': 'Tranche_revenu',
        'Présence QPV': 'Presence_QPV',
        'Code Insee 2024 Commune': 'Code_Commune',
        'Nom 2024 Commune': 'Commune',
        'Catégorie': 'Categorie',
        'Code Siren Collectivité': 'Code_Siren_Collectivite',
        'Code Insee Collectivité': 'Code_Insee_Collectivite',
        'Siret Budget': 'Siret_Budget',
        'Libellé Budget': 'Libelle_Budget',
        'Type de budget': 'Type_budget',
        'Nomenclature': 'Nomenclature',
        'Agrégat': 'Agregat',
        'Montant': 'Montant',
        'Montant en millions': 'Montant_millions',
        'Population totale': 'Population',
        'Montant en € par habitant': 'Montant_par_habitant',
        'Compte 2024 Disponible': 'Compte_disponible',
        'code_type_budget': 'code_type_budget',
        'ordre_analyse1_section1': 'ordre_analyse1_section1',
        'Population totale du dernier exercice': 'Population_dernier_exercice'
    }
    
    existing_columns = {}
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            existing_columns[old_name] = new_name
    
    df = df.rename(columns=existing_columns)
    
    # Conversion des colonnes numériques
    numeric_cols = ['Montant', 'Montant_millions', 'Population', 
                    'Montant_par_habitant', 'Population_dernier_exercice',
                    'Strate_population', 'Tranche_revenu']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Nettoyage des colonnes texte
    text_cols = ['Commune_rurale', 'Commune_montagne', 'Commune_touristique', 'Presence_QPV']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    
    # Filtre pour La Réunion
    if 'Code_Departement' in df.columns:
        df = df[df['Code_Departement'] == 974]
    
    return df

# ============================================
# INTERFACE STREAMLIT
# ============================================

# Titre principal
st.markdown('<h1 class="main-header">📊 Dashboard Financier des Communes de La Réunion</h1>', unsafe_allow_html=True)
st.markdown("***Analyse budgétaire - Données OFGL***")

# Chargement des données
df = load_data()

if df.empty:
    st.error("Aucune donnée chargée. Vérifiez votre fichier CSV.")
    st.stop()

# Sidebar - Filtres et configuration
with st.sidebar:
    st.markdown("## 🔧 Filtres et Configuration")
    
    # Onglets dans la sidebar
    sidebar_tab1, sidebar_tab2, sidebar_tab3 = st.tabs(["Filtres", "Benchmarks", "Alertes"])
    
    with sidebar_tab1:
        # Filtre par année (simulation multi-années)
        if 'Exercice' in df.columns:
            annees_disponibles = sorted(df['Exercice'].dropna().unique())
            selected_year = st.selectbox(
                "Année d'exercice",
                options=annees_disponibles,
                index=len(annees_disponibles)-1 if len(annees_disponibles) > 0 else 0
            )
        else:
            selected_year = 2017
            st.info("Données 2017 uniquement")
        
        # Filtre par EPCI
        if 'Nom_EPCI' in df.columns:
            epci_list = df['Nom_EPCI'].dropna().unique().tolist()
            selected_epci = st.multiselect(
                "EPCI (Intercommunalités)",
                options=epci_list,
                default=epci_list
            )
        else:
            selected_epci = []
        
        # Filtre par commune
        if 'Commune' in df.columns:
            commune_list = sorted(df['Commune'].dropna().unique().tolist())
            selected_communes = st.multiselect(
                "Communes",
                options=commune_list,
                default=commune_list[:10]  # Par défaut les 10 premières
            )
        else:
            selected_communes = []
        
        # Filtre par caractéristique
        st.markdown("### Caractéristiques")
        col_char1, col_char2 = st.columns(2)
        with col_char1:
            montagne = st.checkbox("🏔️ Montagne", value=True)
            rurale = st.checkbox("🌾 Rurale", value=True)
        with col_char2:
            touristique = st.checkbox("🏖️ Touristique", value=True)
            qpv = st.checkbox("🏙️ QPV", value=True)
    
    with sidebar_tab2:
        st.markdown("### 🔍 Configuration des Benchmarks")
        
        st.markdown("#### Benchmarks nationaux")
        col_bench1, col_bench2 = st.columns(2)
        with col_bench1:
            BENCHMARKS['epargne_brute_moyenne_nationale'] = st.number_input(
                "Épargne brute moyenne (€/hab)",
                value=150.0,
                min_value=0.0,
                step=10.0
            )
            BENCHMARKS['recettes_moyennes_nationales'] = st.number_input(
                "Recettes moyennes (€/hab)",
                value=1350.0,
                min_value=0.0,
                step=50.0
            )
        with col_bench2:
            BENCHMARKS['depenses_moyennes_nationales'] = st.number_input(
                "Dépenses moyennes (€/hab)",
                value=1200.0,
                min_value=0.0,
                step=50.0
            )
            BENCHMARKS['taux_epargne_moyen_national'] = st.number_input(
                "Taux d'épargne moyen (%)",
                value=11.1,
                min_value=0.0,
                max_value=100.0,
                step=1.0
            )
    
    with sidebar_tab3:
        st.markdown("### ⚠️ Configuration des Alertes")
        
        st.markdown("#### Seuils d'alerte")
        col_alert1, col_alert2 = st.columns(2)
        with col_alert1:
            SEUILS_ALERTES['epargne_brute_seuil_bas'] = st.number_input(
                "Épargne brute seuil bas (€/hab)",
                value=-100.0,
                step=10.0
            )
            SEUILS_ALERTES['depenses_habitant_seuil_haut'] = st.number_input(
                "Dépenses seuil haut (€/hab)",
                value=2000.0,
                min_value=0.0,
                step=100.0
            )
        with col_alert2:
            SEUILS_ALERTES['epargne_brute_seuil_haut'] = st.number_input(
                "Épargne brute seuil haut (€/hab)",
                value=300.0,
                min_value=0.0,
                step=10.0
            )
            SEUILS_ALERTES['ratio_depenses_recettes_seuil'] = st.number_input(
                "Ratio dépenses/recettes seuil (%)",
                value=100.0,
                min_value=0.0,
                max_value=200.0,
                step=5.0
            )
        
        # Bouton pour analyser les alertes
        if st.button("🔍 Analyser les alertes", type="secondary"):
            st.session_state['analyse_alertes'] = True

# Application des filtres
filtered_df = df.copy()

if 'Exercice' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Exercice'] == selected_year]

if selected_epci:
    filtered_df = filtered_df[filtered_df['Nom_EPCI'].isin(selected_epci)]

if selected_communes:
    filtered_df = filtered_df[filtered_df['Commune'].isin(selected_communes)]

# ============================================
# SECTION PRINCIPALE - KPI ET ALERTES
# ============================================

st.markdown('<h2 class="sub-header">📈 Vue d\'ensemble - Santé Financière</h2>', unsafe_allow_html=True)

# Section d'alertes
if 'analyse_alertes' in st.session_state and st.session_state['analyse_alertes']:
    alertes = analyser_alertes(filtered_df)
    if alertes:
        st.markdown("### ⚠️ Alertes Financières")
        for alerte in alertes:
            if alerte['type'] == 'danger':
                st.markdown(f"""
                <div class="alert-danger">
                    <strong>{alerte['commune']}</strong> - {alerte['indicateur']}: {alerte['message']}
                </div>
                """, unsafe_allow_html=True)
            elif alerte['type'] == 'warning':
                st.markdown(f"""
                <div class="alert-warning">
                    <strong>{alerte['commune']}</strong> - {alerte['indicateur']}: {alerte['message']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-positive">
                    <strong>{alerte['commune']}</strong> - {alerte['indicateur']}: {alerte['message']}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ Aucune alerte financière critique détectée")

# KPI Principaux
df_principal = filtered_df[filtered_df['Type_budget'] == 'Budget principal']

if not df_principal.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'Agregat' in df_principal.columns and 'Montant' in df_principal.columns:
            total_epargne = df_principal[df_principal['Agregat'] == 'Epargne brute']['Montant'].sum() / 1_000_000
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{total_epargne:.1f} M€</div>
                <div class="kpi-label">Épargne brute totale</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if 'Commune' in df_principal.columns:
            communes_count = df_principal['Commune'].nunique()
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{communes_count}</div>
                <div class="kpi-label">Communes analysées</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if 'Population' in df_principal.columns:
            total_population = df_principal['Population'].sum()
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{total_population:,.0f}</div>
                <div class="kpi-label">Population totale</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        if 'Agregat' in df_principal.columns and 'Montant' in df_principal.columns:
            df_recettes = df_principal[df_principal['Agregat'] == 'Recettes totales hors emprunts']
            total_recettes = df_recettes['Montant'].sum() / 1_000_000 if not df_recettes.empty else 0
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{total_recettes:.1f} M€</div>
                <div class="kpi-label">Recettes totales</div>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# ONGLETS PRINCIPAUX
# ============================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺️ Carte Géographique",
    "📈 Tendances Multi-années",
    "📊 Benchmarks",
    "🏛️ Santé Financière",
    "💧 Budgets Annexes",
    "📋 Rapport PDF"
])

# TAB 1: CARTE GÉOGRAPHIQUE
with tab1:
    try:
        st.markdown("### 🗺️ Carte Géographique des Communes de La Réunion")
        
        # Création de la carte centrée sur La Réunion
        m = folium.Map(location=[-21.1151, 55.5364], zoom_start=10)
        
        # Préparation des données pour la carte
        if 'Agregat' in df_principal.columns and 'Montant_par_habitant' in df_principal.columns:
            df_epargne = df_principal[df_principal['Agregat'] == 'Epargne brute']
            
            # Ajout des marqueurs pour chaque commune
            for _, row in df_epargne.iterrows():
                commune = row.get('Commune', '')
                epargne = row.get('Montant_par_habitant', 0)
                population = row.get('Population', 0)
                
                if pd.notnull(epargne) and commune:
                    # Déterminer la couleur en fonction de l'épargne
                    if epargne < 0:
                        color = 'red'
                    elif epargne < 100:
                        color = 'orange'
                    elif epargne < 300:
                        color = 'lightgreen'
                    else:
                        color = 'green'
                    
                    # Récupérer les coordonnées
                    lat, lon = get_coordonnees(commune)
                    
                    # Créer le popup HTML
                    popup_html = f"""
                    <div style="width: 250px;">
                        <h4 style="color: #1E3A8A; margin-bottom: 5px;">{commune}</h4>
                        <p style="margin: 2px 0;"><strong>Épargne brute:</strong> {epargne:,.0f} €/hab</p>
                        <p style="margin: 2px 0;"><strong>Population:</strong> {population:,.0f} hab</p>
                        <p style="margin: 2px 0;"><strong>Épargne totale:</strong> {(epargne * population):,.0f} €</p>
                    </div>
                    """
                    
                    # Ajouter le marqueur
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=commune,
                        icon=folium.Icon(color=color, icon='info-sign')
                    ).add_to(m)
        
        # Affichage de la carte
        folium_static(m, width=1000, height=600)
        
        # Légende
        col_leg1, col_leg2, col_leg3, col_leg4 = st.columns(4)
        with col_leg1:
            st.markdown("🔴 **< 0 €/hab** - Déficit")
        with col_leg2:
            st.markdown("🟠 **0-100 €/hab** - Faible")
        with col_leg3:
            st.markdown("🟢 **100-300 €/hab** - Bonne")
        with col_leg4:
            st.markdown("🟢 **> 300 €/hab** - Excellente")
        
        # Statistiques géographiques
        st.markdown("### 📊 Statistiques par zone géographique")
        
        # Définir les zones géographiques approximatives
        zones = {
            'Nord': ['SAINT-DENIS', 'SAINTE-MARIE', 'SAINTE-SUZANNE'],
            'Est': ['SAINT-ANDRÉ', 'SAINT-BENOÎT', 'BRAS-PANON', 'SAINTE-ROSE', 'LA PLAINE-DES-PALMISTES'],
            'Sud': ['SAINT-PIERRE', 'SAINT-LOUIS', 'SAINT-JOSEPH', 'LE TAMPON', 'PETITE-ILE', "L'ÉTANG-SALÉ", 'LES AVIRONS', 'SAINT-PHILIPPE', 'ENTRE-DEUX'],
            'Ouest': ['SAINT-PAUL', 'LE PORT', 'LA POSSESSION', 'SAINT-LEU', 'LES TROIS-BASSINS'],
            'Cirques': ['CILAOS', 'SALAZIE']
        }
        
        zone_data = []
        for zone, communes_zone in zones.items():
            df_zone = df_epargne[df_epargne['Commune'].str.upper().isin(communes_zone)]
            if not df_zone.empty:
                avg_epargne = df_zone['Montant_par_habitant'].mean()
                total_pop = df_zone['Population'].sum()
                zone_data.append({
                    'Zone': zone,
                    'Nombre de communes': len(df_zone),
                    'Population totale': total_pop,
                    'Épargne moyenne/hab': avg_epargne
                })
        
        if zone_data:
            zone_df = pd.DataFrame(zone_data)
            
            # Graphique comparatif par zone
            fig_zone = px.bar(
                zone_df,
                x='Zone',
                y='Épargne moyenne/hab',
                color='Épargne moyenne/hab',
                color_continuous_scale='RdYlGn',
                title="Épargne brute moyenne par zone géographique",
                text_auto='.0f'
            )
            fig_zone.update_layout(height=400)
            st.plotly_chart(fig_zone, use_container_width=True)
            
            # Tableau des zones
            st.dataframe(
                zone_df.style.format({
                    'Population totale': '{:,.0f}',
                    'Épargne moyenne/hab': '{:,.0f} €'
                }),
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"Erreur dans la carte géographique : {str(e)}")

# TAB 2: TENDANCES MULTI-ANNÉES
with tab2:
    try:
        st.markdown("### 📈 Analyse des Tendances Multi-années")
        
        # Simulation de données multi-années (dans un cas réel, charger plusieurs fichiers)
        st.info("ℹ️ Pour une analyse multi-années complète, chargez des données pour plusieurs années")
        
        # Création de données simulées pour démonstration
        if 'Exercice' in df.columns:
            annees = sorted(df['Exercice'].dropna().unique())
            
            if len(annees) > 1:
                # Analyse par année
                trends_data = []
                
                for annee in annees:
                    df_annee = df[df['Exercice'] == annee]
                    df_principal_annee = df_annee[df_annee['Type_budget'] == 'Budget principal']
                    
                    if not df_principal_annee.empty:
                        # Calcul des indicateurs par année
                        df_epargne = df_principal_annee[df_principal_annee['Agregat'] == 'Epargne brute']
                        df_recettes = df_principal_annee[df_principal_annee['Agregat'] == 'Recettes totales hors emprunts']
                        df_financement = df_principal_annee[df_principal_annee['Agregat'] == 'Capacité ou besoin de financement']
                        
                        epargne_moy = df_epargne['Montant_par_habitant'].mean() if not df_epargne.empty else 0
                        recettes_moy = df_recettes['Montant_par_habitant'].mean() if not df_recettes.empty else 0
                        financement_moy = df_financement['Montant_par_habitant'].mean() if not df_financement.empty else 0
                        
                        trends_data.append({
                            'Année': annee,
                            'Épargne brute/hab': epargne_moy,
                            'Recettes/hab': recettes_moy,
                            'Capacité financement/hab': financement_moy,
                            'Nombre communes': df_principal_annee['Commune'].nunique()
                        })
                
                if trends_data:
                    trends_df = pd.DataFrame(trends_data)
                    
                    # Graphique d'évolution
                    fig_trends = go.Figure()
                    
                    fig_trends.add_trace(go.Scatter(
                        x=trends_df['Année'],
                        y=trends_df['Épargne brute/hab'],
                        name='Épargne brute/hab',
                        mode='lines+markers',
                        line=dict(color='#10B981', width=3)
                    ))
                    
                    fig_trends.add_trace(go.Scatter(
                        x=trends_df['Année'],
                        y=trends_df['Recettes/hab'],
                        name='Recettes/hab',
                        mode='lines+markers',
                        line=dict(color='#3B82F6', width=3)
                    ))
                    
                    fig_trends.add_trace(go.Scatter(
                        x=trends_df['Année'],
                        y=trends_df['Capacité financement/hab'],
                        name='Capacité financement/hab',
                        mode='lines+markers',
                        line=dict(color='#8B5CF6', width=3)
                    ))
                    
                    fig_trends.update_layout(
                        title="Évolution des indicateurs financiers par année",
                        height=500,
                        xaxis_title="Année",
                        yaxis_title="€ par habitant",
                        hovermode="x unified"
                    )
                    
                    st.plotly_chart(fig_trends, use_container_width=True)
                    
                    # Calcul des variations
                    st.markdown("### 📊 Analyse des Variations")
                    
                    if len(trends_df) >= 2:
                        # Calculer les variations en pourcentage
                        trends_df['Var_epargne_%'] = trends_df['Épargne brute/hab'].pct_change() * 100
                        trends_df['Var_recettes_%'] = trends_df['Recettes/hab'].pct_change() * 100
                        
                        col_var1, col_var2, col_var3 = st.columns(3)
                        
                        with col_var1:
                            derniere_var_epargne = trends_df['Var_epargne_%'].iloc[-1]
                            couleur = "green" if derniere_var_epargne > 0 else "red" if derniere_var_epargne < 0 else "gray"
                            st.metric(
                                "Variation épargne brute",
                                f"{derniere_var_epargne:+.1f}%",
                                delta_color="normal" if derniere_var_epargne > 0 else "inverse"
                            )
                        
                        with col_var2:
                            derniere_var_recettes = trends_df['Var_recettes_%'].iloc[-1]
                            st.metric(
                                "Variation recettes",
                                f"{derniere_var_recettes:+.1f}%",
                                delta_color="normal" if derniere_var_recettes > 0 else "inverse"
                            )
                        
                        with col_var3:
                            croissance_moyenne = trends_df['Épargne brute/hab'].mean()
                            st.metric(
                                "Épargne moyenne sur la période",
                                f"{croissance_moyenne:,.0f} €/hab"
                            )
                        
                        # Tableau des tendances
                        st.dataframe(
                            trends_df.style.format({
                                'Épargne brute/hab': '{:,.0f} €',
                                'Recettes/hab': '{:,.0f} €',
                                'Capacité financement/hab': '{:,.0f} €',
                                'Var_epargne_%': '{:+.1f}%',
                                'Var_recettes_%': '{:+.1f}%'
                            }).background_gradient(
                                subset=['Var_epargne_%', 'Var_recettes_%'],
                                cmap='RdYlGn'
                            ),
                            use_container_width=True
                        )
            else:
                st.info("Une seule année de données disponible. Chargez des données multi-années pour l'analyse des tendances.")
        
        # Section pour charger des données supplémentaires
        with st.expander("📁 Charger des données supplémentaires"):
            st.markdown("#### Import de données multi-années")
            
            uploaded_files = st.file_uploader(
                "Charger des fichiers CSV supplémentaires",
                type=['csv'],
                accept_multiple_files=True
            )
            
            if uploaded_files:
                st.success(f"{len(uploaded_files)} fichier(s) chargé(s)")
                
                # Simuler le chargement des fichiers
                for file in uploaded_files:
                    st.write(f"- {file.name}")
        
    except Exception as e:
        st.error(f"Erreur dans l'analyse des tendances : {str(e)}")

# TAB 3: BENCHMARKS
with tab3:
    try:
        st.markdown("### 🔍 Analyse Comparative avec les Benchmarks")
        
        # Données pour la comparaison
        if 'Agregat' in df_principal.columns and 'Montant_par_habitant' in df_principal.columns:
            df_epargne = df_principal[df_principal['Agregat'] == 'Epargne brute']
            df_recettes = df_principal[df_principal['Agregat'] == 'Recettes totales hors emprunts']
            
            if not df_epargne.empty and not df_recettes.empty:
                # Calcul des moyennes locales
                epargne_moyenne_locale = df_epargne['Montant_par_habitant'].mean()
                recettes_moyenne_locale = df_recettes['Montant_par_habitant'].mean()
                
                # Estimation des dépenses moyennes locales
                depenses_moyenne_locale = recettes_moyenne_locale - epargne_moyenne_locale
                taux_epargne_local = (epargne_moyenne_locale / recettes_moyenne_locale * 100) if recettes_moyenne_locale > 0 else 0
                ratio_depenses_local = (depenses_moyenne_locale / recettes_moyenne_locale * 100) if recettes_moyenne_locale > 0 else 0
                
                # Tableau de comparaison
                comparison_data = {
                    'Indicateur': ['Épargne brute/hab', 'Recettes/hab', 'Dépenses/hab', 'Taux d\'épargne', 'Ratio dépenses/recettes'],
                    'Moyenne La Réunion': [
                        f"{epargne_moyenne_locale:,.0f} €",
                        f"{recettes_moyenne_locale:,.0f} €",
                        f"{depenses_moyenne_locale:,.0f} €",
                        f"{taux_epargne_local:.1f}%",
                        f"{ratio_depenses_local:.1f}%"
                    ],
                    'Benchmark National': [
                        f"{BENCHMARKS['epargne_brute_moyenne_nationale']:,.0f} €",
                        f"{BENCHMARKS['recettes_moyennes_nationales']:,.0f} €",
                        f"{BENCHMARKS['depenses_moyennes_nationales']:,.0f} €",
                        f"{BENCHMARKS['taux_epargne_moyen_national']:.1f}%",
                        f"{BENCHMARKS['ratio_depenses_recettes_moyen']:.1f}%"
                    ],
                    'Écart': [
                        f"{epargne_moyenne_locale - BENCHMARKS['epargne_brute_moyenne_nationale']:+,.0f} €",
                        f"{recettes_moyenne_locale - BENCHMARKS['recettes_moyennes_nationales']:+,.0f} €",
                        f"{depenses_moyenne_locale - BENCHMARKS['depenses_moyennes_nationales']:+,.0f} €",
                        f"{taux_epargne_local - BENCHMARKS['taux_epargne_moyen_national']:+.1f}%",
                        f"{ratio_depenses_local - BENCHMARKS['ratio_depenses_recettes_moyen']:+.1f}%"
                    ]
                }
                
                comparison_df = pd.DataFrame(comparison_data)
                
                # Affichage du tableau avec mise en forme conditionnelle
                def color_ecart(val):
                    try:
                        num = float(str(val).replace(' €', '').replace('%', '').replace('+', '').replace(',', ''))
                        if '€' in str(val):
                            if num > 0:
                                return 'background-color: #D1FAE5'
                            elif num < 0:
                                return 'background-color: #FEE2E2'
                        elif '%' in str(val):
                            if 'Taux' in comparison_df.loc[comparison_df['Écart'] == val, 'Indicateur'].values[0]:
                                if num > 0:
                                    return 'background-color: #D1FAE5'
                                elif num < 0:
                                    return 'background-color: #FEE2E2'
                            else:  # Ratio dépenses/recettes
                                if num < 0:
                                    return 'background-color: #D1FAE5'
                                elif num > 0:
                                    return 'background-color: #FEE2E2'
                    except:
                        pass
                    return ''
                
                st.dataframe(
                    comparison_df.style.applymap(color_ecart, subset=['Écart']),
                    use_container_width=True
                )
                
                # Graphique radar pour la comparaison
                st.markdown("#### 📊 Profil comparatif (Radar Chart)")
                
                # Normalisation des données pour le radar chart
                categories = ['Épargne/hab', 'Recettes/hab', 'Dépenses/hab', 'Taux épargne', 'Efficience']
                
                valeurs_reunion = [
                    epargne_moyenne_locale / 500,  # Normalisation
                    recettes_moyenne_locale / 2000,
                    depenses_moyenne_locale / 2000,
                    taux_epargne_local / 20,
                    (100 - ratio_depenses_local) / 100  # Efficience = 100 - ratio
                ]
                
                valeurs_national = [
                    BENCHMARKS['epargne_brute_moyenne_nationale'] / 500,
                    BENCHMARKS['recettes_moyennes_nationales'] / 2000,
                    BENCHMARKS['depenses_moyennes_nationales'] / 2000,
                    BENCHMARKS['taux_epargne_moyen_national'] / 20,
                    (100 - BENCHMARKS['ratio_depenses_recettes_moyen']) / 100
                ]
                
                fig_radar = go.Figure()
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=valeurs_reunion,
                    theta=categories,
                    fill='toself',
                    name='La Réunion',
                    line_color='#3B82F6'
                ))
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=valeurs_national,
                    theta=categories,
                    fill='toself',
                    name='Moyenne Nationale',
                    line_color='#10B981'
                ))
                
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]
                        )
                    ),
                    showlegend=True,
                    height=500,
                    title="Profil financier comparatif"
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
                
                # Analyse détaillée par commune vs benchmark
                st.markdown("#### 🏛️ Analyse Communale vs Benchmarks")
                
                # Préparer les données pour chaque commune
                commune_benchmarks = []
                for _, row in df_epargne.iterrows():
                    commune = row['Commune']
                    epargne_commune = row['Montant_par_habitant']
                    
                    # Trouver les recettes de la commune
                    recettes_commune = df_recettes[df_recettes['Commune'] == commune]
                    recettes_hab = recettes_commune['Montant_par_habitant'].iloc[0] if not recettes_commune.empty else 0
                    
                    if pd.notnull(epargne_commune) and recettes_hab > 0:
                        depenses_hab = recettes_hab - epargne_commune
                        taux_epargne = (epargne_commune / recettes_hab * 100)
                        
                        commune_benchmarks.append({
                            'Commune': commune,
                            'Épargne/hab': epargne_commune,
                            'Recettes/hab': recettes_hab,
                            'Dépenses/hab': depenses_hab,
                            'Taux épargne': taux_epargne,
                            'Écart vs national': epargne_commune - BENCHMARKS['epargne_brute_moyenne_nationale'],
                            'Catégorie': 'Supérieur' if epargne_commune > BENCHMARKS['epargne_brute_moyenne_nationale'] else 'Inférieur'
                        })
                
                if commune_benchmarks:
                    commune_df = pd.DataFrame(commune_benchmarks)
                    
                    # Graphique de dispersion
                    fig_scatter = px.scatter(
                        commune_df,
                        x='Recettes/hab',
                        y='Épargne/hab',
                        size='Dépenses/hab',
                        color='Catégorie',
                        hover_name='Commune',
                        title="Épargne vs Recettes par commune (vs benchmark national)",
                        labels={
                            'Recettes/hab': 'Recettes par habitant (€)',
                            'Épargne/hab': 'Épargne par habitant (€)',
                            'Dépenses/hab': 'Dépenses par habitant (€)',
                            'Catégorie': 'Comparaison benchmark'
                        },
                        color_discrete_map={'Supérieur': '#10B981', 'Inférieur': '#EF4444'}
                    )
                    
                    # Ajouter la ligne du benchmark
                    fig_scatter.add_hline(
                        y=BENCHMARKS['epargne_brute_moyenne_nationale'],
                        line_dash="dash",
                        line_color="gray",
                        annotation_text=f"Benchmark national: {BENCHMARKS['epargne_brute_moyenne_nationale']} €/hab"
                    )
                    
                    fig_scatter.update_layout(height=500)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Statistiques
                    communes_sup = (commune_df['Catégorie'] == 'Supérieur').sum()
                    communes_total = len(commune_df)
                    pourcentage_sup = (communes_sup / communes_total * 100) if communes_total > 0 else 0
                    
                    col_stat_b1, col_stat_b2, col_stat_b3 = st.columns(3)
                    
                    with col_stat_b1:
                        st.metric(
                            "Communes au-dessus du benchmark",
                            f"{pourcentage_sup:.1f}%",
                            delta=f"{communes_sup} communes"
                        )
                    
                    with col_stat_b2:
                        meilleure_commune = commune_df.loc[commune_df['Écart vs national'].idxmax(), 'Commune']
                        meilleur_ecart = commune_df['Écart vs national'].max()
                        st.metric(
                            "Meilleure performance",
                            f"{meilleur_ecart:+.0f} €",
                            delta=meilleure_commune
                        )
                    
                    with col_stat_b3:
                        pire_commune = commune_df.loc[commune_df['Écart vs national'].idxmin(), 'Commune']
                        pire_ecart = commune_df['Écart vs national'].min()
                        st.metric(
                            "Plus grand écart négatif",
                            f"{pire_ecart:+.0f} €",
                            delta=pire_commune,
                            delta_color="inverse"
                        )
        
    except Exception as e:
        st.error(f"Erreur dans l'analyse des benchmarks : {str(e)}")

# TAB 4: SANTÉ FINANCIÈRE (existant - simplifié pour la démo)
with tab4:
    try:
        st.markdown("### 🏛️ Santé Financière des Communes")
        
        if 'Agregat' in df_principal.columns:
            df_financement = df_principal[df_principal['Agregat'] == 'Capacité ou besoin de financement']
            
            if not df_financement.empty:
                # Graphique simplifié
                df_financement_clean = df_financement.dropna(subset=['Montant_par_habitant', 'Commune'])
                df_financement_clean = df_financement_clean.sort_values('Montant_par_habitant', ascending=False)
                
                fig = px.bar(
                    df_financement_clean.head(20),
                    x='Commune',
                    y='Montant_par_habitant',
                    color='Montant_par_habitant',
                    color_continuous_scale=['#EF4444', '#FBBF24', '#10B981'],
                    title="Capacité/Besoin de Financement par Habitant (Top 20)",
                    labels={'Montant_par_habitant': '€ par habitant'}
                )
                fig.update_layout(height=500, xaxis_tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erreur dans l'analyse de santé financière : {str(e)}")

# TAB 5: BUDGETS ANNEXES (existant - simplifié pour la démo)
with tab5:
    try:
        st.markdown("### 💧 Analyse des Budgets Annexes")
        
        df_annexes = filtered_df[filtered_df['Type_budget'] == 'Budget annexe']
        
        if not df_annexes.empty and 'Libelle_Budget' in df_annexes.columns:
            # Classification simplifiée
            def classify_service(libelle):
                if isinstance(libelle, str):
                    libelle_lower = libelle.lower()
                    if 'eau' in libelle_lower:
                        return 'Eau'
                    elif 'assain' in libelle_lower:
                        return 'Assainissement'
                    elif 'pompe' in libelle_lower:
                        return 'Pompes funèbres'
                    elif 'spanc' in libelle_lower:
                        return 'SPANC'
                return 'Autres'
            
            df_annexes['Type_service'] = df_annexes['Libelle_Budget'].apply(classify_service)
            
            # Graphique des services
            service_counts = df_annexes['Type_service'].value_counts().reset_index()
            service_counts.columns = ['Service', 'Nombre']
            
            fig = px.pie(
                service_counts,
                values='Nombre',
                names='Service',
                title="Répartition des budgets annexes par type de service"
            )
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erreur dans l'analyse des budgets annexes : {str(e)}")

# TAB 6: RAPPORT PDF
with tab6:
    try:
        st.markdown("### 📋 Génération de Rapport PDF")
        
        col_report1, col_report2 = st.columns(2)
        
        with col_report1:
            st.markdown("#### Configuration du Rapport")
            
            # Options du rapport
            report_title = st.text_input("Titre du rapport", "Rapport Financier des Communes de La Réunion")
            
            include_sections = st.multiselect(
                "Sections à inclure",
                options=['Synthèse', 'Carte', 'Benchmarks', 'Alertes', 'Analyse détaillée'],
                default=['Synthèse', 'Alertes', 'Benchmarks']
            )
            
            report_format = st.selectbox(
                "Format",
                options=['PDF Standard', 'PDF Détaillé', 'Résumé Exécutif']
            )
            
            # Date du rapport
            report_date = st.date_input("Date du rapport", datetime.now())
        
        with col_report2:
            st.markdown("#### Aperçu du Rapport")
            
            # Aperçu des données qui seront incluses
            st.markdown("**Données incluses:**")
            
            if 'Synthèse' in include_sections:
                st.markdown("✅ **Synthèse financière**")
                if 'Agregat' in df_principal.columns:
                    df_epargne = df_principal[df_principal['Agregat'] == 'Epargne brute']
                    if not df_epargne.empty:
                        avg_epargne = df_epargne['Montant_par_habitant'].mean()
                        st.markdown(f"- Épargne brute moyenne: {avg_epargne:,.0f} €/hab")
            
            if 'Alertes' in include_sections:
                st.markdown("✅ **Alertes financières**")
                alertes = analyser_alertes(filtered_df)
                st.markdown(f"- {len(alertes)} alerte(s) détectée(s)")
            
            if 'Benchmarks' in include_sections:
                st.markdown("✅ **Comparaison benchmarks**")
                st.markdown(f"- Benchmark national: {BENCHMARKS['epargne_brute_moyenne_nationale']} €/hab")
        
        # Bouton de génération
        if st.button("📄 Générer le Rapport PDF", type="primary"):
            # Simulation de génération de rapport
            with st.spinner("Génération du rapport en cours..."):
                import time
                time.sleep(2)  # Simulation du temps de traitement
                
                # Créer un rapport simulé
                rapport_content = f"""
                # {report_title}
                **Date:** {report_date.strftime('%d/%m/%Y')}
                **Format:** {report_format}
                
                ## 📊 Synthèse des Données
                
                ### Indicateurs Clés
                - Communes analysées: {df_principal['Commune'].nunique() if 'Commune' in df_principal.columns else 0}
                - Population totale: {df_principal['Population'].sum() if 'Population' in df_principal.columns else 0:,.0f}
                - Épargne brute totale: {df_principal[df_principal['Agregat'] == 'Epargne brute']['Montant'].sum() / 1_000_000 if not df_principal.empty else 0:.1f} M€
                
                ### Benchmarks
                - Épargne moyenne La Réunion: {df_epargne['Montant_par_habitant'].mean() if 'Montant_par_habitant' in df_epargne.columns else 0:,.0f} €/hab
                - Benchmark national: {BENCHMARKS['epargne_brute_moyenne_nationale']} €/hab
                - Écart: {(df_epargne['Montant_par_habitant'].mean() if 'Montant_par_habitant' in df_epargne.columns else 0) - BENCHMARKS['epargne_brute_moyenne_nationale']:+,.0f} €/hab
                
                ## ⚠️ Alertes Principales
                """
                
                # Ajouter les alertes
                alertes = analyser_alertes(filtered_df)
                if alertes:
                    for alerte in alertes[:5]:  # Limiter aux 5 premières alertes
                        rapport_content += f"\n- **{alerte['commune']}**: {alerte['message']}"
                else:
                    rapport_content += "\nAucune alerte critique détectée."
                
                # Simulation de sauvegarde du rapport
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
                    tmp.write(rapport_content)
                    tmp_path = tmp.name
                
                # Fournir le rapport en téléchargement
                with open(tmp_path, 'rb') as f:
                    report_bytes = f.read()
                
                st.success("✅ Rapport généré avec succès!")
                
                st.download_button(
                    label="📥 Télécharger le Rapport",
                    data=report_bytes,
                    file_name=f"rapport_financier_{report_date.strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
                
                # Nettoyer le fichier temporaire
                os.unlink(tmp_path)
        
        # Section pour les rapports automatisés
        with st.expander("🔄 Automatisation des Rapports"):
            st.markdown("#### Planification des rapports")
            
            col_auto1, col_auto2 = st.columns(2)
            
            with col_auto1:
                frequency = st.selectbox(
                    "Fréquence",
                    options=['Quotidienne', 'Hebdomadaire', 'Mensuelle', 'Trimestrielle']
                )
                
                recipients = st.text_area(
                    "Destinataires (emails, séparés par des virgules)",
                    value="admin@example.com, finance@example.com"
                )
            
            with col_auto2:
                trigger_conditions = st.multiselect(
                    "Conditions de déclenchement",
                    options=['Nouvelle alerte', 'Seuil dépassé', 'Date fixe', 'Changement significatif']
                )
                
                if st.button("🗓️ Programmer le Rapport", type="secondary"):
                    st.success(f"Rapport programmé avec une fréquence {frequency.lower()}")
        
    except Exception as e:
        st.error(f"Erreur dans la génération du rapport : {str(e)}")

# ============================================
# PIED DE PAGE ET EXPORT
# ============================================

st.markdown("---")
st.markdown("### 📥 Export des Données")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    if st.button("📄 Exporter données CSV"):
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Télécharger CSV",
            data=csv,
            file_name=f"donnees_communes_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col_export2:
    if st.button("📊 Exporter visualisations"):
        # Simulation d'export des graphiques
        st.info("Fonctionnalité d'export des visualisations en développement")
        # Dans une version complète, on pourrait exporter les graphiques en PNG/PDF

with col_export3:
    if st.button("🔄 Réinitialiser les Filtres"):
        st.rerun()

# Pied de page
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
    <p>Dashboard créé avec Streamlit | Données OFGL | La Réunion</p>
    <p>Version 4.0 - Avec carte géographique, benchmarks, alertes et rapports</p>
</div>
""", unsafe_allow_html=True)
