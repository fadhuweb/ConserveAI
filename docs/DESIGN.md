# ConserveAI — Interface Design

This document specifies the dashboard UI (built in Figma for the design deliverable)
and the live API interface (Swagger UI) used for the initial software demo.

The machine-learning model is served through a **FastAPI backend**; the **Swagger UI**
at `/docs` is the working API interface demonstrated in this submission. The React
dashboard below is the planned frontend (next milestone) and is captured here as a
wireframe/mockup for the design requirement.

---

## 1. Planned dashboard — wireframes

### 1.1 Login screen

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                    🛡  ConserveAI                       │
│        Wildlife threat forecasting — Nigeria           │
│                                                        │
│            ┌──────────────────────────┐                │
│            │ Username                  │                │
│            └──────────────────────────┘                │
│            ┌──────────────────────────┐                │
│            │ Password                  │                │
│            └──────────────────────────┘                │
│            ┌──────────────────────────┐                │
│            │         Log in           │                │
│            └──────────────────────────┘                │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 1.2 Park manager dashboard (main screen)

```
┌────────────────────────────────────────────────────────────────────┐
│  ConserveAI   Yankari Game Reserve            manager_yankari ▾ │ ⎋ │
├────────────────────────────────────────────────────────────────────┤
│  TODAY'S RISK                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 🔥 Fire      │  │ 💧 Drought   │  │ 🌿 Vegetation│              │
│  │   16%  LOW   │  │  98%  HIGH   │  │  48%  MED    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├──────────────────────────────────┬─────────────────────────────────┤
│  30-DAY FORECAST HISTORY          │   ZONE MAP                      │
│   risk                            │   ┌───────────┬───────────┐     │
│  1.0┤        drought ___          │   │  NW       │   NE      │     │
│     │      __/                    │   │  ███      │   ██      │     │
│  0.5┤  fire/   veg ~~~~           │   ├───────────┼───────────┤     │
│     │ ~~~~~~                      │   │  SW       │   SE      │     │
│  0.0└──────────────────────       │   │  ██       │   ███     │     │
│      Apr   May   Jun              │   └───────────┴───────────┘     │
│                                   │   (shaded by allocation)        │
├──────────────────────────────────┴─────────────────────────────────┤
│  RECOMMENDATION                                                     │
│   Budget [ $10,000 ]   Zone priority:                              │
│                          NW [High▾] NE [Normal▾] SW [Low▾] SE [High▾]│
│   ┌──────────────────────┐                                         │
│   │  Get Recommendations │                                         │
│   └──────────────────────┘                                         │
│   Result:  8× Water Trucking · 5× Community · 1× Fire Patrol        │
│            Drought 98% → 15%   Cost $9,900 / $10,000                │
└────────────────────────────────────────────────────────────────────┘
```

### 1.3 National overview (admin only)

```
┌────────────────────────────────────────────────────────────────────┐
│  ConserveAI — National Overview                    admin ▾  │  ⎋   │
├────────────────────────────────────────────────────────────────────┤
│  Park              Fire     Drought   Vegetation   Updated          │
│  ─────────────────────────────────────────────────────────────────  │
│  Yankari           🔴 99%   🟢 1%     🟡 45%       2026-06-03       │
│  Cross River       🔴 98%   🟢 1%     🟡 46%       2026-06-03       │
│  Gashaka-Gumti     🔴 99%   🟢 1%     🟡 44%       2026-06-03       │
│  Kainji Lake       🔴 99%   🟢 1%     🟡 44%       2026-06-03       │
│  Chad Basin        🔴 99%   🟢 1%     🟡 47%       2026-06-03       │
│  Old Oyo           🔴 99%   🟢 1%     🟡 45%       2026-06-03       │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Figma build spec

Recreate the three screens above with these settings:

- **Frame size:** 1440 × 1024 (desktop)
- **Font:** Inter or Roboto — 24px headings, 14px body
- **Palette:**
  - Fire `#E64A19` · Drought `#1976D2` · Vegetation `#388E3C`
  - Risk pills: high `#D32F2F`, medium `#F9A825`, low `#43A047`
  - Background `#F5F7FA`, cards white with 8px radius + subtle shadow
- **Components to draw:**
  1. Three **risk cards** (icon, threat name, percentage, HIGH/MED/LOW pill)
  2. A **line chart** placeholder with three coloured lines (use Figma's pen or a chart plugin)
  3. A **2×2 zone grid** (Leaflet stand-in) with quadrants shaded by allocation
  4. A **recommendation panel**: budget input, four zone-priority dropdowns, a button, and a result block
  5. The **national overview table** with coloured status dots
- **Navigation flow (prototype links):** Login → Manager Dashboard → (admin) National Overview

Export each frame as PNG into `docs/screenshots/` (see below).

---

## 3. Screenshot checklist (Swagger UI — the live demo interface)

Start the server, open `http://localhost:8000/docs`, and capture these into
`docs/screenshots/`:

| File name | What to capture |
|-----------|-----------------|
| `01_swagger_overview.png` | The full `/docs` page showing the API title, description with demo accounts, and the four tag groups collapsed |
| `02_login.png` | `POST /auth/login` expanded, request body filled with `admin` / `admin2025`, and the 200 response |
| `03_national_overview.png` | `GET /national-overview` 200 response showing all six parks |
| `04_forecasts.png` | `GET /forecasts/yankari` 200 response with the forecast history array |
| `05_recommend.png` | `POST /recommend` with `{"park":"yankari","budget":10000}` and the response showing `allocation` + `zone_allocations` |
| `06_sensitivity.png` | `POST /sensitivity` 200 response with the robustness report |

Plus the three Figma frames:

| File name | What to capture |
|-----------|-----------------|
| `figma_01_login.png` | Login frame |
| `figma_02_dashboard.png` | Manager dashboard frame |
| `figma_03_national.png` | National overview frame |

These ten images cover the "Designs (mockups + screenshots of the app interfaces)"
requirement and feed the README and the video demo.
