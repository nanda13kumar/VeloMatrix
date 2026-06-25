#!/usr/bin/env python3
"""
Seed gitignored local workspace with FOUR realistic demo products:
  1. AdminService   — tier-2 internal; complacency & security debt
  2. APIGateway     — tier-0 platform perimeter; mostly exemplary
  3. ProductCatalog — tier-1 commerce; fast delivery, DB/DR cracks
  4. PaymentService — tier-0 PCI-scoped; security/DR strong, DORA constrained
Run from repo root:  python3 scripts/seed_local_demo.py
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from domain.enums import QueryDialect
from domain.schemas import (
    BindingSpec, CatalogProduct, CatalogRoot,
    DimensionTemplate, ProductBindingsFile, SubDimensionTemplate,
)

POLICY = "vm-policy-seed-2026-06-12"

# ── helpers ───────────────────────────────────────────────────────────────────

def _sub(sid, title, desc, w, *, nn=False, ts="", ir="", wr="", go="", gs=None):
    return SubDimensionTemplate(
        id=sid, title=title, description=desc, weight=w,
        non_negotiable=nn, tradeoff_summary=ts,
        importance_rationale=ir, weight_rationale=wr,
        guide_overview=go, guide_signals=gs or [],
    )

def sb(score, sources, conf="medium"):
    return BindingSpec(
        connector_id="static", dialect=QueryDialect.SQL, query_body="",
        parameters={"score_0_10": score, "evidence_sources": sources, "confidence": conf},
        schedule_cron="0 */6 * * *",
    )

# ── dimension templates ───────────────────────────────────────────────────────

def dim_req():
    return DimensionTemplate(
        id="requirements", title="Requirement Management",
        description="Traceability, refinement hygiene, change control, and DoR/DoD evidence.",
        weight=0.10,
        dimension_importance="Poor requirements flow creates downstream rework; caps maximum delivery quality.",
        subdimensions=[
            _sub("req-trace","Traceability (epic→code→test)",
                 "Tickets link to commits/PRs/tests; avoids orphan work.",0.9,nn=True,
                 ts="Tooling tax vs auditability — automate links via VCS hooks.",
                 ir="Incident response and audits require reconstructing intent quickly.",
                 wr="High weight: missing traceability invalidates many other signals.",
                 go="Bidirectional links in Jira/GitHub Projects to PRs and test cases.",
                 gs=["Issue keys in commits","PR template checklists","Test case IDs in CI"]),
            _sub("req-dor-dod","DoR / DoD enforcement",
                 "Stories not pulled until ready; releases not marked done without evidence.",0.7,
                 ts="Strict gates reduce thrash but slow intake — use lightweight DoR for spikes.",
                 ir="Prevents fake velocity: work started without acceptance criteria.",
                 wr="0.7 — reflects team maturity variance.",
                 go="Inspect board policies, PR merge rules, and release checklists.",
                 gs=["Template fields enforced","Release notes automation","Blocked column analytics"]),
            _sub("req-change-ctrl","Change control & impact analysis",
                 "Non-trivial changes have documented impact analysis and stakeholder sign-off.",0.6,
                 ts="Over-process kills velocity — scope to tier-0 and cross-team changes.",
                 ir="Unreviewed changes cause cascade failures across shared platforms.",
                 wr="0.6 — good CI/CD partially compensates for process gaps.",
                 go="RFC/ADR process, CAB scope, and automated dependency-change detection.",
                 gs=["ADR/RFC count","CAB scope definition","Automated breaking-change alerts"]),
        ],
    )

def dim_avail():
    return DimensionTemplate(
        id="availability", title="Availability & SRE",
        description="SLIs/SLOs, error budgets, alerting quality, capacity planning, and BCP hooks.",
        weight=0.15,
        dimension_importance="Customer trust is tied to measured reliability. Without SLOs, on-call is noise.",
        subdimensions=[
            _sub("avail-slo","SLO definitions & user-centric SLIs",
                 "SLOs per critical journey; SLIs match user pain, not only infra CPU.",1.0,nn=True,
                 ts="Tighter SLOs burn budget faster — negotiate scope with product.",
                 ir="Without SLOs, on-call reacts to noise and severity is subjective.",
                 wr="Maximum sub-weight: SLOs anchor the entire availability story.",
                 go="Multi-window burn alerts; SLO as code where possible.",
                 gs=["SLO YAML in repo","Burn-rate alerts","Customer journey map"]),
            _sub("avail-budget","Error budget policy",
                 "Budget exhaustion gates risky change (deploy freeze, feature flags).",0.85,
                 ts="Hard freezes hurt roadmap — use progressive delivery not binary stop.",
                 ir="Budget policy converts metrics into decisions, not just dashboards.",
                 wr="Below SLI quality — policy without SLIs is hollow.",
                 go="Policy documented and automated (CI checks, launch tiers).",
                 gs=["Budget dashboards","Change advisory linkage","Postmortem triggers"]),
            _sub("avail-alerting","Alerting quality & on-call hygiene",
                 "Alerts are actionable, routed correctly, and not silenced long-term.",0.8,
                 ts="Too few = blind spots; too many = fatigue and suppression.",
                 ir="Alert quality determines MTTR. Noisy paging destroys morale.",
                 wr="0.8 — bad alerting directly inflates MTTR.",
                 go="Measure alert-to-page ratio, suppression rate, and MTTA.",
                 gs=["Alert-to-page ratio","On-call load metrics","Resolved-without-action rate"]),
            _sub("avail-bcp","BCP / dependency mapping",
                 "Critical upstreams documented; failover paths exercised on cadence.",0.65,
                 ts="Full BIA per microservice is expensive — tier by blast radius.",
                 ir="Prevents unknown single points of failure outside your cluster.",
                 wr="0.65 — many teams defer BCP until after first major outage.",
                 go="Service catalog dependency graphs and vendor SLAs.",
                 gs=["Runbooks","Game days","Chaos scoped to tier-0"]),
        ],
    )

def dim_dora():
    return DimensionTemplate(
        id="dora", title="DORA & Delivery",
        description="Deployment frequency, lead time, change failure rate, and time to restore.",
        weight=0.15,
        dimension_importance="Throughput without stability is debt. This dimension pairs both sides of the delivery coin.",
        subdimensions=[
            _sub("dora-df","Deployment frequency",
                 "Production deploy events per week from canonical pipeline metadata.",0.75,
                 ts="More deploys without quality gates inflate the metric.",
                 ir="Proxy for batch size and integration risk.",
                 wr="0.75 — must be paired with CFR to avoid gaming.",
                 go="Pipeline IDs and environment tags over raw commits.",
                 gs=["GitHub Actions / Jenkins audit logs","Argo CD history","Loki deploy events"]),
            _sub("dora-cfr","Change failure rate",
                 "Incidents or rollbacks correlated to releases (trailing 30-day window).",0.95,
                 ts="CFR is sensitive to incident taxonomy — garbage labels → garbage signal.",
                 ir="Directly captures stability of the change process.",
                 wr="Near-non-negotiable for customer-impacting services.",
                 go="Join deploy markers with incident timelines; exclude unrelated infra noise.",
                 gs=["PagerDuty/Opsgenie","ITSM categories","Tagged hotfixes"]),
            _sub("dora-lt","Lead time for changes",
                 "Commit → production latency (p50 and p95).",0.7,
                 ts="Monorepos and shared pipelines skew per-service attribution.",
                 ir="Long tails hide blocked teams even if median looks fine.",
                 wr="0.7 — measurement complexity and toolchain variance.",
                 go="VCS + CI timestamps sliced by service ownership tags.",
                 gs=["PR merge time","Build queue depth","Approval wait states"]),
            _sub("dora-mttr","Mean time to restore",
                 "P50 time from incident declared to service restored to SLO.",0.85,
                 ts="MTTR is inflated by poor runbooks and missing observability — both fixable.",
                 ir="Customers feel MTTR directly; most business-visible DORA metric.",
                 wr="0.85 — restoration speed determines blast radius.",
                 go="PagerDuty/Opsgenie from open to resolved; correlate with rollback.",
                 gs=["Incident duration percentiles","Rollback rate","Escalation chain depth"]),
        ],
    )

def dim_security():
    return DimensionTemplate(
        id="security", title="Security & Compliance",
        description="SAST/DAST/SCA, container scan, SBOM, secrets hygiene, IAM, runtime posture, and control evidence.",
        weight=0.20,
        dimension_importance="Security is a non-negotiable floor. A single exploit can end a product's reputation.",
        subdimensions=[
            _sub("sec-sast","SAST coverage & critical findings aging",
                 "Static analysis on default branch; criticals remediated within policy SLA.",1.0,nn=True,
                 ts="Wrong rule tuning creates fatigue — tune with AppSec, never silence.",
                 ir="Earliest and cheapest vulnerability discovery in the SDLC.",
                 wr="Maximum sub-weight within Security pillar.",
                 go="SonarQube/Mend/GitHub Advanced Security; gate merges on new criticals.",
                 gs=["PR annotations","Quality gate history","Suppressions audit"]),
            _sub("sec-sca","SCA / SBOM & container scan",
                 "Exploitable CVE focus; SBOM attestation in CI; Trivy/Snyk on all images.",0.9,nn=True,
                 ts="SBOM noise vs signal — prioritise reachable vulns via EPSS score.",
                 ir="Supply chain attacks are mainstream threat vectors.",
                 wr="0.9 — direct complement to SAST, different attack surface.",
                 go="Base image refresh cadence and merge-bot dependency PRs.",
                 gs=["CycloneDX in CI","Image signing (cosign)","Registry scan cadence"]),
            _sub("sec-iam","IAM & secrets hygiene",
                 "No long-lived admin keys; secrets manager adoption; quarterly access review.",0.85,nn=True,
                 ts="JIT access adds latency — compensate with break-glass paths.",
                 ir="Credential theft is the top breach pattern globally.",
                 wr="0.85 — raised to non-negotiable level for tier-0.",
                 go="CloudTrail/IAM Access Analyzer + vault audit + secret scanning.",
                 gs=["MFA enforcement rate","Key age reports","JIT role adoption"]),
            _sub("sec-dast","DAST / runtime API scanning",
                 "Automated dynamic tests against staging; findings in security backlog.",0.7,
                 ts="DAST coverage depends on staging parity — gaps cause false negatives.",
                 ir="SAST misses runtime-only vulns like authentication bypass.",
                 wr="0.7 — important but harder to operationalise.",
                 go="OWASP ZAP / Burp DAST in CI nightly; gate on critical findings.",
                 gs=["DAST run frequency","Critical findings SLA","Staging parity score"]),
            _sub("sec-runtime","Runtime container & workload posture",
                 "Falco/Defender rules active; anomalous syscalls alert to SOC.",0.65,
                 ts="Runtime agents add latency and overhead — tune profiles carefully.",
                 ir="Post-exploit detection is the last line of defence before data exfil.",
                 wr="0.65 — maturity ladder; many teams address static posture first.",
                 go="Falco rules in IaC; eBPF-based syscall monitoring with SOC integration.",
                 gs=["Falco rule count","Alert→SOC ticket SLA","Privileged container count"]),
        ],
    )

def dim_testing():
    return DimensionTemplate(
        id="testing", title="Testing & Quality Gates",
        description="CI reliability, test pyramid, contract tests, performance gates, and coverage governance.",
        weight=0.10,
        dimension_importance="Tests encode trust in change velocity. Without them, every deploy is a gamble.",
        subdimensions=[
            _sub("test-ci","CI reliability & flake management",
                 "Flake rate <2%; quarantined tests tracked to closure within policy SLA.",0.9,
                 ts="Over-quarantining hides risk — cap quarantine age at 14 days.",
                 ir="Flaky CI erodes trust in green builds and hides regressions.",
                 wr="0.9 — prerequisite for meaningful coverage and gate metrics.",
                 go="Track rerun rate, dominant failing jobs, and queue latency.",
                 gs=["JUnit reports","Build analytics","Auto-deflake bots"]),
            _sub("test-coverage","Code coverage & mutation baseline",
                 "Coverage tracked per service with regression gates; mutation score for critical paths.",0.7,
                 ts="Coverage % alone is vanity — pair with mutation and branch coverage.",
                 ir="Low coverage on auth/payment paths is high risk.",
                 wr="0.7 — important but not as foundational as CI reliability.",
                 go="Jacoco/Istanbul/pytest-cov + Pitest; fail PR on coverage regression.",
                 gs=["Coverage delta on PR","Mutation score trend","Uncovered critical paths"]),
            _sub("test-contract","Contract / API compatibility tests",
                 "Consumer-driven contracts or schema snapshot tests for all public APIs.",0.65,
                 ts="Contracts cost authoring time — prioritise tier-0 interfaces first.",
                 ir="Prevents silent breaking changes in polyglot microservice estates.",
                 wr="0.65 — not every service needs Pact on day one.",
                 go="Pact/Schemathesis/Postman collections in CI.",
                 gs=["Breaking change detection","Schema versioning","Consumer Pact matrix"]),
            _sub("test-perf","Performance & load regression gates",
                 "Baseline p95 latency tested in CI nightly; regressions block merge.",0.6,
                 ts="Full load tests in CI are expensive — use micro-benchmarks for hot paths.",
                 ir="Performance regressions ship silently and compound over releases.",
                 wr="0.6 — relevant for all user-facing services.",
                 go="k6/Gatling/JMeter in nightly; alert on >10% p95 regression vs baseline.",
                 gs=["Baseline p95 in repo","Regression gate in pipeline","Flame graph cadence"]),
        ],
    )

def dim_finops():
    return DimensionTemplate(
        id="finops", title="Cost & Budget (FinOps)",
        description="Allocation quality, rightsizing lifecycle, anomaly detection, and exec review cadence.",
        weight=0.08,
        dimension_importance="Runaway cloud spend is an operational and strategic risk. FinOps maturity predicts sustainability.",
        subdimensions=[
            _sub("fin-alloc","Cost allocation & chargeback/showback",
                 "Every major service has tagging-based cost attribution (team/product/env).",0.85,
                 ts="Perfect allocation has diminishing returns — target top 80% spend first.",
                 ir="Unattributed spend cannot be governed or optimised.",
                 wr="High weight: without allocation, all other FinOps is guesswork.",
                 go="Cloud billing exports + mandatory tag policies + Cloudability/Apptio.",
                 gs=["Tag compliance %","Monthly anomaly reports","Budget alerts"]),
            _sub("fin-rightsize","Rightsizing recommendations closed-loop",
                 "Recommendations from cloud advisor/Kubecost tracked to ticket closure.",0.75,
                 ts="Aggressive rightsizing without perf tests harms latency SLOs.",
                 ir="Closes insight-to-action loop — the missing step in most FinOps programmes.",
                 wr="0.75 — pairs with allocation quality.",
                 go="Integrate recommendations with Jira/Linear; track MTTR on savings tasks.",
                 gs=["Open savings tickets","Rollback rate after resize","Monthly savings realised"]),
            _sub("fin-anomaly","Cost anomaly detection & response",
                 "Automated alerts on spend spikes; runbooks for common causes.",0.6,
                 ts="Too sensitive = noise; too loose = monthly surprise bills.",
                 ir="Anomalies caught within hours cost 10× less than month-end surprises.",
                 wr="0.6 — complements allocation; less critical than tagging foundation.",
                 go="AWS Cost Anomaly Detection / GCP Budget Alerts with runbook linkage.",
                 gs=["Anomaly→ticket SLA","False positive rate","P95 resolution time"]),
        ],
    )

def dim_database():
    return DimensionTemplate(
        id="database", title="Database Maturity",
        description="Backup/RPO validation, migration safety, least-privilege access, and performance baselines.",
        weight=0.10,
        dimension_importance="Data loss or schema drift incidents are the most expensive and reputation-damaging failure class.",
        subdimensions=[
            _sub("db-backup","Backup & restore validation",
                 "Automated backups with tested restores; documented RPO/RTO per environment.",1.0,nn=True,
                 ts="Frequent full restores cost I/O — use logical subsets for large stores.",
                 ir="Untested backups are Schrödinger backups. RTO unknown until you need it.",
                 wr="Maximum weight — the non-negotiable floor for any production database.",
                 go="Restore drills in change calendar; alert on backup job failures.",
                 gs=["PITR enabled","Last restore drill date","Backup monitoring alerts"]),
            _sub("db-migrations","Schema migration safety",
                 "Expand/contract patterns; zero-downtime DDL; rollback scripts in every PR.",0.85,nn=True,
                 ts="Heavy migration tooling slows small teams — still need minimum guardrails.",
                 ir="Schema mistakes are a common outage class, often unrecoverable without restore.",
                 wr="0.85 — near-non-negotiable for services with production traffic.",
                 go="Flyway/Liquibase reviews; online DDL checks; shadow traffic.",
                 gs=["Migration CI gate","Backwards-compatible releases","Lock contention metrics"]),
            _sub("db-access","Least-privilege DB access & audit",
                 "App uses dedicated service accounts; no shared passwords; query audit enabled.",0.75,
                 ts="Granular roles add management overhead — amortise via secrets manager.",
                 ir="Over-privileged DB accounts turn any RCE into full data exfil.",
                 wr="0.75 — pairs with IAM posture in Security dimension.",
                 go="Service account per microservice; rotate via Vault/AWS Secrets Manager.",
                 gs=["Shared password count = 0","Audit log enabled","Secrets manager adoption"]),
            _sub("db-perf","Performance baseline & query governance",
                 "Slow-query log analysed; P95 query latency baselined; N+1 detected in CI.",0.6,
                 ts="Full explain-plan CI gates are expensive — focus on top-5 slowest queries.",
                 ir="Undetected query regressions are a common SLO violation cause.",
                 wr="0.6 — important but addressable incrementally.",
                 go="PgBadger/PMM/Datadog APM slow-query dashboards; ORM N+1 detection.",
                 gs=["Slow query alerting","Index coverage rate","Query regression gate"]),
        ],
    )

def dim_dr():
    return DimensionTemplate(
        id="dr", title="DR & Resilience Risk",
        description="RTO/RPO targets, restore drills, multi-site readiness, chaos experiments, and tabletops.",
        weight=0.07,
        dimension_importance="DR is insurance — invisible until it fails catastrophically during an actual incident.",
        subdimensions=[
            _sub("dr-rpo","RPO / RTO clarity & validated tests",
                 "Documented targets per tier; game days prove numbers with observed data.",0.95,nn=True,
                 ts="Multi-region active/active is expensive — align DR spend to tiering.",
                 ir="Executives underwrite risk with these numbers; untested targets are fiction.",
                 wr="Highest within DR — the foundational contract with the business.",
                 go="Cross-check backups, replication lag, and failover runbooks vs stated targets.",
                 gs=["Last successful drill","Observed failover vs target","Data loss window tests"]),
            _sub("dr-runbooks","DR runbooks & on-call readiness",
                 "Step-by-step runbooks for all critical failure modes; on-call can execute without author.",0.8,
                 ts="Over-detailed runbooks go stale — keep short and automate the steps.",
                 ir="MTTR is dominated by confusion. Runbooks are the antidote.",
                 wr="0.8 — missing runbooks inflate MTTR directly.",
                 go="Runbooks in repo, linked from alerts; tested in tabletops quarterly.",
                 gs=["Runbook completeness audit","Tabletop exercise cadence","Alert→runbook link rate"]),
            _sub("dr-chaos","Chaos / fault injection cadence",
                 "Controlled fault experiments validate graceful degradation.",0.55,
                 ts="Chaos without SLOs is theater — pair with observable metrics.",
                 ir="Finds unknown dependencies and assumptions before customers do.",
                 wr="0.55 — maturity ladder; not all teams ready early.",
                 go="Gremlin/Litmus/Chaos Mesh with blast-radius controls and abort criteria.",
                 gs=["Blast radius tags","Abort criteria defined","Dashboards during drills"]),
        ],
    )

# ── catalog ───────────────────────────────────────────────────────────────────

def build_catalog() -> CatalogRoot:
    # Shared dimension order per product reflects their risk prioritisation
    products = [
        CatalogProduct(
            id="admin-service", name="AdminService", tier="tier2", team="Platform",
            dimensions=[dim_security(), dim_dora(), dim_testing(), dim_req(),
                        dim_avail(), dim_finops(), dim_database(), dim_dr()],
        ),
        CatalogProduct(
            id="api-gateway", name="APIGateway", tier="tier0", team="Platform",
            dimensions=[dim_security(), dim_avail(), dim_dora(), dim_dr(),
                        dim_testing(), dim_database(), dim_finops(), dim_req()],
        ),
        CatalogProduct(
            id="product-catalog", name="ProductCatalog", tier="tier1", team="Commerce",
            dimensions=[dim_dora(), dim_testing(), dim_req(), dim_security(),
                        dim_avail(), dim_database(), dim_finops(), dim_dr()],
        ),
        CatalogProduct(
            id="payment-service", name="PaymentService", tier="tier0", team="Payments",
            dimensions=[dim_security(), dim_dr(), dim_avail(), dim_database(),
                        dim_dora(), dim_testing(), dim_req(), dim_finops()],
        ),
    ]
    return CatalogRoot(policy_version=POLICY, products=products)


# ── scores ────────────────────────────────────────────────────────────────────
# Each product tells a realistic story:
#   AdminService   — internal complacency: mediocre security, weak SRE, OK delivery, poor DR
#   APIGateway     — platform discipline: strong security, strong avail, good DORA, solid DR
#   ProductCatalog — commerce velocity: fast DORA, good testing, but weak DB safety + DR
#   PaymentService — PCI-driven: exemplary security + DR, constrained DORA (CAB overhead)

SCORES = {
    "admin-service": {
        # Security — internal tool mindset: SAST never configured, no SBOM
        "sec-sast": 2.8,   # criticals open >30 days; SonarQube not in pipeline
        "sec-sca": 3.1,    # no SBOM; trivy only in ad-hoc scans
        "sec-iam": 4.2,    # shared DB passwords still in use; vault partially adopted
        "sec-dast": 1.5,   # no DAST ever run
        "sec-runtime": 2.0,# no Falco; no runtime monitoring
        # DORA — frequent but chaotic deploys
        "dora-df": 6.5,    # deploys often but without discipline
        "dora-cfr": 3.8,   # ~25% of deploys cause a hotfix
        "dora-lt": 5.5,    # moderate lead time
        "dora-mttr": 4.0,  # slow restore; no runbooks
        # Testing — some unit tests, no contracts, CI flaky
        "test-ci": 5.2,    # 8% flake rate; no quarantine policy
        "test-coverage": 4.8, # ~45% coverage, no regression gate
        "test-contract": 2.5, # zero contract tests
        "test-perf": 2.0,  # no perf baseline
        # Requirements — ad-hoc Jira usage
        "req-trace": 4.5,  # some tickets linked, most not
        "req-dor-dod": 3.5,# informal DoR, no DoD
        "req-change-ctrl": 3.0, # no RFC process; verbal sign-offs
        # Availability — SLOs exist on paper only
        "avail-slo": 3.2,  # SLO defined in a doc nobody reads
        "avail-budget": 2.5,# no error budget enforcement
        "avail-alerting": 4.0,# default cloud alerts, no tuning
        "avail-bcp": 2.8,  # no BCP documented
        # FinOps — cost centre tag missing
        "fin-alloc": 3.5,  # 60% tagged, no chargeback
        "fin-rightsize": 3.0,# recommendations seen, never actioned
        "fin-anomaly": 2.5,# no anomaly detection configured
        # Database — SQL Server; DBA single point of failure
        "db-backup": 6.0,  # backups run, but restores never tested
        "db-migrations": 3.5,# manual SQL scripts, no CI gate
        "db-access": 3.8,  # shared sa account still used in one service
        "db-perf": 4.5,    # slow-query log enabled, nobody reviews it
        # DR — completely untested
        "dr-rpo": 2.5,     # targets in a slide deck; never drilled
        "dr-runbooks": 3.0,# partial runbooks from 2023
        "dr-chaos": 1.0,   # no chaos experiments ever
    },
    "api-gateway": {
        # Security — perimeter service; highest scrutiny
        "sec-sast": 8.8,   # SonarQube + GHAS; zero open criticals
        "sec-sca": 8.5,    # Snyk + Trivy; SBOM in every release
        "sec-iam": 8.0,    # vault + JIT roles; quarterly access review done
        "sec-dast": 7.2,   # ZAP in nightly; findings triaged within 48h
        "sec-runtime": 7.5,# Falco rules tuned; SOC integration active
        # DORA — mature CI/CD; multiple deploys per day
        "dora-df": 9.0,    # 15 deploys/week; canary + blue-green
        "dora-cfr": 8.2,   # CFR ~4%; robust rollback automation
        "dora-lt": 8.5,    # p50 lead time ~2h
        "dora-mttr": 8.0,  # MTTR p50 ~18min; runbooks linked to alerts
        # Testing — comprehensive but perf gate missing
        "test-ci": 8.5,    # <1% flake; quarantine SLA enforced
        "test-coverage": 7.8,# 78% coverage; mutation baseline set
        "test-contract": 8.0,# Pact matrix for all downstream consumers
        "test-perf": 6.5,  # load tests exist but not blocking pipeline yet
        # Requirements — ADR process mature
        "req-trace": 8.5,  # every PR links to ticket and test case
        "req-dor-dod": 7.5,# DoR/DoD enforced in tooling
        "req-change-ctrl": 8.0,# RFC process for breaking changes; ADRs in repo
        # Availability — SLO 99.95%; multi-window burn alerts
        "avail-slo": 9.2,  # 3 SLOs defined; SLO-as-code via Sloth
        "avail-budget": 8.5,# budget exhaustion triggers CAB review automatically
        "avail-alerting": 8.8,# <5% noise rate; pages are actionable
        "avail-bcp": 7.5,  # upstreams mapped; failover tested annually
        # FinOps — well tagged, rightsizing in progress
        "fin-alloc": 8.5,  # 97% tagged; showback dashboard live
        "fin-rightsize": 7.0,# recommendations tracked; some delayed
        "fin-anomaly": 7.5,# anomaly alerts configured; 2 false positives/month
        # Database — PostgreSQL; fully managed RDS
        "db-backup": 9.0,  # PITR; restore drilled quarterly
        "db-migrations": 8.5,# Flyway + CI gate; expand/contract enforced
        "db-access": 8.0,  # per-service roles; vault rotation
        "db-perf": 7.5,    # slow-query dashboards; p95 gated in CI
        # DR — tested bi-annually; RTO target 15min
        "dr-rpo": 8.5,     # RPO 5min achieved in last drill
        "dr-runbooks": 8.0,# runbooks in repo; linked from PagerDuty
        "dr-chaos": 6.5,   # quarterly chaos days; Litmus in staging
    },
    "product-catalog": {
        # Security — reasonable but SCA/DAST gaps
        "sec-sast": 7.0,   # Sonar in CI; medium findings backlog growing
        "sec-sca": 5.5,    # Trivy in CI; SBOM not attested
        "sec-iam": 6.5,    # vault adopted; 2 legacy shared accounts remain
        "sec-dast": 4.0,   # DAST run manually quarterly
        "sec-runtime": 4.5,# Falco installed but default rules only
        # DORA — high velocity commerce team
        "dora-df": 9.2,    # 20+ deploys/week; feature flags heavy
        "dora-cfr": 6.8,   # CFR 12%; DB migration incidents inflate it
        "dora-lt": 8.0,    # p50 ~1.5h; PR review backlog managed
        "dora-mttr": 6.5,  # MTTR ~45min; runbooks exist but stale
        # Testing — good coverage, weak perf/contract
        "test-ci": 7.5,    # 3% flake rate; improving trend
        "test-coverage": 7.2,# 71% coverage; regression gate on main
        "test-contract": 5.0,# Pact only for checkout integration
        "test-perf": 4.5,  # perf tests exist; not blocking yet
        # Requirements — Jira mature; no change control RFC
        "req-trace": 7.8,  # strong Jira discipline; PR → ticket linking enforced
        "req-dor-dod": 7.0,# DoR enforced; DoD weaker
        "req-change-ctrl": 5.5,# informal for DB changes; no RFC process
        # Availability — SLO defined but budget policy weak
        "avail-slo": 7.5,  # SLO 99.9%; alerting on it
        "avail-budget": 5.8,# budget tracked but no automated gate
        "avail-alerting": 7.0,# reasonable; some alert fatigue on DB metrics
        "avail-bcp": 5.0,  # dependencies listed; not drilled
        # FinOps — active FinOps programme
        "fin-alloc": 7.5,  # 90% tagged; per-env cost breakdown
        "fin-rightsize": 6.5,# recommendations in Jira; ~70% actioned
        "fin-anomaly": 6.0,# AWS anomaly detection active; some false positives
        # Database — biggest risk area; migration incidents in history
        "db-backup": 7.0,  # backups automated; restore tested 6 months ago
        "db-migrations": 4.5,# Flyway adopted recently; 2 incidents this year
        "db-access": 5.5,  # mostly service accounts; 1 shared legacy account
        "db-perf": 5.8,    # slow-query log; no p95 CI gate yet
        # DR — never formally tested; RPO unknown in practice
        "dr-rpo": 3.5,     # RPO target stated; never drilled; replication lag unknown
        "dr-runbooks": 4.5,# partial runbooks; missing DB restore steps
        "dr-chaos": 2.5,   # no chaos experiments
    },
    "payment-service": {
        # Security — PCI-DSS drives high bar
        "sec-sast": 9.5,   # zero criticals; SLA 7-day; suppression audited weekly
        "sec-sca": 9.2,    # Snyk + Trivy; SBOM attested; base images weekly
        "sec-iam": 9.5,    # JIT roles enforced; hardware MFA; quarterly access review
        "sec-dast": 8.5,   # ZAP + Burp; nightly on staging; PCI scope in scope
        "sec-runtime": 8.8,# Falco + Defender; SOC 24/7; anomaly in minutes
        # DORA — CAB overhead caps deploy frequency; quality compensates
        "dora-df": 5.5,    # ~2 deploys/week; CAB approval required
        "dora-cfr": 9.0,   # CFR ~1.5%; extensive pre-prod validation
        "dora-lt": 5.0,    # lead time ~5d p50 due to CAB cycle
        "dora-mttr": 9.2,  # MTTR p50 ~8min; automated rollback + runbooks
        # Testing — comprehensive; mutation + perf gated
        "test-ci": 9.0,    # <0.5% flake; quarantine policy strictly enforced
        "test-coverage": 8.5,# 85% coverage; mutation gate on payment paths
        "test-contract": 8.8,# Pact matrix for all card network integrations
        "test-perf": 8.5,  # p99 latency gated; load test in every release
        # Requirements — formal change management
        "req-trace": 9.0,  # mandatory traceability; audited for PCI
        "req-dor-dod": 8.5,# strict DoR/DoD; PCI control mapping required
        "req-change-ctrl": 9.0,# RFC + CAB for all changes; signed artefacts
        # Availability — 99.99% SLA; SLO-as-code
        "avail-slo": 9.5,  # 4 SLOs; burn alerts; automated rollback at 5%
        "avail-budget": 9.0,# budget exhaustion = auto-freeze; board-level visibility
        "avail-alerting": 9.2,# <1% noise; pages are always actionable
        "avail-bcp": 8.5,  # upstreams + card networks mapped; tested annually
        # FinOps — strict cost governance for PCI environment
        "fin-alloc": 8.8,  # 99% tagged; per-PCI-scope cost breakdown
        "fin-rightsize": 7.5,# rightsizing conservative; perf tested before every resize
        "fin-anomaly": 8.5,# anomaly detection + SIEM integration
        # Database — Oracle + Aurora; strict DBA controls
        "db-backup": 9.8,  # PITR + logical backups; restore drilled monthly
        "db-migrations": 9.0,# formal migration review process; rollback mandatory
        "db-access": 9.5,  # zero shared accounts; Vault + hardware tokens
        "db-perf": 8.0,    # PMM dashboards; p99 query gate in CI
        # DR — bi-annual full DR test with observed RTO/RPO
        "dr-rpo": 9.5,     # RPO 30s; RTO 5min; last drill passed
        "dr-runbooks": 9.2,# comprehensive runbooks; tabletop quarterly; PCI evidence
        "dr-chaos": 7.0,   # chaos in pre-prod; blast radius strictly controlled
    },
}

SOURCES = {
    "sec": ["sonarqube","snyk","trivy","github_advanced_security","falco"],
    "dora": ["github_actions","loki","pagerduty","argocd"],
    "test": ["github_actions","junit","sonarqube"],
    "req": ["jira","github_projects"],
    "avail": ["prometheus","grafana","sloth","pagerduty"],
    "fin": ["aws_cur","kubecost","cloudability"],
    "db": ["rds_audit","flyway_ci","datadog_apm"],
    "dr": ["runbooks_repo","dr_drill_calendar","litmus_chaos"],
}

def _sources(sid):
    prefix = sid.split("-")[0]
    return SOURCES.get(prefix, ["static"])

# ── bindings ──────────────────────────────────────────────────────────────────

def _confidence(score):
    if score >= 8.0: return "high"
    if score >= 5.5: return "medium"
    return "low"

def build_bindings(catalog: CatalogRoot) -> ProductBindingsFile:
    out = {}
    for prod in catalog.products:
        pmap = {}
        prod_scores = SCORES.get(prod.id, {})
        for dim in prod.dimensions:
            for sub in dim.subdimensions:
                sc = prod_scores.get(sub.id, 5.5)
                pmap[sub.id] = sb(sc, _sources(sub.id), _confidence(sc))
        out[prod.id] = pmap
    return ProductBindingsFile(version="1", bindings=out)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    dest = ROOT / "local" / "demo-data"
    dest.mkdir(parents=True, exist_ok=True)

    catalog  = build_catalog()
    bindings = build_bindings(catalog)

    (dest / "catalog.json").write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    (dest / "bindings.json").write_text(bindings.model_dump_json(indent=2), encoding="utf-8")

    print(f"Catalog  → {dest / 'catalog.json'}")
    print(f"Bindings → {dest / 'bindings.json'}")
    print()
    print("Products seeded:")
    for p in catalog.products:
        prod_scores = SCORES.get(p.id, {})
        avg = round(sum(prod_scores.values()) / len(prod_scores), 2) if prod_scores else "—"
        print(f"  {p.name:20s}  tier={p.tier}  team={p.team}  sub-dims={len(prod_scores)}  raw-avg≈{avg}")
    print()
    print("These paths are gitignored — safe for local demo + connector experiments.")

if __name__ == "__main__":
    main()
