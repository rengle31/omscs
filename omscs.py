import datetime
import html
import json
import re
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st

TERM_URL = "https://raw.githubusercontent.com/omshub/data/refs/heads/main/data/202605.json"
COURSES_URL = "https://raw.githubusercontent.com/omshub/data/refs/heads/main/static/courses.json"

EXCLUDED_TITLE_PATTERNS = (
    "doctoral thesis",
    "special problems",
    "master's thesis",
    "masters thesis",
)


def _is_excluded(title: str) -> bool:
    t = (title or "").lower()
    return any(p in t for p in EXCLUDED_TITLE_PATTERNS)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "omscs-occupancy/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


@st.cache_data(ttl=300, show_spinner="Loading latest course data…")
def load_data():
    term_data = fetch_json(TERM_URL)
    courses_meta = fetch_json(COURSES_URL)

    alias_map = {
        cid: ", ".join(meta.get("aliases") or []) for cid, meta in courses_meta.items()
    }
    full_name_map = {cid: meta.get("name", "") for cid, meta in courses_meta.items()}

    rows = []
    for course_id, course in term_data.get("courses", {}).items():
        for section in course.get("sections", []):
            section_num = section.get("sectionNumber", "") or ""
            if not (len(section_num) >= 2 and section_num[0] == "O" and section_num[1].isdigit()):
                continue

            title = html.unescape(full_name_map.get(course_id) or course.get("name", ""))
            if _is_excluded(title):
                continue

            capacity = section.get("capacity") or 0
            enrolled = section.get("enrolled") or 0
            seats_available = section.get("seatsAvailable")
            if seats_available is None:
                seats_available = max(capacity - enrolled, 0)
            wait_count = section.get("waitCount") or 0
            wait_capacity = section.get("waitCapacity") or 0
            wait_left = max(wait_capacity - wait_count, 0)
            fill_rate = (
                int(round(100 * (enrolled + wait_count) / capacity)) if capacity else 0
            )

            rows.append(
                {
                    "Title": title,
                    "Aliases": alias_map.get(course_id, ""),
                    "Course Number": course.get("courseNumber", ""),
                    "Section": section_num,
                    "CRN": section.get("crn", ""),
                    "Instructor": section.get("instructor", "") or "",
                    "Seats Total": capacity,
                    "Seats Taken": enrolled,
                    "WL Taken": wait_count,
                    "WL Left": wait_left,
                    "Seats Left": seats_available,
                    "% Fill Rate": fill_rate,
                }
            )

    df = pd.DataFrame(rows)

    last_updated_raw = term_data.get("lastUpdated")
    data_timestamp = None
    if last_updated_raw:
        try:
            data_timestamp = datetime.datetime.fromisoformat(
                last_updated_raw.replace("Z", "+00:00")
            )
        except ValueError:
            data_timestamp = None

    return df, data_timestamp, term_data.get("termName", "")


def apply_status(df: pd.DataFrame) -> pd.DataFrame:
    conditions = [
        (df["Seats Left"]) <= 0 | (df["WL Taken"] > df["Seats Left"]),
        (df["% Fill Rate"] >= 75) & (df["Seats Left"] > 0),
        df["% Fill Rate"] < 75,
    ]
    choices = ["🔴", "🟠", "🟢"]
    df.insert(0, "Status", np.select(conditions, choices, default="🔴"))
    return df


def _term_mask(df: pd.DataFrame, term: str) -> pd.Series:
    term = term.strip()
    if not term:
        return pd.Series(True, index=df.index)

    esc = re.escape(term)
    alias_pattern = rf"(?:^|,\s*){esc}(?:\s*,|$)"
    word_pattern = rf"\b{esc}\b"

    return (
        df["Title"].str.contains(esc, case=False, na=False, regex=True)
        | df["Aliases"].str.contains(alias_pattern, case=False, na=False, regex=True)
        | df["Course Number"].astype(str).str.contains(esc, case=False, na=False, regex=True)
        | df["Instructor"].str.contains(word_pattern, case=False, na=False, regex=True)
        | df["CRN"].astype(str).str.contains(esc, case=False, na=False, regex=True)
    )


def search_df(df: pd.DataFrame, query: str) -> pd.DataFrame:
    query = (query or "").strip()
    if not query:
        return df

    or_mask = pd.Series(False, index=df.index)
    for clause in query.split("|"):
        and_terms = [t for t in (p.strip() for p in clause.split("&")) if t]
        if not and_terms:
            continue
        and_mask = pd.Series(True, index=df.index)
        for term in and_terms:
            and_mask &= _term_mask(df, term)
        or_mask |= and_mask
    return df[or_mask]


def main():
    st.set_page_config(layout="wide", page_title="OMSCS Course Occupancy")
    st.markdown(
        """
        <style>
            .block-container { padding-top: 3rem; }
            .right-align-container { text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns([1, 8, 1])

    with middle:
        st.markdown(
            """<div class="right-align-container"><a href='https://ko-fi.com/Y8Y51S5314' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a></div>""",
            unsafe_allow_html=True,
        )

        try:
            df, data_timestamp, term_name = load_data()
        except Exception as exc:
            st.markdown("## OMSCS Course Occupancy")
            st.error(f"Data unavailable: {exc}. Try again later.")
            return

        header = "OMSCS Course Occupancy"
        if term_name:
            header += f" — {term_name}"
        st.markdown(f"## {header}")

        if data_timestamp is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            age = now - data_timestamp
            age = datetime.timedelta(seconds=max(int(age.total_seconds()), 0))
            st.text(
                f"Data Age: {age}, Data Timestamp: "
                f"{data_timestamp.astimezone(datetime.timezone.utc):%Y-%m-%d %H:%M:%S} UTC"
            )

        if df.empty:
            st.warning("No online sections found in the source data.")
            return

        df = apply_status(df)
        df.sort_values(by="Seats Left", ascending=False, inplace=True, ignore_index=True)

        search_term = st.text_input(
            "**Search** — course number, title keywords, alias (e.g. `NLP`), instructor, or CRN. "
            "Combine with `&` (AND) and `|` (OR), e.g. `ML | NLP`, `reinforcement & learning`."
        )
        filtered = search_df(df, search_term)

        st.caption(f"Showing {len(filtered):,} of {len(df):,} sections")

        st.dataframe(
            filtered,
            height="content",
            width="stretch",
            hide_index=True,
            column_config={
                "Instructor": None,
                "% Fill Rate": st.column_config.ProgressColumn(
                    "% Fill Rate",
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                    color="blue",
                ),
            },
        )


if __name__ == "__main__":
    main()
