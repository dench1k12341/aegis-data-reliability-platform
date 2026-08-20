<h1 align="center">Aegis Data Reliability Platform</h1>

<p align="center">
  An end-to-end analytics engineering platform that separates bad data from real business incidents, explains root-cause evidence, and turns governed facts into executive decisions.
</p>

<p align="center">
  <a href="https://github.com/dench1k12341/aegis-data-reliability-platform/actions/workflows/ci.yml">
    <img alt="Aegis CI" src="https://github.com/dench1k12341/aegis-data-reliability-platform/actions/workflows/ci.yml/badge.svg">
  </a>
  <img alt="Python 3.12+" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white">
  <img alt="DuckDB" src="https://img.shields.io/badge/DuckDB-FFF000?logo=duckdb&logoColor=111111">
  <img alt="dbt" src="https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white">
  <img alt="Power BI" src="https://img.shields.io/badge/Power%20BI-F2C811?logo=powerbi&logoColor=111111">
  <img alt="pytest" src="https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white">
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-green.svg">
</p>

<p align="center">
  <img src="docs/screenshots/power-bi/01-executive-command-center.png" alt="Aegis Executive Command Center Power BI page">
</p>

## Overview

Most dashboards assume that the data underneath them is trustworthy.

Aegis does not.

Before interpreting KPI movements, Aegis asks a more important question:

> **Did the business change, or did the data break?**

Aegis simulates a European commerce and logistics platform, injects controlled data and operational failures, and then detects them without reading the ground-truth incident file.

The project combines data generation, observability, reconciliation, anomaly detection, root-cause analysis, incident classification, DuckDB warehousing, dbt transformations, automated testing, Power BI analytics, and grounded AI reporting.

The result is a complete decision-intelligence workflow:

```text
KPI changes
    ↓
Can the underlying data be trusted?
    ↓
┌──────────────────────────────┐
│                              │
DATA TRUST FAILED        DATA TRUST PASSED
│                              │
Data incident            Business incident
│                              │
Do not trust KPI         Investigate operations
│                              │
Fix data pipeline        Root-cause analysis
                               ↓
                         Operational action
```

### Why this project matters

A traditional dashboard can show that a KPI deteriorated.

Aegis goes one step further by determining whether that deterioration is caused by:

- broken telemetry or unreliable data,
- or a real operational/business problem.

This distinction prevents teams from reacting to false signals and helps decision-makers focus on the correct remediation path.

---

## Tech Stack

| Area | Technologies |
|---|---|
| Data Engineering | Python, pandas, NumPy, PyArrow |
| Analytics Warehouse | DuckDB, SQL |
| Analytics Engineering | dbt Core, dbt-duckdb |
| Data Quality | Reconciliation controls, completeness, uniqueness, freshness, volume and null checks |
| Analytics | SQL, statistical anomaly detection, RCA scoring |
| Machine Learning | scikit-learn, SciPy |
| BI & Visualization | Microsoft Power BI, DAX |
| AI | Groq, OpenAI-compatible LLMs, grounded prompt packs |
| AI Safety Layer | Factual validation, evidence constraints, self-correction |
| Testing | pytest, pytest-cov |
| CI/CD | GitHub Actions |
| Configuration | YAML, Pydantic, python-dotenv |
| Version Control | Git, GitHub |

---

## Key Results

All values below are reproducible from the deterministic `dev` configuration and are asserted by analytical contracts or captured in the governed evidence package.

| Area | Verified result |
|---|---|
| Dataset | 25,000 orders, 22,000 shipments, 150,000 tracking events, 4,000 support cases |
| Commerce trust | 25,000 orders reconciled with 0 payment mismatches |
| Data incident | 7 affected days, 219 missing purchase events, 58.13% event coverage, 29.28% revenue capture |
| Business incident | Warsaw hub, 27 shipment touches, 100% delay rate, 109.31% average network load |
| Customer impact | 4 incident support cases, 0% support SLA, 3.25 average CSAT |
| Incident registry | 2 incidents: 1 data incident and 1 business incident |
| RCA | Network Congestion / Warehouse Overload ranked as strongest explanatory factor |
| Governed AI | Factual validator caught a 6-vs-7-day duration error and self-correction reduced warnings from 1 to 0 |
| Regression testing | Warehouse and Gold-layer contracts validated through pytest |
| CI | Deterministic pipeline, dbt build and regression tests run automatically in GitHub Actions |

