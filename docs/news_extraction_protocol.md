# News Extraction Protocol — ConserveAI Incident Labeling

## Purpose

This protocol defines how drought and vegetation degradation incidents are
extracted from Nigerian news sources to generate training labels for the
ConserveAI threat detection models. Labels derived from news incidents follow
the semi-supervised approach: for each incident on date D, all rows in
[D-30, D] are labeled 1 for the relevant threat type. Rows with no supporting
news evidence remain unlabeled (NaN), not 0.

---

## Sources to Search (in priority order)

| Source | URL | Notes |
|---|---|---|
| Daily Trust | dailytrust.com | Northeast Nigeria focus; most consistent Yankari coverage |
| Premium Times | premiumtimesng.com | National coverage; environment section |
| Vanguard | vanguardngr.com | Lagos-based; national reach |
| Punch | punchng.com | National; environment and agriculture sections |
| The Guardian Nigeria | guardian.ng | National; nature and property sections |
| EnviroNews Nigeria | environewsnigeria.com | Environment specialist; good archive |
| BBC Pidgin | bbc.com/pidgin | Broad northern Nigeria coverage |
| Reuters Nigeria | reuters.com (Nigeria tag) | International wire; major events only |
| Mongabay Africa | news.mongabay.com | Conservation-focused; good archive |
| WCS Nigeria | nigeria.wcs.org | Official reports; dateable field observations |
| ACReSAL | acresal.gov.ng | World Bank project; intervention dates documented |

---

## Search Keywords by Threat Type

### Drought
- "drought Yankari"
- "water shortage Yankari"
- "dry conditions Bauchi wildlife"
- "waterhole Yankari"
- "Gaji river dry"
- "drought Bauchi state wildlife"
- "water scarcity Yankari Game Reserve"
- "elephant water Yankari"

### Vegetation Degradation
- "deforestation Yankari"
- "encroachment Yankari Game Reserve"
- "illegal grazing Yankari"
- "vegetation loss Bauchi reserve"
- "bush burning Yankari"
- "illegal logging Bauchi park"
- "charcoal Yankari"
- "habitat loss Yankari"

---

## Date Handling Rules

- Use the date the event is reported as occurring, not the article publication date
- If an article says "the drought has persisted since July" and is published
  in September, use July 1 as the incident date
- If only a season is given ("last dry season"), use the midpoint of that
  season for the park (e.g., January 15 for Yankari dry season Nov-Mar)
- If only a year is given with no month, use July 1 of that year as a
  conservative midpoint
- If a range is stated ("between June and August"), use the midpoint (July 1)

---

## Inclusion Criteria

An incident is included if ALL of the following are true:

1. The event occurred in or directly affecting one of the six target parks
2. The event can be assigned a date with confidence of +/- 3 months or better
3. The event represents genuine ecological stress, not routine seasonal
   conditions (dry season zero rainfall is NOT a drought incident)
4. The source is a named publication or organisation (no anonymous blogs)

An incident is excluded if:
- It describes only poaching or security incidents with no ecological stress
- The location is Bauchi State generally but not the park specifically
- The date cannot be estimated to within 3 months
- The source cannot be verified

---

## Confidence Levels

| Level | Meaning |
|---|---|
| High | Specific date, named location inside park, direct quote from ranger/official |
| Medium | Month and year, park named, ecological impact described |
| Low | Year only, or park region named but not park specifically |

Only High and Medium confidence incidents are used for labeling.
Low confidence incidents are recorded but excluded from label generation.

---

## incidents.csv Column Definitions

| Column | Description |
|---|---|
| park | Park key (e.g., yankari) |
| threat_type | drought or vegetation |
| incident_date | Best estimate of event date (YYYY-MM-DD) |
| date_confidence | high / medium / low |
| source_url | Full URL of article or report |
| source_name | Publication name |
| description | One sentence description of the incident |
| notes | Any judgment calls or caveats |

---

## Extraction Findings — Yankari Game Reserve (2020-2025)

Systematic searches were conducted across all sources listed above using all
keywords listed above on 2026-05-15.

**Drought incidents:** Zero dateable incidents recovered. Coverage of Yankari
drought conditions in English-language Nigerian news is absent for 2020-2025.
Daily Trust articles most likely to contain relevant content returned HTTP 403
Forbidden to automated access; manual review is required to confirm absence.

**Vegetation degradation incidents:** Zero dateable incidents recovered.
Academic sources contain vegetation loss data but reference periods ending in
2016-2017, outside the 2020-2025 target window.

**Decision:** Given zero recoverable incidents, drought and vegetation labels
were derived algorithmically from the climate and NDVI data already collected,
using ecologically validated thresholds consistent with the independent
ground-truth definitions in the project scope document. See
src/data_pipeline/label_drought_vegetation.py for implementation and the
thesis Methods section for full justification.

This outcome is consistent with the risk note in the Implementation Plan:
"If Yankari has zero drought or vegetation incidents in the news, that is a
finding worth reporting in the discussion."