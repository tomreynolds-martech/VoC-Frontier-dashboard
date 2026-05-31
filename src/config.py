"""Central configuration: data path, column mapping, and survey metadata.

The dashboard reads its data from the CSV committed inside the repo at
``data/frontiers_responses.csv``. To update the dashboard, replace that file
(same column headers) and reload the app.
"""
from __future__ import annotations

import os

# --- Paths -----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_CSV = os.path.join(DATA_DIR, "frontiers_responses.csv")

APP_TITLE = "Frontiers 2026 - Voice of Customer"
APP_ICON = "📊"

# --- Column mapping --------------------------------------------------------
# Maps the exact CSV header text -> a short, code-friendly field name.
# Header matching is whitespace/newline tolerant (see data.py).
COLUMN_MAP = {
    "Responsedate": "response_date",
    "Name": "name",
    "Account Name": "account_name",
    "Email": "email",
    "Attendee Type": "attendee_type",
    "Campaign Name": "campaign_name",
    "Adhoc SFDC Account - ID": "sfdc_account_id",
    "Adhoc SFDC Contact - ID": "sfdc_contact_id",
    "Program Name": "program_name",
    "Survey ID": "survey_id",
    "How satisfied are you with the relevance and value of the content presented at Frontiers 2026?": "satisfaction",
    "Fuel for Brand Fandom Keynote": "keynote",
    "Q+A Panel with Editors": "panel",
    "Workshop": "workshop",
    "How likely are you to apply the strategies or insights shared during Frontiers with your business?": "apply",
    "Based on your experience with us, how likely are you to collaborate with News\nAustralia in the future?": "collaborate",
    "What would be the most helpful next step for your business?": "next_step",
    "What is the reason for providing the score? (Optional)": "reason",
    "What is one thing we could change or add that would have made this event more impactful for you? (optional)": "improvement",
}

# Numeric survey-score fields (1-5 scale) and their display labels.
SCORE_FIELDS = {
    "satisfaction": "Overall Satisfaction",
    "keynote": "Fuel for Brand Fandom Keynote",
    "panel": "Q+A Panel with Editors",
    "workshop": "Workshop",
    "apply": "Likelihood to Apply",
    "collaborate": "Likelihood to Collaborate",
}

# Open-text fields and their display labels.
TEXT_FIELDS = {
    "next_step": "Most Helpful Next Step",
    "reason": "Reason for Score",
    "improvement": "Suggested Improvement",
}

SCORE_MIN, SCORE_MAX = 1, 5

# Stop-words used for lightweight theme extraction in qualitative insights.
STOP_WORDS = set(
    """a an the and or but if then else for to of in on at by with without from as is are was were
    be been being it its this that these those i you he she we they them us our your their my me
    was very really great good nice well had has have do did so just too much more most some any
    all no not nor about into over under out up down off than no thank thanks event events day
    workshop session sessions news australia frontiers year felt feel like would could really""".split()
)
