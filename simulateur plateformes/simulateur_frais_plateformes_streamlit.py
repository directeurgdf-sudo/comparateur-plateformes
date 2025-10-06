import math
from dataclasses import dataclass
from typing import List, Dict, Literal

import pandas as pd
import streamlit as st

# ==========================
#  🎨 Thème & Styles GDF (Raleway + Vert #4BAB77)
# ==========================
GDF_GREEN = "#4BAB77"
GDF_TEXT_ON_GREEN = "#FFFFFF"

CUSTOM_CSS = f"""
<style>
/* Police Raleway partout */
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;600;700&display=swap');
html, body, [class^="css"] {{ font-family: 'Raleway', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; }}

/* Sidebar en vert GDF */
section[data-testid="stSidebar"] > div {{
  background:{GDF_GREEN}!important; color:{GDF_TEXT_ON_GREEN}!important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{ color:{GDF_TEXT_ON_GREEN}!important; }}

/* Pastille blanche "Paramètres" */
.sidebar-pill {{
  display:inline-block; background:#FFFFFF; color:#000000;
  padding:8px 14px; border-radius:999px; font-weight:700;
}}

/* Titres façon bouton */
.gdf-btn-title {{
  display:inline-block; padding:10px 16px; border-radius:9999px;
  background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-weight:700;
  letter-spacing: .2px; box-shadow: 0 2px 6px rgba(0,0,0,.08);
}}

/* Table HTML personnalisée */
.gdf-table table {{
  width:100%; border-collapse:collapse; font-size:0.95rem;
}}
.gdf-table th, .gdf-table td {{
  padding:10px 12px; border-bottom:1px solid #eee; text-align:right;
}}
.gdf-table th:first-child, .gdf-table td:first-child {{ text-align:left; }}
.gdf-table thead th {{ background:#fafafa; position:sticky; top:0; z-index:1; }}
.gdf-table .row-gdf td {{ background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-weight:700; }}
.gdf-table td.col-highlight {{ background:#E3F2EA; color:#000; font-weight:700; }}
.badge-gdf {{
  display:inline-block; padding:2px 8px; border-radius:999px; background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-size:.80rem; margin-left:6px;
}}
</style>
"""

# ==========================
#  Modèle
# ==========================
FeeMode = Literal["percentage", "fixed"]

@dataclass
class Platform:
    name: str
    host_commission_pct: float          # ex: 8 pour 8%
    client_fee_mode: FeeMode            # "percentage" (pourcentage du prix de vente) ou "fixed" (forfait fixe)
    client_fee_value: float             # % si percentage, € si fixed

    def client_fee_amount(self, sale_price: float) -> float:
        if self.client_fee_mode == "percentage":
            return sale_price * (self.client_fee_value / 100.0)
        return self.client_fee_value

    def base_before_client_fees(self, sale_price: float) -> float:
        return sale_price - self.client_fee_amount(sale_price)

    def host_net(self, sale_price: float) -> float:
        base = self.base_before_client_fees(sale_price)
        return base * (1 - self.host_commission_pct / 100.0)

# ==========================
#  Config (plateformes figées, sauf GDF)
# ==========================
# Gîtes de France par défaut (nom sans “– Chambre d’hôtes”)
GDF_DEFAULT = Platform(
    name="Gîtes de France",
    host_commission_pct=8.0,
    client_fee_mode="fixed",
    client_fee_value=6.0,
)

# Autres plateformes (non modifiables dans l'UI)
FIXED_PLATFORMS: List[Platform] = [
    Platform("Tripadvisor / FlipKey", host_commission_pct=3.0,  client_fee_mode="percentage", client_fee_value=12.0),
    Platform("Airbnb host-only",      host_commission_pct=15.5, client_fee_mode="percentage", client_fee_value=0.0),
    Platform("Vrbo / Abritel",        host_commission_pct=8.0,  client_fee_mode="percentage", client_fee_value=9.0),
    Platform("Airbnb split",          host_commission_pct=3.0,  client_fee_mode="percentage", client_fee_value=15.0),
    Platform("Booking.com",           host_commission_pct=17.0, client_fee_mode="percentage", client_fee_value=0.0),
    Platform("Holidu",                host_commission_pct=25.0, client_fee_mode="percentage", client_fee_value=0.0),
]

