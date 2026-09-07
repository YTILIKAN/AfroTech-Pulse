# dashboard/theme.py — Charte visuelle partagée du dashboard : couleurs de marque et
# gabarit Plotly commun aux trois graphiques (formes = magnitude / géographie / temps,
# donc une seule teinte séquentielle, pas de palette catégorielle).

import plotly.graph_objects as go
import plotly.io as pio

# --- Palette de marque ---
ENCRE = "#1C1A17"          # texte principal
ENCRE_DOUCE = "#6B655C"    # texte secondaire, axes
SURFACE = "#FCFCFB"
SURFACE_CARTE = "#F4F1EC"
GRILLE = "#E7E2D9"
TERRE = "#EFEBE2"          # fond des pays sur la carte
ACCENT = "#E0561F"         # couleur « signal » (validée CVD + contraste)

# Échelle séquentielle : une seule teinte chaude, clair -> foncé (magnitude).
ECHELLE_SEQ = [
    [0.00, "#FBEEDF"],
    [0.25, "#F1C89B"],
    [0.50, "#E39A5E"],
    [0.75, "#CB6234"],
    [1.00, "#8A2D19"],
]

POLICE = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

_template = go.layout.Template()
_template.layout = go.Layout(
    font=dict(family=POLICE, size=13, color=ENCRE),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=8, t=8, b=8),
    colorway=[ACCENT],
    xaxis=dict(showgrid=False, zeroline=False, linecolor=GRILLE, ticks="outside",
               tickcolor=GRILLE, color=ENCRE_DOUCE, title_font=dict(size=12)),
    yaxis=dict(showgrid=True, gridcolor=GRILLE, zeroline=False,
               linecolor="rgba(0,0,0,0)", color=ENCRE_DOUCE, title_font=dict(size=12)),
    hoverlabel=dict(bgcolor=ENCRE, bordercolor=ENCRE,
                    font=dict(color="#FFFFFF", family=POLICE, size=12)),
    geo=dict(bgcolor="rgba(0,0,0,0)", landcolor=TERRE, lakecolor="rgba(0,0,0,0)",
             showframe=False, showcoastlines=False, showcountries=True,
             countrycolor="#FFFFFF"),
    coloraxis=dict(colorbar=dict(thickness=10, outlinewidth=0, len=0.7,
                                 tickfont=dict(color=ENCRE_DOUCE, size=11),
                                 title=dict(font=dict(color=ENCRE_DOUCE, size=11)))),
)
pio.templates["afrotech"] = _template

# Config passée à st.plotly_chart : dashboard public, pas d'édition -> barre d'outils masquée.
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}


def styliser(fig, hauteur=None):
    """Applique le gabarit Plotly de la marque à une figure et la retourne.

    Fixe le template `afrotech` (palette, typographie, axes, infobulles) et masque la
    légende. `hauteur` force la hauteur en pixels quand elle dépend du nombre de barres.
    """
    fig.update_layout(template="afrotech", showlegend=False)
    if hauteur is not None:
        fig.update_layout(height=hauteur)
    return fig
