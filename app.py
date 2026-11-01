from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Southern Appalachian Garnet Explorer", page_icon="💎", layout="wide")
st.title("Southern Appalachian Bedrock Garnet Explorer")
st.caption("Explore individual bedrock garnet compositions, geological context, and sample localities.")

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

c1, c2, c3 = st.columns(3)
c1.metric("Selected analyses", f"{len(subset):,}")
c2.metric("Coordinate pairs", f"{len(subset[['Latitude', 'Longitude']].dropna().drop_duplicates()):,}")
c3.metric("Geological units", f"{subset['Unit'].nunique():,}")

tab_data, tab_map, tab_chem, tab_pt = st.tabs(["Data explorer", "Sample map", "Garnet chemistry", "Pressure–temperature"])

with tab_data:
    st.subheader("Bedrock garnet analyses")
    st.dataframe(subset, use_container_width=True, hide_index=True)
    st.download_button("Download filtered CSV", data=subset.to_csv(index=False).encode("utf-8"),
                       file_name="southern_appalachian_garnet_filtered.csv", mime="text/csv")

with tab_map:
    st.subheader("Sample localities")
    st.caption("One marker per unique coordinate pair. Markers indicate sample locations, not individual grains.")
    points = subset.dropna(subset=["Latitude", "Longitude"])
    if not points.empty:
        sites = (points.groupby(["Latitude", "Longitude"], as_index=False)
                 .agg(analyses=("Garnet_ID", "size"), units=("Unit", "nunique")))
        st.map(sites.rename(columns={"Latitude": "latitude", "Longitude": "longitude"}))
        st.dataframe(sites, use_container_width=True, hide_index=True)
    else:
        st.info("No mapped samples match these filters.")

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

st.divider()
st.caption("Source: uploaded Southern Appalachian bedrock garnet compilation. Interpret sample locations, lithologies, and P–T values in their original geological context.")
