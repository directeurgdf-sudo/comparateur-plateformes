import math
from dataclasses import dataclass
from typing import List, Dict, Literal

import pandas as pd
import streamlit as st

# ==========================
#  🎨 Thème & Styles GDF (RaleWay + Vert #4BAB77)
# ==========================
GDF_GREEN = "#4BAB77"  # vert GDF demandé
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
section[data-testid="stSidebar"] .stSlider > div > div > div {{ color:{GDF_TEXT_ON_GREEN}!important; }}

/***** Titres façon bouton *****/
.gdf-btn-title {{
  display:inline-block; padding:10px 16px; border-radius:9999px;
  background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-weight:700;
  letter-spacing: .2px; box-shadow: 0 2px 6px rgba(0,0,0,.08);
}}

/***** Table HTML personnalisée *****/
.gdf-table table {{
  width:100%; border-collapse:collapse; font-size:0.95rem;
}}
.gdf-table th, .gdf-table td {{
  padding:10px 12px; border-bottom:1px solid #eee; text-align:right;
}}
.gdf-table th:first-child, .gdf-table td:first-child {{ text-align:left; }}
.gdf-table thead th {{ background:#fafafa; position:sticky; top:0; z-index:1; }}
.gdf-table .row-gdf td {{ background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-weight:700; }}
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
    host_commission_pct: float  # ex: 8 pour 8%
    client_fee_mode: FeeMode    # "percentage" (pourcentage du prix de vente) ou "fixed" (forfait fixe)
    client_fee_value: float     # % si percentage, € si fixed

    def client_fee_amount(self, sale_price: float) -> float:
        if self.client_fee_mode == "percentage":
            return sale_price * (self.client_fee_value / 100.0)
        return self.client_fee_value

    def base_before_client_fees(self, sale_price: float) -> float:
        return sale_price - self.client_fee_amount(sale_price)

    def host_net(self, sale_price: float) -> float:
        base = self.base_before_client_fees(sale_price)
        return base * (1 - self.host_commission_pct / 100.0)

    def global_fees(self, sale_price: float) -> float:
        return sale_price - self.host_net(sale_price)


# ==========================
#  Config (plateformes figées, sauf GDF)
# ==========================
# Gîtes de France (éditable dans la barre latérale)
GDF_DEFAULT = Platform(
    name="Gîtes de France – Chambre d'hôtes",
    host_commission_pct=8.0,
    client_fee_mode="fixed",
    client_fee_value=6.0,
)

# Autres plateformes (non modifiables dans l'UI)
FIXED_PLATFORMS: List[Platform] = [
    Platform("Tripadvisor / FlipKey", host_commission_pct=3.0, client_fee_mode="percentage", client_fee_value=12.0),
    Platform("Airbnb host-only", host_commission_pct=15.5, client_fee_mode="percentage", client_fee_value=0.0),
    Platform("Vrbo / Abritel", host_commission_pct=8.0, client_fee_mode="percentage", client_fee_value=9.0),
    Platform("Airbnb split", host_commission_pct=3.0, client_fee_mode="percentage", client_fee_value=15.0),
    Platform("Booking.com", host_commission_pct=17.0, client_fee_mode="percentage", client_fee_value=0.0),
    Platform("Holidu", host_commission_pct=25.0, client_fee_mode="percentage", client_fee_value=0.0),
]

DEFAULT_PRICE_POINTS = [100, 300, 500, 1000, 1500, 2000]

# ==========================
#  UI
# ==========================
st.set_page_config(page_title="Comparateur de plateformes — Gîtes de France", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Nouveau titre remplacé
st.markdown('<span class="gdf-btn-title">🏆 Classement des plateformes</span>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<span class="gdf-btn-title">⚙️ Paramètres Gîtes de France</span>', unsafe_allow_html=True)
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

    prices_txt = st.text_input("Prix de vente testés (séparés par des virgules)", value=", ".join(str(p) for p in DEFAULT_PRICE_POINTS))

# Parse prix
_def_prices = []
for chunk in prices_txt.replace(";", ",").split(","):
    s = chunk.strip().replace("€", "").replace(" ", "")
    if not s:
        continue
    try:
        _def_prices.append(float(s))
    except ValueError:
        pass
PRICE_POINTS = sorted(list({round(x, 2) for x in (_def_prices or DEFAULT_PRICE_POINTS)}))

# Construire la liste finale des plateformes (GDF éditée + autres figées)
GDF = Platform(gdf_name, host_commission_pct, client_fee_mode, client_fee_value)
PLATFORMS: List[Platform] = [GDF] + FIXED_PLATFORMS

# ==========================
#  Calculs
# ==========================

def compute_table(platforms: List[Platform], prices: List[float]) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    for p in platforms:
        for price in prices:
            client_fee = round(p.client_fee_amount(price), 2)
            base = round(p.base_before_client_fees(price), 2)
            net = round(p.host_net(price), 2)
            total_fees = round(p.global_fees(price), 2)
            rows.append({
                "Plateforme": p.name,
                "Barème appliqué": f"Hôte {p.host_commission_pct:g}% | Client " + (f"{p.client_fee_value:g}%" if p.client_fee_mode == "percentage" else f"{p.client_fee_value:g} €"),
                "Prix de vente (client)": price,
                "Frais client (€)": client_fee,
                "Base avant frais client": base,
                "Net hôte (€)": net,
                "Frais globaux (€)": total_fees,
            })
    df = pd.DataFrame(rows)
    df = df.sort_values(["Plateforme", "Prix de vente (client)"]).reset_index(drop=True)
    return df

DF = compute_table(PLATFORMS, PRICE_POINTS)

# ==========================
#  Rendu HTML stylé (mise en avant GDF)
# ==========================

def table_to_html(df: pd.DataFrame) -> str:
    # Build header
    thead = "<thead><tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr></thead>"
    rows_html = []
    for _, row in df.iterrows():
        is_gdf = str(row["Plateforme"]).lower().startswith("gîtes de france")
        tr_class = "row-gdf" if is_gdf else ""
        tds = []
        for col in df.columns:
            val = row[col]
            if isinstance(val, float) and col != "Prix de vente (client)":
                text = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            elif col == "Prix de vente (client)":
                text = f"{int(val)} €" if float(val).is_integer() else f"{val} €"
            else:
                text = str(val)
            # ajouter badge GDF à la 1ère col
            if col == "Plateforme" and is_gdf:
                text = f"{text} <span class='badge-gdf'>GDF</span>"
            tds.append(f"<td>{text}</td>")
        rows_html.append(f"<tr class='{tr_class}'>" + "".join(tds) + "</tr>")
    tbody = "<tbody>" + "".join(rows_html) + "</tbody>"
    return f"<div class='gdf-table'><table>{thead}{tbody}</table></div>"

# ==========================
#  Affichage (classements en haut, tableau comparatif en bas)
# ==========================

# CLASSEMENTS EN HAUT
for price in PRICE_POINTS:
    sub = DF[DF["Prix de vente (client)"] == price].copy()
    sub_net = sub.sort_values("Net hôte (€)", ascending=False).reset_index(drop=True)
    sub_fees = sub.sort_values("Frais globaux (€)").reset_index(drop=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Top net hôte – {int(price)} €**")
        st.markdown(table_to_html(sub_net[["Plateforme", "Net hôte (€)"]]), unsafe_allow_html=True)
    with c2:
        st.markdown(f"**Frais globaux les plus faibles – {int(price)} €**")
        st.markdown(table_to_html(sub_fees[["Plateforme", "Frais globaux (€)"]]), unsafe_allow_html=True)

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
    cfg = pd.DataFrame([
        {
            "Plateforme": GDF.name,
            "Commission hôte (%)": GDF.host_commission_pct,
            "Type frais client": "pourcentage du prix de vente" if GDF.client_fee_mode == "percentage" else "forfait fixe",
            "Valeur frais client": GDF.client_fee_value,
        }
    ])
    st.download_button(
        label="Exporter les paramètres GDF (CSV)",
        data=cfg.to_csv(index=False).encode("utf-8"),
        file_name="gdf_config.csv",
        mime="text/csv",
    )

st.caption(
    "Formules : Base avant frais client = Prix de vente − Frais client ·· Net hôte = Base × (1 − commission hôte) ·· Frais globaux = Prix − Net hôte."
)
