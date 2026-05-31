# Frontiers 2026 - Voice of Customer Dashboard

A single-page **Streamlit** dashboard for **Frontiers 2026 Voice-of-Customer**
survey results. It reads its data from a CSV committed inside this repo.
**To update the dashboard, replace the CSV and reload** — no admin panel, no login.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.40-red)

---

## What it shows

- **KPI scorecards** — total responses, overall satisfaction, keynote / panel /
  workshop, likelihood to apply, likelihood to collaborate, most requested next step
- **Trend over time** with a view toggle: **Overall / Attendee Type / Campaign**
- **Agency vs Client** comparison
- **Campaign performance** ranking
- **Score-distribution heat map** (by attendee type or campaign)
- **Qualitative insights** — top themes + verbatim comments for next step, reason,
  and suggested improvement
- **Response explorer** with CSV export of the filtered view
- **Filters** — Campaign, Attendee Type, Account, Response Date, open-text search

The dashboard shows absolute counts and average scores only (1-5 scale).

---

## Updating the data

The dashboard's data source is **`data/frontiers_responses.csv`**.

1. Export a fresh **Frontiers Responses** CSV (same column headers).
2. Replace `data/frontiers_responses.csv` in the repo (commit + push, or just
   overwrite the file locally).
3. Reload the app (or click **Reload data** in the sidebar).

Header matching is whitespace/newline tolerant; the column mapping lives in
`src/config.py`. Expected columns: `Responsedate`, `Name`, `Account Name`,
`Email`, `Attendee Type`, `Campaign Name`, the six 1-5 survey-score questions, and
the three open-text questions.

---

## Run locally

```bash
git clone <your-repo-url>
cd frontiers-voc-dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501.

---

## Deploy on Streamlit Community Cloud (via GitHub)

1. Push this repo to GitHub.
2. Go to https://share.streamlit.io → **New app**.
3. Select your repo/branch and set the main file to `app.py`.
4. Deploy — `requirements.txt` is installed automatically.

To update a deployed app later, just commit a new `data/frontiers_responses.csv`;
the app reloads from it.

---

## Project structure

```
frontiers-voc-dashboard/
├── app.py                       # The dashboard (single page)
├── src/
│   ├── config.py                # Data path, column mapping, survey metadata
│   ├── data.py                  # CSV load + normalisation
│   └── charts.py                # Plotly chart builders + theme extraction
├── data/
│   └── frontiers_responses.csv  # Source data (replace this to update)
├── .streamlit/config.toml       # Theme + server settings
├── requirements.txt
└── README.md
```
