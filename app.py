from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Southern Appalachian Garnet Analysis Database", page_icon="💎", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --garnet-red: #8f1d2c;
        --garnet-red-dark: #681522;
        --garnet-rose: #fbf3f3;
    }
    .stApp {
        background: linear-gradient(180deg, #fffafa 0, #ffffff 340px);
    }
    [data-testid="stHeader"] {
        background: rgba(255, 250, 250, 0.85);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1440px;
    }
    h1 {
        color: var(--garnet-red-dark);
        letter-spacing: -0.035em;
        font-weight: 750;
    }
    [data-testid="stCaptionContainer"] {
        color: #66565a;
    }
    [data-testid="stSidebar"] {
        background: var(--garnet-rose);
        border-right: 1px solid #f0dddd;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #f0dddd;
        border-top: 3px solid var(--garnet-red);
        border-radius: 0.65rem;
        padding: 1rem 1.1rem;
        box-shadow: 0 3px 12px rgba(104, 21, 34, 0.05);
    }
    [data-testid="stMetricLabel"] {
        color: #66565a;
    }
    [data-baseweb="tab-list"] {
        gap: 0.35rem;
        border-bottom: 1px solid #ead7da;
    }
    [data-baseweb="tab"] {
        color: #66565a;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        color: var(--garnet-red);
        border-bottom-color: var(--garnet-red);
    }
    .stButton > button, .stDownloadButton > button {
        border-color: var(--garnet-red);
        color: var(--garnet-red);
        border-radius: 0.5rem;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--garnet-red);
        color: #ffffff;
        border-color: var(--garnet-red);
    }
    a {
        color: var(--garnet-red);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.color_discrete_sequence = [
    "#8f1d2c", "#bd3947", "#d96b72", "#6f2735", "#e7a1a4", "#a94c59"
]

st.title("Southern Appalachian Garnet")
st.caption("Select sample locations on the map to focus the analyses below.")

DATA_FILE = Path(__file__).parent / "Final_Database.csv"

@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE, low_memory=False)

try:
    df = load_data()
except FileNotFoundError:
    st.error("Final_Database.csv must be in the same repository folder as app.py.")
    st.stop()

with st.sidebar:
    st.header("Filter analyses")
    states = st.multiselect("State", sorted(df["State"].dropna().unique()), default=sorted(df["State"].dropna().unique()))
    subset = df[df["State"].isin(states)]
    lithologies = st.multiselect("Lithology category", sorted(subset["Lithology_Category"].dropna().unique()))
    if lithologies:
        subset = subset[subset["Lithology_Category"].isin(lithologies)]
    units = st.multiselect("Geological unit", sorted(subset["Unit"].dropna().unique()))
    if units:
        subset = subset[subset["Unit"].isin(units)]
    search = st.text_input("Search garnet ID or author sample ID")
    if search.strip():
        matches = (subset["Garnet_ID"].astype(str).str.contains(search.strip(), case=False, regex=False, na=False)
                   | subset["Author_Sample_ID"].astype(str).str.contains(search.strip(), case=False, regex=False, na=False))
        subset = subset[matches]
    st.caption("Lithology and unit names are displayed exactly as provided in the source CSV.")

st.caption(
    "Each marker represents one unique coordinate pair; marker size indicates the number "
    "of analyses at that location."
)
map_sites = (
    df.dropna(subset=["Latitude", "Longitude"])
    .groupby(["Latitude", "Longitude"], as_index=False)
    .agg(State=("State", "first"), analyses=("Garnet_ID", "size"), units=("Unit", "nunique"))
    .reset_index(drop=True)
)
if not map_sites.empty:
    fig_map = px.scatter_map(
        map_sites,
        lat="Latitude",
        lon="Longitude",
        size="analyses",
        size_max=18,
        hover_name="State",
        hover_data={"analyses": True, "units": True, "Latitude": True, "Longitude": True},
        zoom=5.5,
        height=560,
    )
    fig_map.update_traces(marker_color="#8f1d2c")
    fig_map.update_layout(
        map_style="open-street-map",
        map_center={"lat": 36.6, "lon": -81.5},
        margin=dict(l=0, r=0, t=0, b=0),
    )
    if "map_widget_version" not in st.session_state:
        st.session_state["map_widget_version"] = 0
    map_event = st.plotly_chart(
        fig_map,
        use_container_width=True,
        key=f"sample_map_{st.session_state['map_widget_version']}",
        on_select="rerun",
        selection_mode=("points", "box", "lasso"),
    )
    selected_site_indices = {
        int(point["point_index"])
        for point in map_event["selection"]["points"]
        if point.get("point_index") is not None
    }
    selected_site_indices = {
        index for index in selected_site_indices if 0 <= index < len(map_sites)
    }
    if selected_site_indices:
        selected_sites = map_sites.iloc[sorted(selected_site_indices)]
        selected_coordinates = set(
            selected_sites[["Latitude", "Longitude"]].itertuples(index=False, name=None)
        )
        subset = subset[
            subset[["Latitude", "Longitude"]]
            .apply(tuple, axis=1)
            .isin(selected_coordinates)
        ]
        st.caption(
            f"{len(selected_site_indices):,} map location(s) selected · "
            f"{len(subset):,} matching analyses after sidebar filters."
        )
    else:
        st.caption("No map locations selected; results include all locations matching the sidebar filters.")
    if st.button("Clear map selection", disabled=not selected_site_indices):
        st.session_state["map_widget_version"] += 1
        st.rerun()
