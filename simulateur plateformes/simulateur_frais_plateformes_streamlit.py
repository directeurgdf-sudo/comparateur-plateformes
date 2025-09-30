import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Literal

import pandas as pd
import streamlit as st

# ------------------------------
# Modèle de données
# ------------------------------
FeeMode = Literal["percentage", "fixed"]

@dataclass
class Platform:
    name: str
    host_commission_pct: float  # ex: 8 pour 8%
    client_fee_mode: FeeMode  # "percentage" ou "fixed"
    client_fee_value: float   # % si percentage, € si fixed
    notes: str = ""

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


# ------------------------------
# Config par défaut (à adapter)
# ------------------------------
DEFAULT_PLATFORMS: List[Platform] = [
    Platform(
        name="Gîtes de France Chambre d'hôtes 8%",
        host_commission_pct=8.0,
        client_fee_mode="fixed",
        client_fee_value=6.0,
        notes="Commission hôte 8% + frais client fixes 6€",
    ),
    Platform(
        name="Tripadvisor / FlipKey",
        host_commission_pct=3.0,
        client_fee_mode="percentage",
        client_fee_value=12.0,
        notes="Exemple: 3% hôte, ~12% client (à ajuster)",
    ),
    Platform(
        name="Airbnb host-only",
        host_commission_pct=15.5,
        client_fee_mode="percentage",
        client_fee_value=0.0,
        notes="Modèle host-only: 15.5% hôte, 0% client",
    ),
    Platform(
        name="Vrbo / Abritel",
        host_commission_pct=8.0,
        client_fee_mode="percentage",
        client_fee_value=9.0,
        notes="Exemple: 8% hôte, ~9% client (à affiner)",
    ),
    Platform(
        name="Airbnb split",
        host_commission_pct=3.0,
        client_fee_mode="percentage",
        client_fee_value=15.0,
        notes="Split: 3% hôte + ~15% client",
    ),
    Platform(
        name="Booking.com",
        host_commission_pct=17.0,
        client_fee_mode="percentage",
        client_fee_value=0.0,
        notes="Commission hôte 17%, pas de frais client",
    ),
    Platform(
        name="Holidu",
        host_commission_pct=25.0,
        client_fee_mode="percentage",
        client_fee_value=0.0,
        notes="Commission hôte 25%, pas de frais client",
    ),
]

DEFAULT_PRICE_POINTS = [100, 300, 500, 1000, 1500, 2000]

# ------------------------------
# UI
# ------------------------------
st.set_page_config(page_title="Simulateur – Frais plateformes", layout="wide")
st.title("📊 Simulateur de commissions et frais client – Plateformes")

st.markdown(
    """
Ce simulateur compare le **net hôte** et les **frais globaux** pour plusieurs plateformes
à différents **prix de vente (payés par le client)**.

**Formules**  
- Base avant frais client = Prix de vente − Frais client  
- Net hôte = (Base avant frais client) × (1 − commission hôte)  
- Frais globaux = Prix de vente − Net hôte

Ajustez les hypothèses dans la barre latérale.
"""
)

