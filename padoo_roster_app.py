#!/usr/bin/env python3
"""
Padoo Cafe Roster App - Cloud Ready Version
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# ==================== CONFIG ====================
st.set_page_config(
    page_title="Padoo Roster",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
FULL_TIMERS = ["Jantzen", "Jessie", "Arman", "Melvin"]
PART_TIMERS = ["Dhib", "Yee Yan", "Sean", "Kelvin"]
ALL_PEOPLE = FULL_TIMERS + PART_TIMERS

WEEKDAY_EARLY = "6:30 AM"
WEEKDAY_LATE = "8:30 AM"
WEEKEND_EARLY = "8:30 AM"
WEEKEND_LATE = "9:00 AM"

WEEKDAY_HOURS = 10.0
WEEKEND_HOURS = 8.0
LATE_WEEKDAY_HOURS = 8.0
LATE_WEEKEND_HOURS = 7.5

# ==================== HELPERS ====================
def is_weekend(day_idx: int) -> bool:
    return day_idx >= 5

def calc_cost(hours: float, rate: float, oncost: float) -> float:
    return round(hours * rate * (1 + oncost), 2)

# ==================== ROSTER ENGINE ====================
def generate_roster(availability: dict, owner_preference: dict):
    roster = {}

    for d in range(7):
        weekend = is_weekend(d)
        early_start = WEEKEND_EARLY if weekend else WEEKDAY_EARLY
        late_start = WEEKEND_LATE if weekend else WEEKDAY_LATE
        full_h = WEEKEND_HOURS if weekend else WEEKDAY_HOURS
        late_h = LATE_WEEKEND_HOURS if weekend else LATE_WEEKDAY_HOURS

        slots = [None, None, None]

        arman_off = d in (3, 4)
        melvin_off = d in (5, 6)

        # Place Arman & Melvin first as early starters
        early_candidates = []
        if not melvin_off:
            early_candidates.append("Melvin")
        if not arman_off:
            early_candidates.append("Arman")

        idx = 0
        for person in early_candidates:
            if idx < 2:
                slots[idx] = (person, early_start, "4:30 PM", full_h, "Full-timer")
                idx += 1

        needed = 3 - sum(1 for s in slots if s is not None)

        day_avail = availability.get(d, {})
        available_pt = [(pt, note.strip()) for pt, note in day_avail.items() if note and note.strip()]

        preferred_owners = [owner for owner, days in owner_preference.items() if d in days]
        candidates = preferred_owners + [pt for pt, _ in available_pt]

        for person in candidates:
            if needed <= 0:
                break
            for i in range(3):
                if slots[i] is None:
                    if i < 2:
                        start = early_start
                        hrs = full_h
                    else:
                        start = late_start
                        hrs = late_h

                    # Special timing overrides for PT
                    if person in PART_TIMERS:
                        note = day_avail.get(person, "").lower()
                        if "8:30" in note and ("13:00" in note or "1:00" in note):
                            start, hrs = "8:30 AM", 4.5
                        elif "12:00" in note or "12pm" in note:
                            start, hrs = "12:00 PM", 4.5
                        elif "9:30" in note:
                            start, hrs = "9:30 AM", 7.0
                        elif "10:00" in note or "after 10" in note:
                            start, hrs = "10:00 AM", 6.5
                        elif "12:30" in note:
                            start, hrs = "12:30 PM", 4.0

                    role = "Owner" if person in ["Jantzen", "Jessie"] else "Part-timer"
                    slots[i] = (person, start, "4:30 PM", hrs, role)
                    needed -= 1
                    break

        # Fallback: force owner if still short
        if needed > 0:
            for owner in ["Jessie", "Jantzen"]:
                if needed <= 0:
                    break
                if not any(s and s[0] == owner for s in slots):
                    for i in range(3):
                        if slots[i] is None:
                            start = early_start if i < 2 else late_start
                            hrs = full_h if i < 2 else late_h
                            slots[i] = (owner, start, "4:30 PM", hrs, "Owner")
                            needed -= 1
                            break

        roster[d] = slots
    return roster

# ==================== UI ====================
st.title("☕ Padoo Cafe Roster App")
st.caption("Auto-generate 3-person daily roster • Track hours • Estimate labour cost")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    week_start = st.date_input("Week starting (Monday)", value=datetime(2026, 10, 5))
    if week_start.weekday() != 0:
        st.warning("Please select a Monday for best results")

    st.divider()
    st.subheader("Owner Shop Days")
    st.caption("Choose 2–3 preferred days each")
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    jantzen_days = st.multiselect("Jantzen days", options=list(range(7)),
                                   format_func=lambda x: day_labels[x], default=[0, 3, 5])
    jessie_days = st.multiselect("Jessie days", options=list(range(7)),
                                  format_func=lambda x: day_labels[x], default=[2, 4, 6])

    st.divider()
    st.subheader("Cost Settings")
    pt_rate = st.number_input("PT rate (RM/hour)", value=10.0, step=0.5)
    oncost = st.slider("Employer on-cost %", 10, 20, 15) / 100.0

# Tabs
tab1, tab2, tab3 = st.tabs(["📅 Generate Roster", "📊 Rules", "💾 How to Save"])

with tab1:
    st.subheader("Part-timer Availability this week")
    st.caption("Type: **F** (full day) | **O** (opening) | **C** (closing) | or special time e.g. `8:30-13:00` / `after 10am` / `12:30 onwards`")

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    availability = {}

    cols = st.columns(7)
    for d, col in enumerate(cols):
        with col:
            st.markdown(f"**{days[d]}**")
            day_avail = {}
            for pt in PART_TIMERS:
                val = st.text_input(pt, key=f"avail_{d}_{pt}", placeholder="F / O / C / time",
                                    label_visibility="collapsed")
                if val and val.strip():
                    day_avail[pt] = val.strip()
            availability[d] = day_avail

    st.divider()

    if st.button("🚀 Generate Roster", type="primary", use_container_width=True):
        owner_pref = {"Jantzen": jantzen_days, "Jessie": jessie_days}
        roster = generate_roster(availability, owner_pref)

        st.success("✅ Roster generated successfully!")

        # Build display
        display_data = []
        total_hours = 0.0
        pt_hours = 0.0
        person_week_hours = {p: 0.0 for p in ALL_PEOPLE}

        for d in range(7):
            slots = roster[d]
            row = {"Day": days[d]}
            day_h = 0.0
            for i, slot in enumerate(slots):
                if slot:
                    name, start, end, hrs, role = slot
                    row[f"Person {i+1}"] = f"{name}\n{start} – {end}\n({hrs}h)"
                    day_h += hrs
                    person_week_hours[name] += hrs
                    if name in PART_TIMERS:
                        pt_hours += hrs
                else:
                    row[f"Person {i+1}"] = "—"
            row["Day Total"] = round(day_h, 1)
            total_hours += day_h
            display_data.append(row)

        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Staff Hours", f"{total_hours:.1f} h")
        c2.metric("PT Hours only", f"{pt_hours:.1f} h")
        c3.metric("Est. PT Cost", f"RM {calc_cost(pt_hours, pt_rate, oncost):,.0f}")
        c4.metric("Avg / Day", f"{total_hours/7:.1f} h")

        # Hours breakdown
        st.subheader("Hours this week by person")
        hours_df = pd.DataFrame([
            {"Name": p, "Hours": round(h, 1),
             "Type": "Full-timer" if p in FULL_TIMERS else "Part-timer"}
            for p, h in person_week_hours.items() if h > 0
        ]).sort_values("Hours", ascending=False)
        st.dataframe(hours_df, use_container_width=True, hide_index=True)

        # Download buttons
        st.subheader("Download / Save")
        col_a, col_b = st.columns(2)

        # CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        col_a.download_button(
            "📥 Download Roster (CSV)",
            data=csv,
            file_name=f"Padoo_Roster_{week_start}.csv",
            mime="text/csv"
        )

        # JSON download for record
        save_data = {
            "week_start": str(week_start),
            "total_hours": total_hours,
            "pt_hours": pt_hours,
            "person_hours": person_week_hours,
            "generated_at": datetime.now().isoformat()
        }
        json_str = json.dumps(save_data, indent=2)
        col_b.download_button(
            "📥 Download Hours Record (JSON)",
            data=json_str,
            file_name=f"Padoo_Hours_{week_start}.json",
            mime="application/json"
        )

with tab2:
    st.subheader("Rules currently locked in the app")
    st.markdown("""
    | Rule | Detail |
    |------|--------|
    | Staffing | **Exactly 3 people** every day |
    | Early starters | **Arman & Melvin** always start at 6:30 AM (weekday) or 8:30 AM (weekend) when they work |
    | Arman | OFF every **Thursday & Friday** |
    | Melvin | OFF every **Saturday & Sunday** |
    | Owners | You choose preferred days in the sidebar (recommended 2–3 days each) |
    | Part-timers | Filled according to what you type in the availability boxes |
    | Special times | Supported (e.g. `8:30-13:00`, `after 10am`, `12:30 onwards`) |
    | Cost | RM10/hour + adjustable employer on-cost (default 15%) |
    """)

with tab3:
    st.subheader("How to keep records")
    st.markdown("""
    Because this is a free online app, data is **not permanently stored** on the server.

    **Recommended way:**
    1. Generate the roster
    2. Click **Download Roster (CSV)** → save to your Google Drive / phone
    3. Click **Download Hours Record (JSON)** if you want to track monthly fairness later

    You can also screenshot the roster or copy-paste into your existing Google Sheet.
    """)

st.divider()
st.caption("Padoo Cafe • Kota Kemuning • Keep labour healthy ☕")