else:
    st.info("No sample coordinates are available to display.")

st.caption("Dataset version 1.0")
with st.expander("Dataset citation"):
    st.markdown(
        'Catlos, Elizabeth, 2026, "Replication Data for: Southern Appalachian Bedrock '
        'Garnet Chemistry and Geological Metadata: A Reference Dataset for Sediment '
        'Provenance Studies", [Texas Data Repository, V1]'
        '(https://doi.org/10.18738/T8/0NBJBO), '
        "UNF:6:PPyEsTark79lKeufq0g== [fileUNF]."
    )

c1, c2, c3 = st.columns(3)
c1.metric("Selected analyses", f"{len(subset):,}")
c2.metric("Coordinate pairs", f"{len(subset[['Latitude', 'Longitude']].dropna().drop_duplicates()):,}")
c3.metric("Geological units", f"{subset['Unit'].nunique():,}")

tab_data, tab_chem, tab_pt, tab_up = st.tabs(["Data explorer", "Garnet chemistry", "Pressure–temperature", "Compare your garnets"])

with tab_data:
    st.subheader("Bedrock garnet analyses")
    st.dataframe(subset, use_container_width=True, hide_index=True)
    st.download_button("Download filtered CSV", data=subset.to_csv(index=False).encode("utf-8"),
                       file_name="southern_appalachian_garnet_filtered.csv", mime="text/csv")

