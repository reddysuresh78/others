<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# yes

Yes — here’s a **supply-chain-specific blueprint**. The base hybrid architecture still stands, but for vendor documents you should make vendors, contracts, obligations, certifications, facilities, products/materials, incidents, and risk signals first-class objects because supplier risk management depends on continuous identification, assessment, monitoring, and mitigation across the supplier ecosystem.[^1]

## Domain model

Your core entities should be richer than a generic document system because procurement contracts define price, delivery timelines, service levels, penalties, renewal/termination rules, and compliance obligations, while supplier risk management needs visibility into tiered suppliers, financial health, geopolitical exposure, operational risk, compliance, and cybersecurity risk.[^1]

Use these top-level objects:

- `Vendor`
- `VendorSite`
- `Contract`
- `ContractClause`
- `Obligation`
- `Certification`
- `Product`
- `Material`
- `Facility`
- `PurchaseOrder`
- `Invoice`
- `Shipment`
- `Incident`
- `AuditFinding`
- `RiskSignal`
- `Jurisdiction`
- `Person/Contact`


## SQL schema

A practical starting schema is below. It keeps exact facts in SQL and leaves long text in chunks/vector search.

```sql
CREATE TABLE vendors (
  vendor_id              BIGSERIAL PRIMARY KEY,
  vendor_name            TEXT NOT NULL,
  normalized_name        TEXT UNIQUE NOT NULL,
  vendor_type            TEXT,                  -- manufacturer, logistics, distributor, service
  parent_vendor_id       BIGINT REFERENCES vendors(vendor_id),
  tier_level             INT,                   -- 1,2,3
  country_code           TEXT,
  region                 TEXT,
  status                 TEXT,                  -- active, blocked, onboarding, offboarded
  criticality            TEXT,                  -- low, medium, high, strategic
  financial_risk_score   NUMERIC,
  cyber_risk_score       NUMERIC,
  operational_risk_score NUMERIC,
  compliance_risk_score  NUMERIC,
  overall_risk_score     NUMERIC,
  last_risk_review_at    TIMESTAMPTZ,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE vendor_sites (
  site_id                BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
  site_name              TEXT,
  country_code           TEXT,
  city                   TEXT,
  address                TEXT,
  site_type              TEXT,                  -- plant, warehouse, office, dc
  latitude               NUMERIC,
  longitude              NUMERIC,
  active                 BOOLEAN DEFAULT TRUE,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE contracts (
  contract_id            BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT NOT NULL REFERENCES vendors(vendor_id),
  contract_number        TEXT UNIQUE,
  contract_type          TEXT,                  -- MSA, SOW, PO-framework, logistics, NDA
  title                  TEXT,
  effective_date         DATE,
  expiration_date        DATE,
  auto_renewal           BOOLEAN,
  renewal_notice_days    INT,
  governing_law          TEXT,
  currency               TEXT,
  total_value            NUMERIC,
  payment_terms_text     TEXT,
  contract_status        TEXT,                  -- draft, active, expired, terminated
  source_doc_id          BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE contract_clauses (
  clause_id              BIGSERIAL PRIMARY KEY,
  contract_id            BIGINT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
  clause_type            TEXT,                  -- sla, indemnity, liability_cap, audit_right, termination
  clause_title           TEXT,
  clause_text            TEXT,
  extracted_value_text   TEXT,
  extracted_value_num    NUMERIC,
  extracted_value_date   DATE,
  confidence             REAL,
  source_doc_id          BIGINT,
  source_chunk_id        BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE obligations (
  obligation_id          BIGSERIAL PRIMARY KEY,
  contract_id            BIGINT REFERENCES contracts(contract_id) ON DELETE CASCADE,
  vendor_id              BIGINT REFERENCES vendors(vendor_id),
  obligation_type        TEXT,                  -- insurance, audit, reporting, certification, sla, notice
  obligation_text        TEXT NOT NULL,
  due_date               DATE,
  recurrence             TEXT,                  -- monthly, quarterly, annual, one-time
  owner_team             TEXT,
  status                 TEXT,                  -- open, met, overdue, waived
  severity               TEXT,                  -- low, medium, high, critical
  source_clause_id       BIGINT REFERENCES contract_clauses(clause_id),
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE certifications (
  certification_id       BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT REFERENCES vendors(vendor_id) ON DELETE CASCADE,
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  cert_type              TEXT,                  -- ISO27001, SOC2, CTPAT, ESG, GMP
  cert_number            TEXT,
  issuer                 TEXT,
  valid_from             DATE,
  valid_to               DATE,
  status                 TEXT,                  -- valid, expiring, expired, revoked
  source_doc_id          BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE products (
  product_id             BIGSERIAL PRIMARY KEY,
  sku                    TEXT UNIQUE,
  product_name           TEXT NOT NULL,
  product_family         TEXT,
  criticality            TEXT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE materials (
  material_id            BIGSERIAL PRIMARY KEY,
  material_code          TEXT UNIQUE,
  material_name          TEXT NOT NULL,
  category               TEXT,
  criticality            TEXT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE vendor_products (
  vendor_id              BIGINT REFERENCES vendors(vendor_id) ON DELETE CASCADE,
  product_id             BIGINT REFERENCES products(product_id) ON DELETE CASCADE,
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  sole_source            BOOLEAN DEFAULT FALSE,
  lead_time_days         INT,
  moq                    NUMERIC,
  PRIMARY KEY (vendor_id, product_id, site_id)
);

CREATE TABLE vendor_materials (
  vendor_id              BIGINT REFERENCES vendors(vendor_id) ON DELETE CASCADE,
  material_id            BIGINT REFERENCES materials(material_id) ON DELETE CASCADE,
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  sole_source            BOOLEAN DEFAULT FALSE,
  lead_time_days         INT,
  PRIMARY KEY (vendor_id, material_id, site_id)
);

CREATE TABLE incidents (
  incident_id            BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT REFERENCES vendors(vendor_id),
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  incident_type          TEXT,                  -- delivery, quality, cyber, compliance, financial
  severity               TEXT,
  incident_date          DATE,
  summary                TEXT,
  root_cause             TEXT,
  impact_amount          NUMERIC,
  source_doc_id          BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE audit_findings (
  finding_id             BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT REFERENCES vendors(vendor_id),
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  audit_date             DATE,
  finding_type           TEXT,                  -- compliance, quality, cyber, ESG
  severity               TEXT,
  finding_text           TEXT,
  remediation_due_date   DATE,
  remediation_status     TEXT,
  source_doc_id          BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE risk_signals (
  risk_signal_id         BIGSERIAL PRIMARY KEY,
  vendor_id              BIGINT REFERENCES vendors(vendor_id),
  site_id                BIGINT REFERENCES vendor_sites(site_id),
  signal_type            TEXT,                  -- sanctions, bankruptcy, breach, strike, flood, war
  signal_source          TEXT,                  -- document, external_feed, analyst
  signal_date            DATE,
  severity               TEXT,
  description            TEXT,
  confidence             REAL,
  source_doc_id          BIGINT,
  metadata               JSONB DEFAULT '{}'::jsonb
);
```