> These are synthetic evaluation results, not production performance claims.

---

## What Aegis Demonstrates

- Deterministic multi-domain data generation with fixed random seeds.
- Commerce, logistics, support and product-event datasets.
- Controlled incident injection.
- Ground-truth isolation from the detection pipeline.
- Data observability and reconciliation controls.
- Blind detection of a purchase telemetry failure.
- Operational KPI anomaly detection.
- Root-cause hypothesis ranking.
- Unified Data Incident vs Business Incident classification.
- Bronze, Silver and Gold warehouse architecture.
- DuckDB analytics warehouse.
- dbt staging, Silver and Gold models.
- dbt source and model tests.
- Power BI executive and operational reporting.
- Incident-level decision intelligence.
- Grounded LLM reporting.
- Automated factual validation.
- Targeted AI self-correction.
- End-to-end CI through GitHub Actions.

---

## Architecture

<p align="center">
  <img src="docs/architecture.svg" alt="Aegis platform architecture from source generation to Power BI and governed AI">
</p>

### High-Level Data Flow

```text
Synthetic Sources
      ↓
RAW Baseline
      ↓
Incident Injection
      ↓
Bronze
      ↓
Data Observability
      ↓
Silver
      ↓
Business Anomaly Detection
      ↓
Root Cause Analysis
      ↓
Incident Classification
      ↓
Gold Analytics Marts
      ↓
Decision Intelligence
      ↓
Grounded AI
      ↓
Factual Validator
      ↓
Self-Correction
      ↓
Power BI / Executive Decision Layer
```

### Platform Layers

| Layer | Responsibility | Main outputs |
|---|---|---|
| Generate | Create commerce, logistics, support and product-event data | Local Parquet datasets |
| Inject | Introduce controlled data and business failures | Bronze incident datasets |
| Observe | Run Data Quality and reconciliation controls | Data incident evidence |
| Detect | Identify operational KPI anomalies | Business incident candidates |
| Explain | Rank root-cause hypotheses | RCA evidence |
| Classify | Separate Data Incidents from Business Incidents | Incident registry |
| Model | Build Bronze, Silver and Gold analytical layers | DuckDB warehouse |
| Transform | Create dbt staging, Silver and Gold models | Reviewable SQL lineage |
| Decide | Build deterministic evidence-based decision briefs | Decision layer |
| Ground | Build constrained AI prompt packs | Evidence-bound LLM inputs |
| Validate | Check LLM output against governed evidence | Validation warnings |
| Correct | Perform targeted correction when needed | Validated final report |
| Consume | Export governed analytics | Power BI report |

The default pipeline contains **20 deterministic steps** and does not require an external AI provider.

---

## Core Incident Logic

Aegis uses Data Trust as the decision gate.

### Data Incident

```text
KPI anomaly
    ↓
Data Quality / reconciliation fails
    ↓
DATA TRUST FAILED
    ↓
DATA INCIDENT
    ↓
Do not use affected KPI
    ↓
Investigate data pipeline
```

### Business Incident

```text
KPI anomaly
    ↓
Data Quality controls pass
    ↓
DATA TRUST PASSED
    ↓
BUSINESS INCIDENT
    ↓
Root-cause analysis
    ↓
Operational intervention
```

---

## Detected Data Incident

A purchase-event telemetry failure was detected for:

**08 Sep 2025 → 14 Sep 2025**

Validated evidence:

| Metric | Result |
|---|---:|
| Expected purchase events | 523 |
| Observed purchase events | 304 |
| Missing events | 219 |
| Event coverage | 58.13% |
| Null purchase values | 136 |
| Revenue capture | 29.28% |
| Data Trust | FAILED |

Operational order records remained available while purchase-event telemetry became incomplete.

The decision layer therefore classified the event as:

```text
DATA_INCIDENT
```

Recommended decision:

> Do not trust affected telemetry KPIs until the telemetry pipeline is repaired and reconciliation passes.

---

## Detected Business Incident

A logistics performance incident was detected in:

**Warsaw, Poland**

Detected period:

**18 Nov 2025 → 01 Dec 2025**

Validated evidence:

| Metric | Result |
|---|---:|
| Affected shipment touches | 27 |
| Delay rate | 100.00% |
| Delivery SLA | 0.00% |
| Average network load | 109.31% |
| Anomaly score | 98.63 |
| Affected support cases | 4 |
| Data Trust | PASSED |

Because logistics Data Quality controls remained valid, Aegis classified the degradation as a real operational problem:

```text
BUSINESS_INCIDENT
```

---

## Root Cause Analysis

Evidence-weighted root-cause ranking for the Warsaw incident:

| Hypothesis | Score |
|---|---:|
| Network Congestion / Warehouse Overload | 100.00 |
| Network Seasonality | 40.63 |
| Carrier-Specific Performance | 30.00 |
| Route / Distance Mix | 5.04 |

The strongest explanatory factor was:

> **Network Congestion / Warehouse Overload**

The reported confidence value belongs to the internal synthetic Aegis scoring framework and should not be interpreted as real-world model accuracy.

---

## Customer Impact

The Warsaw logistics incident propagated into customer support metrics.

| Metric | Non-Incident | Incident |
|---|---:|---:|
| Support SLA | 67.92% | 0.00% |
| Average CSAT | 4.23 | 3.25 |
| Escalation Rate | 12.39% | 25.00% |

Incident deltas:

```text
Support SLA       -67.92 pp
CSAT              -0.98
Escalation Rate   +12.61 pp
```

This demonstrates how Aegis links operational failures to downstream customer impact.

---

## Power BI Report

The Power BI semantic model uses:

- a shared date dimension,
- weighted percentage measures,
- domain-specific Gold marts,
- governed DAX measures,
- a disconnected incident-level command-center table,
- conditional formatting,
- incident status panels,
- report navigation,
- reset-filter actions.

Detailed modeling guidance and DAX definitions are documented in:

[powerbi/POWER_BI_MODEL.md](powerbi/POWER_BI_MODEL.md)

### 01 Executive Command Center

[![Executive Command Center](docs/screenshots/power-bi/01-executive-command-center.png)](docs/screenshots/power-bi/01-executive-command-center.png)

Executive view of orders, shipments, revenue, delivery SLA and incident state.

---

### 02 Operations Control Tower

[![Operations Control Tower](docs/screenshots/power-bi/02-operations-control-tower.png)](docs/screenshots/power-bi/02-operations-control-tower.png)

Operational logistics KPIs, city/carrier rankings, network load and incident-level operational detail.

---

### 03 Commerce & Revenue

[![Commerce and Revenue](docs/screenshots/power-bi/03-commerce-revenue.png)](docs/screenshots/power-bi/03-commerce-revenue.png)

Trusted operational revenue, order trends, customer segments, countries, channels and payment performance.

---

### 04 Customer Experience

[![Customer Experience](docs/screenshots/power-bi/04-customer-experience.png)](docs/screenshots/power-bi/04-customer-experience.png)

Support SLA, CSAT, escalation, root causes and incident-vs-normal customer impact.

---

### 05 Data Reliability Center

[![Data Reliability Center](docs/screenshots/power-bi/05-data-reliability-center.png)](docs/screenshots/power-bi/05-data-reliability-center.png)

Expected-vs-observed event reconciliation, missing events, revenue capture and Data Trust status.

---

### 06 Incident & RCA Command Center

[![Incident and RCA Command Center](docs/screenshots/power-bi/06-incident-rca-command-center.png)](docs/screenshots/power-bi/06-incident-rca-command-center.png)

Unified Data Incident and Business Incident view with root-cause ranking and decision path.

---

### 07 AI Decision Assistant

[![AI Decision Assistant](docs/screenshots/power-bi/07-ai-decision-assistant.png)](docs/screenshots/power-bi/07-ai-decision-assistant.png)