with tab_chem:
    st.subheader("Garnet endmember compositions")
    components = ["Almandine_%", "Spessartine_%", "Pyrope_%", "Grossular_%"]
    if subset.empty:
        st.info("No analyses match these filters.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            x = st.selectbox("X-axis", components, index=2)
        with col2:
            y = st.selectbox("Y-axis", components, index=3)
        fig = px.scatter(subset, x=x, y=y, color="Lithology_Category",
                         hover_data=["Garnet_ID", "Author_Sample_ID", "State", "Unit"],
                         opacity=0.65, render_mode="webgl")
        fig.update_layout(legend_title_text="Lithology", height=560)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Endmember values come directly from the uploaded CSV; no renormalization is applied here.")
        st.markdown("**Ternary view (Almandine–Pyrope–Grossular)**")
        st.caption("Spessartine is omitted from the displayed ternary axes; the three shown components are normalized to 100% for this plot only.")
        tern = subset.copy()
        tern["tern_sum"] = tern[["Almandine_%", "Pyrope_%", "Grossular_%"]].sum(axis=1)
        tern = tern[tern["tern_sum"] > 0].copy()
        for comp in ["Almandine_%", "Pyrope_%", "Grossular_%"]:
            tern["tern_" + comp] = 100 * tern[comp] / tern["tern_sum"]
        if not tern.empty:
            tri = px.scatter_ternary(tern, a="tern_Almandine_%", b="tern_Pyrope_%", c="tern_Grossular_%",
                                     color="Lithology_Category", hover_name="Garnet_ID",
                                     hover_data=["Unit", "Spessartine_%"])
            tri.update_layout(height=650)
            st.plotly_chart(tri, use_container_width=True)

with tab_pt:
    st.subheader("Reported peak metamorphic conditions")
    st.caption("Only records containing both peak pressure and temperature appear in this graph. Missing values are not estimated.")
    pt = subset.dropna(subset=["Peak_Pressure_kbar", "Peak_Temperature_C"])
    if not pt.empty:
        fig = px.scatter(pt, x="Peak_Temperature_C", y="Peak_Pressure_kbar", color="Lithology_Category",
                         hover_data=["Garnet_ID", "Unit", "State"], opacity=0.7)
        fig.update_layout(xaxis_title="Temperature (°C)", yaxis_title="Pressure (kbar)", height=580)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{len(pt):,} of {len(subset):,} selected analyses include both values.")
    else:
        st.info("No selected analyses contain both pressure and temperature values.")

with tab_up:
    st.subheader("Upload and compare your garnet compositions")
    st.caption("Upload a CSV with endmember columns (mol %). Your data is compared with the analyses currently selected in the sidebar and is not stored.")
    comps = ["Almandine_%", "Spessartine_%", "Pyrope_%", "Grossular_%"]
    template = pd.DataFrame({"Sample_ID": ["Example-1"], "Almandine_%": [65.0], "Spessartine_%": [5.0],
                             "Pyrope_%": [12.0], "Grossular_%": [18.0]})
    st.download_button("Download CSV template", data=template.to_csv(index=False).encode("utf-8"),
                       file_name="garnet_upload_template.csv", mime="text/csv")
    uploaded = st.file_uploader("Upload CSV", type="csv")
    if uploaded is not None:
        try:
            user = pd.read_csv(uploaded)
        except Exception:
            st.error("Could not read the file as CSV.")
            st.stop()
        missing = [c for c in comps if c not in user.columns]
        if missing:
            st.error("Missing required columns: " + ", ".join(missing))
        else:
            if "Sample_ID" not in user.columns:
                user.insert(0, "Sample_ID", [f"Upload-{i + 1}" for i in range(len(user))])
            for c in comps:
                user[c] = pd.to_numeric(user[c], errors="coerce")
            user = user.dropna(subset=comps).reset_index(drop=True)
            ref = subset.dropna(subset=comps)
            if user.empty:
                st.warning("No rows with complete numeric endmember values.")
            elif ref.empty:
                st.info("No database analyses match the sidebar filters.")
            else:
                st.success(f"{len(user):,} uploaded analyses compared with {len(ref):,} database analyses.")
                u1, u2 = st.columns(2)
                ux = u1.selectbox("X-axis", comps, index=2, key="up_x")
                uy = u2.selectbox("Y-axis", comps, index=3, key="up_y")
                fig = px.scatter(ref, x=ux, y=uy, color="Lithology_Category", opacity=0.4,
                                 hover_data=["Garnet_ID", "Unit", "State"], render_mode="webgl")
                fig.add_scatter(x=user[ux], y=user[uy], mode="markers", name="Your samples", text=user["Sample_ID"],
                                marker=dict(color="black", size=11, symbol="star", line=dict(color="white", width=1)))
                fig.update_layout(legend_title_text="Lithology", height=560)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("**Percentile of each uploaded sample within the selected database analyses**")
                pct = user[["Sample_ID"]].copy()
                for c in comps:
                    pct[c.replace("_%", " pctl")] = [round(100 * (ref[c] <= v).mean(), 1) for v in user[c]]
                st.dataframe(pct, use_container_width=True, hide_index=True)

                st.markdown("**Closest database match (Aitchison distance)**")
                st.caption("Endmembers are closed to 100%, zeros are replaced with 0.01 before the centered log-ratio (clr) transform, and distance is Euclidean in clr space.")

                def clr(values):
                    arr = np.clip(np.asarray(values, dtype=float), 0.01, None)
                    arr = arr / arr.sum(axis=-1, keepdims=True)
                    logs = np.log(arr)
                    return logs - logs.mean(axis=-1, keepdims=True)

                ref_clr = clr(ref[comps].to_numpy())
                rows = []
                for _, r in user.iterrows():
                    d = np.linalg.norm(ref_clr - clr(r[comps].to_numpy()), axis=1)
                    best = ref.iloc[int(d.argmin())]
                    rows.append({"Sample_ID": r["Sample_ID"], "Closest Garnet_ID": best["Garnet_ID"],
                                 "Distance": round(float(d.min()), 2), "Lithology": best["Lithology_Category"],
                                 "Unit": best["Unit"], "State": best["State"]})
                matches_df = pd.DataFrame(rows)
                st.dataframe(matches_df, use_container_width=True, hide_index=True)
                st.download_button("Download matches CSV", data=matches_df.to_csv(index=False).encode("utf-8"),
                                   file_name="garnet_closest_matches.csv", mime="text/csv")

st.divider()
st.caption("Source: uploaded Southern Appalachian bedrock garnet compilation. Interpret sample locations, lithologies, and P–T values in their original geological context.")