with st.sidebar:
    st.header("⚙️ Paramètres")

    # Liste des prix
    custom_prices = st.text_input(
        "Prix de vente à tester (séparés par des virgules)",
        value=", ".join(str(p) for p in DEFAULT_PRICE_POINTS),
    )
    # parse
    def parse_prices(txt: str) -> List[float]:
        out = []
        for chunk in txt.replace(";", ",").split(","):
            s = chunk.strip().replace("€", "").replace(" ", "")
            if not s:
                continue
            try:
                out.append(float(s))
            except ValueError:
                pass
        return sorted(list({round(x, 2) for x in out}))

    price_points = parse_prices(custom_prices) or DEFAULT_PRICE_POINTS

    st.divider()
    st.subheader("Plateformes")

    # Édition des plateformes
    edited_platforms: List[Platform] = []

    for i, p in enumerate(DEFAULT_PLATFORMS):
        with st.expander(f"{p.name}", expanded=(i == 0)):
            name = st.text_input(f"Nom {i+1}", value=p.name, key=f"name_{i}")
            host_commission_pct = st.number_input(
                f"Commission hôte (%) — {name}", min_value=0.0, max_value=100.0, step=0.1,
                value=p.host_commission_pct, key=f"host_{i}"
            )
            mode = st.selectbox(
                f"Type de frais client — {name}", ["percentage", "fixed"],
                index=0 if p.client_fee_mode == "percentage" else 1, key=f"mode_{i}"
            )
            value_lbl = "%" if mode == "percentage" else "€"
            client_fee_value = st.number_input(
                f"Montant frais client ({value_lbl}) — {name}", min_value=0.0, step=0.1,
                value=p.client_fee_value, key=f"client_{i}"
            )
            notes = st.text_input(f"Notes — {name}", value=p.notes, key=f"notes_{i}")

            edited_platforms.append(
                Platform(
                    name=name,
                    host_commission_pct=host_commission_pct,
                    client_fee_mode=mode,  # type: ignore[arg-type]
                    client_fee_value=client_fee_value,
                    notes=notes,
                )
            )

# ------------------------------
# Calculs
# ------------------------------

def compute_table(platforms: List[Platform], prices: List[float]) -> pd.DataFrame:
    rows: List[Dict[str, float]] = []
    for p in platforms:
        for price in prices:
            client_fee = round(p.client_fee_amount(price), 2)
            base = round(p.base_before_client_fees(price), 2)
            net = round(p.host_net(price), 2)
            total_fees = round(p.global_fees(price), 2)
            rows.append({
                "Plateforme": p.name,
                "Barème appliqué": f"Hôte {p.host_commission_pct:g}% | Client " +
                    (f"{p.client_fee_value:g}%" if p.client_fee_mode == "percentage" else f"{p.client_fee_value:g} €"),
                "Prix de vente (client)": price,
                "Frais client (€)": client_fee,
                "Base avant frais client": base,
                "Net hôte (€)": net,
                "Frais globaux (€)": total_fees,
            })
    df = pd.DataFrame(rows)
    # Tri par plateforme puis prix
    df = df.sort_values(["Plateforme", "Prix de vente (client)"]).reset_index(drop=True)
    return df


df = compute_table(edited_platforms, price_points)

# ------------------------------
# Affichage
# ------------------------------

st.subheader("Tableau comparatif")
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Prix de vente (client)": st.column_config.NumberColumn("Prix de vente (client)", step=1, format="%d €"),
        "Frais client (€)": st.column_config.NumberColumn(format="%.2f €"),
        "Base avant frais client": st.column_config.NumberColumn(format="%.2f €"),
        "Net hôte (€)": st.column_config.NumberColumn(format="%.2f €"),
        "Frais globaux (€)": st.column_config.NumberColumn(format="%.2f €"),
    }
)

# Résumés pour chaque prix
st.subheader("Classements par prix")
for price in price_points:
    sub = df[df["Prix de vente (client)"] == price].copy()
    sub_net = sub.sort_values("Net hôte (€)", ascending=False)
    sub_fees = sub.sort_values("Frais globaux (€)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Top net hôte – {int(price)} €**")
        st.table(sub_net[["Plateforme", "Net hôte (€)"]].reset_index(drop=True))
    with c2:
        st.markdown(f"**Frais globaux les plus faibles – {int(price)} €**")
        st.table(sub_fees[["Plateforme", "Frais globaux (€)"]].reset_index(drop=True))

# Export
st.subheader("Export")
col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        label="Télécharger le tableau (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="comparatif_plateformes.csv",
        mime="text/csv",
    )
with col_b:
    st.download_button(
        label="Télécharger les paramètres (JSON)",
        data=pd.DataFrame([asdict(p) for p in edited_platforms]).to_json(orient="records", force_ascii=False).encode("utf-8"),
        file_name="plateformes_config.json",
        mime="application/json",
    )

st.caption(
    "💡 Remarque : adaptez les taux/valeurs selon les sources officielles. Les résultats de la simulation dépendent de ces hypothèses."
)