This schema directly supports questions about expiring contracts, missed obligations, SLA breaches, certification gaps, incident patterns, sole-source exposure, and vendor concentration.[^1]

## Wiki structure

Your wiki should revolve around vendor intelligence, not just generic summaries. Procurement contract management works best when obligations, performance, renewals, and risks are visible and continuously tracked rather than buried in PDFs.[^1]

Suggested structure:

```text
wiki/
  vendors/
    acme-corp.md
  contracts/
    msa-acme-2025.md
  risks/
    acme-risk-profile.md
  timelines/
    acme-timeline.md
  products/
    battery-cell-x12.md
  materials/
    lithium-carbonate.md
  dashboards/
    expiring-contracts.md
    expiring-certifications.md
    overdue-obligations.md
    single-source-risk.md
    high-risk-vendors.md
    geopolitical-exposure.md
  contradictions/
    acme-contract-vs-operations.md
  log.md
```

**Vendor page template**

```yaml
---
type: vendor
vendor_id: 42
criticality: strategic
tier_level: 1
countries: [CN, VN]
active_contracts: [C-1001, C-1044]
products: [battery-cell-x12]
materials: [lithium-carbonate]
open_risks:
  - cyber
  - geopolitical
last_updated: 2026-05-23
---

# Vendor summary
# Key contracts
# Sites and countries
# Performance history
# Risk profile
# Certifications
# Open obligations
# Incidents and findings
# Contradictions
# Sources
```


## Ingestion pipeline

For supply-chain documents, add domain-specific extraction stages because contracts and risk files contain operationally important clauses and dates that generic chunking alone will not capture.[^1]

Pipeline:

1. **Classify document**

- contract, amendment, SOW, PO, invoice, shipment notice, certificate, audit report, scorecard, incident report, email.[^1]

2. **Parse and chunk**

- preserve section headings, tables, clause numbers, appendix references.

3. **Entity linking**

- match vendor names, aliases, sites, products, materials, contract IDs, PO numbers.

4. **Clause extraction**

- scope, SLA, delivery timeline, payment terms, penalties, liability caps, audit rights, termination, renewal, confidentiality, cybersecurity, ESG, insurance.[^2][^1]

5. **Obligation extraction**

- who must do what by when; recurrence; breach/penalty.

6. **Risk extraction**

