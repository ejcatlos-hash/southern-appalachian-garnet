# Southern Appalachian Bedrock Garnet Explorer

Streamlit app exploring the Southern Appalachian bedrock garnet compilation.

The landing page leads with an interactive sample map. Click markers or use box/lasso selection to focus the data explorer and analysis tabs on selected locations; sidebar filters can further narrow those results.

## Deploy
1. Place `app.py`, `requirements.txt`, and `Final_Database.csv` at the repository root.
2. On Streamlit Community Cloud, create an app from that GitHub repository.
3. Select branch `main`, entry point `app.py`, and deploy.

## Local run
`pip install -r requirements.txt`
`streamlit run app.py`

The app preserves source lithology and geological unit labels, and does not impute missing P–T data.
