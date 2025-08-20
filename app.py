# app.py
# Core Innovation • Parametric Budget (Sim)
# Two‑pane Streamlit app (Phone + Dashboard), fully local simulation, no external APIs.

import math
import time
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import qrcode
from PIL import Image
import streamlit as st


# =============================================================================
# Brand & Theme
# =============================================================================
BRAND = {
    "name": "Hermosillo",
    "logo_url": "https://hermosillo.com/wp-content/uploads/2019/08/horizontal-hermosillo-experience-matters-registered-logo.png",
    "orange": "#FF6A00",
    "paper": "#FFFFFF",
    "surface": "#F6F7FA",
    "stroke": "#E5E7EB",
    "ink": "#0F172A",
    "ink_soft": "#334155",
}

TITLE = "Core Innovation • Parametric Budget (Sim)"
SUBTITLE = "Hermosillo — Experience Matters"


# =============================================================================
# State
# =============================================================================
def init_state():
    defaults = dict(
        dark_mode=False,
        project="North Hub DC",
        sent_flag=False,
        last_sent_ts=None,
        # phone defaults
        project_type="Warehouse",
        built_area=10000,
        structural_system="Steel",
        envelope="Standard",
        quality="Standard",
        region="North",
        opt_skylights=True,
        opt_mezzanine=False,
        opt_hvac=True,
        checklist={
            "Soil report available": True,
            "As-built utilities verified": True,
            "Permitting path confirmed": False,
            "Vendor pre-qualification complete": True,
            "BIM execution plan approved": False,
            "LEED considerations": True,
            "Early procurement planned": False,
        },
        pulse=False,
        fake_link=None,
        fake_qr=None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_all():
    keep = {"dark_mode"}
    for k in list(st.session_state.keys()):
        if k not in keep:
            del st.session_state[k]
    init_state()


def load_preset(p_type, area, structure, envelope, quality, region, skylights, mezz, hvac):
    st.session_state.project_type = p_type
    st.session_state.built_area = area
    st.session_state.structural_system = structure
    st.session_state.envelope = envelope
    st.session_state.quality = quality
    st.session_state.region = region
    st.session_state.opt_skylights = skylights
    st.session_state.opt_mezzanine = mezz
    st.session_state.opt_hvac = hvac
    st.session_state.pulse = True
    st.toast("Preset loaded")


# Initialize on first run
init_state()


# =============================================================================
# CSS (only styles; no wrapper tags around widgets)
# =============================================================================
def inject_css():
    if st.session_state.dark_mode:
        paper = "#0B1220"
        surface = "#111827"
        stroke = "#1F2937"
        ink = "#F8FAFC"
        ink_soft = "#CBD5E1"
        shadow = "0 8px 24px rgba(0,0,0,0.35)"
        band_bg = "#0F172A"
    else:
        paper = BRAND["paper"]
        surface = BRAND["surface"]
        stroke = BRAND["stroke"]
        ink = BRAND["ink"]
        ink_soft = BRAND["ink_soft"]
        shadow = "0 8px 24px rgba(2,6,23,0.08)"
        band_bg = "#F3F4F6"

    st.markdown(
        f"""
        <style>
        :root {{
            --brand-orange: {BRAND["orange"]};
            --paper: {paper};
            --surface: {surface};
            --stroke: {stroke};
            --ink: {ink};
            --ink-soft: {ink_soft};
            --shadow: {shadow};
            --band-bg: {band_bg};
            --radius-xl: 20px;
            --radius-2xl: 26px;
        }}

        .stApp {{ background: var(--paper); color: var(--ink); }}
        .block-container {{ max-width: 1400px; padding-top: 1.2rem; padding-bottom: 2.5rem; }}

        /* Banner */
        .top-banner {{
            width: 100%;
            display: flex; align-items: center; gap: 14px;
            background: var(--surface);
            border: 1px solid var(--stroke);
            border-radius: var(--radius-2xl);
            padding: 10px 14px;
            box-shadow: var(--shadow);
        }}
        .top-banner img {{ height: 28px; object-fit: contain; }}
        .top-banner .title {{ font-weight: 700; font-size: 1.1rem; color: var(--ink); }}
        .top-banner .subtitle {{ font-size: 0.9rem; color: var(--ink-soft); }}

        /* “Full‑bleed” control band illusion */
        .control-band-spacer {{
            margin-left:-24px; margin-right:-24px; margin-top:14px; margin-bottom:-6px;
            height:36px; background: var(--band-bg); border-bottom:1px solid var(--stroke);
        }}

        /* Give bordered containers a card look */
        div[aria-live="polite"] > div:has(> div[role="group"]),
        section[data-testid="stSidebar"] div[role="group"] {{
            border: 1px solid var(--stroke);
            background: var(--surface);
            border-radius: var(--radius-2xl);
            box-shadow: var(--shadow);
            padding: 12px;
        }}

        /* Pills */
        .pill {{
            display:inline-block; padding:6px 12px; border-radius:999px;
            border:1px solid var(--stroke); background: var(--paper);
            color: var(--ink-soft); font-size: .85rem; margin: 4px 6px 0 0;
        }}
        .pill.orange {{
            border-color: var(--brand-orange);
            background: rgba(255,106,0,.08);
            color: var(--brand-orange);
        }}

        /* Tiny “phone” feel: make the first bordered container under the left column narrower */
        .left-phone-sizer > div:first-child {{
            max-width: 420px;
            margin: 0 auto;
            border-radius: 36px !important;
        }}
        .phone-notch {{
            height: 24px;
            background: linear-gradient(0deg, rgba(0,0,0,0.08), rgba(0,0,0,0.12));
            border-top-left-radius: 36px; border-top-right-radius: 36px;
            margin: -12px -12px 6px -12px;  /* stretch to card edges */
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# =============================================================================
# Computation & Visualization
# =============================================================================
def capture_scenario():
    return {
        "project": st.session_state.project,
        "project_type": st.session_state.project_type,
        "area_m2": int(st.session_state.built_area),
        "structural_system": st.session_state.structural_system,
        "envelope": st.session_state.envelope,
        "quality": st.session_state.quality,
        "region": st.session_state.region,
        "opts": {
            "skylights": st.session_state.opt_skylights,
            "mezzanine": st.session_state.opt_mezzanine,
            "hvac": st.session_state.opt_hvac,
        },
        "checklist": st.session_state.checklist,
        "sent_at": st.session_state.last_sent_ts,
    }


def compute_simulation(scn: dict):
    base_table = {
        ("Warehouse", "Steel"): 420,
        ("Warehouse", "Concrete"): 450,
        ("Office", "Steel"): 520,
        ("Office", "Concrete"): 560,
        ("Retail", "Steel"): 480,
        ("Retail", "Concrete"): 510,
    }
    base = base_table[(scn["project_type"], scn["structural_system"])]
    region_mult = {"North": 0.95, "Central": 1.00, "South": 1.05}[scn["region"]]
    envelope_mult = {"Standard": 1.00, "Insulated": 1.08}[scn["envelope"]]
    quality_mult = {"Basic": 0.95, "Standard": 1.00, "Premium": 1.12}[scn["quality"]]
    unit_cost_base = base * region_mult * envelope_mult * quality_mult

    adders = 0
    if scn["opts"]["skylights"]:
        adders += 8
    if scn["opts"]["mezzanine"]:
        adders += 60
    if scn["opts"]["hvac"]:
        adders += 45

    unchecked = sum(1 for v in scn["checklist"].values() if not v)
    contingency_pct = min(unchecked * 0.005, 0.05)

    area = scn["area_m2"]
    subtotal = area * (unit_cost_base + adders)
    total = subtotal * (1 + contingency_pct)

    structure = total * 0.35
    envelope = total * 0.18
    mep = total * 0.20
    finishes = total * 0.22
    contingency_val = total - (structure + envelope + mep + finishes)

    if scn["structural_system"] == "Steel":
        steel_t = round(area * 0.02, 1)
        conc_m3 = round(area * 0.05, 1)
        co2 = round(steel_t * 1.8 + conc_m3 * 0.1, 1)
        lead_weeks = 14 if scn["opts"]["mezzanine"] else 12
    else:
        steel_t = round(area * 0.008, 1)
        conc_m3 = round(area * 0.12, 1)
        co2 = round(steel_t * 1.4 + conc_m3 * 0.22, 1)
        lead_weeks = 16 if scn["opts"]["mezzanine"] else 14

    if scn["opts"]["hvac"]:
        lead_weeks += 1
    if scn["region"] == "South":
        lead_weeks += 1

    unit_cost_total = total / area if area else 0

    return {
        "unit_cost": round(unit_cost_total, 2),
        "total_cost": round(total, 0),
        "contingency_pct": round(contingency_pct * 100, 1),
        "steel_t": steel_t,
        "concrete_m3": conc_m3,
        "co2_tons": co2,
        "lead_time_wks": int(lead_weeks),
        "cost_buckets": {
            "Structure": round(structure, 0),
            "Envelope": round(envelope, 0),
            "MEP": round(mep, 0),
            "Finishes": round(finishes, 0),
            "Contingency": round(contingency_val, 0),
        },
        "subtotal_no_cont": round(subtotal, 0),
        "adders_per_m2": adders,
    }


def show_scenario_summary(scn, calc):
    colA, colB = st.columns([1.4, 1])
    with colA:
        st.write(
            f"**Project:** {scn['project']}  \n"
            f"**Date/Time:** {scn['sent_at']}  \n"
            f"**Area:** {scn['area_m2']:,} m²"
        )
        st.markdown("**Selections**")
        pills = [
            ("Type", scn["project_type"]),
            ("Structure", scn["structural_system"]),
            ("Envelope", scn["envelope"]),
            ("Quality", scn["quality"]),
            ("Region", scn["region"]),
        ]
        st.markdown("".join([f'<span class="pill orange">{k}: {v}</span>' for k, v in pills]), unsafe_allow_html=True)
    with colB:
        st.markdown("**Key Notes**")
        notes = []
        if scn["opts"]["skylights"]:
            notes.append("Skylights (↓ lighting energy)")
        if scn["opts"]["mezzanine"]:
            notes.append("Mezzanine included")
        if scn["opts"]["hvac"]:
            notes.append("HVAC included")
        unchecked = [k for k, v in scn["checklist"].items() if not v]
        if unchecked:
            notes.append(f"Checklist gaps: {len(unchecked)} (↑ contingency)")
        st.write("• " + "\n• ".join(notes) if notes else "No special options")


def make_3d_box(scn):
    ratios = {"Warehouse": 2.2, "Office": 1.2, "Retail": 1.6}
    ratio = ratios.get(scn["project_type"], 1.5)
    area = max(scn["area_m2"], 1)
    length = math.sqrt(area * ratio)
    width = area / length
    base_height = {"Basic": 9, "Standard": 11, "Premium": 13}[scn["quality"]]
    if scn["opts"]["mezzanine"]:
        base_height += 2

    x = [0, length, length, 0, 0, length, length, 0]
    y = [0, 0, width, width, 0, 0, width, width]
    z = [0, 0, 0, 0, base_height, base_height, base_height, base_height]
    i = [0, 0, 0, 1, 2, 4, 5, 6, 7, 3, 1, 2]
    j = [1, 4, 3, 5, 3, 5, 6, 7, 4, 2, 5, 6]
    k = [4, 5, 7, 6, 7, 1, 2, 4, 0, 1, 4, 5]

    mesh = go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=BRAND["orange"], opacity=0.3)
    edges = go.Scatter3d(
        x=[x[0], x[1], None, x[1], x[2], None, x[2], x[3], None, x[3], x[0], None,
           x[4], x[5], None, x[5], x[6], None, x[6], x[7], None, x[7], x[4], None,
           x[0], x[4], None, x[1], x[5], None, x[2], x[6], None, x[3], x[7], None],
        y=[y[0], y[1], None, y[1], y[2], None, y[2], y[3], None, y[3], y[0], None,
           y[4], y[5], None, y[5], y[6], None, y[6], y[7], None, y[7], y[4], None,
           y[0], y[4], None, y[1], y[5], None, y[2], y[6], None, y[3], y[7], None],
        z=[z[0], z[1], None, z[1], z[2], None, z[2], z[3], None, z[3], z[0], None,
           z[4], z[5], None, z[5], z[6], None, z[6], z[7], None, z[7], z[4], None,
           z[0], z[4], None, z[1], z[5], None, z[2], z[6], None, z[3], z[7], None],
        mode="lines",
        line=dict(width=4),
    )
    scene = dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), aspectmode="data")
    fig = go.Figure(data=[mesh, edges])
    fig.update_layout(
        scene=scene,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=("#0B1220" if st.session_state.dark_mode else BRAND["paper"]),
        showlegend=False,
    )
    return fig


def show_kpis(calc):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Cost", f"${calc['total_cost']:,.0f}")
    c2.metric("Unit Cost (USD/m²)", f"${calc['unit_cost']:,.2f}")
    c3.metric("Contingency", f"{calc['contingency_pct']}%")
    c4.metric("CO₂ (tCO₂e)", f"{calc['co2_tons']:,.1f}")
    c5.metric("Lead Time", f"{calc['lead_time_wks']} wks")


def make_donut(bucket_dict):
    labels = list(bucket_dict.keys())
    values = list(bucket_dict.values())
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55, textinfo="label+percent")])
    fig.update_traces(hoverinfo="label+value+percent", pull=[0.02] * len(labels))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def make_quantities_bar(calc):
    df = pd.DataFrame({"Quantity": ["Steel (t)", "Concrete (m³)"], "Value": [calc["steel_t"], calc["concrete_m3"]]})
    fig = go.Figure(data=[go.Bar(x=df["Quantity"], y=df["Value"])])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title="")
    return fig


def make_quality_line(scn, _calc):
    qualities = ["Basic", "Standard", "Premium"]
    unit_costs = []
    for q in qualities:
        scn2 = dict(scn)
        scn2["quality"] = q
        c2 = compute_simulation(scn2)
        unit_costs.append(c2["unit_cost"])
    fig = go.Figure(data=[go.Scatter(x=qualities, y=unit_costs, mode="lines+markers")])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title="USD/m²")
    return fig


# =============================================================================
# Header
# =============================================================================
with st.container():
    st.markdown(
        f"""
        <div class="top-banner">
            <img src="{BRAND['logo_url']}" alt="Hermosillo Logo" />
            <div>
                <div class="title">{TITLE}</div>
                <div class="subtitle">{SUBTITLE}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Control Band (full‑bleed look + bordered card)
# =============================================================================
st.markdown('<div class="control-band-spacer"></div>', unsafe_allow_html=True)
with st.container(border=True):
    c1, c2, c3, c4, c5 = st.columns([1.3, 1, 1, 1, 1.2])

    with c1:
        st.session_state.project = st.selectbox(
            "Project",
            ["North Hub DC", "MX HQ Office", "Sunset Retail Plaza"],
            index=["North Hub DC", "MX HQ Office", "Sunset Retail Plaza"].index(st.session_state.project),
        )

    with c2:
        if st.button("Preset: Basic Whse 10k m²", use_container_width=True):
            load_preset("Warehouse", 10000, "Steel", "Standard", "Basic", "North", skylights=True, mezz=False, hvac=True)

    with c3:
        if st.button("Preset: Premium Office 5k m²", use_container_width=True):
            load_preset("Office", 5000, "Concrete", "Insulated", "Premium", "Central", skylights=False, mezz=True, hvac=True)

    with c4:
        if st.button("Preset: Retail Std 3k m²", use_container_width=True):
            load_preset("Retail", 3000, "Steel", "Standard", "Standard", "South", skylights=True, mezz=False, hvac=True)

    with c5:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("Reset simulation", use_container_width=True):
                reset_all()
                st.toast("Reset done.")
        with col_b:
            st.session_state.dark_mode = st.toggle("Dark mode", value=st.session_state.dark_mode)


# =============================================================================
# Two Columns
# =============================================================================
left, right = st.columns([0.9, 1.1], gap="large")

# -----------------------------------------------------------------------------
# Left: Phone Panel (only Streamlit containers)
# -----------------------------------------------------------------------------
with left:
    st.markdown("#### Phone (Simulation)")

    # narrow the card visually (CSS targets this wrapper)
    with st.container():
        st.markdown('<div class="left-phone-sizer">', unsafe_allow_html=True)

        with st.container(border=True):
            # A visual notch at the top edge (safe: cosmetic element)
            st.markdown('<div class="phone-notch"></div>', unsafe_allow_html=True)

            with st.form("phone_form", clear_on_submit=False):
                st.caption("Parametric Budget Checklist")

                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.project_type = st.selectbox(
                        "Project Type",
                        ["Warehouse", "Office", "Retail"],
                        index=["Warehouse", "Office", "Retail"].index(st.session_state.project_type),
                    )
                with c2:
                    st.session_state.structural_system = st.radio(
                        "Structural System",
                        ["Steel", "Concrete"],
                        horizontal=True,
                        index=["Steel", "Concrete"].index(st.session_state.structural_system),
                    )

                st.session_state.built_area = st.slider("Built Area (m²)", 500, 50000, int(st.session_state.built_area), step=500)

                c3, c4, c5 = st.columns(3)
                with c3:
                    st.session_state.envelope = st.selectbox(
                        "Envelope",
                        ["Standard", "Insulated"],
                        index=["Standard", "Insulated"].index(st.session_state.envelope),
                    )
                with c4:
                    st.session_state.quality = st.select_slider(
                        "Quality Level", options=["Basic", "Standard", "Premium"], value=st.session_state.quality
                    )
                with c5:
                    st.session_state.region = st.selectbox(
                        "Region (Cost Index)",
                        ["North", "Central", "South"],
                        index=["North", "Central", "South"].index(st.session_state.region),
                    )

                st.divider()
                st.caption("Options")
                c6, c7, c8 = st.columns(3)
                with c6:
                    st.session_state.opt_skylights = st.checkbox("Skylights", value=st.session_state.opt_skylights)
                with c7:
                    st.session_state.opt_mezzanine = st.checkbox("Mezzanine", value=st.session_state.opt_mezzanine)
                with c8:
                    st.session_state.opt_hvac = st.checkbox("HVAC", value=st.session_state.opt_hvac)

                st.divider()
                st.caption("Parametric Checklist (affects contingency)")
                new_checklist = {}
                for item, val in st.session_state.checklist.items():
                    new_checklist[item] = st.checkbox(item, value=val)
                st.session_state.checklist = new_checklist

                st.divider()
                send_col, share_col = st.columns([1.2, 1])
                with send_col:
                    send_clicked = st.form_submit_button("Send to Dashboard", use_container_width=True)
                with share_col:
                    share_clicked = st.form_submit_button("Create Share Link (fake) 🔗", use_container_width=True)

                if send_clicked:
                    st.session_state.sent_flag = True
                    st.session_state.last_sent_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.pulse = False
                    st.toast("Sent!", icon="✅")
                    time.sleep(0.05)

                if share_clicked:
                    fake_url = f"https://core-inn.hermosillo/sim/{int(time.time())}"
                    st.session_state.fake_link = fake_url
                    img = qrcode.make(fake_url)
                    bio = BytesIO()
                    img.save(bio, format="PNG")
                    bio.seek(0)
                    st.session_state.fake_qr = bio.getvalue()
                    st.toast("Fake share link created")

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.fake_link and st.session_state.fake_qr:
        with st.container(border=True):
            st.markdown("##### Share (Demo)")
            st.write(st.session_state.fake_link)
            st.image(st.session_state.fake_qr, caption="QR (fake)", width=160)


# -----------------------------------------------------------------------------
# Right: Dashboard Panel (cards = bordered containers)
# -----------------------------------------------------------------------------
with right:
    st.markdown("#### Dashboard")

    if st.session_state.sent_flag:
        scenario = capture_scenario()
        calc = compute_simulation(scenario)

        # 1) Scenario Summary
        with st.container(border=True):
            st.subheader("Scenario Summary")
            show_scenario_summary(scenario, calc)

        # 2) 3D Model Preview
        with st.container(border=True):
            st.subheader("3D Model Preview")
            fig3d = make_3d_box(scenario)
            st.plotly_chart(fig3d, use_container_width=True)

        # 3) Cost & KPIs
        with st.container(border=True):
            st.subheader("Cost & KPIs")
            show_kpis(calc)

        # 4) Charts
        with st.container(border=True):
            st.subheader("Analytics")
            c_a, c_b = st.columns([1, 1])
            with c_a:
                st.caption("Cost Distribution")
                st.plotly_chart(make_donut(calc["cost_buckets"]), use_container_width=True)
            with c_b:
                st.caption("Quantities")
                st.plotly_chart(make_quantities_bar(calc), use_container_width=True)

            st.caption("Cost vs. Quality Level")
            st.plotly_chart(make_quality_line(scenario, calc), use_container_width=True)

    else:
        with st.container(border=True):
            st.subheader("Waiting for scenario")
            st.write("Use the **Phone** on the left and press **Send to Dashboard** to simulate results.")


# =============================================================================
# Footer
# =============================================================================
st.markdown(
    """
    <div style="opacity:.65; font-size:.8rem; margin-top:24px;">
      This is a local simulation. No external services. Replace cost/3D with real engines later. <!-- [INTEGRATION POINT] -->
    </div>
    """,
    unsafe_allow_html=True,
)