Validated evidence, grounded AI executive reporting and factual validation status.

---

## AI Grounding and Self-Correction

AI is optional and is **not used as an independent source of truth**.

The analytical pipeline remains authoritative.

```text
Validated Evidence
      ↓
Decision Brief
      ↓
Grounded LLM
      ↓
Factual Validator
      ↓
Self-Correction
      ↓
Validated Executive Report
```

The workflow:

1. The deterministic pipeline creates an incident registry.
2. A deterministic decision brief is generated from validated evidence.
3. A grounded prompt exposes only incident-specific evidence.
4. Guardrails prohibit invented metrics, root causes and unsupported claims.
5. The LLM generates an executive explanation.
6. A factual validator compares the output against governed evidence.
7. If warnings exist, one targeted correction pass is executed.
8. The corrected report is validated again.

### Demonstrated validation case

For `AEGIS-INC-001`, the initial AI response described the incident as a six-day window.

The actual incident dates cover seven calendar days.

The validator detected the inconsistency:

```text
Initial warnings: 1
```

Self-correction was executed:

```text
Self-correction: Completed
```

Final result:

```text
Final warnings: 0
Grounding status: PASSED
```

For the business incident, no correction was required.

```text
Initial warnings: 0
Self-correction: Not required
Final warnings: 0
Grounding status: PASSED
```

The live demonstration currently uses:

```text
Provider: Groq
Model: openai/gpt-oss-120b
```

External knowledge restrictions are enforced through the grounding and prompt policy; they should not be interpreted as network-level isolation.

---

## Data Architecture

Aegis uses a layered analytical architecture.

### RAW

Clean deterministic baseline data before incidents.

### Bronze

Source-aligned datasets after incident injection.

Bronze represents what the analytical platform actually receives.

### Silver

Validated and business-ready analytical entities.

Examples:

```text
orders_enriched
shipments_enriched
support_enriched
app_funnel_daily
daily_purchase_reconciliation
warehouse_anomaly_windows
```

### Gold

Business-facing analytical marts.

Examples:

```text
executive_daily
logistics_performance
data_reliability_daily
customer_experience
commerce_performance
incident_command_center
```

---

## DuckDB Analytics Warehouse

The local warehouse is built in:

```text
data/warehouse/aegis.duckdb
```

Schemas:

```text
bronze
silver
gold
meta
```

The database itself is generated locally and intentionally excluded from Git.

---

## dbt Analytics Engineering Layer

The repository includes a dbt project for SQL lineage, model documentation and automated testing.

Current dbt structure:

```text
sources
   ↓
staging
   ↓
silver
   ↓
gold
```

Run:

```powershell
dbt build --profiles-dir dbt
```

The dbt project currently contains:

- 11 sources,
- 12 models,
- source-level tests,
- staging tests,
- Silver model tests,
- Gold model tests.

A validated local build executes:

```text
83 resources/tests successfully
```

Generate lineage documentation:

```powershell
dbt docs generate --profiles-dir dbt
dbt docs serve --profiles-dir dbt
```

---

## Setup

### Prerequisites

- Python 3.12+
- Git
- Power BI Desktop only if recreating the dashboard
- Optional API key for live AI execution

### Clone

```powershell
git clone https://github.com/dench1k12341/aegis-data-reliability-platform.git
cd aegis-data-reliability-platform
```

### Create environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No secrets are required for the deterministic pipeline.

For optional live AI execution:

```powershell
Copy-Item .env.example .env
```

Then add either:

```text
GROQ_API_KEY
```

or:

```text
OPENAI_API_KEY
```

The local `.env` file is ignored by Git.

---

## Running the Platform

### Full deterministic pipeline

```powershell
python -m src.pipeline.run_all
```

The pipeline runs 20 stages from data generation through Gold analytics marts.

### List pipeline steps

```powershell
python -m src.pipeline.run_all --list
```

### Resume from a specific step

Example:

```powershell
python -m src.pipeline.run_all --from-step 13
```

### Optional Groq AI execution

```powershell
python -m src.ai.run_decision_assistant_groq
```

