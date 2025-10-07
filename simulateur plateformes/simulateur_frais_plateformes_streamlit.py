import math
from dataclasses import dataclass
from typing import List, Dict, Literal, Optional, Tuple

import pandas as pd
import streamlit as st

# ==========================
#  🎨 Thème & Styles GDF (Raleway + Vert #4BAB77)
# ==========================
GDF_GREEN = "#4BAB77"
GDF_DARK = "#00653F"  # pour sélecteurs
GDF_TEXT_ON_GREEN = "#FFFFFF"  # texte noir dans les pastilles, cf. maquette

CUSTOM_CSS = f"""
<style>
/* Police Raleway partout */
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;600;700&display=swap');
html, body, [class^="css"] {{ font-family: 'Raleway', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; }}

/* Sidebar en vert GDF */
section[data-testid="stSidebar"] > div {{
  background:{GDF_GREEN}!important; color:#FFFFFF!important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{ color:#FFFFFF!important; }}

/* Titres façon bouton (texte noir sur vert) */
.gdf-btn-title {{
  display:inline-block; padding:10px 16px; border-radius:9999px;
  background:{GDF_GREEN}; color:{GDF_TEXT_ON_GREEN}; font-weight:700;
  letter-spacing:.2px; box-shadow:0 2px 6px rgba(0,0,0,.08);
}}

/* Table HTML personnalisée */
.gdf-table table {{ width:100%; border-collapse:collapse; font-size:0.95rem; }}
.gdf-table th, .gdf-table td {{ padding:10px 12px; border-bottom:1px solid #eee; text-align:right; }}
.gdf-table th:first-child, .gdf-table td:first-child {{ text-align:left; }}
.gdf-table thead th {{ background:#fafafa; position:sticky; top:0; z-index:1; }}
.gdf-table .row-gdf td {{ background:{GDF_GREEN}; color:#FFFFFF; font-weight:700; }}
.gdf-table td.col-highlight {{ background:#E3F2EA; color:#000; font-weight:700; }}
.badge-gdf {{ display:inline-block; padding:2px 8px; border-radius:999px; background:{GDF_GREEN}; color:#000; font-size:.80rem; margin-left:6px; border:1px solid rgba(0,0,0,.15); }}
/* Forcer la couleur des sélecteurs (accent #00653F) */
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{ border-color:#00653F!important; }}
section[data-testid="stSidebar"] .stSelectbox svg {{ fill:#00653F!important; color:#00653F!important; }}
</style>
"""

# ==========================
#  Modèle
# ==========================
FeeMode = Literal["percentage", "fixed"]

@dataclass
class Platform:
    name: str
    host_commission_pct: float          # % côté hôte
    client_fee_mode: FeeMode            # "percentage" ou "fixed"
    client_fee_value: float             # % si percentage, € si fixed
    client_fee_floor_eur: float = 0.0   # plancher quand percentage
    client_fee_cap_eur: Optional[float] = None  # plafond quand percentage (None = pas de plafond)

    def client_fee_amount(self, sale_price: float) -> float:
        """Frais client en € selon le mode, avec plancher/plafond éventuels."""
        if self.client_fee_mode == "percentage":
            pct_val = sale_price * (self.client_fee_value / 100.0)
            floor = float(self.client_fee_floor_eur or 0.0)
            cap = float(self.client_fee_cap_eur) if self.client_fee_cap_eur is not None else None
            fee = max(pct_val, floor)
            if cap is not None:
                fee = min(fee, cap)
            return fee
        return self.client_fee_value

    def base_before_client_fees(self, sale_price: float) -> float:
        return sale_price - self.client_fee_amount(sale_price)

    def host_net(self, sale_price: float) -> float:
        base = self.base_before_client_fees(sale_price)
        return base * (1 - self.host_commission_pct / 100.0)

# --- Inversion pour retrouver P (prix public) à partir du net N ---

def _solve_price_from_net_percentage(N: float, h: float, cp: float, floor: float, cap: Optional[float]) -> float:
    """Résout P pour N avec frais client en %, incluant plancher/plafond.
    Régimes testés: floor, plafond, proportionnel. On retourne le P cohérent minimal.
    """
    candidates: List[Tuple[float, str]] = []
    # 1) plancher actif
    P_floor = N / (1 - h) + floor
    if cp * P_floor <= floor + 1e-9:
        candidates.append((P_floor, "floor"))
    # 2) plafond actif
    if cap is not None:
        P_cap = N / (1 - h) + cap
        if cp * P_cap >= cap - 1e-9:
            candidates.append((P_cap, "cap"))
    # 3) proportionnel
    denom = (1 - cp) * (1 - h)
    if denom <= 0:
        denom = 1e-12
    P_pct = N / denom
    ok_low = (cp * P_pct >= floor - 1e-9)
    ok_high = True if cap is None else (cp * P_pct <= cap + 1e-9)
    if ok_low and ok_high:
        candidates.append((P_pct, "pct"))
    return min((p for p, _ in candidates), default=max(P_floor, P_pct))


