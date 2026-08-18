SELECT
    case_date AS report_date,

    COUNT(*) AS support_cases,

    ROUND(
        AVG(support_sla_met) * 100,
        2
    ) AS support_sla_pct,

    ROUND(
        AVG(csat_score),
        2
    ) AS avg_csat,

    ROUND(
        AVG(escalated_flag) * 100,
        2
    ) AS escalation_rate_pct

FROM {{ ref('silver_support_cases') }}

GROUP BY case_date
