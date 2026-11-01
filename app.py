from pathlib import Path
import numpy as np
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

tab_data, tab_map, tab_chem, tab_pt, tab_up = st.tabs(["Data explorer", "Sample map", "Garnet chemistry", "Pressure–temperature", "Compare your garnets"])

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
