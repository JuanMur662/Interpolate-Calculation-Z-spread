"""
Fair Z-spread Calculator for new corporate bond issues.

Three methodologies:
  1. Interpolation  -> target tenor BETWEEN issuer's existing bonds
  2. Extrapolation  -> target tenor OUTSIDE issuer's range (anchor + sector shape)
  3. Proxy curve    -> brand-new issuer (peer median + adjustments)

Run locally:
    pip install -r requirements.txt
    streamlit run fair_spread_calculator.py

Deploy free public link:
    Push to GitHub -> connect at https://share.streamlit.io

Built for credit research / portfolio management workflows.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Fair Z-spread Calculator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1300px; }
    .result-box {
        background: #f5f5f4;
        padding: 20px 24px;
        border-radius: 12px;
        margin: 8px 0 16px;
        border-left: 4px solid #185FA5;
    }
    .result-num { font-size: 36px; font-weight: 600; color: #185FA5; line-height: 1.1; }
    .result-label { font-size: 13px; color: #6b6b69; margin-bottom: 4px; }
    h1 { font-weight: 600; }
    .stTabs [data-baseweb="tab"] { padding: 10px 18px; font-size: 15px; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Core math
# ------------------------------------------------------------------
def linear_interp(df: pd.DataFrame, target: float):
    """Linear interpolation on a (tenor, spread) DataFrame. Returns None if outside range."""
    pts = df.sort_values("tenor").reset_index(drop=True)
    if pts.empty:
        return None
    if len(pts) == 1:
        return float(pts.iloc[0]["spread"])

    exact = pts[pts["tenor"] == target]
    if not exact.empty:
        return float(exact.iloc[0]["spread"])

    for i in range(len(pts) - 1):
        x1, x2 = pts.iloc[i]["tenor"], pts.iloc[i + 1]["tenor"]
        if x1 <= target <= x2:
            y1, y2 = pts.iloc[i]["spread"], pts.iloc[i + 1]["spread"]
            w = (target - x1) / (x2 - x1) if x2 != x1 else 0
            return float(y1 + w * (y2 - y1))
    return None


def make_chart(issuer=None, sector=None, peers=None, target=None,
               implied_curve=None, peer_median=None, height=420):
    """Build the curve visualization."""
    fig = go.Figure()

    if implied_curve is not None and len(implied_curve) > 0:
        c = implied_curve.sort_values("tenor")
        fig.add_trace(go.Scatter(
            x=c["tenor"], y=c["spread"], mode="lines",
            name="Implied issuer curve", line=dict(color="#D85A30", width=2, dash="dot")
        ))

    if issuer is not None and len(issuer) > 0:
        s = issuer.sort_values("tenor")
        fig.add_trace(go.Scatter(
            x=s["tenor"], y=s["spread"], mode="lines+markers",
            name="Issuer bonds",
            line=dict(color="#185FA5", width=2.5),
            marker=dict(size=12, color="#185FA5", line=dict(width=1, color="white")),
        ))

    if sector is not None and len(sector) > 0:
        s = sector.sort_values("tenor")
        fig.add_trace(go.Scatter(
            x=s["tenor"], y=s["spread"], mode="lines+markers",
            name="Sector / peer curve",
            line=dict(color="#888780", width=1.5, dash="dash"),
            marker=dict(size=8, color="#888780"),
        ))

    if peers is not None and len(peers) > 0:
        text = peers["issuer"] if "issuer" in peers.columns else None
        fig.add_trace(go.Scatter(
            x=peers["tenor"], y=peers["spread"], mode="markers",
            name="Peers",
            marker=dict(size=12, color="#888780", line=dict(width=1, color="white")),
            text=text,
            hovertemplate="<b>%{text}</b><br>%{y:.0f} bps<extra></extra>" if text is not None else None,
        ))

    if peer_median is not None:
        fig.add_hline(y=peer_median, line_dash="dot", line_color="#888780",
                      annotation_text=f"Peer median: {peer_median:.0f} bps",
                      annotation_position="top right")

    if target is not None:
        fig.add_trace(go.Scatter(
            x=[target["tenor"]], y=[target["spread"]], mode="markers",
            name="Fair Z-spread (new)",
            marker=dict(size=22, color="#D85A30", symbol="star",
                        line=dict(width=2, color="white")),
        ))

    fig.update_layout(
        height=height,
        xaxis_title="Tenor (years)",
        yaxis_title="Z-spread (bps)",
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        margin=dict(l=50, r=20, t=20, b=60),
        template="plotly_white",
        hovermode="closest",
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=12),
    )
    fig.update_xaxes(gridcolor="#e8e8e6")
    fig.update_yaxes(gridcolor="#e8e8e6")
    return fig


def export_to_excel(scenario_name: str, summary: dict, inputs: dict) -> bytes:
    """Export scenario to a multi-sheet Excel."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([summary]).to_excel(writer, sheet_name="Summary", index=False)
        for sheet_name, df in inputs.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


