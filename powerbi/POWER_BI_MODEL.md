# Aegis Power BI Model

## Tables

- dim_date
- executive_daily
- logistics_performance
- data_reliability_daily
- customer_experience
- commerce_performance
- incident_command_center

## Relationships

Create these relationships as:

- Cardinality: One-to-many
- Cross filter direction: Single
- Active: Yes

dim_date[date]
    1 -> *
executive_daily[report_date]

dim_date[date]
    1 -> *
logistics_performance[report_date]

dim_date[date]
    1 -> *
data_reliability_daily[report_date]

dim_date[date]
    1 -> *
customer_experience[report_date]

dim_date[date]
    1 -> *
commerce_performance[report_date]

Do NOT connect incident_command_center directly by date.
It has incident-level granularity and should remain disconnected.

## Date Table

Mark dim_date as the official Date Table using:

dim_date[date]

Sort:

dim_date[month_name]
by
dim_date[month_number]

## Core Measures

### Executive

Total Orders =
SUM(executive_daily[orders])

Total Shipments =
SUM(executive_daily[shipments])

Purchase Events =
SUM(executive_daily[purchase_events])

Data Incident Days =
SUM(executive_daily[data_incident_flag])

### Commerce

Total Order Value =
SUM(commerce_performance[total_order_value_eur])

Completed Revenue =
SUM(commerce_performance[completed_revenue_eur])

Returned Value =
SUM(commerce_performance[returned_value_eur])

Total Commerce Orders =
SUM(commerce_performance[orders])

Completed Orders =
SUM(commerce_performance[completed_orders])

Returned Orders =
SUM(commerce_performance[returned_orders])

Cancelled Orders =
SUM(commerce_performance[cancelled_orders])

Pending Orders =
SUM(commerce_performance[pending_orders])

Completed AOV =
DIVIDE(
    [Completed Revenue],
    [Completed Orders]
)

Payment Success % =
DIVIDE(
    SUM(commerce_performance[paid_payments]),
    SUM(commerce_performance[orders])
)

### Logistics

Shipment Touches =
SUM(logistics_performance[shipment_touches])

Delayed Shipments =
SUM(logistics_performance[delayed_shipments])

SLA Met Shipments =
SUM(logistics_performance[sla_met_shipments])

Delay Rate % =
DIVIDE(
    [Delayed Shipments],
    [Shipment Touches]
)

Delivery SLA % =
DIVIDE(
    [SLA Met Shipments],
    [Shipment Touches]
)

Average Network Load % =
DIVIDE(
    SUMX(
        logistics_performance,
        logistics_performance[avg_network_load_pct]
            * logistics_performance[shipment_touches]
    ),
    [Shipment Touches]
)

Incident Shipment Touches =
CALCULATE(
    [Shipment Touches],
    logistics_performance[business_incident_flag] = 1
)

### Data Reliability

Expected Purchases =
SUM(data_reliability_daily[expected_purchase_count])

Observed Purchases =
SUM(data_reliability_daily[observed_purchase_count])

Missing Purchase Events =
SUM(data_reliability_daily[missing_purchase_events])

Event Coverage % =
DIVIDE(
    [Observed Purchases],
    [Expected Purchases]
)

Expected Revenue =
SUM(data_reliability_daily[expected_revenue_eur])

Observed Event Revenue =
SUM(data_reliability_daily[observed_event_revenue_eur])

Revenue Capture % =
DIVIDE(
    [Observed Event Revenue],
    [Expected Revenue]
)

Data Trust Failed Days =
CALCULATE(
    COUNTROWS(data_reliability_daily),
    data_reliability_daily[data_trust_status] = "FAILED"
)

### Customer Experience

Support Cases =
SUM(customer_experience[support_cases])

Affected Customers =
SUM(customer_experience[customers_contacting])

Support SLA % =
DIVIDE(
    SUMX(
        customer_experience,
        customer_experience[support_sla_pct]
            * customer_experience[support_cases]
    ),
    [Support Cases]
) / 100

Average CSAT =
DIVIDE(
    SUMX(
        customer_experience,
        customer_experience[avg_csat]
            * customer_experience[support_cases]
    ),
    [Support Cases]
)

Escalation Rate % =
DIVIDE(
    SUMX(
        customer_experience,
        customer_experience[escalation_rate_pct]
            * customer_experience[support_cases]
    ),
    [Support Cases]
) / 100

Incident Support Cases =
CALCULATE(
    [Support Cases],
    customer_experience[business_incident_flag] = 1
)

### Incident Command Center

Total Incidents =
COUNTROWS(incident_command_center)

Data Incidents =
CALCULATE(
    [Total Incidents],
    incident_command_center[classification] = "DATA_INCIDENT"
)

Business Incidents =
CALCULATE(
    [Total Incidents],
    incident_command_center[classification] = "BUSINESS_INCIDENT"
)

Failed Data Trust Incidents =
CALCULATE(
    [Total Incidents],
    incident_command_center[data_trust_status] = "FAILED"
)

Critical Incidents =
CALCULATE(
    [Total Incidents],
    incident_command_center[severity] = "Critical"
)

Maximum Incident Confidence =
MAX(incident_command_center[confidence_score])

Maximum Anomaly Score =
MAX(incident_command_center[anomaly_score])

## Formatting

Format as percentage:
- Payment Success %
- Delay Rate %
- Delivery SLA %
- Event Coverage %
- Revenue Capture %
- Support SLA %
- Escalation Rate %

Format as EUR:
- Total Order Value
- Completed Revenue
- Returned Value
- Completed AOV
- Expected Revenue
- Observed Event Revenue

Format Average CSAT with 2 decimal places.

## Recommended Report Pages

1. Executive Command Center
2. Operations Control Tower
3. Commerce & Revenue
4. Customer Experience
5. Data Reliability Center
6. Incident & RCA Command Center
7. AI Decision Assistant

## Important Modeling Rule

Do not sum pre-calculated percentages directly.

Use weighted measures for:
- network load
- support SLA
- escalation rate
- CSAT

The incident_command_center table has one row per incident and should remain
logically separate from daily fact tables.