### Optional OpenAI execution

```powershell
python -m src.ai.run_decision_assistant
```

The OpenAI runner requires an account with available API quota.

---

## Power BI Export

Generate the governed Power BI datasets:

```powershell
python -m src.warehouse.export_powerbi
python -m src.warehouse.export_powerbi_date
```

Generated files are written to:

```text
powerbi/data/
```

The directory remains local and is ignored by Git.

---

## Testing

Run all regression tests:

```powershell
pytest -v
```

The current regression suite verifies:

- expected schemas,
- Bronze table inventory,
- deterministic row counts,
- Silver model existence,
- uniqueness of business keys,
- payment reconciliation,
- purchase-event reconciliation,
- detection of the data incident,
- detection of the Warsaw business anomaly,
- Gold mart contracts,
- customer-impact reconciliation,
- incident command-center consistency,
- warehouse metadata.

Example validated result:

```text
17 passed
```

Coverage can also be executed with:

```powershell
pytest --cov=src --cov-report=term-missing
```

---

## CI/CD

Aegis includes a GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

It executes automatically on:

```text
push → main
pull_request → main
```

The workflow:

```text
Checkout repository
      ↓
Set up Python
      ↓
Install dependencies
      ↓
Run deterministic Aegis pipeline
      ↓
dbt build
      ↓
pytest regression tests
```

This verifies that the repository can rebuild its analytical state from source code.

---

## Repository Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── config/
│   └── settings.yaml
│
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── silver/
│   │   └── gold/
│   └── profiles.yml
│
├── docs/
│   ├── architecture.svg
│   └── screenshots/
│       └── power-bi/
│
├── powerbi/
│   └── POWER_BI_MODEL.md
│
├── sql/
│   ├── silver/
│   └── gold/
│
├── src/
│   ├── generate/
│   ├── incidents/
│   ├── quality/
│   ├── anomaly/
│   ├── rca/
│   ├── decision/
│   ├── ai/
│   ├── warehouse/
│   └── pipeline/
│
├── tests/
│   ├── test_gold_contracts.py
│   └── test_warehouse_contracts.py
│
├── .env.example
├── .gitignore
├── dbt_project.yml
├── LICENSE
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Generated Files Excluded from Git

The repository intentionally excludes:

```text
.venv/
.env
data/raw/
data/bronze/
data/silver/
data/gold/
data/warehouse/
artifacts/
logs/
*.duckdb
*.db
*.sqlite
*.pbix
*.pbit
powerbi/data/
target/
dbt/target/
dbt/logs/
dbt/dbt_packages/
IDE metadata
temporary files
```

This keeps the repository lightweight and prevents generated data, secrets and local application files from being committed.

---

## Limitations

Aegis is a portfolio-grade synthetic analytical system, not a production deployment.

Important limitations:

- All source data is synthetic.
- Injected incidents are deterministic evaluation scenarios.
- Root-cause scores represent evidence-weighted hypotheses, not proof of causality.
- Model Confidence belongs to the internal Aegis scoring framework and is not real-world accuracy.
- The project uses a local DuckDB warehouse rather than a distributed production platform.
- Production orchestration, streaming ingestion, IAM, alert routing and cloud infrastructure are outside the project scope.
- The factual validator is rule-based and cannot guarantee detection of every possible hallucination.
- Live LLM responses may vary by provider or model version.
- External knowledge restrictions are enforced through prompt policy, not through network-level isolation.
- The Power BI binary is intentionally excluded from source control.
- Screenshots provide a reviewable representation of the dashboard.

---

## Design Principles

Aegis follows several core principles:

```text
Analytics first, AI second.

Trust the data before interpreting the KPI.

Separate data failures from business failures.

Keep ground truth isolated from detection.

Use AI to explain validated evidence,
not to invent analytical conclusions.

Make every important result reproducible.
```

---

## License

This project is released under the [MIT License](LICENSE).

---

## Author

**Denys Dolhov**

Data Analytics • Data Quality • Analytics Engineering • Operations Intelligence

GitHub: [dench1k12341](https://github.com/dench1k12341)