# ==========================
#  UI
# ==========================
st.set_page_config(page_title="Comparateur de plateformes — Gîtes de France", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Titre haut : Classement
st.markdown('<span class="gdf-btn-title">🏆 Classement des plateformes</span>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<span class="sidebar-pill">Paramètres</span>', unsafe_allow_html=True)
    st.write("Seuls les paramètres Gîtes de France sont modifiables. Les autres plateformes sont figées.")

    # Édition GDF uniquement
    gdf_name = st.text_input("Nom affiché", value=GDF_DEFAULT.name)
    host_commission_pct = st.number_input("Commission hôte (%)", min_value=0.0, max_value=100.0, step=0.1, value=GDF_DEFAULT.host_commission_pct)

    mode_label = st.selectbox(
        "Type de frais client",
        options=["pourcentage du prix de vente", "forfait fixe"],
        index=1 if GDF_DEFAULT.client_fee_mode == "fixed" else 0,
    )
    client_fee_mode: FeeMode = "percentage" if mode_label == "pourcentage du prix de vente" else "fixed"
    value_lbl = "%" if client_fee_mode == "percentage" else "€"
    client_fee_value = st.number_input(f"Montant des frais client ({value_lbl})", min_value=0.0, step=0.1, value=GDF_DEFAULT.client_fee_value)

    st.divider()
    # Méthode de saisie (doc: un seul tarif; option net propriétaire)  [comparateur.pdf p.1]
    method = st.radio("Méthode de saisie", ["Prix public payé par le client", "Tarif net propriétaire"], index=0)
    if method == "Prix public payé par le client":
        input_mode = "price_client"
        input_value = st.number_input("Prix public (client)", min_value=0.0, step=50.0, value=1000.0)
    else:
        input_mode = "net_host"
        input_value = st.number_input("Tarif net propriétaire", min_value=0.0, step=50.0, value=850.0)

# Construire plateformes (GDF éditée + figées)
GDF = Platform(gdf_name, host_commission_pct, client_fee_mode, client_fee_value)
PLATFORMS: List[Platform] = [GDF] + FIXED_PLATFORMS

# ==========================
#  Calculs
# ==========================
def compute_table(platforms: List[Platform], input_mode: str, input_value: float) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    for p in platforms:
        h = p.host_commission_pct / 100.0

        # Trouver le prix public P selon la méthode choisie
        if input_mode == "price_client":
            P = float(input_value)
        else:
            # on connaît le Net hôte N et on remonte au prix public P
            N = float(input_value)
            if p.client_fee_mode == "percentage":
                cp = p.client_fee_value / 100.0
                denom = (1 - cp) * (1 - h)
                P = N / denom if denom != 0 else float("inf")
            else:
                f = p.client_fee_value
                denom = (1 - h)
                P = f + (N / denom) if denom != 0 else float("inf")

        # Calculs dérivés
        client_fee = p.client_fee_amount(P)
        base = P - client_fee
        host_comm_eur = base * h
        net = base - host_comm_eur

        method_txt = (
            f"pourcentage du prix de vente ({p.client_fee_value:g}%)"
            if p.client_fee_mode == "percentage"
            else f"forfait fixe ({p.client_fee_value:g} €)"
        )

        rows.append({
            "Plateforme": p.name,
            "Méthode calcul": method_txt,
            "Taux de commission (%)": round(p.host_commission_pct, 2),
            "Frais clients (€)": round(client_fee, 2),
            "Frais hôte (€)": round(host_comm_eur, 2),
            "Net hôte (€)": round(net, 2),
            "Total prix public (client) (€)": round(P, 2),
        })

    df = pd.DataFrame(rows)

    # Mettre GDF en tête
    df["_is_gdf"] = df["Plateforme"].str.lower().str.startswith("gîtes de france")
    df = pd.concat([df[df["_is_gdf"]], df[~df["_is_gdf"]]]).drop(columns=["_is_gdf"])
    return df

DF = compute_table(PLATFORMS, input_mode, input_value)

# ==========================
#  Rendu HTML stylé (mise en avant GDF + colonnes surlignées)
# ==========================
def table_to_html(df: pd.DataFrame) -> str:
    thead = "<thead><tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr></thead>"
    rows_html = []
    for _, row in df.iterrows():
        is_gdf = str(row["Plateforme"]).lower().startswith("gîtes de france")
        tr_class = "row-gdf" if is_gdf else ""
        tds = []
        for col in df.columns:
            val = row[col]
            if isinstance(val, float):
                text = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                text = str(val)
            cls = ""
            if col in ("Net hôte (€)", "Total prix public (client) (€)"):
                cls = "col-highlight"
            if col == "Plateforme" and is_gdf:
                text = f"{text} <span class='badge-gdf'>GDF</span>"
            tds.append(f"<td class='{cls}'>{text}</td>")
        rows_html.append(f"<tr class='{tr_class}'>" + "".join(tds) + "</tr>")
    tbody = "<tbody>" + "".join(rows_html) + "</tbody>"
    return f"<div class='gdf-table'><table>{thead}{tbody}</table></div>"

# ==========================
#  Affichage (classement en haut, tableau comparatif en bas)
# ==========================
# Classement pour le tarif unique
sub = DF.copy()
sub_net = sub.sort_values("Net hôte (€)", ascending=False).reset_index(drop=True)
sub_price = sub.sort_values("Total prix public (client) (€)").reset_index(drop=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Top net hôte**")
    st.markdown(table_to_html(sub_net[["Plateforme", "Net hôte (€)"]]), unsafe_allow_html=True)
with c2:
    st.markdown("**Prix public le plus bas**")
    st.markdown(table_to_html(sub_price[["Plateforme", "Total prix public (client) (€)"]]), unsafe_allow_html=True)

# Tableau comparatif
st.markdown('<span class="gdf-btn-title">📋 Tableau comparatif</span>', unsafe_allow_html=True)
st.markdown(table_to_html(DF), unsafe_allow_html=True)

# ==========================
#  Exports
# ==========================
col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        label="Télécharger le tableau (CSV)",
        data=DF.to_csv(index=False).encode("utf-8"),
        file_name="comparatif_plateformes.csv",
        mime="text/csv",
    )
with col_b:
    cfg = pd.DataFrame([{
        "Plateforme": GDF.name,
        "Commission hôte (%)": GDF.host_commission_pct,
        "Type frais client": "pourcentage du prix de vente" if GDF.client_fee_mode == "percentage" else "forfait fixe",
        "Valeur frais client": GDF.client_fee_value,
        "Méthode de saisie": "Prix public (client)" if input_mode == "price_client" else "Tarif net propriétaire",
        "Valeur saisie": input_value,
    }])
    st.download_button(
        label="Exporter les paramètres GDF (CSV)",
        data=cfg.to_csv(index=False).encode("utf-8"),
        file_name="gdf_config.csv",
        mime="text/csv",
    )

st.caption("Formules : "
           "Base avant frais client = Prix public − Frais clients ·· "
           "Net hôte = Base × (1 − commission hôte) ·· "
           "Si saisie 'net hôte', on remonte le prix public selon la méthode (pourcentage ou fixe).")
