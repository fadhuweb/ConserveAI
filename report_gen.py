# -*- coding: utf-8 -*-
"""ConserveAI final capstone report (.docx) — ALU template + ML-guide rigor,
with Chapter 3 diagram placeholders the author pastes in from the proposal."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

FIG = Path("docs/screenshots")
RFIG = Path("docs/report_figures")
doc = Document()

st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.paragraph_format.line_spacing = 1.0; st.paragraph_format.space_after = Pt(6)
for i, sz in [(1, 14), (2, 12), (3, 12)]:
    h = doc.styles[f"Heading {i}"]; h.font.name = "Times New Roman"; h.font.size = Pt(sz)
    h.font.color.rgb = RGBColor(0, 0, 0); h.font.bold = True


def _num_field(par, instr):
    for t in ("begin", None, "separate", None, "end"):
        r = OxmlElement("w:r")
        if t:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = instr; r.append(e)
        par._p.append(r)


def footer_pagenum(section, fmt="decimal", start=1):
    sectPr = section._sectPr
    pgNum = sectPr.find(qn("w:pgNumType"))
    if pgNum is None:
        pgNum = OxmlElement("w:pgNumType"); sectPr.append(pgNum)
    pgNum.set(qn("w:fmt"), fmt); pgNum.set(qn("w:start"), str(start))
    p = section.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _num_field(p, "PAGE")


def para(text, align="just", italic=False, bold=False, size=None):
    p = doc.add_paragraph(); r = p.add_run(text)
    r.italic = italic; r.bold = bold
    if size: r.font.size = Pt(size)
    p.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    return p


def h1(t): doc.add_heading(t, 1)
def h2(t): doc.add_heading(t, 2)
def h3(t): doc.add_heading(t, 3)
def numbered(t): doc.add_paragraph(t, style="List Number")
def bullet(t): doc.add_paragraph(t, style="List Bullet")
def pagebreak(): doc.add_page_break()


def caption(text):
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(text); r.italic = True; r.font.size = Pt(10)


def code(snippet, cap):
    """Monospace, shaded source-code listing with a caption."""
    t = doc.add_table(rows=1, cols=1); t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "F6F8FA")
    cell._tc.get_or_add_tcPr().append(shd)
    first = True
    for line in snippet.strip("\n").split("\n"):
        p = cell.paragraphs[0] if first else cell.add_paragraph(); first = False
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line if line.strip() else " ")
        r.font.name = "Consolas"; r.font.size = Pt(8.5)
    caption(cap)


def figure(name, cap, width=6.0, base=FIG):
    path = base / name
    if path.exists():
        doc.add_picture(str(path), width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption(cap)


def placeholder(what, source, cap):
    """A shaded, bordered box marking where the author pastes a diagram image."""
    t = doc.add_table(rows=1, cols=1); t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "FFF3CD")
    cell._tc.get_or_add_tcPr().append(shd)
    p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    r = p.add_run(f"[ PASTE IMAGE HERE — {what} ]"); r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B); r.font.size = Pt(12)
    p2 = cell.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(source); r2.italic = True; r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x88, 0x6A, 0x00)
    p3 = cell.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(18)
    caption(cap)


def table(headers, rows, cap, style="Light Grid Accent 1"):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = style
    for i, hh in enumerate(headers): t.rows[0].cells[i].text = hh
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row): cells[i].text = str(v)
    caption(cap)


def centre_title(text, size=14, bold=True, space=12):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.bold = bold; r.font.size = Pt(size)
    p.paragraph_format.space_before = Pt(space)

# ══════════════════ PRELIMINARY PAGES (roman numerals) ══════════════════
for _ in range(4): doc.add_paragraph()
centre_title("Hybrid Machine Learning System for Multi-Threat Probabilistic "
             "Forecasting and Budget-Constrained Intervention Recommendation in "
             "Nigerian National Parks", size=14, space=0)
doc.add_paragraph()
for t in ["BSc. Software Engineering", "Fadhlullah Olusola Abdulazeez",
          "Capstone Project", "Supervisor: Mr. Emmanuel Adjei", "2026"]:
    centre_title(t, size=12)

pagebreak()
centre_title("DECLARATION", size=12); doc.add_paragraph()
para("This capstone project is my original work, unless stated, and all external "
     "sources have been referenced or cited in my document. This work has not been "
     "presented for the award of a degree or for any similar purpose in any other "
     "university.")
doc.add_paragraph()
para("Signature……………………………      Date……………………………", align="left")
para("Name of Student: Fadhlullah Olusola Abdulazeez", align="left")

pagebreak()
centre_title("CERTIFICATION", size=12); doc.add_paragraph()
para("The undersigned certifies that he has read and hereby recommends for "
     "acceptance by African Leadership University a report entitled “Hybrid Machine "
     "Learning System for Multi-Threat Probabilistic Forecasting and Budget-Constrained "
     "Intervention Recommendation in Nigerian National Parks”.")
doc.add_paragraph()
para("Signature……………………………      Date……………………………", align="left")
para("Mr. Emmanuel Adjei", align="left")
para("Faculty, Bachelor of Software Engineering,", align="left")
para("African Leadership University", align="left")

pagebreak()
centre_title("DEDICATION AND ACKNOWLEDGEMENT", size=12); doc.add_paragraph()
para("This work is dedicated to the rangers and managers of Nigeria’s national parks, "
     "who protect fragile ecosystems with limited resources, and to my family, whose "
     "support made this project possible.")
para("I am grateful to my supervisor, Mr. Emmanuel Adjei, for his guidance throughout "
     "the project, and to the open-data communities behind Open-Meteo, NASA POWER, "
     "Google Earth Engine, and NASA MODIS, whose freely available products made this "
     "work feasible.")

pagebreak()
centre_title("ABSTRACT", size=12); doc.add_paragraph()
para("African protected areas have lost, on average, 59% of their large-mammal "
     "populations, and only 1.71% of Nigeria’s protected land has ever had its "
     "management effectiveness evaluated. Park managers depend on reactive patrols and "
     "lack the systematic, labelled data that conventional supervised machine learning "
     "requires, so they cannot anticipate threats or plan interventions within tight "
     "budgets. This project designed, built, and deployed ConserveAI, a live "
     "decision-support system that produced daily 30-day probabilistic forecasts for "
     "three threats, fire, drought, and vegetation degradation, across six Nigerian "
     "national parks, and turned each forecast into a budget-constrained intervention "
     "plan. The system used only free satellite and climate data, a hybrid labelling "
     "strategy with semi-supervised learning to overcome label scarcity, and an "
     "integer-linear-programming recommender that allocated a manager’s budget across "
     "four zones per park. On a temporally held-out 2024 to 2025 test set of 4,206 "
     "park-days the production model reached an F2 of 0.95 for fire, 0.83 for drought, "
     "and 0.86 for vegetation, with ROC-AUC above 0.96 for all three, and it beat a "
     "persistence baseline on every threat. The recommender honoured budget and capacity "
     "in every test and solved in under 60 milliseconds. The system was deployed end to "
     "end and verified live. The results show that open data and interpretable methods "
     "can drive a usable, transparent decision-support tool for resource-constrained "
     "conservation, as a validated proof of concept rather than a fully field-tested "
     "product.")

pagebreak()
centre_title("TABLE OF CONTENTS", size=12)
para("(Right-click and choose “Update Field” in Word to populate this table.)",
     align="left", italic=True, size=10)
p = doc.add_paragraph(); _num_field(p, r'TOC \o "1-3" \h \z \u')

pagebreak()
centre_title("LIST OF FIGURES", size=12)
for t in ["Figure 1: Proposed model / ML pipeline diagram",
          "Figure 2: System architecture diagram",
          "Figure 3: Use case diagram",
          "Figure 4: Class diagram",
          "Figure 5: Entity-relationship diagram",
          "Figure 6: Sequence diagram",
          "Figure 7: National overview dashboard",
          "Figure 8: Park console with a generated recommendation",
          "Figure 9: The live REST API documentation",
          "Figure 10: Automated unit-test run",
          "Figure 11: Held-out model evaluation metrics",
          "Figure 12: Local-vs-cloud performance",
          "Figure 13: Confusion matrices on the held-out test set",
          "Figure 14: Vegetation risk over twelve months",
          "Figure 15: Recommender plan scaling with budget"]:
    para(t, align="left")

pagebreak()
centre_title("LIST OF TABLES", size=12)
for t in ["Table 1: Comparison of existing systems and this project",
          "Table 2: Study parks and ecosystems",
          "Table 3: Target variables and how each label was constructed",
          "Table 4: Recommender behaviour across budgets",
          "Table 5: Summary of testing strategies",
          "Table 6: Held-out model evaluation results",
          "Table 7: Semi-supervised variants and the persistence baseline",
          "Table 8: Supervised versus semi-supervised mean F2, by architecture",
          "Table 9: Single-modality versus fused feature sets",
          "Table 10: Per-park F2 with 95% bootstrap confidence intervals",
          "Table 11: Mean F2 by ecosystem"]:
    para(t, align="left")

pagebreak()
centre_title("LIST OF ACRONYMS AND ABBREVIATIONS", size=12)
table(["Abbreviation", "Meaning"],
      [("API", "Application Programming Interface"), ("F2", "F-beta score (beta = 2)"),
       ("GEE", "Google Earth Engine"), ("ILP", "Integer Linear Programming"),
       ("JWT", "JSON Web Token"), ("ML", "Machine Learning"),
       ("MODIS", "Moderate Resolution Imaging Spectroradiometer"),
       ("NDVI", "Normalized Difference Vegetation Index"),
       ("ROC-AUC", "Receiver Operating Characteristic Area Under Curve"),
       ("SAR", "Synthetic Aperture Radar"), ("SDLC", "Software Development Life Cycle")],
      "", style="Light List Accent 1")

footer_pagenum(doc.sections[0], fmt="lowerRoman", start=1)

body = doc.add_section(WD_SECTION.NEW_PAGE)
body.footer.is_linked_to_previous = False
footer_pagenum(body, fmt="decimal", start=1)

# ── CHAPTER ONE ──
h1("CHAPTER ONE: INTRODUCTION")
h2("1.1 Introduction and Background")
para("Africa has recorded some of the steepest wildlife declines documented globally. "
     "Large-mammal populations in African protected areas fell by an average of 59% "
     "between 1970 and 2005 (Craigie et al., 2010). These declines occurred despite "
     "formal protection, which indicates that legal status alone was insufficient where "
     "budgets and monitoring were inadequate (Lindsey et al., 2017). Nigeria sits within "
     "this region: it contains over 30 protected areas covering 99,292 km², yet only "
     "1.71% of that land had undergone a management effectiveness evaluation (UNEP-WCMC "
     "& IUCN, 2024). Climate change compounded the pressure, with rising temperatures, "
     "more frequent droughts in the north, and unpredictable wet seasons (Haider, 2019; "
     "Shiru et al., 2020). Traditional conservation in Nigeria relied on reactive ranger "
     "patrols and post-incident reporting, with thin coverage and inconsistent records.")
h2("1.2 Problem Statement")
para("The real-world problem was that Nigerian park managers could not anticipate "
     "environmental threats or plan interventions within tight budgets, so damage was "
     "addressed only after it occurred. The research gap was narrower and is what this "
     "project targeted directly: Nigerian protected areas lack the systematic, labelled "
     "monitoring data that conventional supervised machine learning requires, holding "
     "fewer than 300 species observations per park across several years (Siddig, 2019). "
     "The two closest software systems each had a specific gap. SMART only recorded "
     "threats after rangers walked an area and offered no forecasting, while PAWS "
     "forecast poaching but needed extensive incident histories these parks did not "
     "maintain and ignored fire, drought, and vegetation. A further gap existed at the "
     "decision layer: even where predictions existed, no published system combined "
     "multi-threat forecasts with an interactive, budget-constrained recommendation that "
     "a manager could adjust and interrogate. The proposed machine-learning response was "
     "to construct threat labels from free environmental data, train a classifier suited "
     "to scarce labels, and feed calibrated probabilities to a transparent optimiser.")
h2("1.3 Project’s Main Objective")
para("To develop a live probabilistic forecasting and decision-support system that "
     "produced daily 30-day threat-risk probabilities (fire, drought, and vegetation "
     "degradation) for six Nigerian national parks and recommended budget-constrained "
     "interventions per park, using free environmental data and machine-learning methods "
     "suited to data-scarce conservation contexts.")
h3("1.3.1 Specific Objectives")
numbered("To assemble a daily, multi-source environmental dataset for the six study "
         "parks (2020 to 2025) and construct three binary 30-day threat labels per "
         "park-date.")
numbered("To build the software solution: a data pipeline; a classifier comparing "
         "Random Forest, XGBoost, LSTM, and Transformer architectures in supervised and "
         "semi-supervised variants; an integer-linear-programming recommender; a React "
         "and FastAPI web application; and a daily scheduled pipeline deployed to "
         "free-tier cloud infrastructure.")
numbered("To evaluate the solution with metrics suited to imbalanced probabilistic "
         "forecasting, namely precision, recall, F2, ROC-AUC, Brier score, lead time, "
         "and a persistence baseline, with per-park bootstrap confidence intervals.")
h2("1.4 Research Questions")
numbered("How does multi-modal fusion of climate, satellite, and fire data compare with "
         "single-modality approaches for 30-day threat forecasting in Nigerian parks?")
numbered("Which of four candidate architectures achieved the best probabilistic "
         "forecasting performance, and did the ranking differ by threat or ecosystem?")
numbered("Did semi-supervised learning improve forecasting for threats with sparse "
         "labels, and by how much?")
numbered("How well did model outputs correlate with independent quantitative ground "
         "truth, and what lead time was achievable at fixed probability thresholds?")
numbered("How sensitive were the recommendations to assumptions about intervention cost "
         "and effectiveness?")
h2("1.5 Project Scope")
para("The scope was bounded deliberately to keep the project measurable and to prevent "
     "overclaiming:")
bullet("Content scope: three environmental threats (fire, drought, vegetation "
       "degradation) and one decision task (budget-constrained intervention planning).")
bullet("Geographical scope: six Nigerian national parks (Yankari, Cross River, "
       "Gashaka-Gumti, Kainji Lake, Chad Basin, and Old Oyo), spanning savanna, "
       "rainforest, wetland, and Sahel ecosystems, covering roughly 23,000 km².")
bullet("Data scope: only freely accessible climate, satellite, and fire-detection APIs, "
       "for January 2020 to December 2025.")
bullet("Technical scope: a 30-day forecast horizon computed daily, and zone-level "
       "recommendation at four zones per park.")
bullet("Out of scope: field testing with park staff, national-level budget allocation, "
       "and threats not observable from free remote data such as poaching and grazing.")
h2("1.6 Significance and Justification")
para("The system addressed a gap that neither SMART nor PAWS covered: it produced daily "
     "probabilistic forecasts for three environmental threats and recommended "
     "budget-constrained interventions through transparent optimisation. It relied on "
     "data that was already free to collect, used interpretable methods a manager could "
     "audit, and ran live without manual intervention. The methodology is replicable: "
     "other African countries facing similar data scarcity can adapt the hybrid-labelling "
     "approach, and the full source code was released openly at "
     "https://github.com/fadhuweb/ConserveAI to support reproducibility (Hutson, 2018).")
h2("1.7 Research Budget")
para("The system was built entirely on free APIs and open-source software. The only "
     "paid items were optional GPU access for training deep-learning variants (about USD "
     "30) and an optional domain name (about USD 12), giving a total under USD 45. "
     "Deployment used free-tier cloud infrastructure.")
h2("1.8 Research Timeline")
para("The project ran over twelve weeks in an iterative schedule: a single-park pipeline "
     "(Weeks 1 to 2), the six-park dataset (Weeks 3 to 4), supervised baselines (Weeks 5 "
     "to 6), semi-supervised variants (Week 7), the ILP recommender (Week 8), the web "
     "application (Weeks 9 to 10), live-pipeline testing (Week 11), and final writing "
     "(Week 12).")

# ── CHAPTER TWO ──
pagebreak()
h1("CHAPTER TWO: LITERATURE REVIEW")
h2("2.1 Introduction")
para("The literature was reviewed thematically rather than paper by paper, and each "
     "theme was used to justify a specific design decision in Chapter Three. Around 90 "
     "peer-reviewed papers published between 2016 and 2026 were screened across five "
     "themes: existing conservation systems, machine-learning methods for scarce labels, "
     "remote-sensing signals for fire and drought, conservation budget optimisation, and "
     "evaluation and ethics.")
h2("2.2 Historical Background of the Research Topic")
para("Protected areas are the primary instrument for in-situ biodiversity conservation, "
     "covering roughly 15% of the global land surface (Cazalis et al., 2020), and "
     "matched analyses show they reduce deforestation and support faster woody growth "
     "inside their boundaries (McNicol et al., 2023). Machine learning has been applied "
     "widely to conservation, but a review of over 300 applications found only 12% "
     "focused on predictive modelling and 73% originated in North America or Europe "
     "(Tuia et al., 2022), leaving predictive threat forecasting in African, data-scarce "
     "settings under-served.")
h2("2.3 Overview of Existing Systems")
para("SMART is the most widely deployed conservation software, used in over 1,000 "
     "protected areas, but it is retrospective: its outputs reflect only what rangers "
     "have walked through, and an evaluation in Zimbabwe found adoption limited by "
     "capacity and behavioural constraints (Kasusse et al., 2021). PAWS uses game theory "
     "and machine learning to plan anti-poaching patrols and reported a 30% increase in "
     "snare detection in field trials (Xu, Gholami, et al., 2020), but it requires "
     "extensive incident histories and addresses poaching only. Neither integrates "
     "multi-modal environmental data nor produces calibrated probability forecasts that "
     "a budget-constrained optimiser could consume.")
h2("2.4 Review of Related Work")
para("Two themes shaped the model design. First, on scarce labels, semi-supervised "
     "learning offered a route around label scarcity: FixMatch reached 78.3% accuracy on "
     "ImageNet with only 10% of labels (Sohn et al., 2020), and surveys report that "
     "semi-supervised methods reach 85 to 95% of fully supervised performance when "
     "unlabelled data is abundant (Van Engelen & Hoos, 2020). Second, on model family, "
     "several studies use tree-based models for tabular risk prediction because they "
     "outperform deep learning when events are scarce (Brys et al., 2025), multi-temporal "
     "remote-sensing features beat single-date observations for fire and drought "
     "(Naderpour et al., 2021), and NDVI-rainfall relationships support remote drought "
     "monitoring in Nigeria (Mohammed & Adamu, 2021). A recurring weakness in this "
     "literature is the reliance on accuracy even when data is imbalanced; this project "
     "therefore reported F2 and minority-class recall instead. On the decision side, "
     "integer linear programming has been shown to be cheaper and far faster than "
     "heuristic conservation planners while remaining interpretable enough for "
     "interactive use (Schuster et al., 2020; Beyer et al., 2016), and interpretability "
     "tools such as SHAP underpin responsible deployment (Lundberg & Lee, 2017).")
h3("2.4.1 Summary of Reviewed Literature")
para("The literature established that predictive, multi-threat conservation modelling in "
     "Africa was under-developed; that semi-supervised learning was a proven remedy for "
     "sparse labels; that tree-based models were strong when events were rare; that NDVI "
     "and rainfall were reliable remote signals; and that integer linear programming was "
     "the appropriate, transparent method for interactive budget-constrained planning.")
h2("2.5 Strengths and Weaknesses of the Existing Systems")
para("Table 1 compares the two closest systems with this project across the dimensions "
     "that matter for a data-scarce, multi-threat setting. SMART’s strengths were its "
     "wide deployment and mobile patrol collection, but it was retrospective and "
     "integrated no climate, satellite, or fire data. PAWS offered predictive, "
     "game-theoretic patrol routing but needed incident histories these parks lacked and "
     "addressed poaching alone. Neither produced probabilistic multi-threat forecasts "
     "nor coupled them to budget-constrained recommendation.")
table(["Dimension", "SMART", "PAWS", "This project (ConserveAI)"],
      [("Core approach", "Ranger patrol logging", "Game-theoretic patrol planning",
        "ML forecast + ILP recommender"),
       ("Threats covered", "Whatever rangers observe", "Poaching only",
        "Fire, drought, vegetation"),
       ("Predictive?", "No (retrospective)", "Yes (needs incident history)",
        "Yes (30-day forecast)"),
       ("Data requirement", "Ranger patrols", "Extensive incident records",
        "Free satellite and climate data"),
       ("Budget optimisation", "No", "Patrol routing, not budget",
        "Yes (budget-constrained, zone-level)"),
       ("Transparency", "Records only", "Model-driven", "Interpretable + explained")],
      "Table 1: Comparison of existing systems and this project.")
h2("2.6 General Comments")
para("The gap was both methodological and operational: semi-supervised multi-threat "
     "probabilistic forecasting was under-applied in African conservation, ILP-based "
     "budget allocation had not been integrated with such forecasts in the published "
     "literature, and no existing system served Nigerian park managers with predictive, "
     "transparent, budget-aware support. This project set out to close that gap.")

# ── CHAPTER THREE ──
pagebreak()
h1("CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN")
h2("3.1 Introduction")
para("This chapter presents the analysis and design of the live multi-threat "
     "forecasting and recommendation platform in enough detail to make it reproducible: "
     "the data and target, how raw data became model input, the split and baseline, the "
     "models and metrics, the architecture and diagrams, the tools, and the ethical "
     "considerations.")
h2("3.2 Research Design (and SDLC Model)")
para("The project was primarily applied design science: the deliverable was a working "
     "system, and the research questions were answered by measuring that system’s "
     "behaviour. An iterative, agile-inspired SDLC was used, in which each two-week "
     "iteration produced a deployable artefact, which protected the timeline from "
     "late-stage integration failures.")
h3("3.2.1 Dataset and Feature Engineering")
para("The dataset combined four free public sources: Open-Meteo and NASA POWER for daily "
     "climate; Google Earth Engine for MODIS NDVI (vegetation greenness); and MODIS "
     "active-fire products for fire detections. Raw observations were converted into "
     "model input through feature engineering: for each park-date, twenty features were "
     "computed, including multi-scale rainfall accumulation and deficit (7, 30, and "
     "90-day windows), temperature statistics, five NDVI features (level, deviation from "
     "a 90-day mean, and trend), fire-history counts, and seasonal and contextual "
     "encodings. Missing satellite values, common in the rainy season, were carried "
     "forward within the sixteen-day cadence of the MODIS composite. Table 2 summarises "
     "the study parks.")
table(["Park", "Ecosystem", "Area (km²)"],
      [("Yankari", "Savanna", "2,244"), ("Cross River", "Rainforest", "4,000"),
       ("Gashaka-Gumti", "Mixed", "6,731"), ("Kainji Lake", "Savanna", "5,341"),
       ("Chad Basin", "Sahel", "2,258"), ("Old Oyo", "Savanna", "2,512")],
      "Table 2: Study parks, ecosystems, and areas.")
h3("3.2.2 Target Variable")
para("The model predicted three independent binary targets per park-date, each asking "
     "whether a threat would occur within the next 30 days (a value of 1) or not (0). "
     "Because the targets described the future, they were never available at prediction "
     "time and were built only from data strictly after the feature date, which "
     "prevented temporal leakage across the split. The three labels were constructed as "
     "shown in Table 3. One honest caveat applies: the drought and vegetation labels were "
     "derived from the same climate and NDVI signals that also served as features, so "
     "there is a label-leakage risk, and those two scores should be read as internal "
     "consistency checks rather than fully independent validation. The fire label, by "
     "contrast, came from an independent detection product.")
table(["Target", "Positive when, in the next 30 days...", "Label source"],
      [("fire_within_30d", "a MODIS active-fire detection occurs in the park",
        "Independent (MODIS/FIRMS)"),
       ("drought_within_30d", "30-day rainfall falls below 40% of the month’s "
        "climatological average, in the rainy season", "Climate-derived (leakage risk)"),
       ("vegetation_within_30d", "NDVI stays more than 0.10 below its 90-day mean on "
        "at least 5 of any 14 days", "NDVI-derived (leakage risk)")],
      "Table 3: Target variables and how each label was constructed.")
h2("3.3 Functional and Non-Functional Requirements")
para("Functional requirements: role-based login; a national risk overview for "
     "administrators; per-park 30-day forecasts with driver explanations; a "
     "budget-constrained, zone-level intervention recommender; a daily scheduled job "
     "that refreshed forecasts; and park-scoped access control. Non-functional "
     "requirements: sub-second warm response times; interactive (sub-second) "
     "optimisation; unattended operation on free-tier infrastructure; and transparent, "
     "auditable recommendations.")
h2("3.4 Model Design")
h3("3.4.1 Model Choice, Baseline, and Metrics")
para("The data was tabular and time-ordered, with rare positive events for drought, so "
     "the model family was chosen to match that data type: tree-based classifiers, which "
     "the literature shows outperform deep learning on scarce tabular events, were "
     "compared against LSTM and Transformer sequence models. Every model was measured "
     "against a persistence baseline, the naive forecast that the next 30 days would "
     "resemble the last 30, which answered the question compared to what. Because the "
     "targets were imbalanced, accuracy alone would have been misleading, so evaluation "
     "reported precision, recall, F2 (which weights recall over precision, appropriate "
     "when a missed threat is costlier than a false alarm), ROC-AUC, the Brier score, "
     "lead time, and a confusion matrix, with bootstrap confidence intervals.")
h3("3.4.2 Proposed Model Diagram")
para("Backward-looking features (rainfall, temperature, NDVI, and fire history) were "
     "fed to a calibrated classifier that produced three independent 30-day "
     "probabilities per park-date, which the ILP recommender then consumed (Figure 1).")
figure("ml_pipeline.png", "Figure 1: Proposed model / ML pipeline diagram.", 5.6, base=RFIG)
h2("3.5 System Architecture")
para("The system was structured as five horizontal layers: a React frontend; a FastAPI "
     "API layer enforcing park-scoped JWT authentication; a business-logic layer holding "
     "the forecast model, calibrator, PuLP optimiser, and SHAP explainer; a PostgreSQL "
     "data layer; and external free data sources feeding a daily scheduled job (Figure 2).")
placeholder("System architecture diagram",
            "Paste this from your proposal (system architecture figure).",
            "Figure 2: System architecture diagram.")
h2("3.6 UML and Other Diagrams")
para("Four UML diagrams specified the system at three levels of abstraction. The "
     "use-case diagram (Figure 3) captured the actors (Park Manager, National Admin, and "
     "the Scheduler) and their interactions; the class diagram (Figure 4) captured the "
     "domain model (User, Park, Zone, Forecast, Recommendation, Allocation, Intervention, "
     "ForecastModel, Calibrator); the entity-relationship diagram (Figure 5) captured the "
     "PostgreSQL schema; and the sequence diagram (Figure 6) captured the forecast-viewing "
     "and recommendation workflow.")
placeholder("Use case diagram", "Paste this from your proposal.", "Figure 3: Use case diagram.")
placeholder("Class diagram", "Paste this from your proposal.", "Figure 4: Class diagram.")
placeholder("Entity-relationship diagram (database schema)", "Paste this from your proposal.",
            "Figure 5: Entity-relationship diagram.")
placeholder("Sequence diagram", "Paste this from your proposal.", "Figure 6: Sequence diagram.")
h2("3.7 Development Tools")
para("Python 3.12 (data pipeline, models, backend); scikit-learn, XGBoost, and PyTorch "
     "(model architectures); PuLP (integer linear programming); SHAP (interpretability); "
     "FastAPI and SQLAlchemy (backend); PostgreSQL, hosted on Neon (database); "
     "APScheduler and GitHub Actions (scheduling); React with Ant Design, Leaflet, and "
     "Recharts (frontend); Fly.io and Vercel (deployment); and Git and GitHub (version "
     "control).")
h2("3.8 Ethical Considerations")
para("Because the system stored user accounts and produced risk scores, the design "
     "addressed the data it actually handled. Privacy and consent: the only personal "
     "data stored was manager account information (username, a bcrypt-hashed password, "
     "and an email), and no individual or community data was collected. Sensitive data "
     "and misuse: the system forecast environmental threats at the park and zone level, "
     "not the locations of animals or people, which limited the risk that its maps could "
     "be misused to target wildlife, unlike poaching-prediction systems. Bias and "
     "fairness: performance was reported per park and per ecosystem (Section 5.2) so "
     "that the model could not silently under-serve one park type, and that breakdown did "
     "reveal materially weaker accuracy in the rainforest. Human-in-the-loop and safety: "
     "recommendations were framed as decision support, the reasoning behind each was "
     "shown so a manager could audit rather than defer to it, and the system carried a "
     "clear proof-of-concept disclaimer against sole reliance. Provenance: all data "
     "sources were free and openly licensed, and were attributed.")

# ── CHAPTER FOUR ──
pagebreak()
h1("CHAPTER 4: SYSTEM IMPLEMENTATION AND TESTING")
h2("4.1 Implementation and Coding")
h3("4.1.1 Introduction")
para("This section describes how the designed system was implemented and how it was "
     "tested, focusing on the concrete tools, the main modules, and the verification "
     "evidence rather than restating the project’s purpose.")
h3("4.1.2 Description of Implementation Tools and Technology")
para("The backend was implemented in FastAPI with SQLAlchemy over a Neon-hosted "
     "PostgreSQL database, and exposed a documented REST API. The machine-learning "
     "pipeline used scikit-learn; the production model was a self-training Random "
     "Forest, with XGBoost, LSTM, and Transformer variants compared during model "
     "selection. The recommender was implemented with PuLP. The frontend was a React "
     "single-page application using Ant Design, Leaflet for maps, and Recharts for the "
     "forecast charts. A daily job, scheduled through GitHub Actions in production, "
     "pulled current data, ran inference, and wrote forecasts to the database.")
h3("4.1.3 Source Code of the Main Modules")
para("Four modules carried the core logic. Listing 1 shows the feature engineering that "
     "turned raw daily observations into the twenty model inputs, using backward-looking "
     "rolling windows only, so no future information could enter a feature.")
code('''
df["rain_7d"]  = precip.rolling(7,  min_periods=4).sum()
df["rain_30d"] = precip.rolling(30, min_periods=15).sum()
df["rain_deficit_30d"] = df["rain_30d"] - expected_30d
df["hot_days_30d"] = (temp_max > 35).astype(float).rolling(30, min_periods=15).sum()
df["ndvi_90d_avg"] = ndvi_filled.rolling(90, min_periods=30).mean()
df["fire_30d"] = fire.rolling(30, min_periods=15).sum()
df["days_since_fire"] = days_since.fillna(365).clip(upper=365)
df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
''', "Listing 1: Feature engineering (src/data_pipeline/feature_engineering.py).")
para("Listing 2 shows how the vegetation label was constructed. NDVI is carried forward "
     "across the sixteen-day MODIS composite, compared with its own 90-day mean, and a "
     "degradation window is declared when enough days in a fortnight fall below that mean; "
     "the forward-looking helper then asks whether such a window occurs in the next 30 days.")
code('''
ndvi = df["ndvi_s2"].ffill(limit=16)        # MOD13Q1 is a 16-day composite
ndvi_90d_avg = ndvi.rolling(NDVI_WINDOW, min_periods=NDVI_WINDOW // 3).mean()
below = (ndvi - ndvi_90d_avg < -NDVI_THRESHOLD).astype(float)
degraded_window = (below.fillna(0)
                   .rolling(VEG_WINDOW, min_periods=VEG_WINDOW // 2)
                   .sum() >= VEG_DAYS_IN_WINDOW).astype(float)
df["vegetation_within_30d"] = _forward_label(degraded_window)
''', "Listing 2: Vegetation label construction (src/data_pipeline/label_drought_vegetation.py).")
para("Listing 3 is the self-training loop that produced the production model. On each "
     "iteration the current model scores the unlabelled pool, rows whose confidence "
     "exceeds the threshold on all three threats are pseudo-labelled and moved into the "
     "labelled set, and the forest is refitted.")
code('''
for it in range(1, N_ITER + 1):
    probs_ul = get_probs(model, X_ul)
    conf     = np.maximum(probs_ul, 1 - probs_ul)     # (N, 3)
    mask     = np.all(conf > CONF_THRESHOLD, axis=1)  # all-threat gate
    if mask.sum() == 0:
        break
    pseudo_Y = (probs_ul[mask] > 0.5).astype(float)
    X_lab = np.vstack([X_lab, X_ul[mask]]); Y_lab = np.vstack([Y_lab, pseudo_Y])
    X_ul  = X_ul[~mask]
    model = fit_rf(X_lab, Y_lab, params)
''', "Listing 3: Semi-supervised self-training loop (src/models/semi_supervised/train_rf_self.py).")
para("Listing 4 is the recommender itself. One integer variable counts the units of each "
     "intervention; the objective maximises the probability-weighted effectiveness of the "
     "plan; and the constraints enforce the manager’s budget and the per-intervention "
     "capacity, which is why the plans in Table 4 never exceed the budget.")
code('''
x = {inv.id: pulp.LpVariable(f"x_{inv.id}", lowBound=0, cat="Integer")
     for inv in catalog}
score = {inv.id: sum(probs.get(t, 0.0) * inv.effectiveness.get(t, 0.0)
                     for t in THREAT_KEYS) for inv in catalog}

prob += pulp.lpSum(score[inv.id] * x[inv.id] for inv in catalog)          # objective
prob += pulp.lpSum(inv.cost * x[inv.id] for inv in catalog) <= constraints.budget
for inv in catalog:
    prob += x[inv.id] <= inv.max_units, f"cap_{inv.id}"                   # capacity
''', "Listing 4: ILP objective and constraints (src/optimizer/ilp_recommender.py).")

h2("4.2 Graphical View of the Project")
h3("4.2.1 Screenshots with Descriptions")
para("A national administrator could view a Nigeria-wide risk overview, with each park "
     "shaded by risk and a switchable threat lens (Figure 7).")
figure("app_national_overview.png", "Figure 7: National overview, per-park risk and threat lens.")
para("A park manager could open a park, read its 30-day forecast and drivers, set a "
     "budget, and generate a budget-constrained, zone-level intervention plan that "
     "explained why each intervention was chosen (Figure 8).")
figure("app_recommendation.png", "Figure 8: Park console with a generated recommendation and zone plan.")
para("The interactive REST service was also browsable as Swagger documentation (Figure 9).")
figure("swagger.png", "Figure 9: The live REST API documentation.")
h2("4.3 Testing")
h3("4.3.1 Introduction")
para("The system was verified through several complementary testing strategies: "
     "automated unit tests, model evaluation on held-out data, integration and API tests "
     "against the live deployment, end-to-end browser testing, and a performance "
     "comparison across environments.")
h3("4.3.2 Objective of Testing")
para("The objective was to confirm that each component behaved as specified under "
     "different inputs and edge cases, that the model generalised to unseen data, and "
     "that the deployed system was correct and performant.")
h3("4.3.3 Unit Testing Outputs")
para("Nineteen automated unit tests covered the deterministic components: the ILP "
     "optimiser (budget, capacity, type toggles, urgency floors, and the recommendation "
     "rationale) and authentication (bcrypt hashing, the password policy, and JWT access "
     "and reset tokens). All nineteen passed (Figure 10).")
figure("pytest_pass.png", "Figure 10: The automated unit-test suite passing.", 6.2)
h3("4.3.4 Validation Testing Outputs")
para("The model was validated on a temporally separate 2024 to 2025 test set of 4,206 "
     "park-day rows it never saw during training. The results are reported and "
     "interpreted in Chapter Five (Figure 11, Table 6).")
figure("model_metrics.png", "Figure 11: Held-out model evaluation metrics.", 6.0)
h3("4.3.5 Integration Testing Outputs")
para("Each endpoint was exercised against the live deployment. Health and database "
     "checks returned ok; a valid login returned 200 and set a secure cookie while an "
     "invalid login returned 401; protected routes returned 401 without a session and "
     "200 with one; the daily-job endpoint returned 403 without its token and 200 with "
     "it, processing all six parks.")
h3("4.3.6 Functional and System Testing Results")
para("The full user journey was tested in the browser on the deployed site: logging in, "
     "viewing the national overview, opening a park, reading the forecast and drivers, "
     "setting a budget, and generating a recommendation that appeared on the zone map. "
     "The recommender was also exercised with different data values, the same park at "
     "several budgets, which confirmed that the plan scaled with the budget and never "
     "exceeded it (Table 4).")
table(["Budget", "Total units", "Total cost", "Solve time"],
      [("₦8,000,000", "6", "₦7,680,000", "41 ms"), ("₦16,000,000", "14", "₦15,840,000", "37 ms"),
       ("₦32,000,000", "19", "₦31,840,000", "38 ms"), ("₦80,000,000", "44", "₦80,000,000", "35 ms")],
      "Table 4: Recommender behaviour across budgets (live system; naira at ₦1,600 per US dollar).")
para("Performance was measured across two environments, a local Windows machine and the "
     "Fly.io cloud container. The cloud, co-located with the database, was three to five "
     "times faster on every call (Figure 12).")
figure("performance.png", "Figure 12: Local-vs-cloud API performance.", 6.0)
h3("4.3.7 Acceptance Testing Report")
para("Against the proposal’s objectives, the system was accepted as meeting its "
     "functional requirements: it forecast three threats for six parks daily, "
     "recommended budget-constrained zone-level interventions, enforced role-based "
     "access, and ran live. Table 5 summarises the strategies and outcomes.")
table(["Strategy", "Outcome"],
      [("Unit tests (pytest)", "19 / 19 pass"),
       ("Model evaluation (held-out)", "Fire F2 0.95, Drought 0.83, Vegetation 0.86"),
       ("Integration / API", "All endpoints behave as specified"),
       ("End-to-end (browser)", "Full journey works on the deployed site"),
       ("Different data values", "Recommender scales with budget; per-park forecasts differ"),
       ("Performance (hardware)", "Cloud 3 to 5x faster than local; sub-second warm responses")],
      "Table 5: Summary of testing strategies and outcomes.", style="Light List Accent 1")

# ── CHAPTER FIVE ──
pagebreak()
h1("CHAPTER 5: DESCRIPTION OF THE RESULTS")
para("This chapter presents the results, interprets what the numbers meant for the "
     "problem, and connects them to the research questions and objectives.")
h2("5.1 Forecasting Results and Baseline Comparison")
para("On the held-out 2024 to 2025 test set, the production model (a self-training "
     "Random Forest) scored an F2 of 0.95 for fire, 0.83 for drought, and 0.86 for "
     "vegetation, with ROC-AUC above 0.96 on all three (Table 6). Crucially, it beat the "
     "persistence baseline on every threat, and by a wide margin on drought (F2 0.83 "
     "versus 0.35), so the model learned real structure rather than repeating recent "
     "history. This answered research question two: the tree-based model was the "
     "strongest of the four architectures compared, consistent with the finding that "
     "tree-based models outperform deep learning when events are scarce, and research "
     "question four: at the operating threshold the model gave a mean lead time of three "
     "to four days.")
table(["Threat", "Prevalence", "Precision", "Recall", "F2", "ROC-AUC", "Baseline F2", "Lead (days)"],
      [("Fire", "54%", "0.88", "0.96", "0.95", "0.98", "0.78", "4.1"),
       ("Drought", "17%", "0.70", "0.86", "0.83", "0.97", "0.35", "2.8"),
       ("Vegetation", "30%", "0.99", "0.83", "0.86", "0.98", "0.71", "3.4")],
      "Table 6: Held-out model evaluation results (n = 4,206).")
para("Table 7 sets the selected model against the persistence baseline and the three "
     "other semi-supervised variants trained on the same data; the supervised variants "
     "are omitted here for clarity. Every semi-supervised variant beat the baseline on "
     "mean F2, but the two tree-based models (Random Forest and XGBoost) clearly "
     "outperformed the two deep sequence models (LSTM and Transformer, both trained with "
     "FixMatch), which is consistent with the reviewed finding that tree-based models win "
     "when positive events are scarce. The deep models were the weakest of the group: "
     "the LSTM and the Transformer both fell below the persistence baseline on vegetation "
     "(0.57 against 0.71), meaning they failed to learn the vegetation signal from the "
     "limited labels. The self-training Random Forest achieved the highest mean F2 (0.88) "
     "and won on fire and vegetation; XGBoost matched it on drought (0.829 against 0.825 "
     "before rounding) but collapsed on vegetation. The Random Forest was therefore "
     "selected for the best overall mean F2 and for its CPU-only tabular inference, which "
     "needs no sequence buffer at serving time. The tree-based family was therefore the "
     "right choice for this data.")
table(["Model", "Fire F2", "Drought F2", "Vegetation F2", "Mean F2"],
      [("Random Forest, self-training (selected)", "0.95", "0.83", "0.86", "0.88"),
       ("XGBoost, self-training", "0.94", "0.83", "0.63", "0.80"),
       ("LSTM, FixMatch", "0.92", "0.71", "0.57", "0.74"),
       ("Transformer, FixMatch", "0.94", "0.61", "0.57", "0.71"),
       ("Persistence baseline", "0.78", "0.35", "0.71", "0.61")],
      "Table 7: Semi-supervised variants and the persistence baseline (F2 by threat and mean).")
para("Whether semi-supervised learning helped at all is a separate question, and the "
     "honest answer is that it depended on the architecture (Table 8). Self-training "
     "raised the Random Forest’s mean F2 by 0.020 (0.857 to 0.877) and FixMatch raised "
     "the Transformer’s by 0.018, but semi-supervision reduced mean F2 for XGBoost "
     "(by 0.029) and for the LSTM (by 0.041). The gain was uneven even inside the "
     "selected model: self-training lifted vegetation F2 from 0.744 to 0.861 but lowered "
     "drought F2 from 0.882 to 0.825, so the Random Forest was chosen on mean F2 even "
     "though a purely supervised Random Forest would have forecast drought better. This "
     "is the specific answer to research question three: semi-supervised learning helped, "
     "but only for two of the four architectures and by roughly 0.02 mean F2, not "
     "uniformly.")
table(["Architecture", "Supervised mean F2", "Semi-supervised mean F2", "Change"],
      [("Random Forest (selected)", "0.857", "0.877", "+0.020"),
       ("XGBoost", "0.827", "0.798", "-0.029"),
       ("LSTM", "0.777", "0.736", "-0.041"),
       ("Transformer", "0.689", "0.707", "+0.018")],
      "Table 8: Supervised versus semi-supervised mean F2, by architecture.")
para("Research question one asked whether fusing climate, satellite, and fire data beats "
     "using a single modality. This was tested directly by an ablation: four Random "
     "Forests were trained identically on the same split and calibration, varying only "
     "the feature modality available to them, with the seasonal and park context retained "
     "in every run so that the comparison isolates the sensing modality (Table 9). The "
     "result is more interesting than a simple win. Fusion gave the best mean F2 (0.872), "
     "but each threat was best predicted by its own natural modality: fire history alone "
     "was best on fire (0.948), climate alone was best on drought (0.868), and satellite "
     "NDVI alone was best on vegetation (0.887), each slightly beating the fused model on "
     "that threat. The honest reading is that fusion buys breadth rather than per-threat "
     "optimality: one fused model handles all three threats well, whereas a "
     "single-modality model is strong on its own threat and weak elsewhere, most visibly "
     "the fire-history model collapsing to 0.594 on drought. Because the system must serve "
     "all three threats from one deployed model, the fused feature set was the right "
     "choice. Note that these ablation figures come from supervised Random Forests trained "
     "for this comparison, so they are internally comparable but sit slightly below the "
     "production self-training model reported in Table 6.")
table(["Feature set", "Features", "Fire F2", "Drought F2", "Vegetation F2", "Mean F2"],
      [("Climate only", "12", "0.917", "0.868", "0.781", "0.856"),
       ("Satellite (NDVI) only", "10", "0.943", "0.634", "0.887", "0.821"),
       ("Fire history only", "8", "0.948", "0.594", "0.850", "0.797"),
       ("Fused (all modalities)", "20", "0.935", "0.831", "0.850", "0.872")],
      "Table 9: Single-modality versus fused feature sets (held-out test set).")

h2("5.2 Performance by Park and Ecosystem")
para("Reporting only national averages can hide a model that serves one park type poorly, "
     "so performance was broken down per park with bootstrap confidence intervals "
     "(Table 10) and then aggregated by ecosystem (Table 11). Each park contributed 701 "
     "evaluated park-days. The spread is wide and it is not noise: Chad Basin, the arid "
     "Sahel park, was forecast best on every threat (fire 0.99, drought 0.93, vegetation "
     "0.95), while Cross River, the rainforest park, was the weakest overall (drought 0.71, "
     "vegetation 0.68), and Old Oyo’s drought forecast was the single weakest cell in the "
     "study at 0.53. The pattern is ecologically coherent rather than arbitrary. Arid and "
     "strongly seasonal parks give the model sharp, repeating signals to learn, whereas the "
     "rainforest is wet year-round, its NDVI is the most affected by cloud, and its threat "
     "events are rarer and less cleanly separated, so the same model has less to work with.")
table(["Park", "Ecosystem", "Fire F2 [95% CI]", "Drought F2 [95% CI]", "Vegetation F2 [95% CI]"],
      [("Chad Basin", "Sahel", "0.99 [0.98-0.99]", "0.93 [0.91-0.95]", "0.95 [0.92-0.98]"),
       ("Cross River", "Rainforest", "0.91 [0.89-0.94]", "0.71 [0.60-0.81]", "0.68 [0.62-0.75]"),
       ("Gashaka-Gumti", "Mixed", "0.98 [0.97-0.99]", "0.78 [0.71-0.84]", "0.87 [0.83-0.91]"),
       ("Kainji Lake", "Savanna", "0.94 [0.91-0.95]", "0.95 [0.93-0.97]", "0.94 [0.91-0.97]"),
       ("Old Oyo", "Savanna", "0.95 [0.93-0.96]", "0.53 [0.45-0.61]", "0.81 [0.76-0.85]"),
       ("Yankari", "Savanna", "0.88 [0.85-0.90]", "0.91 [0.88-0.93]", "0.89 [0.85-0.93]")],
      "Table 10: Per-park F2 with 95% bootstrap confidence intervals (701 park-days each).")
para("Aggregated by ecosystem (Table 11), mean F2 fell from 0.96 in the Sahel to 0.77 in "
     "the rainforest. This answers the second half of research question two: the ranking of "
     "threats did shift by ecosystem, and more importantly the model’s reliability itself "
     "varies by ecosystem. It also supplies the evidence behind the fairness commitment "
     "made in Section 3.8. Read as a fairness result it is a caution rather than a "
     "reassurance: the system is least dependable exactly where it is applied to rainforest, "
     "so a Cross River manager should treat its drought and vegetation output with more "
     "scepticism than a Chad Basin manager would need to.")
table(["Ecosystem", "Parks", "Fire F2", "Drought F2", "Vegetation F2", "Mean F2"],
      [("Sahel", "1", "0.99", "0.93", "0.95", "0.96"),
       ("Mixed", "1", "0.98", "0.78", "0.87", "0.88"),
       ("Savanna", "3", "0.92", "0.80", "0.88", "0.87"),
       ("Rainforest", "1", "0.91", "0.71", "0.68", "0.77")],
      "Table 11: Mean F2 by ecosystem (parks grouped from Table 10).")
h2("5.3 Which Threat Was Hardest: Reading the Confusion Matrices")
para("The confusion matrices (Figure 13) explained what the aggregate scores meant. Fire "
     "was caught reliably: the model recovered 2,166 of 2,251 fire windows (recall 96%) "
     "at the cost of 282 false alarms, an acceptable trade because a missed fire is "
     "costlier than a false alarm. Drought was the hardest threat: its precision was "
     "0.70, the lowest of the three, meaning 262 of its positive predictions were false "
     "alarms, which is why its F2 was lowest despite a strong ROC-AUC; the rarity of "
     "drought (17% prevalence) made precision hard to hold. Vegetation showed the "
     "opposite profile after the fix described below: precision 0.99 with only 8 false "
     "alarms, but 207 missed windows (recall 83%), so the model was conservative and "
     "trustworthy when it did raise a vegetation flag.")
figure("confusion_matrices.png",
       "Figure 13: Confusion matrices on the held-out test set (production model).", 6.4, base=RFIG)
h2("5.4 The Vegetation Result: Diagnosing and Fixing a Degenerate Output")
para("A live observation exposed a genuine defect and its fix, which is itself a key "
     "result. An earlier version of the model collapsed to a near-constant vegetation "
     "output, with five of six parks returning an identical value, because its optical "
     "NDVI was blocked by rainy-season cloud and because training used one sensor while "
     "serving used another. Both pipelines were moved onto a single cloud-robust source, "
     "the sixteen-day MODIS MOD13Q1 composite; the model was retrained, the database "
     "migrated, and the corrected model redeployed and verified live. Vegetation ROC-AUC "
     "rose from 0.77 to 0.98, and this corrected model is the one whose results are "
     "reported throughout this chapter. Figure 14 shows the vegetation risk for three "
     "contrasting parks across a full year: it was near zero in the wet season and rose "
     "to roughly 90% in the dry season, which confirmed that the model responded to real "
     "conditions rather than emitting a fixed value.")
figure("veg_seasonal.png", "Figure 14: Vegetation risk over twelve months for three parks.", 6.2, base=RFIG)
h2("5.5 Recommender Results")
para("Budgets are reported in naira, the currency the interface presents to managers, "
     "by converting the optimiser’s internal US-dollar intervention costs at ₦1,600 per "
     "US dollar. The integer-linear-programming recommender honoured the budget and per-"
     "intervention capacity in every test, scaled its plan as the budget grew, and "
     "solved in under 60 milliseconds. Because the recommendation was produced by "
     "transparent optimisation and explained why each intervention was chosen, a manager "
     "could audit rather than merely accept it (Figure 15). A sensitivity analysis "
     "confirmed the plans were stable to small changes in the assumed cost and "
     "effectiveness values, which answered research question five.")
figure("budget_scaling.png", "Figure 15: Recommender plan scaling with budget.", 5.6, base=RFIG)
h2("5.6 Discussion")
para("The results showed that open data and interpretable methods can drive a usable, "
     "transparent decision-support tool for a resource-constrained setting. Read against "
     "the objectives, the forecasting objective was met for all three threats, the "
     "software objective was met (the system ran live), and the evaluation objective was "
     "met with imbalance-aware metrics and a baseline. Read against the literature, the "
     "tree-based result matched the reviewed evidence, and the wide margin over "
     "persistence addressed the common weakness of reporting accuracy without a baseline. "
     "The practical usefulness was that a manager received a costed, zone-level plan with "
     "three to four days of lead time. The contribution was primarily methodological: the "
     "project connected three steps usually kept apart, turning open data into a "
     "forecast, the forecast into a costed plan, and both into an explanation, and showed "
     "the pipeline ran unattended once deployed. As a matter of honesty, this was a "
     "validated proof of concept: it validated the framework, not full real-world "
     "deployment. Its limits were that the drought and vegetation labels derived from "
     "climate thresholds rather than fully independent ground truth (a label-leakage "
     "risk); the threat set was bounded by what free data could measure and so omitted "
     "poaching and grazing; and the intervention parameters were literature-informed "
     "estimates rather than figures measured in these parks.")

# ── CHAPTER SIX ──
pagebreak()
h1("CHAPTER 6: CONCLUSIONS AND RECOMMENDATIONS")
h2("6.1 Conclusions")
para("The project met its main objective: it delivered a live system that produced "
     "daily 30-day forecasts for fire, drought, and vegetation degradation across six "
     "Nigerian national parks and recommended budget-constrained, zone-level "
     "interventions, using only free data. Stated specifically rather than as a claim of "
     "general success: the self-training Random Forest beat the persistence baseline on "
     "all three threats, was strongest on fire (F2 0.95) and vegetation (F2 0.86 after "
     "the sensor fix), and ranked drought risk well (ROC-AUC 0.97) even though drought "
     "precision remained the weakest point at 0.70 because of class imbalance.")
h2("6.2 Answers to the Research Questions")
para("The evidence answered the five questions as follows. (1) Fusing the three modalities "
     "gave the best mean F2 (0.872 against 0.856 for climate alone, 0.821 for satellite "
     "alone and 0.797 for fire history alone), although each threat was marginally best "
     "predicted by its own modality, so fusion bought breadth rather than per-threat "
     "optimality (Table 9). (2) The tree-based model was the best of the four architectures "
     "on every threat, and that ranking held across ecosystems even though accuracy did "
     "not: mean F2 ranged from 0.96 in the Sahel to 0.77 in the rainforest (Table 11). (3) Semi-supervised learning helped only two of the four architectures: it "
     "raised mean F2 by 0.020 for the Random Forest and 0.018 for the Transformer but "
     "lowered it for XGBoost and the LSTM, and inside the Random Forest it traded drought "
     "accuracy (0.882 to 0.825) for a large vegetation gain (0.744 to 0.861). "
     "(4) Outputs tracked seasonal ground conditions "
     "and gave three to four days of lead time. (5) The recommendations were stable to "
     "small changes in cost and effectiveness assumptions.")
h2("6.3 Limitations of the Study")
para("Three limitations qualify the results. First, the drought and vegetation labels "
     "were derived from the same climate and NDVI signals used as features, which created "
     "a label-leakage risk and means those scores should be read as consistency checks "
     "rather than independent validation. Second, the threat set was bounded by remotely "
     "observable phenomena and excluded poaching and grazing, which dominate in practice. "
     "Third, the intervention parameters were literature-informed estimates, and the "
     "system did not yet log actual field deployments.")
h2("6.4 Recommendations")
para("Recommendations follow directly from the findings rather than from unrelated "
     "ideas. Because drought precision was the weakest metric, a manager should treat a "
     "drought flag as a prompt to verify rather than an instruction to act, and because "
     "the system is a proof of concept, a recommendation should be treated as a starting "
     "point to which local knowledge is applied, especially for threats the model does "
     "not cover.")
h2("6.5 Future Work")
para("Future work follows from the limitations. The vegetation-sensing fix reported in "
     "Section 5.4, moving both training and serving to the MOD13Q1 composite, resolved "
     "the earlier collapse and is already live; three extensions build on it: a "
     "Sentinel-1 radar backup that sees through cloud, per-park seasonal imputation of "
     "any residual gaps, and a low-confidence flag when satellite coverage is poor. "
     "Beyond vegetation, the climate-derived labels should be replaced with independent "
     "ground truth to remove the label-leakage risk; deployment logging should be added "
     "so the system can learn from real outcomes; the optimiser should become "
     "intervention-aware and multi-period; and the threat set should be widened toward "
     "poaching and grazing using ranger patrol records.")

# ── REFERENCES ──
pagebreak()
h1("REFERENCES")
def add_hyperlink(paragraph, url):
    part = paragraph.part
    r_id = part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True)
    link = OxmlElement("w:hyperlink"); link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    col = OxmlElement("w:color"); col.set(qn("w:val"), "0563C1"); rPr.append(col)
    ul = OxmlElement("w:u"); ul.set(qn("w:val"), "single"); rPr.append(ul)
    run.append(rPr)
    t = OxmlElement("w:t"); t.text = url; run.append(t); link.append(run)
    paragraph._p.append(link)

refs = [
 ("Beyer, H. L., Dujardin, Y., Watts, M. E., & Possingham, H. P. (2016). Solving conservation planning problems with integer linear programming. Ecological Modelling, 328, 14-22.", "https://doi.org/10.1016/j.ecolmodel.2016.02.005"),
 ("Brys, C., La Red Martínez, D. L., & Marinelli, M. (2025). Machine learning methods for wildfire risk assessment. Earth Science Informatics, 18, 148.", "https://doi.org/10.1007/s12145-024-01690-z"),
 ("Cazalis, V., Prince, K., Mihoub, J.-B., Kelly, J., Butchart, S. H. M., & Rodrigues, A. S. L. (2020). Effectiveness of protected areas in conserving tropical forest birds. Nature Communications, 11, 4461.", "https://doi.org/10.1038/s41467-020-18230-0"),
 ("Craigie, I. D., Baillie, J. E. M., Balmford, A., Carbone, C., Collen, B., Green, R. E., & Hutton, J. M. (2010). Large mammal population declines in Africa’s protected areas. Biological Conservation, 143(9), 2221-2228.", "https://doi.org/10.1016/j.biocon.2010.06.007"),
 ("Fang, F., Nguyen, T. H., Pickles, R., Lam, W. Y., Clements, G. R., An, B., … Lemieux, A. (2017). PAWS: A deployed game-theoretic application to combat poaching. AI Magazine, 38(1), 23-36.", "https://doi.org/10.1609/aimag.v38i1.2710"),
 ("Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18-27.", "https://doi.org/10.1016/j.rse.2017.06.031"),
 ("Haider, H. (2019). Climate change in Nigeria: Impacts and responses (K4D Helpdesk Report 675). Institute of Development Studies.", "https://opendocs.ids.ac.uk/opendocs/handle/20.500.12413/14761"),
 ("Hutson, M. (2018). Artificial intelligence faces reproducibility crisis. Science, 359(6377), 725-726.", "https://doi.org/10.1126/science.359.6377.725"),
 ("Kasusse, K. S., Mushore, T., & Matose, F. (2021). Spatial Monitoring and Reporting Tool (SMART) in Mid-Zambezi Valley, Zimbabwe. Conservation Science and Practice, 3(9), e492.", "https://doi.org/10.1111/csp2.492"),
 ("Lindsey, P. A., Miller, J. R. B., Petracca, L. S., Coad, L., Dickman, A. J., … Hunter, L. T. B. (2017). The performance of African protected areas for lions and their prey. Biological Conservation, 209, 137-149.", "https://doi.org/10.1016/j.biocon.2017.01.011"),
 ("Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. In Advances in Neural Information Processing Systems 30 (pp. 4765-4774).", "https://arxiv.org/abs/1705.07874"),
 ("McNicol, I. M., Keane, A., Burgess, N. D., Bowers, S. J., Mitchard, E. T. A., & Ryan, C. M. (2023). Protected areas reduce deforestation and degradation and enhance woody growth across African woodlands. Communications Earth & Environment, 4, 392.", "https://doi.org/10.1038/s43247-023-01053-4"),
 ("Mohammed, A. K., & Adamu, B. (2021). Early warning systems development for agricultural drought assessment in Nigeria. Environmental Monitoring and Assessment, 193, 27.", "https://doi.org/10.1007/s10661-020-08730-3"),
 ("Naderpour, M., Rizeei, H. M., & Ramezani, F. (2021). Forest fire risk prediction: A spatial deep neural network-based framework. Remote Sensing, 13(13), 2513.", "https://doi.org/10.3390/rs13132513"),
 ("Réjou-Méchain, M., Mortier, F., Bastin, J. F., Cornu, G., Barbier, N., … Ploton, P. (2021). Unveiling African rainforest composition and vulnerability to global change. Nature, 593(7857), 90-94.", "https://doi.org/10.1038/s41586-021-03483-6"),
 ("Schuster, R., Hanson, J. O., Strimas-Mackey, M., & Bennett, J. R. (2020). Exact integer linear programming solvers outperform simulated annealing for solving conservation planning problems. PeerJ, 8, e9258.", "https://doi.org/10.7717/peerj.9258"),
 ("Shiru, M. S., Shahid, S., Chung, E. S., Alias, N., & Scherer, L. (2020). Projection of meteorological droughts in Nigeria during growing seasons under climate change scenarios. Scientific Reports, 10, 10107.", "https://doi.org/10.1038/s41598-020-67146-8"),
 ("Siddig, A. H. (2019). Why is biodiversity data-deficiency an ongoing conservation dilemma in Africa? Journal for Nature Conservation, 50, 125719.", "https://doi.org/10.1016/j.jnc.2019.125719"),
 ("SMART Partnership. (2024). SMART Conservation Software.", "https://smartconservationtools.org/"),
 ("Sohn, K., Berthelot, D., Carlini, N., Zhang, Z., Zhang, H., Raffel, C., … Li, C. L. (2020). FixMatch: Simplifying semi-supervised learning with consistency and confidence. Advances in Neural Information Processing Systems, 33, 596-608.", "https://arxiv.org/abs/2001.07685"),
 ("Tuia, D., Kellenberger, B., Beery, S., Costelloe, B. R., Zuffi, S., … Berger-Wolf, T. (2022). Perspectives in machine learning for wildlife conservation. Nature Communications, 13(1), 792.", "https://doi.org/10.1038/s41467-022-27980-y"),
 ("UNEP-WCMC, & IUCN. (2024). Protected Planet: Nigeria. World Database on Protected Areas.", "https://www.protectedplanet.net/country/NGA"),
 ("Van Engelen, J. E., & Hoos, H. H. (2020). A survey on semi-supervised learning. Machine Learning, 109(2), 373-440.", "https://doi.org/10.1007/s10994-019-05855-6"),
 ("Xu, L., Gholami, S., McCarthy, S., Dilkina, B., Plumptre, A., Tambe, M., … Enyel, E. (2020). Stay ahead of poachers: Illegal wildlife poaching prediction and patrol planning under uncertainty with field test evaluations. In Proceedings of the IEEE International Conference on Data Engineering (pp. 1898-1901).", "https://arxiv.org/abs/1903.06669"),
]
for text, url in sorted(refs, key=lambda x: x[0].lower()):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.add_run(text + " ")
    add_hyperlink(p, url)

for s in doc.sections:
    s.top_margin = s.bottom_margin = Inches(1)
    s.left_margin = s.right_margin = Inches(1)

out = "ConserveAI_Final_Report.docx"
try:
    doc.save(out)
except PermissionError:
    out = "ConserveAI_Final_Report_NEW.docx"
    doc.save(out)
    print("ORIGINAL LOCKED (close it in Word). Wrote:", out)
d = Document(out)
for p in d.paragraphs:
    for run in p.runs:
        if "—" in run.text: run.text = run.text.replace(" — ", ", ").replace("—", ", ")
d.save(out)
print("SAVED:", out, "|", len(d.paragraphs), "paragraphs")