def price_from_net(platform: Platform, net: float) -> float:
    h = platform.host_commission_pct / 100.0
    if platform.client_fee_mode == "percentage":
        cp = platform.client_fee_value / 100.0
        floor = float(platform.client_fee_floor_eur or 0.0)
        cap = float(platform.client_fee_cap_eur) if platform.client_fee_cap_eur is not None else None
        return _solve_price_from_net_percentage(net, h, cp, floor, cap)
    else:
        # frais fixe f : N = (P - f)*(1-h)  =>  P = f + N/(1-h)
        denom = (1 - h)
        return (platform.client_fee_value + net / denom) if denom != 0 else float("inf")

# ==========================
#  Config (plateformes figées, sauf GDF)
# ==========================
GDF_DEFAULT = Platform(
    name="Gîtes de France",
    host_commission_pct=8.0,
    client_fee_mode="fixed",
    client_fee_value=6.0,
)

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
# Overrides CSS ciblés (pas de f-string -> pas besoin de doubler les accolades)
st.markdown("""
<style>
/* Couleur primaire Streamlit (impacte radio/checkbox/accents) */
:root { --primary-color: #00653F; }

/* Accent sélecteurs (dropdowns) dans la sidebar */
section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div { border-color:#00653F !important; box-shadow:0 0 0 1px #00653F1A !important; }
section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:focus { box-shadow:0 0 0 2px #00653F66 !important; border-color:#00653F !important; }
section[data-testid="stSidebar"] .stSelectbox svg { color:#00653F !important; fill:#00653F !important; }

/* Radio & checkbox en vert GDF (au lieu de rouge) */
section[data-testid="stSidebar"] input[type="radio"],
section[data-testid="stSidebar"] input[type="checkbox"] { accent-color:#00653F !important; }

/* Champs texte/numériques: bordure/focus en vert */
section[data-testid="stSidebar"] input:focus, 
section[data-testid="stSidebar"] textarea:focus { border-color:#00653F !important; box-shadow:0 0 0 2px rgba(0,101,63,0.35) !important; outline:none !important; }

/* Boutons + / - des number_input en vert */
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button { background:#4BAB77 !important; border-color:#4BAB77 !important; color:#FFFFFF !important; }

/* Force la ligne GDF en vert (tous tableaux rendus) */
.gdf-table .row-gdf td { background:#4BAB77 !important; color:#FFFFFF !important; font-weight:700; }

/* Titre-badge vert lisible en blanc */
.gdf-btn-title { color:#FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# Titre haut : Classement
st.title("🏆 Comparateurs de frais de réservation")

with st.sidebar:
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

st.caption("Formules : Base avant frais client = Prix public − Frais clients ·· Net propriétaire = Base × (1 − commission propriétaire). Si saisie 'net propriétaire', le prix public est recalculé en tenant compte du type de frais client (%, plancher/plafond éventuels ou forfait).")

# 🔧 Forcer EN DERNIER la couleur verte des radios/checkbox (après l'hydratation Streamlit)
st.markdown("""
<style>
section[data-testid="stSidebar"] input[type="radio"],
section[data-testid="stSidebar"] input[type="checkbox"],
div[data-testid="stSidebar"] [role="radiogroup"] input[type="radio"],
div[data-testid="stSidebar"] [data-baseweb="radio"] input[type="radio"] {
  accent-color:#00653F !important;
}
</style>
""", unsafe_allow_html=True)

# Renfort couleur VERT sur radios/checkbox (BaseWeb) + icônes SVG (fin de script)
st.markdown("""
<style>
/* Radios (BaseWeb) : cercle et point sélectionné */
section[data-testid="stSidebar"] [data-baseweb="radio"] svg { color:#00653F !important; fill:#00653F !important; }
section[data-testid="stSidebar"] [role="radiogroup"] svg { color:#00653F !important; fill:#00653F !important; }
section[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div svg { color:#00653F !important; fill:#00653F !important; }

/* Checkbox (BaseWeb) */
section[data-testid="stSidebar"] [data-baseweb="checkbox"] svg { color:#00653F !important; fill:#00653F !important; }
section[data-testid="stSidebar"] [data-baseweb="checkbox"] input:checked + div svg { color:#00653F !important; fill:#00653F !important; }

/* Fallback accent-color */
section[data-testid="stSidebar"] input[type="radio"],
section[data-testid="stSidebar"] input[type="checkbox"] { accent-color:#00653F !important; }
</style>
""", unsafe_allow_html=True)