- financial distress, sanctions, breach news, labor issues, late delivery, quality failures, geopolitical exposure, natural disaster exposure, certification expiry.[^1]

7. **Write outputs**

- SQL rows for exact facts,
- vector chunks for retrieval,
- wiki updates for vendor/contract/timeline/risk pages.[^1]


## Router rules

You should use supply-chain-specific routing because questions often mix counts, clauses, operational evidence, and dependency reasoning.


| Question pattern | Primary path | Secondary path |
| :-- | :-- | :-- |
| “How many vendors have expiring ISO certs in 60 days?” | SQL. | Retrieval for certificate evidence. |
| “What are Acme’s renewal terms?” | Contract clause lookup in SQL.[^1] | Retrieval for exact language. |
| “Why is Acme high risk?” | Wiki risk page. | Retrieval for incidents/audits/news. |
| “Which products are sole-sourced from vendors in region X?” | SQL + relationship tables.[^3][^4] | Wiki for narrative impact. |
| “Show all SLA breaches for vendor Y and root causes” | SQL for counts/dates.[^1] | Retrieval + wiki timeline for root-cause synthesis. |
| “What changed with vendor Z in the last year?” | Wiki timeline. | SQL incidents/obligations + retrieval evidence. |

## Important additions

I would add two important things beyond the earlier blueprint.

First, add a **relationship layer** for multi-tier exposure. Knowledge graphs are especially useful in supply chains because they model relationships among suppliers, facilities, materials, products, and flows, making it easier to identify hidden dependencies, vulnerabilities, and alternatives. You do not need a full graph DB on day one, but you should at least model link tables so you can traverse vendor → site → material → product → customer program.[^3][^4][^5]

Second, add **risk scoring pipelines**. Supplier risk management is a continuous cycle of identifying, evaluating, prioritizing, mitigating, and monitoring supplier risks, not a one-time document extraction task. So keep calculated scores and score components separately:

- inherent risk,
- residual risk,
- latest signals,
- overdue obligations,
- open findings,
- certification expiry proximity,
- concentration / single-source exposure.


## Example questions

With this blueprint, the system can answer:

- “How many strategic vendors have contracts expiring in Q3?”[^1]
- “Which vendors have audit rights in contract but no audit in last 12 months?”[^1]
- “List sole-source materials supplied from flood-prone sites.”[^4][^3]
- “Which high-risk vendors also handle customer PII?”
- “Summarize delivery failures for Acme and whether SLA penalties were enforceable.”[^1]


## Recommendation

So yes, the architecture should be adapted into a **vendor intelligence + contract intelligence + risk monitoring** platform. The most important changes are:

- richer supply-chain tables,
- clause and obligation extraction,
- vendor-centric wiki pages,
- relationship modeling for multi-tier dependencies,
- continuous risk scoring and monitoring.[^4][^1]

The best implementation order is:

1. Contracts + vendors + obligations.[^1]
2. Certifications + incidents + audit findings.
3. Products/materials/sites relationships.[^5][^4]
4. Risk scoring + dashboards.

Would you like me to do the next step as a **complete technical design doc** with:

1. table DDL,
2. wiki markdown templates,
3. extraction JSON schemas,
4. LangGraph router pseudocode,
5. sample supply-chain queries and answers?
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2

[^2]: https://www.llamaindex.ai/glossary/contract-clause-extraction

[^3]: https://eccenca.com/blog/article/how-ai-and-knowledge-graphs-strengthen-supply-chain-resilience

[^4]: https://www.expresscomputer.in/guest-blogs/how-knowledge-graphs-can-transform-supply-chain-management-in-india/90559/

[^5]: https://storymaps.arcgis.com/stories/2ae0b6a6ee114618b9db8cb35440b71d

[^6]: https://secureframe.com/blog/supply-chain-risk-assessment

[^7]: https://www.ivalua.com/blog/supply-chain-risk-management/

[^8]: https://www.metricstream.com/insights/5-best-practices-VRM.htm

[^9]: https://panorays.com/blog/vendor-risk-management-complete-guide/

[^10]: https://www.linkedin.com/top-content/supply-chain-management/supplier-code-of-conduct-development/supplier-conduct-risk-mitigation/

[^11]: https://www.sirion.ai/library/contract-management/contract-data-management/

[^12]: https://www.waru.edu/acquipedia-article/supply-chain-risk-management-scrm-overview

[^13]: https://www.ivalua.com/blog/procurement-contracts/

[^14]: https://www.gep.com/info-guide/supplier-risk-management-a-comprehensive-guide

[^15]: https://hitrustalliance.net/blog/third-party-risk-management-for-vendors

[^16]: https://www.malbek.io/blog/contract-data-extraction-implementation-readiness

