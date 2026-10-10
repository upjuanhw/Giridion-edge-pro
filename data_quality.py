"""Validation of public ESPN season results. Never silently treat partial data as complete."""
import pandas as pd

REQUIRED = {"date", "home", "away", "home_score", "away_score"}

def audit_games(frame):
    """Return structured, non-mutating quality findings for a season dataset."""
    findings = {"rows": len(frame), "invalid_dates": 0, "invalid_scores": 0,
                "missing_teams": 0, "duplicate_matchups": 0, "duplicate_ids": 0}
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    if frame.empty:
        return findings
    dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    home = frame["home"].fillna("").astype(str).str.strip()
    away = frame["away"].fillna("").astype(str).str.strip()
    hs = pd.to_numeric(frame["home_score"], errors="coerce")
    vs = pd.to_numeric(frame["away_score"], errors="coerce")
    findings["invalid_dates"] = int(dates.isna().sum())
    findings["invalid_scores"] = int((hs.isna() | vs.isna() | (hs < 0) | (vs < 0) | (hs % 1 != 0) | (vs % 1 != 0)).sum())
    findings["missing_teams"] = int(((home == "") | (away == "") | (home == away)).sum())
    keys = pd.DataFrame({"date": dates.dt.date, "home": home, "away": away})
    findings["duplicate_matchups"] = int(keys.duplicated().sum())
    if "event_id" in frame.columns:
        ids = frame["event_id"].fillna("").astype(str).str.strip()
        findings["duplicate_ids"] = int(ids[ids.ne("")].duplicated().sum())
    return findings

def is_clean(audit):
    return not any(v for k,v in audit.items() if k != "rows")