# ------------------------------------------------------------------
# Sidebar — methodology + global notes
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Methodology")
    st.markdown("""
**Three pricing methods, depending on data:**

**1. Interpolate** — target tenor sits *between* issuer's bonds.
Pure linear interpolation on Z-spreads.

**2. Extrapolate** — target tenor is *outside* issuer's range.
- **Level** anchor = issuer's nearest bond
- **Shape** = sector / peer curve slope
- Add liquidity / extrapolation premium (10–30 bps typical)

**3. Proxy** — brand-new issuer with no curve.
- Median of comparable peers
- Plus issuer-specific adjustments (size, debut, leverage, covenants)
- Optional: build full curve using sector slopes
    """)
    st.divider()
    st.markdown("""
**Rule of thumb**

> *Interpolation = science  
> Extrapolation = art  
> Proxy = judgment*

Always sanity-check against:
- Sovereign + sector + rating triangle
- New-issue concession (10–25 bps typical)
- Trader gut-check
    """)
    st.divider()
    st.caption("Built for credit research workflows. Illustrative only — confirm with your own framework before pricing real trades.")


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("Fair Z-spread Calculator")
st.markdown(
    "<p style='color: #6b6b69; margin-top: -10px;'>"
    "Pricing new corporate bond issues across three real-world scenarios.</p>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["📊 Interpolate", "📈 Extrapolate", "🆕 New issuer (proxy)"])

# ==================================================================
# TAB 1 — INTERPOLATE
# ==================================================================
with tab1:
    st.markdown("##### Use when the new issue tenor falls *between* the issuer's existing bonds.")
    st.write("")

    col1, col2 = st.columns([1, 1.3], gap="large")

    with col1:
        target_t1 = st.number_input(
            "Target tenor (years)", value=6.0, min_value=0.25, max_value=50.0, step=0.25, key="t1"
        )

        st.markdown("**Issuer's existing bonds**")
        default_bonds_1 = pd.DataFrame({
            "tenor": [3.0, 5.0, 7.0, 10.0],
            "spread": [150.0, 200.0, 240.0, 280.0],
        })
        bonds_1 = st.data_editor(
            default_bonds_1, num_rows="dynamic", key="bonds1",
            use_container_width=True,
            column_config={
                "tenor": st.column_config.NumberColumn("Tenor (Y)", format="%.2f", min_value=0.0),
                "spread": st.column_config.NumberColumn("Z-spread (bps)", format="%.0f", min_value=0.0),
            },
        )

    with col2:
        bonds_1c = bonds_1.dropna()
        fair_1 = None
        if len(bonds_1c) < 2:
            st.error("Add at least 2 bonds to interpolate.")
        else:
            sorted_b = bonds_1c.sort_values("tenor").reset_index(drop=True)
            min_t, max_t = sorted_b["tenor"].min(), sorted_b["tenor"].max()

            if target_t1 < min_t or target_t1 > max_t:
                st.warning(
                    f"Target {target_t1:.2f}Y is outside issuer's range "
                    f"({min_t:.2f}Y – {max_t:.2f}Y). Switch to **Extrapolate** tab."
                )
            else:
                fair_1 = linear_interp(bonds_1c, target_t1)
                st.markdown(
                    f"""
                    <div class="result-box">
                        <div class="result-label">Fair Z-spread for {target_t1:.2f}Y new issue</div>
                        <div class="result-num">{fair_1:.0f} bps</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                lower = sorted_b[sorted_b["tenor"] <= target_t1].iloc[-1]
                upper = sorted_b[sorted_b["tenor"] >= target_t1].iloc[0]
                w = (
                    (target_t1 - lower["tenor"]) / (upper["tenor"] - lower["tenor"])
                    if upper["tenor"] != lower["tenor"] else 0
                )

                with st.expander("Calculation breakdown", expanded=True):
                    st.markdown(
                        f"**Method:** Linear interpolation between the issuer's "
                        f"{lower['tenor']:.2f}Y and {upper['tenor']:.2f}Y bonds."
                    )
                    breakdown = pd.DataFrame({
                        "Component": [
                            f"Lower anchor: {lower['tenor']:.2f}Y bond",
                            f"Upper anchor: {upper['tenor']:.2f}Y bond",
                            f"Weight to upper anchor",
                            "**Fair Z-spread**",
                        ],
                        "Value": [
                            f"{lower['spread']:.0f} bps",
                            f"{upper['spread']:.0f} bps",
                            f"{w*100:.0f}%",
                            f"**{fair_1:.0f} bps**",
                        ],
                    })
                    st.table(breakdown)

    if fair_1 is not None:
        st.markdown("##### Curve visualization")
        fig1 = make_chart(issuer=bonds_1c, target={"tenor": target_t1, "spread": fair_1})
        st.plotly_chart(fig1, use_container_width=True)

        # Export
        excel_bytes = export_to_excel(
            "Interpolate",
            {"Method": "Interpolate", "Target tenor (Y)": target_t1, "Fair Z-spread (bps)": round(fair_1)},
            {"Issuer bonds": bonds_1c},
        )
        st.download_button(
            "📥 Download scenario (Excel)", data=excel_bytes,
            file_name=f"fair_spread_interpolate_{target_t1}Y.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ==================================================================
# TAB 2 — EXTRAPOLATE
# ==================================================================
with tab2:
    st.markdown(
        "##### Use when the new issue tenor is *outside* the issuer's range. "
        "Anchor at the issuer's nearest bond, borrow shape from the sector curve."
    )
    st.write("")

    col1, col2 = st.columns([1, 1.3], gap="large")

    with col1:
        target_t2 = st.number_input(
            "Target tenor (years)", value=5.0, min_value=0.25, max_value=50.0, step=0.25, key="t2"
        )
        liq_prem = st.number_input(
            "Liquidity / extrapolation premium (bps)",
            value=15, step=5, key="liq",
            help="Extra spread for going outside issuer's known curve. 10–30 bps typical.",
        )

        st.markdown("**Issuer's existing bonds (level anchor)**")
        default_bonds_2 = pd.DataFrame({"tenor": [7.0, 10.0], "spread": [220.0, 260.0]})
        bonds_2 = st.data_editor(
            default_bonds_2, num_rows="dynamic", key="bonds2",
            use_container_width=True,
            column_config={
                "tenor": st.column_config.NumberColumn("Tenor (Y)", format="%.2f", min_value=0.0),
                "spread": st.column_config.NumberColumn("Z-spread (bps)", format="%.0f", min_value=0.0),
            },
        )

        st.markdown("**Sector / peer curve (shape source)**")
        default_sector_2 = pd.DataFrame({
            "tenor": [3.0, 5.0, 7.0, 10.0],
            "spread": [130.0, 170.0, 200.0, 240.0],
        })
        sector_2 = st.data_editor(
            default_sector_2, num_rows="dynamic", key="sector2",
            use_container_width=True,
            column_config={
                "tenor": st.column_config.NumberColumn("Tenor (Y)", format="%.2f", min_value=0.0),
                "spread": st.column_config.NumberColumn("Z-spread (bps)", format="%.0f", min_value=0.0),
            },
        )

    with col2:
        bonds_2c = bonds_2.dropna()
        sector_2c = sector_2.dropna()
        fair_2 = None
        anchor_2 = None

        if len(bonds_2c) == 0:
            st.error("Add at least 1 issuer bond as anchor.")
        elif len(sector_2c) < 2:
            st.error("Add at least 2 sector points for the shape.")
        else:
            tmp = bonds_2c.copy()
            tmp["dist"] = (tmp["tenor"] - target_t2).abs()
            anchor_2 = tmp.loc[tmp["dist"].idxmin()]

            sector_at_t = linear_interp(sector_2c, target_t2)
            sector_at_a = linear_interp(sector_2c, anchor_2["tenor"])

            if sector_at_t is None or sector_at_a is None:
                st.error(
                    f"Sector curve must cover both target ({target_t2}Y) and anchor "
                    f"({anchor_2['tenor']}Y). Add more sector points."
                )
            else:
                sector_delta = sector_at_t - sector_at_a
                min_t, max_t = bonds_2c["tenor"].min(), bonds_2c["tenor"].max()
                is_extrap = target_t2 < min_t or target_t2 > max_t
                liq_applied = liq_prem if is_extrap else 0
                fair_2 = anchor_2["spread"] + sector_delta + liq_applied

                st.markdown(
                    f"""
                    <div class="result-box">
                        <div class="result-label">Fair Z-spread for {target_t2:.2f}Y new issue</div>
                        <div class="result-num">{fair_2:.0f} bps</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not is_extrap:
                    st.info(
                        f"Target is INSIDE issuer range ({min_t:.2f}Y–{max_t:.2f}Y). "
                        f"Use **Interpolate** tab for a cleaner result. "
                        f"Liquidity premium not applied."
                    )

                with st.expander("Calculation breakdown", expanded=True):
                    direction = "longer" if target_t2 > max_t else ("shorter" if target_t2 < min_t else "within")
                    st.markdown(
                        f"**Method:** Anchored at issuer's {anchor_2['tenor']:.2f}Y bond, "
                        f"shape borrowed from sector curve. Target is **{direction}** than issuer range."
                    )
                    breakdown = pd.DataFrame({
                        "Component": [
                            f"Anchor: issuer {anchor_2['tenor']:.2f}Y bond",
                            f"Sector slope {anchor_2['tenor']:.2f}Y → {target_t2:.2f}Y",
                            "Liquidity / extrapolation premium",
                            "**Fair Z-spread**",
                        ],
                        "Value": [
                            f"{anchor_2['spread']:.0f} bps",
                            f"{sector_delta:+.0f} bps",
                            f"{liq_applied:+.0f} bps",
                            f"**{fair_2:.0f} bps**",
                        ],
                    })
                    st.table(breakdown)

    if fair_2 is not None:
        st.markdown("##### Curve visualization")
        fig2 = make_chart(
            issuer=bonds_2c, sector=sector_2c,
            target={"tenor": target_t2, "spread": fair_2},
        )
        st.plotly_chart(fig2, use_container_width=True)

        excel_bytes = export_to_excel(
            "Extrapolate",
            {"Method": "Extrapolate", "Target tenor (Y)": target_t2,
             "Anchor tenor (Y)": float(anchor_2["tenor"]),
             "Liquidity premium (bps)": liq_prem,
             "Fair Z-spread (bps)": round(fair_2)},
            {"Issuer bonds": bonds_2c.drop(columns="dist", errors="ignore"),
             "Sector curve": sector_2c},
        )
        st.download_button(
            "📥 Download scenario (Excel)", data=excel_bytes,
            file_name=f"fair_spread_extrapolate_{target_t2}Y.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ==================================================================
# TAB 3 — PROXY (NEW ISSUER)
# ==================================================================
with tab3:
    st.markdown(
        "##### Use for a brand-new issuer with no existing bonds. "
        "Median of comparable peers + issuer-specific adjustments."
    )
    st.write("")

    col1, col2 = st.columns([1, 1.3], gap="large")

    with col1:
        target_t3 = st.number_input(
            "Target tenor (years)", value=5.0, min_value=0.25, max_value=50.0, step=0.25, key="t3"
        )

        st.markdown("**Comparable peers (Z-spread at target tenor)**")
        default_peers = pd.DataFrame({
            "issuer": ["Ecopetrol", "Petrobras", "Frontera", "Pemex"],
            "spread": [215.0, 195.0, 240.0, 280.0],
            "include": [True, True, True, False],
        })
        peers = st.data_editor(
            default_peers, num_rows="dynamic", key="peers",
            use_container_width=True,
            column_config={
                "issuer": st.column_config.TextColumn("Peer issuer"),
                "spread": st.column_config.NumberColumn("Z-spread (bps)", format="%.0f", min_value=0.0),
                "include": st.column_config.CheckboxColumn("Include in median", help="Uncheck to exclude outliers"),
            },
        )

        st.markdown("**Issuer-specific adjustments (bps)**")
        adj_size = st.number_input("Size (smaller than peers = positive)", value=15, step=5, key="adj_size")
        adj_debut = st.number_input("Debut / first-time issuer premium", value=20, step=5, key="adj_debut")
        adj_lev = st.number_input("Leverage (higher = positive)", value=10, step=5, key="adj_lev")
        adj_cov = st.number_input("Covenants / collateral (better = negative)", value=-10, step=5, key="adj_cov")
        adj_other = st.number_input("Other (jurisdiction, ESG, sector tilt, etc.)", value=0, step=5, key="adj_other")

        st.divider()
        build_curve = st.checkbox(
            "Build full implied issuer curve (using sector shape)",
            help="Generates Z-spreads at standard tenors using sector slopes anchored at the proxy fair value.",
        )

        sector_3c = None
        if build_curve:
            st.markdown("**Sector / peer curve (for shape)**")
            default_sector_3 = pd.DataFrame({
                "tenor": [2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0],
                "spread": [110.0, 130.0, 170.0, 200.0, 240.0, 270.0, 290.0, 310.0],
            })
            sector_3 = st.data_editor(
                default_sector_3, num_rows="dynamic", key="sector3",
                use_container_width=True,
                column_config={
                    "tenor": st.column_config.NumberColumn("Tenor (Y)", format="%.2f", min_value=0.0),
                    "spread": st.column_config.NumberColumn("Z-spread (bps)", format="%.0f", min_value=0.0),
                },
            )
            sector_3c = sector_3.dropna()

    with col2:
        peers_c = peers.dropna(subset=["spread"])
        peers_inc = peers_c[peers_c["include"] == True] if "include" in peers_c.columns else peers_c
        fair_3 = None
        median_val = None
        implied_curve = None

        if len(peers_inc) < 2:
            st.error("Include at least 2 peers to compute a median.")
        else:
            median_val = float(peers_inc["spread"].median())
            total_adj = adj_size + adj_debut + adj_lev + adj_cov + adj_other
            fair_3 = median_val + total_adj

            st.markdown(
                f"""
                <div class="result-box">
                    <div class="result-label">Fair Z-spread for {target_t3:.2f}Y new issue</div>
                    <div class="result-num">{fair_3:.0f} bps</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Calculation breakdown", expanded=True):
                excluded = len(peers_c) - len(peers_inc)
                msg = f"**Method:** Median of {len(peers_inc)} included peer Z-spreads"
                if excluded > 0:
                    msg += f" ({excluded} excluded as outliers)"
                msg += " plus issuer-specific adjustments."
                st.markdown(msg)

                breakdown = pd.DataFrame({
                    "Component": [
                        f"Peer median ({len(peers_inc)} issuers)",
                        "Size adjustment",
                        "Debut premium",
                        "Leverage adjustment",
                        "Covenants / collateral",
                        "Other",
                        "Total adjustments",
                        "**Fair Z-spread**",
                    ],
                    "Value": [
                        f"{median_val:.0f} bps",
                        f"{adj_size:+d} bps",
                        f"{adj_debut:+d} bps",
                        f"{adj_lev:+d} bps",
                        f"{adj_cov:+d} bps",
                        f"{adj_other:+d} bps",
                        f"{total_adj:+d} bps",
                        f"**{fair_3:.0f} bps**",
                    ],
                })
                st.table(breakdown)

            # Build full curve
            if build_curve and sector_3c is not None and len(sector_3c) >= 2:
                anchor_sector = linear_interp(sector_3c, target_t3)
                if anchor_sector is not None:
                    s_min, s_max = sector_3c["tenor"].min(), sector_3c["tenor"].max()
                    standard_tenors = [t for t in [1, 2, 3, 5, 7, 10, 15, 20, 30] if s_min <= t <= s_max]
                    rows = []
                    for t in standard_tenors:
                        sec_t = linear_interp(sector_3c, t)
                        if sec_t is not None:
                            rows.append({"tenor": t, "spread": fair_3 + (sec_t - anchor_sector)})
                    if rows:
                        implied_curve = pd.DataFrame(rows)
                        st.markdown("##### Implied issuer curve")
                        st.dataframe(
                            implied_curve.rename(columns={"tenor": "Tenor (Y)", "spread": "Z-spread (bps)"})
                            .style.format({"Z-spread (bps)": "{:.0f}", "Tenor (Y)": "{:.1f}"}),
                            use_container_width=True, hide_index=True,
                        )

    if fair_3 is not None:
        st.markdown("##### Visualization")
        peers_chart = peers_inc.copy()
        peers_chart["tenor"] = target_t3 + np.linspace(-0.2, 0.2, len(peers_chart)) if len(peers_chart) > 1 else target_t3
        fig3 = make_chart(
            peers=peers_chart,
            target={"tenor": target_t3, "spread": fair_3},
            implied_curve=implied_curve,
            peer_median=median_val,
        )
        st.plotly_chart(fig3, use_container_width=True)

        export_dict = {"Peers": peers_c}
        if implied_curve is not None:
            export_dict["Implied curve"] = implied_curve
        if sector_3c is not None:
            export_dict["Sector curve"] = sector_3c

        excel_bytes = export_to_excel(
            "Proxy",
            {"Method": "Proxy (new issuer)", "Target tenor (Y)": target_t3,
             "Peer median (bps)": round(median_val) if median_val else None,
             "Total adjustments (bps)": adj_size + adj_debut + adj_lev + adj_cov + adj_other,
             "Fair Z-spread (bps)": round(fair_3)},
            export_dict,
        )
        st.download_button(
            "📥 Download scenario (Excel)", data=excel_bytes,
            file_name=f"fair_spread_proxy_{target_t3}Y.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------
st.divider()
st.caption(
    "**Sanity-check every result**: (1) does it fit the sovereign + sector + rating triangle? "
    "(2) Would a trader laugh? (3) Is new-issue concession baked in (10–25 bps)?"
)
