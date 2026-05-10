"""
Build the DMRC HR Compendium structured JSON knowledge base.

This script encodes all 13 chapters (A–M) of the DMRC HR Compendium
(Updated November 2023, 356 pages) into a typed, structured JSON file
that can be ingested via:

    PYTHONPATH=. python scripts/ingest_policy_kb.py \\
        --file data/dmrc_hr_knowledge_base.json \\
        --document-key dmrc_hr_compendium_nov23 \\
        --title "DMRC HR Compendium November 2023" \\
        --replace

Usage:
    python scripts/build_kb.py
    python scripts/build_kb.py --out /custom/path/kb.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build() -> dict:
    kb: dict = {
        "metadata": {
            "document": "DMRC HR Compendium - Updated November 2023",
            "organization": "Delhi Metro Rail Corporation Ltd. (DMRC)",
            "total_pages": 356,
            "chapters": 13,
            "generated": "2025",
            "usage": (
                "Optimized for RAG chatbot retrieval. Each chapter has: "
                "summary_chunk (listing queries), rules (specific queries), "
                "tables (calculation queries), authority_index (approval queries), "
                "office_order_index (citation queries), cross_references (multi-chapter queries)."
            ),
        },
        "chapters": {

            # ─────────────────────────────────────────────────────────────────
            "A": {
                "chapter_id": "A",
                "chapter_title": "General Conditions of Service Rules",
                "page_range": "1-48",
                "summary": (
                    "Governs all fundamental employment conditions for DMRC employees including "
                    "classification, appointment modes, probation, performance appraisal, transfer, "
                    "resignation, retirement and superannuation."
                ),
                "key_topics": [
                    "Employee Classification", "Appointment", "Probation", "Seniority",
                    "Performance Appraisal", "Assets & Liabilities", "Hours of Work", "Holidays",
                    "Transfer", "Training", "Resignation", "VRS", "Superannuation",
                ],
                "summary_chunk": (
                    "Chapter A — General Conditions of Service Rules covers the following: "
                    "(1) Employee Classification: Non-Executive grades (Unskilled Rs.16000-50000 to "
                    "Sr.Supervisor-I Rs.50000-160000) and Executive grades (AM Rs.50000-160000 to "
                    "MD Rs.200000-370000). "
                    "(2) Appointment: 6 modes — Direct Recruitment, Deputation, Absorption, "
                    "Post-Retirement Contractual, Lateral Induction, Compassionate; minimum age 18, "
                    "maximum 28. "
                    "(3) Probation: 2 years for Non-Executive/AM/Manager; 1 year for DGM and above. "
                    "(4) Surety Bond: 3 years for all direct recruits; training cost recoverable if "
                    "employee leaves within bond period. "
                    "(5) Resignation: minimum 90-day notice. "
                    "(6) Assets & Liabilities: Annual submission by 31st March mandatory; prior "
                    "permission for transactions exceeding 2 months gross salary. "
                    "(7) APAR: Annual grading — Outstanding, Very Good, Good, Average, Below Average; "
                    "two consecutive Below Average = adverse action. "
                    "(8) Training: DMRA (Delhi Metro Rail Academy) conducts induction and advanced "
                    "training; report within 30 days of return. "
                    "(9) Higher Studies: Permission after 3 years service (2 years for DGM+); "
                    "correspondence/part-time only. "
                    "(10) Transfer: Liability anywhere in DMRC; max 6 days joining time. "
                    "(11) Holidays: 2 Restricted Holidays per year + 3 compulsory National Holidays. "
                    "(12) VRS: After 20 years service or age 50; 3-month notice. "
                    "(13) Service Review: At age 50 and 55; compulsory retirement possible. "
                    "(14) Superannuation: Age 60, last day of the month. "
                    "(15) Lien on deputation: Maximum 3 years."
                ),
                "rules": [
                    {
                        "rule_id": "A.1",
                        "rule_title": "Classification of Employees",
                        "applies_to": ["all employees"],
                        "content": (
                            "Employees classified into Non-Executive (Unskilled to Sr.Supervisor-I) "
                            "and Executive (AM to MD). Non-executives: Unskilled 16000-50000, "
                            "Semi-skilled 20000-60000, Skilled Maintainer 25000-80000, "
                            "Maintainers & Assistants 35000-110000, Supervisor-II 37000-115000, "
                            "Supervisor-I 40000-125000, Sr.Supervisor-II 46000-145000, "
                            "Sr.Supervisor-I 50000-160000. "
                            "Executives: AM 50000-160000, Manager 60000-180000, DGM 70000-200000, "
                            "Sr.DGM 80000-220000, JGM 90000-240000, AGM 100000-260000, "
                            "GM/Sr.GM/CGM 120000-280000, ED 150000-300000, Director 180000-340000, "
                            "MD 200000-370000. GM and CGM level entitled to special pay of Rs.2500/- pm."
                        ),
                        "key_points": [
                            "Two broad categories: Non-Executive and Executive",
                            "18 grades total",
                            "GM/CGM get special pay Rs.2500/month",
                            "Board-level officers may have different terms as per appointment letters",
                        ],
                        "office_orders": [],
                        "approval_authority": "Board of Directors",
                        "amounts_or_limits": "Pay range: Rs.16000-50000 to Rs.200000-370000",
                    },
                    {
                        "rule_id": "A.2",
                        "rule_title": "Appointment",
                        "applies_to": ["all employees"],
                        "content": (
                            "6 modes of intake: (a) Direct Recruitment, (b) Deputation, "
                            "(c) Absorption of Deputationists, (d) Post-Retirement Contractual Engagement, "
                            "(e) Lateral Induction, (f) Compassionate appointment. "
                            "Minimum age 18, maximum 28 for entry-level direct recruit. "
                            "Medical fitness mandatory from DMRC-nominated hospital, valid 6 months. "
                            "Surety Bond of 3 years for all direct recruits and contract employees; "
                            "training cost recoverable on early exit. "
                            "Minimum notice for resignation: 90 days."
                        ),
                        "key_points": [
                            "6 modes of intake",
                            "Min age 18, Max age 28 for direct recruit",
                            "Medical fitness from nominated hospital mandatory",
                            "Probation: 2 yrs (Non-Exec/AM/Manager), 1 yr (DGM+)",
                            "Surety bond: 3 years",
                            "Min notice for resignation: 90 days",
                        ],
                        "office_orders": [],
                        "approval_authority": "Managing Director",
                        "amounts_or_limits": "Min age 18; Max age 28; Probation 1-2 years; Notice 90 days",
                    },
                    {
                        "rule_id": "A.5",
                        "rule_title": "Performance Appraisal",
                        "applies_to": ["all employees"],
                        "content": (
                            "Annual Performance Appraisal Report (APAR) mandatory. "
                            "Appraisal period: April to March. "
                            "Grading: Outstanding, Very Good, Good, Average, Below Average. "
                            "Two consecutive Below Average ratings may lead to adverse action. "
                            "Self-appraisal submitted by employee, then assessed by Reporting Officer "
                            "and Reviewing Officer."
                        ),
                        "key_points": [
                            "APAR mandatory annually (April–March)",
                            "5 grades: Outstanding, Very Good, Good, Average, Below Average",
                            "2 consecutive Below Average → adverse action",
                            "3-tier: Self-appraisal → Reporting Officer → Reviewing Officer",
                        ],
                        "office_orders": [],
                        "approval_authority": "Reviewing Officer / HOD",
                        "amounts_or_limits": "",
                    },
                    {
                        "rule_id": "A.6",
                        "rule_title": "Assets and Liabilities",
                        "applies_to": ["all employees"],
                        "content": (
                            "Annual statement of assets and liabilities (immovable property, shares, "
                            "debentures, cash, insurance policies etc.) to be submitted by 31st March "
                            "each year. Non-submission = misconduct. Prior permission required for any "
                            "transaction exceeding 2 months' gross salary."
                        ),
                        "key_points": [
                            "Annual submission deadline: 31st March",
                            "Covers all movable and immovable assets",
                            "Non-submission = misconduct",
                            "Prior permission for transactions > 2 months gross salary",
                        ],
                        "office_orders": [],
                        "approval_authority": "Competent Authority",
                        "amounts_or_limits": "Threshold: 2 months gross salary",
                    },
                    {
                        "rule_id": "A.7",
                        "rule_title": "Hours of Work",
                        "applies_to": ["all employees"],
                        "content": (
                            "Standard: 8 hours per day, 5 days/week for office staff. "
                            "Field/O&M staff: 6 days/week. "
                            "Compensatory rest granted for work on weekly off/holidays "
                            "(Non-executives only). 30-min lunch break."
                        ),
                        "key_points": [
                            "Office: 8 hrs/day, 5 days/week",
                            "O&M/Field: 6 days/week",
                            "Compensatory rest for Non-executives only",
                        ],
                        "office_orders": [],
                        "approval_authority": "Department Head",
                        "amounts_or_limits": "8 hours/day",
                    },
                    {
                        "rule_id": "A.8",
                        "rule_title": "Holidays",
                        "applies_to": ["all employees"],
                        "content": (
                            "Employees may avail up to 2 Restricted Holidays (RH) per year from the "
                            "declared list. 3 compulsory National Holidays: Republic Day (26 Jan), "
                            "Independence Day (15 Aug), Gandhi Jayanti (2 Oct). "
                            "Holiday list notified at start of each calendar year."
                        ),
                        "key_points": [
                            "2 Restricted Holidays per year",
                            "3 compulsory National Holidays",
                            "Annual holiday list notified by HR",
                        ],
                        "office_orders": [],
                        "approval_authority": "HR Department",
                        "amounts_or_limits": "2 Restricted Holidays per year",
                    },
                    {
                        "rule_id": "A.9",
                        "rule_title": "Transfer",
                        "applies_to": ["all employees"],
                        "content": (
                            "Transfer is an administrative exigency; employees liable to transfer "
                            "anywhere in DMRC's area of operation. Orders must be complied with within "
                            "joining time. Transfer expenses reimbursed as per TA/DA rules. "
                            "Hardship transfer requests considered by competent authority on merit."
                        ),
                        "key_points": [
                            "Transfer anywhere in DMRC jurisdiction",
                            "Joining time: max 6 days",
                            "Transfer expenses reimbursed per TA/DA rules",
                            "Hardship requests considered on merit",
                        ],
                        "office_orders": [],
                        "approval_authority": "Competent Authority / Functional Director",
                        "amounts_or_limits": "Max 6 days joining time",
                    },
                    {
                        "rule_id": "A.14",
                        "rule_title": "Resignation",
                        "applies_to": ["all employees"],
                        "content": (
                            "Minimum 90-day notice for resignation. Salary in lieu of notice period "
                            "may be paid. Surety bond amount and training costs recoverable if "
                            "resignation within 3 years of joining. Withdrawal of resignation permitted "
                            "before acceptance by competent authority."
                        ),
                        "key_points": [
                            "Min 90-day notice",
                            "Payment in lieu of notice possible",
                            "Surety bond + training cost recoverable within 3 years",
                            "Withdrawal permitted before acceptance",
                        ],
                        "office_orders": [],
                        "approval_authority": "Competent Authority",
                        "amounts_or_limits": "90-day minimum notice",
                    },
                    {
                        "rule_id": "A.19",
                        "rule_title": "Review of Service at Age 50/55",
                        "applies_to": ["all employees"],
                        "content": (
                            "Service of all employees reviewed at age 50 and 55. Committee-based review. "
                            "If performance unsatisfactory, employee may be compulsorily retired in "
                            "public interest with 3 months' notice or pay in lieu. "
                            "No stigma attached — not a disciplinary action."
                        ),
                        "key_points": [
                            "Review at age 50 and 55",
                            "3-month notice for compulsory retirement",
                            "No stigma — not disciplinary",
                        ],
                        "office_orders": [],
                        "approval_authority": "Review Committee / Board",
                        "amounts_or_limits": "3 months notice",
                    },
                    {
                        "rule_id": "A.20",
                        "rule_title": "Voluntary Retirement",
                        "applies_to": ["all employees"],
                        "content": (
                            "VRS after completing 20 years qualifying service or attaining age 50. "
                            "3 months notice required or payment in lieu. "
                            "Notice period may be waived by competent authority. "
                            "Pension/gratuity payable on VRS."
                        ),
                        "key_points": [
                            "Eligible after 20 yrs service or age 50",
                            "3-month notice (or pay in lieu)",
                            "Pension/gratuity payable",
                        ],
                        "office_orders": [],
                        "approval_authority": "Competent Authority",
                        "amounts_or_limits": "20 years service or age 50; 3-month notice",
                    },
                    {
                        "rule_id": "A.22",
                        "rule_title": "Superannuation",
                        "applies_to": ["all employees"],
                        "content": (
                            "Normal superannuation at age 60. Employees retire on the last day of the "
                            "month in which they turn 60. No extension beyond 60 except for specific "
                            "specialized posts with Board approval. "
                            "NOC and departmental clearance mandatory."
                        ),
                        "key_points": [
                            "Superannuation at age 60",
                            "Last working day = last day of birth month",
                            "No extension without Board approval",
                            "NOC and clearance mandatory",
                        ],
                        "office_orders": [],
                        "approval_authority": "Board of Directors (for extension)",
                        "amounts_or_limits": "Age 60",
                    },
                ],
                "tables": [
                    {
                        "table_id": "A.T1",
                        "table_title": "Employee Categories and IDA Pay Scales (w.e.f. 01.01.2017)",
                        "description": "Complete list of DMRC employee grades with IDA pay scales",
                        "data": [
                            {"category": "Non-Executive", "grade": "Unskilled", "pay_scale_rs": "16000-50000"},
                            {"category": "Non-Executive", "grade": "Semi-skilled", "pay_scale_rs": "20000-60000"},
                            {"category": "Non-Executive", "grade": "Skilled Maintainer", "pay_scale_rs": "25000-80000"},
                            {"category": "Non-Executive", "grade": "Maintainers and Assistants", "pay_scale_rs": "35000-110000"},
                            {"category": "Non-Executive", "grade": "Supervisor-II", "pay_scale_rs": "37000-115000"},
                            {"category": "Non-Executive", "grade": "Supervisor-I", "pay_scale_rs": "40000-125000"},
                            {"category": "Non-Executive", "grade": "Sr. Supervisors-II", "pay_scale_rs": "46000-145000"},
                            {"category": "Non-Executive", "grade": "Sr. Supervisor-I", "pay_scale_rs": "50000-160000"},
                            {"category": "Executive", "grade": "Assistant Manager (AM)", "pay_scale_rs": "50000-160000"},
                            {"category": "Executive", "grade": "Manager", "pay_scale_rs": "60000-180000"},
                            {"category": "Executive", "grade": "Dy. General Manager (DGM)", "pay_scale_rs": "70000-200000"},
                            {"category": "Executive", "grade": "Sr. DGM", "pay_scale_rs": "80000-220000"},
                            {"category": "Executive", "grade": "Jt. General Manager (JGM)", "pay_scale_rs": "90000-240000"},
                            {"category": "Executive", "grade": "Addl. GM / Sr. AGM", "pay_scale_rs": "100000-260000"},
                            {"category": "Executive", "grade": "GM / Sr. GM / CGM", "pay_scale_rs": "120000-280000"},
                            {"category": "Executive", "grade": "Executive Director (ED)", "pay_scale_rs": "150000-300000"},
                            {"category": "Executive", "grade": "Director", "pay_scale_rs": "180000-340000"},
                            {"category": "Executive", "grade": "Managing Director (MD)", "pay_scale_rs": "200000-370000"},
                        ],
                    },
                ],
                "authority_index": [
                    {"action": "Resignation acceptance", "authority": "Competent Authority (HOD for Non-Exec, Director for Exec)", "rule_ref": "A.14"},
                    {"action": "VRS approval", "authority": "Competent Authority", "rule_ref": "A.20"},
                    {"action": "Superannuation extension", "authority": "Board of Directors", "rule_ref": "A.22"},
                    {"action": "Service review at 50/55 — compulsory retirement", "authority": "Review Committee / Board", "rule_ref": "A.19"},
                    {"action": "Rule interpretation / relaxation", "authority": "Managing Director", "rule_ref": "A.24"},
                    {"action": "Transfer orders", "authority": "Competent Authority / Functional Director", "rule_ref": "A.9"},
                    {"action": "Higher studies NOC", "authority": "HR Department", "rule_ref": "A.13"},
                ],
                "office_order_index": [],
                "cross_references": [
                    {"from_rule": "A.9", "to_chapter": "D", "to_rule": "D.8", "relationship": "Transfer entitlements governed by TA/DA rules"},
                    {"from_rule": "A.14", "to_chapter": "F", "to_rule": "F.3.3", "relationship": "Leave encashment on resignation linked to earned leave rules"},
                    {"from_rule": "A.20", "to_chapter": "F", "to_rule": "F.4.2", "relationship": "Leave encashment on VRS governed by Leave Rules Chapter F"},
                    {"from_rule": "A.22", "to_chapter": "F", "to_rule": "F.4.2", "relationship": "Leave encashment on superannuation — up to 300 days EL"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "B": {
                "chapter_id": "B",
                "chapter_title": "Conduct, Discipline and Appeal Rules",
                "page_range": "49-85",
                "summary": "Governs the code of conduct, misconduct definitions, disciplinary proceedings, penalties, suspension, subsistence allowance, and appeals for all regular DMRC employees.",
                "key_topics": ["General Conduct", "Misconduct", "Suspension", "Subsistence Allowance", "Penalties", "Disciplinary Authority", "Inquiry Procedure", "Appeals", "Anti-corruption", "Sexual Harassment"],
                "summary_chunk": (
                    "Chapter B — Conduct, Discipline and Appeal Rules covers: "
                    "(1) Applicability: All regular employees (excludes casual, contract, post-retirement contractual, consultants). "
                    "(2) General Conduct: Maintain absolute integrity, devotion to duty; no acts unbecoming of a public servant; zero tolerance for sexual harassment at workplace. "
                    "(3) Misconduct (Rule 5): 24 specific acts including theft/fraud (5.1), bribery (5.2), disproportionate assets (5.3), false information (5.4), willful insubordination (5.6), absence without leave >4 consecutive days (5.7), habitual late attendance (5.8), sleeping on duty (5.16), criminal offense (5.17), sexual harassment (5.22), subletting staff quarters (5.24), non-disclosure of foreign visits (5.23). "
                    "(4) Penalties: Minor — censure, withholding increment/promotion, recovery of losses; Major — reduction in pay, compulsory retirement, removal, dismissal. "
                    "(5) Suspension: With subsistence allowance at 50% of pay for first 90 days, 75% beyond 90 days; review by committee mandatory before extension beyond 90 days. "
                    "(6) Disciplinary Proceedings: Charge sheet → inquiry officer → inquiry report → action on report. "
                    "(7) Appeals: Employee can appeal to Appellate Authority within 45 days. "
                    "(8) Code of Ethics: National interest, equal opportunity, no conflict of interest, protecting company assets."
                ),
                "rules": [
                    {"rule_id": "B.2", "rule_title": "Application", "applies_to": ["all regular employees"], "content": "Rules apply to all regular DMRC employees. Excludes: casual/contingency employees, contract/re-employment/retainership/consultant/post-retirement contractual/advisor personnel.", "key_points": ["Applies to all regular employees", "Excludes contract, casual, consultant, PRCE"], "office_orders": [], "approval_authority": "", "amounts_or_limits": ""},
                    {"rule_id": "B.5", "rule_title": "Misconduct", "applies_to": ["all regular employees"], "content": "Without prejudice to generality, the following are treated as misconduct: 5.1 Theft/fraud/dishonesty with Corporation property; 5.2 Bribery or illegal gratification; 5.3 Disproportionate assets; 5.4 False information at appointment; 5.5 Acts prejudicial to Corporation interest; 5.6 Willful insubordination; 5.7 Absence without leave >4 consecutive days without explanation; 5.8 Habitual late/irregular attendance; 5.9 Neglect of work/negligence; 5.10 Damage to Corporation property; 5.11 Tampering with safety devices; 5.12 Drunkenness/riotous behavior; 5.13 Gambling within premises; 5.14 Smoking where prohibited; 5.16 Sleeping on duty; 5.17 Criminal offense involving moral turpitude; 5.22 Sexual harassment; 5.23 Non-disclosure of private foreign visits within 2 weeks; 5.24 Subletting of staff quarters.", "key_points": ["24 specific acts of misconduct listed", "Absence >4 days without explanation = misconduct", "Non-disclosure of foreign visits within 2 weeks = misconduct", "Subletting staff quarters = misconduct", "Sexual harassment = misconduct"], "office_orders": [], "approval_authority": "Disciplinary Authority", "amounts_or_limits": "Absence > 4 consecutive days without explanation"},
                    {"rule_id": "B.37", "rule_title": "Suspension", "applies_to": ["all regular employees"], "content": "Competent authority may place employee under suspension when: (a) disciplinary proceedings are contemplated or pending; (b) case involving moral turpitude is under investigation; (c) employee's continued presence is prejudicial to inquiry. Suspension reviewed by committee before 90-day extension.", "key_points": ["Suspension pending disciplinary proceedings", "Review committee mandatory before extension beyond 90 days", "Deemed suspension if dismissal/removal set aside on appeal"], "office_orders": [], "approval_authority": "Competent Authority", "amounts_or_limits": "Review mandatory before 90-day extension"},
                    {"rule_id": "B.38", "rule_title": "Subsistence Allowance", "applies_to": ["suspended employees"], "content": "During suspension: (a) 50% of pay for first 90 days; (b) 75% of pay if suspension extended beyond 90 days and employee is not responsible for delay in proceedings; (c) Full pay if suspension set aside. Dearness allowance payable on subsistence allowance.", "key_points": ["First 90 days: 50% of pay", "Beyond 90 days (if not employee's fault): 75%", "Full pay if suspension later set aside", "DA payable on subsistence allowance"], "office_orders": [], "approval_authority": "Disciplinary Authority", "amounts_or_limits": "50% pay (first 90 days), 75% pay (beyond 90 days)"},
                    {"rule_id": "B.40", "rule_title": "Penalties", "applies_to": ["all regular employees"], "content": "Minor Penalties: (i) Censure; (ii) Withholding of increment with cumulative effect; (iii) Withholding of promotion; (iv) Recovery from pay of whole/part of pecuniary loss caused. Major Penalties: (v) Reduction to lower stage in pay scale; (vi) Reduction to lower post/grade; (vii) Compulsory retirement; (viii) Removal from service (not disqualified from re-employment); (ix) Dismissal (disqualified from re-employment).", "key_points": ["4 Minor penalties: censure, withholding increment, withholding promotion, recovery", "5 Major penalties: reduction, compulsory retirement, removal, dismissal", "Dismissal = disqualified from future employment; Removal = not disqualified"], "office_orders": [], "approval_authority": "Disciplinary Authority (as per Schedule A)", "amounts_or_limits": ""},
                    {"rule_id": "B.50", "rule_title": "Appeals", "applies_to": ["all regular employees"], "content": "Employee can appeal against any penalty order to the Appellate Authority specified in Schedule A. Appeal must be submitted within 45 days of receipt of order. Appellate authority may confirm, modify or set aside the penalty.", "key_points": ["Appeal within 45 days of order", "Appellate authority can confirm, modify or set aside", "As per Schedule A"], "office_orders": [], "approval_authority": "Appellate Authority (per Schedule A)", "amounts_or_limits": "45 days to appeal"},
                ],
                "tables": [
                    {"table_id": "B.T1", "table_title": "Penalties Classification", "description": "Minor and Major penalties under DMRC Conduct Rules", "data": [{"type": "Minor", "penalty": "Censure"}, {"type": "Minor", "penalty": "Withholding of increment with cumulative effect"}, {"type": "Minor", "penalty": "Withholding of promotion"}, {"type": "Minor", "penalty": "Recovery of pecuniary loss"}, {"type": "Major", "penalty": "Reduction to lower stage in pay scale"}, {"type": "Major", "penalty": "Reduction to lower post/grade"}, {"type": "Major", "penalty": "Compulsory retirement"}, {"type": "Major", "penalty": "Removal from service (eligible for re-employment)"}, {"type": "Major", "penalty": "Dismissal (not eligible for re-employment)"}]},
                    {"table_id": "B.T2", "table_title": "Subsistence Allowance Rates", "description": "Allowance payable during suspension", "data": [{"period": "First 90 days of suspension", "rate": "50% of pay + DA"}, {"period": "Beyond 90 days (if delay not due to employee)", "rate": "75% of pay + DA"}, {"period": "If suspension set aside / exonerated", "rate": "Full pay (notional)"}]},
                ],
                "authority_index": [
                    {"action": "Initiate disciplinary proceedings", "authority": "Competent Authority / Disciplinary Authority (Schedule A)", "rule_ref": "B.41"},
                    {"action": "Impose minor penalties", "authority": "As per Schedule A", "rule_ref": "B.44"},
                    {"action": "Impose major penalties", "authority": "As per Schedule A", "rule_ref": "B.42"},
                    {"action": "Place employee under suspension", "authority": "Competent Authority", "rule_ref": "B.37"},
                    {"action": "Hear appeals", "authority": "Appellate Authority (Schedule A)", "rule_ref": "B.50"},
                ],
                "office_order_index": [],
                "cross_references": [
                    {"from_rule": "B.37", "to_chapter": "C", "to_rule": "C.28", "relationship": "Subsistence allowance paid from pay & allowances during suspension"},
                    {"from_rule": "B.5.24", "to_chapter": "K", "to_rule": "K.12", "relationship": "Subletting of quarters is misconduct under B.5.24"},
                    {"from_rule": "B.40", "to_chapter": "A", "to_rule": "A.21", "relationship": "Termination of service on disciplinary grounds"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "C": {
                "chapter_id": "C",
                "chapter_title": "Pay and Allowances Rules",
                "page_range": "86-119",
                "summary": "Covers all pay scales, dearness allowance, perks, HRA, transport, night duty, hard duty, miscellaneous allowances, leased accommodation, mobile/laptop facility and other entitlements.",
                "key_topics": ["Pay Scales", "Dearness Allowance", "Perks", "HRA", "Transport", "Night Duty Allowance", "Hard Duty/KM Allowance", "Leased Accommodation", "Mobile/Laptop", "Foreign Pay"],
                "summary_chunk": (
                    "Chapter C — Pay and Allowances covers: "
                    "(1) Pay Scales (IDA pattern, w.e.f. 01.01.2017): 18 grades from Unskilled Rs.16000-50000 to MD Rs.200000-370000. "
                    "(2) Dearness Allowance: IDA pattern, revised quarterly. "
                    "(3) Perks: Maximum ceiling 31.5% of basic pay (cafeteria approach). "
                    "(4) HRA: X-class cities 27%, Y-class 18%, Z-class 9% of basic pay. "
                    "(5) Transport: Vehicle provided to eligible grades; non-executive staff get transport allowance. "
                    "(6) Night Duty Allowance: For O&M non-executives on roster duty; maximum 18 nights per month. "
                    "(7) Hard Duty/Kilometrage Allowance: For field/O&M staff based on km covered. "
                    "(8) Leased Accommodation: Grade-wise lease ceilings. "
                    "(9) Mobile/Telecom and laptop facility for eligible grades. "
                    "(10) Shifting Allowance on transfer."
                ),
                "rules": [
                    {"rule_id": "C.1", "rule_title": "Pay Scales", "applies_to": ["all employees"], "content": "IDA pay scales effective 01.01.2017. Non-Executive: Unskilled 16000-50000, Semi-skilled 20000-60000, Skilled Maintainer 25000-80000, Maintainers & Assistants 35000-110000, Supervisor-II 37000-115000, Supervisor-I 40000-125000, Sr. Supervisor-II 46000-145000, Sr. Supervisor-I 50000-160000. Executive: AM 50000-160000, Manager 60000-180000, DGM 70000-200000, Sr. DGM 80000-220000, JGM 90000-240000, AGM 100000-260000, GM/Sr.GM/CGM 120000-280000, ED 150000-300000, Directors 180000-340000, MD 200000-370000.", "key_points": ["IDA pattern effective 01.01.2017", "18 grades total", "Sr. AGM special allowance Rs.2500/month after 3 years at AGM"], "office_orders": ["O.O. No. PP/2927/2019 dated 03.12.2019"], "approval_authority": "Board", "amounts_or_limits": "Rs.16000-50000 to Rs.200000-370000"},
                    {"rule_id": "C.2", "rule_title": "Dearness Allowance", "applies_to": ["all employees"], "content": "DA admissible on IDA (Industrial Dearness Allowance) pattern, revised quarterly based on AICPI. DA calculated on basic pay.", "key_points": ["IDA pattern", "Revised quarterly", "Based on AICPI", "Calculated on basic pay"], "office_orders": [], "approval_authority": "Board/Management", "amounts_or_limits": "Varies quarterly"},
                    {"rule_id": "C.3", "rule_title": "Perks", "applies_to": ["all employees"], "content": "Perks admissible under cafeteria approach subject to maximum ceiling of 31.5% of basic pay. Employee can choose components within the ceiling.", "key_points": ["Cafeteria approach — employee chooses components", "Maximum ceiling: 31.5% of basic pay"], "office_orders": ["O.O. No. PP/1486/2014 dated 24.09.2014", "O.O. No. PP/2534/2018 dated 09.01.2018"], "approval_authority": "HR Department", "amounts_or_limits": "Max 31.5% of basic pay"},
                    {"rule_id": "C.4", "rule_title": "House Rent Allowance (HRA)", "applies_to": ["all employees"], "content": "HRA rates: X-class cities 27%, Y-class cities 18%, Z-class cities 9% of basic pay. Not payable if DMRC accommodation occupied.", "key_points": ["X-class: 27%", "Y-class: 18%", "Z-class: 9%", "Not payable if DMRC accommodation occupied"], "office_orders": ["O.O. No. PP/2072/2015 dated 15.03.2022", "O.O. No. PP/2647/2018 dated 27.09.2018"], "approval_authority": "Finance Department", "amounts_or_limits": "27% / 18% / 9% of basic pay"},
                    {"rule_id": "C.7", "rule_title": "Night Duty Allowance", "applies_to": ["O&M non-executives", "O&M executives up to specified level"], "content": "NDA for O&M non-executive employees performing roster duty involving night shifts. Payment maximum for 18 nights per month. Partial night duty to Train Operators strictly on basis of reporting timing.", "key_points": ["O&M non-executives on roster duty", "Maximum 18 nights per month", "Based on reporting timing"], "office_orders": ["O.O. No. PP-2925/2019 dated 03.12.2019"], "approval_authority": "O&M HOD", "amounts_or_limits": "Max 18 nights per month"},
                    {"rule_id": "C.8", "rule_title": "Hard Duty / Kilometrage Allowance", "applies_to": ["O&M field staff"], "content": "Kilometrage Allowance based on 'Sign On'. Paid to eligible O&M field staff based on kilometers covered during duty. Revised effective 01.12.2019.", "key_points": ["Replaced Hard Duty Allowance", "Based on kilometers covered", "Applicable to O&M field staff"], "office_orders": ["O.O. No. PP-2925/2019 dated 03.12.2019"], "approval_authority": "O&M HOD", "amounts_or_limits": "As per approved km rates"},
                ],
                "tables": [
                    {"table_id": "C.T1", "table_title": "HRA Rates by City Category", "description": "House Rent Allowance rates for different city categories", "data": [{"city_category": "X-class", "hra_rate": "27% of basic pay", "examples": "Delhi, Mumbai, Kolkata, Chennai, Hyderabad, Bangalore"}, {"city_category": "Y-class", "hra_rate": "18% of basic pay", "examples": "Other state capitals and large cities"}, {"city_category": "Z-class", "hra_rate": "9% of basic pay", "examples": "All other cities"}]},
                    {"table_id": "C.T2", "table_title": "Perks Ceiling", "description": "Maximum perks ceiling for all grades", "data": [{"applicable_to": "All employees", "perks_ceiling": "31.5% of basic pay", "approach": "Cafeteria"}]},
                ],
                "authority_index": [
                    {"action": "Perks component selection", "authority": "Employee (within ceiling approved by HR)", "rule_ref": "C.3"},
                    {"action": "HRA payment", "authority": "Finance Department", "rule_ref": "C.4"},
                    {"action": "NDA approval", "authority": "O&M HOD", "rule_ref": "C.7"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/2927/2019", "date": "03.12.2019", "subject": "Pay scale revision", "rule_ref": "C.1"},
                    {"oo_number": "O.O. No. PP/1486/2014", "date": "24.09.2014", "subject": "Perks/cafeteria allowance revision", "rule_ref": "C.3"},
                    {"oo_number": "O.O. No. PP/2534/2018", "date": "09.01.2018", "subject": "Perks and cafeteria allowance", "rule_ref": "C.3"},
                    {"oo_number": "O.O. No. PP/2072/2015", "date": "15.03.2022", "subject": "HRA rates", "rule_ref": "C.4"},
                    {"oo_number": "O.O. No. PP-2925/2019", "date": "03.12.2019", "subject": "Revision of NDA, HDA/KM allowance rates", "rule_ref": "C.7,C.8"},
                ],
                "cross_references": [
                    {"from_rule": "C.4", "to_chapter": "K", "to_rule": "K.12", "relationship": "HRA not payable if DMRC staff quarters occupied"},
                    {"from_rule": "C.2", "to_chapter": "F", "to_rule": "F.3.3", "relationship": "DA included in earned leave salary calculation"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "D": {
                "chapter_id": "D",
                "chapter_title": "Travelling Allowance / Daily Allowance Rules (TA/DA)",
                "page_range": "120-134",
                "summary": "Governs reimbursement of travel, hotel, daily allowance and transfer-related expenses for DMRC employees on official tours and transfers.",
                "key_topics": ["Travel Entitlement", "Daily Allowance", "Hotel Charges", "Transfer Grant", "Transportation of Personal Effects", "Composite TA", "Local Journey", "TA Advance"],
                "summary_chunk": (
                    "Chapter D — TA/DA Rules covers: "
                    "(1) Objective: Compensate employees for travel, stay and food expenses on official tours and transfers. "
                    "(2) Travel Entitlement by grade: MD/TMM — Air (highest class); ED/CGM — Air (domestic highest); HODs Rs.120000-280000 — Air Y class / AC-1 Rail; Rs.70000-200000+ — Air Economy / 1st AC Rail; Rs.50000-160000 Exec — Air Economy / 2nd AC Rail; Rs.35000-110000 — First Class/3rd AC Rail; Rs.25000-80000 — First Class/AC 3-Tier; Below Rs.25000-80000 — 2nd Sleeper. "
                    "(3) Daily Allowance (A1 cities): MD/TMM Rs.1400/day, ED/CGM/SGM/GM Rs.1200/day, DGM/Sr.DGM/JGM/AGM Rs.1000/day, Manager/AM Rs.900/day, Rs.25000-80000 and above up to highest non-exec Rs.800/day, Below Rs.25000-80000 Rs.500/day. "
                    "(4) DA proportional: Up to 6 hrs = 30%, 6-12 hrs = 70%, over 12 hrs = 100%. First 30 days full DA; 30-90 days 50% DA. "
                    "(5) Hotel Charges (X-class cities): MD actual; ED/CGM Rs.10000; GM Rs.9000; DGM-AGM Rs.6800; Manager/AM Rs.4500; Rs.25000-80000+ Rs.2300; Below Rs.25000-80000 Rs.1700. "
                    "(6) Composite Transfer Grant (CTG): 80% of last month basic pay for transfer >20 km; 1/3rd for transfer <20 km within same city. "
                    "(7) TA advance up to 90% of estimated expenditure; settlement within 30 days; 10% p.a. interest on delayed settlement."
                ),
                "rules": [
                    {"rule_id": "D.1", "rule_title": "Objective and Applicability", "applies_to": ["all regular employees", "probationers", "re-employed", "deputationists"], "content": "TA/DA Rules provide monetary compensation for travel, stay, food expenses on official tour and transfer. Applies to all regular employees, probationers, re-employed, extension, deputationists. Not applicable to casual/daily-rated/contract employees unless specifically extended by MD.", "key_points": ["Covers tour and transfer expenses", "Excludes casual and contract employees unless specifically extended"], "office_orders": [], "approval_authority": "Controlling Officer", "amounts_or_limits": ""},
                    {"rule_id": "D.6", "rule_title": "Mode of Travel Entitlement", "applies_to": ["all regular employees"], "content": "Travel entitlement: MD/TMM: Air (Domestic Highest/Intl. First Class); ED/CGM: Air (Domestic Highest/Intl. Business); HODs Rs.120000-280000: Air Y-Class domestic / Rail AC-1; Rs.70000-200000 to <120000: Air Economy, Rail 1st AC; Rs.50000-160000 Exec: Air Economy, Rail 2nd AC; Rs.35000-110000: Rail First Class/Rajdhani 3rd AC; Rs.25000-80000: Rail First Class/AC 3-Tier; Below Rs.25000-80000: Rail 2nd Sleeper.", "key_points": ["8 grade-wise travel categories", "Air travel entitled from Rs.50000-160000 Executive and above", "GM with Basic Pay Rs.175000+ entitled to Business Class"], "office_orders": ["O.O. No. PP-2925/2019 dated 03.12.2019"], "approval_authority": "Controlling Officer", "amounts_or_limits": "TA advance up to 90% of estimated expenditure; settle within 30 days"},
                    {"rule_id": "D.7", "rule_title": "Daily Allowance Rates", "applies_to": ["all regular employees"], "content": "DA rates for A1 cities: MD/TMM Rs.1400/day; ED/CGM/SGM/GM Rs.1200/day; DGM/Sr.DGM/JGM/AGM Rs.1000/day; Manager/AM Rs.900/day; Rs.25000-80000 and above upto highest non-exec Rs.800/day; Below Rs.25000-80000 Rs.500/day. DA proportional: upto 6 hrs = 30%, 6-12 hrs = 70%, over 12 hrs = 100%. Full DA for first 30 days; 50% for 30-90 days.", "key_points": ["6 grade-wise DA rates", "MD: Rs.1400/day; Lowest: Rs.500/day", "Proportional based on hours: 30%/70%/100%", "Full DA for first 30 days; 50% for 30-90 days"], "office_orders": ["O.O. No. PP-2925/2019 dated 03.12.2019", "O.O. No. PP-1801/2014 dated 02.07.2014"], "approval_authority": "HOD (for extension beyond 30 days)", "amounts_or_limits": "MD Rs.1400/day to lowest Rs.500/day"},
                    {"rule_id": "D.7.3", "rule_title": "Hotel Charges", "applies_to": ["all regular employees"], "content": "Hotel charges (X-class cities, exclusive of taxes): MD — actual; ED/CGM Rs.10000; GM Rs.9000; DGM/Sr.DGM/JGM/AGM Rs.6800; Manager/AM Rs.4500; Rs.25000-80000+ Rs.2300; Below Rs.25000-80000 Rs.1700. Y&Z class cities: MD actual; ED/CGM Rs.8000; GM Rs.7200; DGM-AGM Rs.5500; Manager/AM Rs.3600; Rs.25000-80000+ Rs.1700; Below Rs.25000-80000 Rs.1400.", "key_points": ["Grade-wise hotel ceilings", "X-class higher than Y/Z class", "Exclusive of taxes", "MD: actual expenses"], "office_orders": ["O.O. No. PP-2925/2019 dated 03.12.2019", "O.O. No. PP-3254/2023 dated 03.03.2023"], "approval_authority": "HOD", "amounts_or_limits": "Rs.1400 to Rs.10000 (X-class)"},
                    {"rule_id": "D.8", "rule_title": "Entitlement on Transfer", "applies_to": ["all regular employees on transfer"], "content": "On transfer: (a) Journey fare for self and family as per travel entitlement; (b) Composite Transfer Grant (CTG): 80% of last month basic pay if transfer involves change of station >20 km; 1/3rd of CTG for transfers <20 km or within same city/NCR. (c) Transportation of personal effects: MD/Directors — 8000 kg @ Rs.50/km; Rs.37000-115000+ — 6000 kg @ Rs.50/km; Rs.35000-80000 and below — 1500 kg @ Rs.15/km.", "key_points": ["CTG: 80% of last basic pay for transfer >20km", "CTG: 1/3rd for transfer <20km / same city", "Address proof mandatory for CTG", "Transportation rates: Rs.15/km to Rs.50/km depending on grade"], "office_orders": ["O.O. No. PP/2715/2019 dated 07.01.2019", "O.O. No. PP/2016/2015 dated 13.07.2015"], "approval_authority": "Controlling Officer / Director", "amounts_or_limits": "CTG: 80% of last basic pay; Transportation: Rs.15-50/km"},
                ],
                "tables": [
                    {"table_id": "D.T1", "table_title": "Daily Allowance Rates (A1 Cities)", "description": "DA entitlement for different grades on official tour", "data": [{"grade": "MD/TMM", "da_per_day_rs": "1400"}, {"grade": "ED/CGM/SGM/GM", "da_per_day_rs": "1200"}, {"grade": "DGM/Sr.DGM/JGM/AGM", "da_per_day_rs": "1000"}, {"grade": "Manager/AM", "da_per_day_rs": "900"}, {"grade": "Rs.25000-80000 to highest non-executive", "da_per_day_rs": "800"}, {"grade": "Below Rs.25000-80000", "da_per_day_rs": "500"}]},
                    {"table_id": "D.T2", "table_title": "Hotel Charges Ceiling (Exclusive of Taxes)", "description": "Maximum hotel reimbursement by grade and city category", "data": [{"grade": "MD/TMM", "x_class_rs": "Actual", "y_z_class_rs": "Actual"}, {"grade": "ED/CGM", "x_class_rs": "10000", "y_z_class_rs": "8000"}, {"grade": "GM", "x_class_rs": "9000", "y_z_class_rs": "7200"}, {"grade": "DGM/Sr.DGM/JGM/AGM", "x_class_rs": "6800", "y_z_class_rs": "5500"}, {"grade": "Manager/AM", "x_class_rs": "4500", "y_z_class_rs": "3600"}, {"grade": "Rs.25000-80000 to highest non-exec", "x_class_rs": "2300", "y_z_class_rs": "1700"}, {"grade": "Below Rs.25000-80000", "x_class_rs": "1700", "y_z_class_rs": "1400"}]},
                    {"table_id": "D.T3", "table_title": "Travel Entitlement on Official Tour", "description": "Mode of travel entitled for different grades", "data": [{"grade": "MD/TMM", "domestic_air": "Highest class", "rail": "Highest class"}, {"grade": "ED/CGM", "domestic_air": "Highest class", "rail": "Highest class"}, {"grade": "HOD (Rs.120000-280000)", "domestic_air": "Y-class", "rail": "AC-1"}, {"grade": "Rs.70000-200000 to <120000", "domestic_air": "Economy", "rail": "1st AC"}, {"grade": "Rs.50000-160000 (Exec)", "domestic_air": "Economy", "rail": "2nd AC"}, {"grade": "Rs.35000-110000", "domestic_air": "Not entitled", "rail": "First Class / Rajdhani 3rd AC"}, {"grade": "Rs.25000-80000", "domestic_air": "Not entitled", "rail": "First Class / AC 3-Tier"}, {"grade": "Below Rs.25000-80000", "domestic_air": "Not entitled", "rail": "2nd Sleeper"}]},
                ],
                "authority_index": [
                    {"action": "Authorize official tour", "authority": "Controlling Officer", "rule_ref": "D.5"},
                    {"action": "Approve hotel stay beyond standard rates", "authority": "HOD (non-exec) / Director (exec)", "rule_ref": "D.7.3"},
                    {"action": "Allow higher class of travel", "authority": "Director concerned", "rule_ref": "D.6.2"},
                    {"action": "Approve TA advance", "authority": "Controlling Officer", "rule_ref": "D.6.4"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP-2925/2019", "date": "03.12.2019", "subject": "Revision of TA/DA rates", "rule_ref": "D.6,D.7"},
                    {"oo_number": "O.O. No. PP-1801/2014", "date": "02.07.2014", "subject": "Cash incentive for economy class travel (GM+)", "rule_ref": "D.7"},
                    {"oo_number": "O.O. No. PP/2715/2019", "date": "07.01.2019", "subject": "Composite Transfer Grant", "rule_ref": "D.8"},
                    {"oo_number": "O.O. No. PP-3254/2023", "date": "03.03.2023", "subject": "Hotel charge revision", "rule_ref": "D.7.3"},
                ],
                "cross_references": [
                    {"from_rule": "D.8", "to_chapter": "A", "to_rule": "A.9", "relationship": "Transfer joining time and entitlements governed by A.9 + D.8"},
                    {"from_rule": "D.6", "to_chapter": "M", "to_rule": "M.4", "relationship": "LTC travel entitlement follows same grade-wise mode as TA/DA"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "E": {
                "chapter_id": "E",
                "chapter_title": "Medical Attendance Rules",
                "page_range": "135-164",
                "summary": "Governs medical reimbursement, empanelled hospitals, OPD/IPD entitlements, cashless treatment, prolonged illness, and family coverage for DMRC employees.",
                "key_topics": ["Empanelled Hospitals", "OPD Reimbursement", "IPD Reimbursement", "Cashless Treatment", "Family Coverage", "Prolonged Treatment", "Room Entitlement", "Medical Advance"],
                "summary_chunk": (
                    "Chapter E — Medical Attendance Rules covers: "
                    "(1) Applicability: All regular employees and specified family members (spouse, children under 25, dependent parents). "
                    "(2) Empanelled Hospitals: DMRC has empanelled hospitals in Delhi/NCR for cashless treatment. "
                    "(3) IPD Room Entitlement: MD/Directors — Nursing Home (Suite/Deluxe); ED/HoDs — Deluxe Room (SNH); Sr.AGM/AGM/JGM/Sr.DGM — Single Room (SNH); DGM/Manager/AM/Sr.Supervisor — Single Room (SNH); Supervisors — Two/three bedded; Non-Supervisors — Economy/General Ward. "
                    "(4) Cashless Treatment: Available at empanelled hospitals; submit certificate within 7 days. "
                    "(5) Prolonged Treatment: HOD approval (non-exec); Director approval (exec); medicine bills max 2 months at a time. "
                    "(6) Family: Spouse, children (son <25), unmarried daughter, dependent parents (income <15% of basic or Rs.9000+DR). "
                    "(7) Medical claims must be submitted within 6 months."
                ),
                "rules": [
                    {"rule_id": "E.family_def", "rule_title": "Family Definition for Medical", "applies_to": ["all employees"], "content": "Family for medical purposes: Spouse; Son (below 25 years or till married/employed); Unmarried daughter (not employed, dependent on employee); Parents residing with employee whose combined monthly income does not exceed 15% of employee's basic pay or Rs.9000 plus dearness relief, whichever is more.", "key_points": ["Spouse always covered", "Son: below 25 or till employed/married", "Unmarried daughter: till employed", "Parents: income < 15% of basic pay or Rs.9000+DR"], "office_orders": [], "approval_authority": "HR Department", "amounts_or_limits": "Parent income threshold: 15% of basic or Rs.9000+DR"},
                    {"rule_id": "E.ipd", "rule_title": "IPD Room Entitlement", "applies_to": ["all employees"], "content": "Room entitlement during hospitalization: MD/Directors — Suite/Deluxe (Nursing Home); ED/HoDs — Deluxe Room (SNH); Sr.AGM/AGM/JGM/Sr.DGM — Single Room (SNH); DGM/Manager/AM/Sr.Supervisor — Single Room (SNH); Supervisors — Two/three bedded; Non-Supervisors — Economy/General Ward.", "key_points": ["6 grade-wise room categories", "MD/Directors: Nursing Home (highest)", "Non-Supervisors: Economy Ward"], "office_orders": ["O.O No. HR/O&M/196/2023 Dt.17.05.2023"], "approval_authority": "HR Department / Empanelled Hospital", "amounts_or_limits": ""},
                    {"rule_id": "E.cashless", "rule_title": "Cashless Treatment", "applies_to": ["all employees"], "content": "Cashless treatment available at DMRC-empanelled hospitals. Employee must submit Reimbursement-cum-Certificate (Annexure E) within 7 days of availing cashless facility.", "key_points": ["Cashless at empanelled hospitals", "Submit certificate within 7 days of discharge"], "office_orders": [], "approval_authority": "HR Department / Finance", "amounts_or_limits": "Certificate within 7 days"},
                    {"rule_id": "E.prolonged", "rule_title": "Prolonged Treatment", "applies_to": ["all employees"], "content": "For prolonged illness, prior approval required. Approval authority: HOD for non-executives; Director for executives. Medicine bills reimbursed for maximum 2 months at a time.", "key_points": ["Prior approval mandatory", "HOD approves for non-exec; Director for exec", "Medicine bills: max 2 months at a time"], "office_orders": [], "approval_authority": "HOD (non-exec) / Director (exec)", "amounts_or_limits": "Medicine bills: max 2 months at a time"},
                    {"rule_id": "E.claims", "rule_title": "Medical Claim Submission", "applies_to": ["all employees"], "content": "Medical claims must be submitted within 6 months of incurring the expense. Employee must certify bills are true and correct. Claims verified by HR then sent to Finance for reimbursement.", "key_points": ["Deadline: 6 months from expense date", "Employee certificate mandatory", "HR verification → Finance reimbursement"], "office_orders": [], "approval_authority": "HR Department → Finance (Establishment)", "amounts_or_limits": "6-month claim submission deadline"},
                ],
                "tables": [
                    {"table_id": "E.T1", "table_title": "IPD Room Entitlement by Grade", "description": "Hospital room category entitled during indoor treatment", "data": [{"grade": "MD/Directors", "room_type": "Suite/Deluxe Room", "hospital_type": "Nursing Home (NH)", "reimbursement_basis": "NH rates"}, {"grade": "ED/HoDs", "room_type": "Deluxe Room", "hospital_type": "Semi-Nursing Home (SNH)", "reimbursement_basis": "NH rates"}, {"grade": "Sr.AGM/AGM/JGM/Sr.DGM", "room_type": "Single Room", "hospital_type": "Semi-Nursing Home (SNH)", "reimbursement_basis": "SNH rates"}, {"grade": "DGM/Manager/AM/Sr.Supervisor", "room_type": "Single Room", "hospital_type": "Semi-Nursing Home (SNH)", "reimbursement_basis": "SNH rates"}, {"grade": "Supervisor", "room_type": "Two/Three bedded", "hospital_type": "", "reimbursement_basis": "SP rates"}, {"grade": "Non-Supervisor", "room_type": "Economy/General Ward", "hospital_type": "", "reimbursement_basis": "SP rates"}]},
                ],
                "authority_index": [
                    {"action": "Approve prolonged treatment", "authority": "HOD (non-exec) / Director (exec)", "rule_ref": "E.prolonged"},
                    {"action": "Medical claim verification", "authority": "HR Department", "rule_ref": "E.claims"},
                    {"action": "Medical advance sanction", "authority": "Finance Department", "rule_ref": "E.advance"},
                    {"action": "Cashless treatment authorization", "authority": "Empanelled Hospital / HR", "rule_ref": "E.cashless"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O No. HR/O&M/196/2023", "date": "17.05.2023", "subject": "IPD room entitlement revision", "rule_ref": "E.ipd"},
                ],
                "cross_references": [
                    {"from_rule": "E.family_def", "to_chapter": "M", "to_rule": "M.3.2", "relationship": "Same family definition applies for LTC"},
                    {"from_rule": "E.prolonged", "to_chapter": "F", "to_rule": "F.3.7", "relationship": "EOL often follows prolonged illness"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "F": {
                "chapter_id": "F",
                "chapter_title": "Leave Rules",
                "page_range": "165-186",
                "summary": "Governs all types of leave available to DMRC employees including casual, special casual, earned, half pay, leave not due, commuted, extraordinary, maternity, paternity, child care, study leave, and leave encashment.",
                "key_topics": ["Casual Leave", "Special Casual Leave", "Earned Leave", "Half Pay Leave", "Leave Not Due", "Commuted Leave", "Extraordinary Leave", "WRIIL", "Quarantine Leave", "Maternity Leave", "Paternity Leave", "Child Care Leave", "Study Leave", "Leave Encashment", "Compensatory Rest"],
                "summary_chunk": (
                    "Chapter F — Leave Rules: DMRC employees have 13 types of leave: "
                    "(1) Casual Leave (CL): 8 days/year for 5-day week office staff; 12 days for O&M/6-day week field staff; cannot be carried over; not combinable with EL/HPL. "
                    "(2) Special Casual Leave (SCL): Up to 30 days/year; for specific purposes — sports, scouts, blood donation (max 4 times/year), sterilization operations, elections, bandh/curfew, staff council meetings, PWD employees (4 extra days). "
                    "(3) Earned Leave (EL): 30 days/year; credited 15 days on 1st Jan and 15 days on 1st July; maintained in Encashable (max 150 days) and Non-Encashable (total max 300 days); max EL at one time: 120 days (180 days if outside India). "
                    "(4) Half Pay Leave (HPL): 20 days/year; no accumulation limit; max at one time: 24 months; leave salary = 50% of pay. "
                    "(5) Leave Not Due (LND): On medical grounds only; after 1 year service; max 360 days in entire service (max 180 days at one time); charged against future HPL. "
                    "(6) Commuted Leave: Charged at double HPL; paid at full EL rate; max 90 days for study course. "
                    "(7) Extraordinary Leave (EOL): When no other leave due; after 6 years service; max 2 years in entire career (6 months per 5 years service); HOD/Director/MD approves; no pay; deemed resignation if absent after EOL expiry. "
                    "(8) WRIIL: Full pay during hospitalization; full pay 6 months post-hospitalization; half pay for 12 months beyond that. "
                    "(9) Quarantine Leave: Up to 21 days (max 30 days exceptional) for infectious disease in household. "
                    "(10) Maternity Leave: 182 days (26 weeks) for up to 2 children; 12 weeks for more than 2 children; 45 days for miscarriage/abortion; 180 days child adoption leave; full pay. "
                    "(11) Paternity Leave: 15 days; for employees with less than 2 children; within 15 days before or 6 months after delivery. "
                    "(12) Child Care Leave (CCL): Women only; confirmed employees with 2 years service; max 730 days (2 years) in entire service; for children below 18; full pay; not more than 3 spells/year. "
                    "(13) Study Leave: After 3 years service; max 12 months at one time (up to 24 months special); max 24 months in entire service; MD approval. "
                    "(14) Leave Encashment: Up to 300 days (EL+HPL) on superannuation/death; 50% of non-encashable EL (max 75 days) on resignation. "
                    "(15) Compensatory Rest: O&M non-executives only; max 3 days at a time; within 30 days."
                ),
                "rules": [
                    {"rule_id": "F.3.1", "rule_title": "Casual Leave", "applies_to": ["all employees"], "content": "CL is for urgent/unforeseen situations. Office staff (5-day week): 8 days/year. O&M/Field staff (6-day week): 12 days/year. Granted in half or full days. Cannot be carried over to next calendar year. Sundays/holidays within CL spell not charged. Cannot be combined with EL/HPL. Pro-rata on joining/separation mid-year.", "key_points": ["Office: 8 days/year; O&M/Field: 12 days/year", "Cannot carry over to next year", "Not combinable with EL or HPL", "Pro-rata on joining/separation", "Applied via ESS"], "office_orders": ["O.O. No. PP/43/99 dated 14.12.99", "O.O. No. PP/1525/2012 dated 14.11.12", "O.O. No. PP/1359/2011 dated 20.12.2011"], "approval_authority": "Controlling Officer / HOD", "amounts_or_limits": "8 days/year (office) or 12 days/year (O&M)"},
                    {"rule_id": "F.3.2", "rule_title": "Special Casual Leave", "applies_to": ["all employees"], "content": "SCL over and above CL entitlement; max 30 days/year total. Purposes: scouts/guides rallies, Republic Day events, sports tournaments, Court attendance, technical meetings, sterilization operations (male vasectomy: 5 days; female tubectomy: 10 days), bandh/curfew, staff council, PWD employees (4 extra days + 10 days for seminars/conferences), blood donation (max 4 times/year), elections.", "key_points": ["Max 30 days/year", "Blood donation: max 4 times/year", "PWD: 4 additional SCL days + 10 for conferences", "Sterilization: 1-10 days depending on operation type", "Combinable with EL or CL (not both)"], "office_orders": ["O.O. No. PP/2553/2018 dated 20.03.2018"], "approval_authority": "HOD", "amounts_or_limits": "Max 30 days/year total"},
                    {"rule_id": "F.3.3", "rule_title": "Earned Leave", "applies_to": ["all regular employees", "deputationists", "temporary employees"], "content": "EL credited 30 days/year: 15 days on 1st Jan, 15 days on 1st July. Two accounts: Encashable (max 150 days) and Non-Encashable; total max 300 days. Max EL at one time: 120 days (180 days if entirely outside India). Leave salary = full pay including perks and DA.", "key_points": ["30 days/year (15 on 1 Jan + 15 on 1 July)", "Encashable max 150 days; Total max 300 days", "Max at one time: 120 days (180 outside India)", "Leave salary: full pay including DA and perks"], "office_orders": ["O.O. No. PP/872/2009 dated 29.01.2009", "O.O. No. PP/2300/2016 dated 15.11.2016", "O.O. No. PP/1788/2014 dated 06.06.2014"], "approval_authority": "Controlling Officer / HOD", "amounts_or_limits": "30 days/year; Max 300 days accumulation"},
                    {"rule_id": "F.3.4", "rule_title": "Half Pay Leave", "applies_to": ["all employees"], "content": "HPL credited 20 days/year (10 on 1st Jan, 10 on 1st July). No limit on accumulation but max HPL at one time: 24 months. Leave salary = 50% of pay + DA.", "key_points": ["20 days/year", "No accumulation limit", "Max at one time: 24 months", "Leave salary: 50% of pay"], "office_orders": [], "approval_authority": "Controlling Officer / HOD", "amounts_or_limits": "20 days/year; Max 24 months at one time; Salary at 50%"},
                    {"rule_id": "F.3.5", "rule_title": "Leave Not Due", "applies_to": ["regular employees"], "content": "LND on medical grounds only; after 1 year service; when no other leave (except CL) due. Max 360 days in entire service (max 180 days at one time). Charged against future HPL earnings. Leave salary same as HPL (50%).", "key_points": ["Medical grounds only", "After 1 year service", "Max 360 days entire service; max 180 days at one time", "Charged against future HPL"], "office_orders": [], "approval_authority": "Competent Authority", "amounts_or_limits": "Max 360 days total; max 180 days at once"},
                    {"rule_id": "F.3.6", "rule_title": "Commuted Leave", "applies_to": ["all employees"], "content": "Commuted leave on medical grounds or approved course of study. Charged at double HPL rate but paid at full EL salary. Max for study course: 90 days (180 HPL). For female on adoption: up to 60 days without medical cert.", "key_points": ["Charged at 2x HPL rate; paid at EL salary", "For medical grounds or approved study", "Max for study: 90 days (= 180 HPL)", "Female adoption: 60 days without medical cert"], "office_orders": [], "approval_authority": "Controlling Officer / HOD", "amounts_or_limits": "Max 90 days for study course"},
                    {"rule_id": "F.3.7", "rule_title": "Extra Ordinary Leave", "applies_to": ["regular employees"], "content": "EOL only when no other leave is due. Must have 6 years qualifying service. Max 2 years in entire career; proportionate: 6 months per 5 years service. Sanctioning authority: HOD for non-supervisor (1st time); Directors for supervisor/exec up to Manager; MD for Dy.HOD and above. No pay during EOL. Deemed resignation if absent after EOL expiry. No private employment during EOL.", "key_points": ["After 6 years qualifying service", "Max 2 years entire career (6 months per 5 years service)", "No pay, no leave earning, no increment", "Deemed resignation if absent after expiry", "No private employment during EOL", "HOD → Director → MD approvals by grade"], "office_orders": ["O.O. No. PP/1917/2015 dated 06.02.2015"], "approval_authority": "HOD (non-supervisor) / Director (supervisor/exec up to Manager) / MD (Dy.HOD+)", "amounts_or_limits": "Max 2 years total; 6 months per 5 years service"},
                    {"rule_id": "F.3.8", "rule_title": "Work Related Illness and Injury Leave (WRIIL)", "applies_to": ["all employees (permanent and temporary)"], "content": "WRIIL for illness/injury attributable to official duties. Provisions: (a) Full pay during entire hospitalization; (b) Full pay for 6 months post-hospitalization; (c) Half pay for next 12 months (commutable to full pay with HPL debit); (d) No EL/HPL credited during WRIIL. Approval: HOD (non-executives), Director (executives).", "key_points": ["Full pay during hospitalization", "Full pay for 6 months post-hospital", "Half pay next 12 months", "No EL/HPL credited during WRIIL", "Incident Report mandatory"], "office_orders": ["O.O. No. PP/3227/2022 dated 03.11.2022", "O.O. No. HR/O&M/361/2022 dated 15.12.2022"], "approval_authority": "HOD (non-exec) / Director (exec)", "amounts_or_limits": "Full pay during hospital + 6 months; Half pay for 12 months beyond"},
                    {"rule_id": "F.3.9", "rule_title": "Quarantine Leave", "applies_to": ["all employees"], "content": "Quarantine leave for infectious disease (cholera, plague, diphtheria, typhus, meningitis, conjunctivitis etc.) in employee's family/household. Employee himself suffering: other leaves apply, not quarantine leave. Max 21 days (up to 30 days exceptional). Salary not affected.", "key_points": ["For infectious disease in household — not employee himself", "Max 21 days ordinary; 30 days exceptional", "Full salary during quarantine leave", "Combinable with other leaves"], "office_orders": [], "approval_authority": "Controlling Officer", "amounts_or_limits": "Max 21 days (30 days exceptional)"},
                    {"rule_id": "F.3.10", "rule_title": "Maternity Leave", "applies_to": ["female regular employees", "deputationists", "long-term contractual on regular pay scale"], "content": "Maternity Leave: (a) Up to 2 children: 182 days (26 weeks); not more than 8 weeks before expected delivery; (b) More than 2 surviving children: 12 weeks total. Miscarriage/abortion: 45 days with medical certificate. Child adoption leave: 180 days for adopting child below 1 year (with less than 2 children). Full pay during ML. Not charged to leave account.", "key_points": ["182 days (26 weeks) for up to 2 children", "12 weeks for more than 2 children", "45 days for miscarriage/abortion", "180 days child adoption leave (child <1 year, <2 children)", "Full pay; not charged to leave account"], "office_orders": ["O.O. No. HR/O&M-140/2022 dated 25.04.2022", "O.O. No. PP/820/2008 dated 13.10.2008", "O.O. No. PP/1955/2015 dated 26.03.2015"], "approval_authority": "Competent Authority / HOD", "amounts_or_limits": "182 days (≤2 children); 12 weeks (>2 children); 45 days (miscarriage)"},
                    {"rule_id": "F.3.11", "rule_title": "Paternity Leave", "applies_to": ["male employees with less than 2 surviving children"], "content": "Paternity Leave: 15 days during confinement/childbirth of wife. Conditions: less than 2 surviving children; full salary; not charged to leave account; combinable with any leave except CL. Can be availed up to 15 days before or within 6 months from date of delivery. Also 15 days on valid adoption of child below 1 year within 6 months of adoption.", "key_points": ["15 days; for employees with <2 children", "Within 15 days before or 6 months after delivery", "Full pay; not charged to leave account", "Also available on adoption of child <1 year"], "office_orders": ["O.O. No. PP/807/2008 dated 15.09.2008", "O.O. No. PP/1955/2015 dated 26.03.2015"], "approval_authority": "Controlling Officer / HOD", "amounts_or_limits": "15 days"},
                    {"rule_id": "F.3.12", "rule_title": "Child Care Leave", "applies_to": ["confirmed regular female employees with min 2 years service"], "content": "CCL for confirmed regular female employees with minimum 2 years service. Max 730 days (2 years) in entire service. For children below 18 (or disabled child any age). Max 3 spells/year (6 spells for single female employees). Minimum 5 days per spell. Full pay; no perks/allowances under cafeteria. Bond for 3 years service after CCL if <5 years service. LTC can be availed during CCL.", "key_points": ["Confirmed female employees with 2+ years service only", "Max 730 days (2 years) entire service", "Child must be below 18 (any age if disabled)", "Max 3 spells/year (6 for single employees); min 5 days/spell", "Bond required if <5 years service"], "office_orders": ["O.O. No. PP/820/2008 dated 13.10.2008", "O.O. PP/1987/2015 dated 22.05.2015"], "approval_authority": "Competent Authority / HOD", "amounts_or_limits": "Max 730 days total; min 5 days per spell"},
                    {"rule_id": "F.3.13", "rule_title": "Study Leave", "applies_to": ["regular employees with 3+ years service"], "content": "Study leave for scientific, technical or managerial studies in Corporation's interest. Eligible after 3 years service. MD is sanctioning authority. Max 12 months at one time; max 24 months in entire service. Leave salary = last pay + DA + HRA (first 180 days) + CCA (first 120 days). Bond required before leave.", "key_points": ["After 3 years service", "MD is approving authority", "Max 12 months at one time; 24 months in entire service", "Leave salary: full pay + DA + HRA (180 days) + CCA (120 days)", "Bond mandatory"], "office_orders": ["O.O. No. PP/3139/2021 dated 26.10.2021"], "approval_authority": "Managing Director", "amounts_or_limits": "Max 12 months at once; 24 months in career"},
                    {"rule_id": "F.4", "rule_title": "Leave Encashment", "applies_to": ["all regular employees"], "content": "Encashment scenarios: (a) Full EL+HPL (up to 300 days) on superannuation, premature retirement, death. (b) During employment: only encashable leave account, once per year, after 2 years qualifying service; max encashable leave 150 days. (c) On resignation/quitting: 50% of non-encashable EL, max 75 days. (d) Disciplinary dismissal/removal: not eligible. (e) PRCE/contract employees: not eligible. Encashment amount: basic pay + special pay + DA; HRA/CCA not included.", "key_points": ["Full 300 days (EL+HPL) on superannuation/death", "During service: once/year from encashable account; after 2 years service", "Resignation: 50% non-encashable EL, max 75 days", "Disciplinary dismissal: no encashment", "Encashment = basic + DA (no HRA/CCA)"], "office_orders": ["O.O. No. PP/798/2008 dated 28.08.2008"], "approval_authority": "HR Department / Finance", "amounts_or_limits": "Max 300 days on superannuation; max 75 days on resignation"},
                    {"rule_id": "F.8", "rule_title": "Compensatory Rest", "applies_to": ["O&M non-executive employees only"], "content": "Compensatory rest granted when non-executive O&M employee works on weekly rest day in emergency. Max 3 days at one time. Must be availed within 30 days. Can be prefixed/suffixed to leave, CL, Sundays, holidays.", "key_points": ["O&M non-executives only", "Max 3 days at one time", "Must be availed within 30 days", "Can prefix/suffix to leave or holidays"], "office_orders": ["O.O. No. O&M/R&T-556 of 2004 dated 20.12.2004"], "approval_authority": "O&M HOD", "amounts_or_limits": "Max 3 days; within 30 days"},
                ],
                "tables": [
                    {"table_id": "F.T1", "table_title": "All Leave Types — Quick Reference", "description": "Summary of all 13 leave types with entitlement and key conditions", "data": [
                        {"leave_type": "Casual Leave (CL)", "entitlement": "8 days/yr (office); 12 days/yr (O&M/field)", "salary": "Full pay", "carry_forward": "No", "who_eligible": "All"},
                        {"leave_type": "Special Casual Leave (SCL)", "entitlement": "Max 30 days/year", "salary": "Full pay", "carry_forward": "No", "who_eligible": "All (specific purposes)"},
                        {"leave_type": "Earned Leave (EL)", "entitlement": "30 days/year; Max 300 days", "salary": "Full pay", "carry_forward": "Yes (max 300)", "who_eligible": "All regular"},
                        {"leave_type": "Half Pay Leave (HPL)", "entitlement": "20 days/year; No max accumulation", "salary": "50% pay", "carry_forward": "Yes (no limit)", "who_eligible": "All"},
                        {"leave_type": "Leave Not Due (LND)", "entitlement": "Max 360 days career; 180 days at once", "salary": "50% pay", "carry_forward": "N/A", "who_eligible": "Regular; after 1 yr; medical grounds"},
                        {"leave_type": "Commuted Leave", "entitlement": "Max 90 days for study; charged 2x HPL", "salary": "Full pay (EL rate)", "carry_forward": "N/A", "who_eligible": "All; medical or approved study"},
                        {"leave_type": "Extra Ordinary Leave (EOL)", "entitlement": "Max 2 years career (6 mths per 5 yrs)", "salary": "No pay", "carry_forward": "N/A", "who_eligible": "Regular; after 6 years service"},
                        {"leave_type": "WRIIL", "entitlement": "Full pay hospital + 6 mths; half pay 12 mths", "salary": "Full/Half", "carry_forward": "N/A", "who_eligible": "All (permanent and temporary)"},
                        {"leave_type": "Quarantine Leave", "entitlement": "Max 21 days (30 exceptional)", "salary": "Full pay", "carry_forward": "N/A", "who_eligible": "All (family infectious disease)"},
                        {"leave_type": "Maternity Leave", "entitlement": "182 days (≤2 children); 12 wks (>2)", "salary": "Full pay", "carry_forward": "N/A", "who_eligible": "Female regular/deputationist"},
                        {"leave_type": "Paternity Leave", "entitlement": "15 days", "salary": "Full pay", "carry_forward": "N/A", "who_eligible": "Male; <2 children"},
                        {"leave_type": "Child Care Leave (CCL)", "entitlement": "730 days entire career; max 3 spells/yr", "salary": "Full pay", "carry_forward": "N/A", "who_eligible": "Confirmed female; 2 yrs service; child <18"},
                        {"leave_type": "Study Leave", "entitlement": "Max 12 mths at once; 24 mths career", "salary": "Full pay + HRA (180d) + CCA (120d)", "carry_forward": "N/A", "who_eligible": "Regular; after 3 yrs service; MD approval"},
                    ]},
                ],
                "authority_index": [
                    {"action": "Sanction CL/SCL", "authority": "Controlling Officer", "rule_ref": "F.3.1, F.3.2"},
                    {"action": "Sanction EL/HPL/LND/Commuted Leave", "authority": "Competent Authority (as per SOP)", "rule_ref": "F.5.2"},
                    {"action": "Sanction EOL for non-supervisor (1st time)", "authority": "HOD", "rule_ref": "F.3.7"},
                    {"action": "Sanction EOL for supervisor/executive up to Manager", "authority": "Director", "rule_ref": "F.3.7"},
                    {"action": "Sanction EOL for Dy.HOD and above", "authority": "Managing Director", "rule_ref": "F.3.7"},
                    {"action": "Sanction Study Leave", "authority": "Managing Director", "rule_ref": "F.3.13.7"},
                    {"action": "Approve WRIIL (non-exec)", "authority": "HOD", "rule_ref": "F.3.8"},
                    {"action": "Approve WRIIL (exec)", "authority": "Director", "rule_ref": "F.3.8"},
                    {"action": "Sanction Maternity/Paternity/CCL", "authority": "Competent Authority / HOD", "rule_ref": "F.3.10,F.3.11,F.3.12"},
                    {"action": "Leave encashment during service", "authority": "HR Department / Finance", "rule_ref": "F.4.3"},
                    {"action": "Ex-India leave (Non-exec/AM/Manager up to 10 days)", "authority": "HOD", "rule_ref": "F.5.12"},
                    {"action": "Ex-India leave (AM/Manager beyond 10 days; Dy.HOD/HOD any duration)", "authority": "Director", "rule_ref": "F.5.12"},
                    {"action": "Rule interpretation/relaxation", "authority": "Managing Director", "rule_ref": "F.10"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/43/99", "date": "14.12.1999", "subject": "Casual Leave pro-rata on separation", "rule_ref": "F.3.1"},
                    {"oo_number": "O.O. No. PP/1525/2012", "date": "14.11.2012", "subject": "Casual Leave rules", "rule_ref": "F.3.1"},
                    {"oo_number": "O.O. No. PP/1359/2011", "date": "20.12.2011", "subject": "Consultant CL card maintenance", "rule_ref": "F.3.1.3"},
                    {"oo_number": "O.O. No. PP/2553/2018", "date": "20.03.2018", "subject": "SCL for Persons with Disabilities", "rule_ref": "F.3.2"},
                    {"oo_number": "O.O. No. PP/872/2009", "date": "29.01.2009", "subject": "PRCE employees leave entitlement", "rule_ref": "F.3.3"},
                    {"oo_number": "O.O. No. PP/2300/2016", "date": "15.11.2016", "subject": "PRCE leave continuation to consultant", "rule_ref": "F.3.3"},
                    {"oo_number": "O.O. No. PP/1788/2014", "date": "06.06.2014", "subject": "EL salary calculation", "rule_ref": "F.3.3.10"},
                    {"oo_number": "O.O. No. PP/1917/2015", "date": "06.02.2015", "subject": "EOL rules and deemed resignation", "rule_ref": "F.3.7"},
                    {"oo_number": "O.O. No. PP/3227/2022", "date": "03.11.2022", "subject": "WRIIL rules", "rule_ref": "F.3.8"},
                    {"oo_number": "O.O. No. HR/O&M/361/2022", "date": "15.12.2022", "subject": "WRIIL SOP", "rule_ref": "F.3.8"},
                    {"oo_number": "O.O. No. HR/O&M-140/2022", "date": "25.04.2022", "subject": "Maternity leave for >2 children", "rule_ref": "F.3.10"},
                    {"oo_number": "O.O. No. PP/820/2008", "date": "13.10.2008", "subject": "Maternity/Adoption/CCL rules", "rule_ref": "F.3.10,F.3.12"},
                    {"oo_number": "O.O. No. PP/807/2008", "date": "15.09.2008", "subject": "Paternity leave rules", "rule_ref": "F.3.11"},
                    {"oo_number": "O.O. No. PP/1955/2015", "date": "26.03.2015", "subject": "Maternity and paternity leave revision", "rule_ref": "F.3.10,F.3.11"},
                    {"oo_number": "O.O. No. PP/798/2008", "date": "28.08.2008", "subject": "Leave encashment rules for PRCE", "rule_ref": "F.4.10"},
                    {"oo_number": "O.O. No. PP/874/2009", "date": "04.02.2009", "subject": "Ex-India leave procedure", "rule_ref": "F.5.12"},
                    {"oo_number": "O.O. No. PP/2843/2019", "date": "27.06.2019", "subject": "Ex-India leave SOP revision", "rule_ref": "F.5.12"},
                    {"oo_number": "O.O. No. PP/3139/2021", "date": "26.10.2021", "subject": "Study leave eligibility revision", "rule_ref": "F.3.13"},
                    {"oo_number": "O.O. No. PP/1189/2010", "date": "14.12.2010", "subject": "Transfer of leave to other Govt. org", "rule_ref": "F.9"},
                ],
                "cross_references": [
                    {"from_rule": "F.3.7", "to_chapter": "B", "to_rule": "B.5.7", "relationship": "Absence >4 days without explanation = misconduct; EOL must be sanctioned"},
                    {"from_rule": "F.4", "to_chapter": "A", "to_rule": "A.20", "relationship": "Leave encashment entitlement on VRS governed by F.4.2"},
                    {"from_rule": "F.3.12", "to_chapter": "M", "to_rule": "M.4", "relationship": "LTC can be availed while on CCL"},
                    {"from_rule": "F.3.13", "to_chapter": "C", "to_rule": "C.4", "relationship": "HRA admissible for first 180 days of study leave"},
                    {"from_rule": "F.8", "to_chapter": "A", "to_rule": "A.7", "relationship": "Compensatory rest for O&M non-executives working on weekly off"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "G": {
                "chapter_id": "G",
                "chapter_title": "House Building Advance (HBA) Rules",
                "page_range": "187-276",
                "summary": "Governs the grant of advance to regular confirmed DMRC employees for construction, purchase, or enlargement of a house, including eligibility, advance limits, interest rates, repayment, and security requirements.",
                "key_topics": ["HBA Eligibility", "HBA Amount", "Cost Ceiling", "Interest Rates", "Repayment", "Disbursement", "Security/Mortgage", "Swapping of Home Loan", "Insurance"],
                "summary_chunk": (
                    "Chapter G — House Building Advance (HBA) Rules: "
                    "(1) Eligibility: Regular confirmed employees only; not applicable to deputationists, ad-hoc, temporary, re-employed, contract, daily-wage employees. "
                    "(2) Purpose: New construction, purchase of new house/flat, enlargement of existing house (after 5 years of possession). "
                    "(3) Cost Ceiling: 139 times basic pay, maximum Rs.1 Crore (excluding cost of land); can be relaxed up to 25% by sanctioning authority. "
                    "(4) HBA Amount: 60 times basic pay or Rs.40 lakh, whichever is less (for new construction/purchase). For enlargement: 60 times basic pay or Rs.20 lakh, whichever is less; only after 5 years. "
                    "(5) Interest Rates: Up to Rs.12 lakh: 5% p.a.; Rs.12-25 lakh: 7.5% p.a.; Above Rs.25 lakh: 9% p.a. Simple interest. "
                    "(6) Repayment: Principal in maximum 240 installments; recovery from salary; must complete before superannuation. "
                    "(7) Security: Employee must mortgage the house to DMRC; title deed to be submitted to DMRC."
                ),
                "rules": [
                    {"rule_id": "G.1", "rule_title": "Eligibility", "applies_to": ["regular confirmed employees"], "content": "HBA available only to regular and confirmed DMRC employees. Not applicable to deputationists, ad-hoc, temporary, re-employed, contract on fixed terms, daily-wage employees. Employee must not have built/purchased a house under any other govt. scheme.", "key_points": ["Regular confirmed employees only", "Excludes deputationists, contract, temporary, PRCE", "Cannot have prior govt. house building benefit", "Must not own house at work station"], "office_orders": [], "approval_authority": "Sanctioning Authority", "amounts_or_limits": ""},
                    {"rule_id": "G.7", "rule_title": "Cost Ceiling", "applies_to": ["all HBA applicants"], "content": "Cost ceiling of house (excluding land): 139 times basic pay, maximum Rs.1 Crore. Relaxable up to 25% in individual cases where sanctioning authority is satisfied on merits.", "key_points": ["Ceiling: 139 times basic pay or Rs.1 Crore (max)", "25% relaxation possible on merit", "Does not include cost of land"], "office_orders": ["O.O. No. PP/2752/2019 dated 30.01.2019"], "approval_authority": "Sanctioning Authority", "amounts_or_limits": "139 x basic pay; max Rs.1 Crore"},
                    {"rule_id": "G.8", "rule_title": "Amount of Advance", "applies_to": ["all HBA applicants"], "content": "HBA limit (including land): 60 times basic pay or Rs.40 lakh, whichever is less. For enlargement: 60 months basic pay or Rs.20 lakh or cost of enlargement or repaying capacity — whichever is least; only after 5 years of possession; only for Delhi/NCR.", "key_points": ["New house: min of (60x basic pay, Rs.40 lakh, cost, repaying capacity)", "Enlargement: min of (60x basic pay, Rs.20 lakh, cost, repaying capacity)", "Enlargement only after 5 years of possession", "Only Delhi/NCR for enlargement"], "office_orders": ["O.O. No. PP/1048/2010 dated 18.02.2010", "O.O. No. PP/2752/2019 dated 30.01.2019"], "approval_authority": "Sanctioning Authority / Director(F)", "amounts_or_limits": "Max Rs.40 lakh (new); Max Rs.20 lakh (enlargement); 60x basic pay limit"},
                    {"rule_id": "G.9", "rule_title": "Rate of Interest", "applies_to": ["all HBA borrowers"], "content": "Simple interest from date of first disbursement. Slab rates: Up to Rs.12 lakh: 5% p.a.; Rs.12-25 lakh: 7.5% p.a.; Above Rs.25 lakh: 9% p.a. For HBA enlargement: 9% p.a. Take-home salary after all deductions: minimum 50% of basic pay + DA.", "key_points": ["Slab: ≤Rs.12L → 5%; Rs.12-25L → 7.5%; >Rs.25L → 9%", "Simple interest", "Enlargement: 9% p.a.", "Take-home minimum: 50% of basic + DA after all deductions"], "office_orders": [], "approval_authority": "Finance Department", "amounts_or_limits": "5% / 7.5% / 9% p.a. (slab rates)"},
                    {"rule_id": "G.16", "rule_title": "Repayment", "applies_to": ["all HBA borrowers"], "content": "Principal repaid in maximum 240 monthly installments; interest in subsequent installments. Recovery from salary. Must be completed before superannuation. House must remain mortgaged to DMRC until full repayment.", "key_points": ["Max 240 monthly installments for principal", "Recovered from salary", "Must complete before superannuation", "House mortgaged to DMRC until full repayment"], "office_orders": [], "approval_authority": "Finance Department", "amounts_or_limits": "Max 240 installments"},
                ],
                "tables": [
                    {"table_id": "G.T1", "table_title": "HBA Interest Rate Slabs", "description": "Interest rates based on advance amount", "data": [{"advance_amount": "Up to Rs.12 lakh", "interest_rate": "5% per annum (simple interest)"}, {"advance_amount": "Rs.12 lakh to Rs.25 lakh", "interest_rate": "7.5% per annum (simple interest)"}, {"advance_amount": "Above Rs.25 lakh", "interest_rate": "9% per annum (simple interest)"}, {"advance_amount": "HBA for Enlargement (any amount)", "interest_rate": "9% per annum (simple interest)"}]},
                    {"table_id": "G.T2", "table_title": "HBA Key Limits", "description": "Amount limits for HBA under different purposes", "data": [{"purpose": "New house / flat construction or purchase", "max_amount": "Rs.40 lakh or 60x basic pay (whichever less)", "cost_ceiling": "139x basic pay max Rs.1 Crore"}, {"purpose": "Enlargement of existing house", "max_amount": "Rs.20 lakh or 60x basic pay (whichever less)", "cost_ceiling": "139x basic pay max Rs.1 Crore"}]},
                ],
                "authority_index": [
                    {"action": "Sanction HBA for executives", "authority": "Director (Finance)", "rule_ref": "G.HBA.sanction"},
                    {"action": "Relax cost ceiling (up to 25%)", "authority": "Sanctioning Authority", "rule_ref": "G.7"},
                    {"action": "Permission to sell mortgaged house", "authority": "DMRC (Finance)", "rule_ref": "G.16"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/2752/2019", "date": "30.01.2019", "subject": "HBA amount and cost ceiling revision", "rule_ref": "G.7,G.8"},
                    {"oo_number": "O.O. No. PP/1048/2010", "date": "18.02.2010", "subject": "HBA limits", "rule_ref": "G.8"},
                    {"oo_number": "O.O. No. PP/1520/2012", "date": "22.10.2012", "subject": "HBA rules revision", "rule_ref": "G.8"},
                ],
                "cross_references": [
                    {"from_rule": "G.1", "to_chapter": "A", "to_rule": "A.3", "relationship": "Only confirmed employees eligible; confirmation process in Chapter A"},
                    {"from_rule": "G.9", "to_chapter": "C", "to_rule": "C.1", "relationship": "Take-home salary (50% min) calculated on basic pay as defined in Chapter C"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "H": {
                "chapter_id": "H",
                "chapter_title": "Recruitment Rules",
                "page_range": "277-288",
                "summary": "Defines the framework for recruitment — categorization of posts, modes of direct recruitment, campus recruitment, contract regularization, compassionate appointment and probation in DMRC.",
                "key_topics": ["Recruitment Modes", "Direct Recruitment", "Campus Recruitment", "Compassionate Appointment", "Contract Regularization", "Post Retirement Contractual Employment", "Probation", "Character Verification"],
                "summary_chunk": (
                    "Chapter H — Recruitment Rules (DMRC Recruitment Rules 2021): "
                    "(1) Modes: Direct Recruitment, Deputation, Absorption, Post-Retirement Contractual Engagement, Lateral Induction, Compassionate Appointment. "
                    "(2) Direct Recruitment: Written test/interview; age min 18, max 28 (relaxation for SC/ST/OBC/PWD/ESM). "
                    "(3) Character Verification: Mandatory before final appointment. "
                    "(4) Training: Induction training at DMRA mandatory for all new recruits. "
                    "(5) Probation: 2 years for Non-Executive/AM/Manager; 1 year for DGM and above. "
                    "(6) PRCE: For retired employees on fixed-term contract; consolidated fee; not eligible for most benefits. "
                    "(7) Compassionate Appointment: For dependent family member of deceased/incapacitated employee; Screening Committee approval."
                ),
                "rules": [
                    {"rule_id": "H.1", "rule_title": "Short Title and Application", "applies_to": ["all employees"], "content": "DMRC Recruitment Rules 2021; in force from date of issuance. Applies to all recruitment in DMRC.", "key_points": ["DMRC Recruitment Rules 2021", "Effective from date of issue"], "office_orders": [], "approval_authority": "Board", "amounts_or_limits": ""},
                    {"rule_id": "H.5", "rule_title": "Direct Recruitment", "applies_to": ["new recruits"], "content": "Direct recruitment from open market through written test and/or interview. Age: minimum 18, maximum 28 for entry-level. Medical fitness mandatory. Character and antecedents verification mandatory. Surety bond of 3 years. All direct recruits undergo induction training at DMRA.", "key_points": ["Written test + interview", "Age 18-28 (with SC/ST/OBC/PWD/ESM relaxation)", "Medical fitness mandatory", "3-year surety bond", "DMRA induction training mandatory"], "office_orders": [], "approval_authority": "Competent Authority / MD", "amounts_or_limits": "Age 18-28"},
                    {"rule_id": "H.10", "rule_title": "Post-Retirement Contractual Employment", "applies_to": ["retired employees"], "content": "PRCE for retired employees engaged on fixed-term contract basis. Consolidated fee structure. Not eligible for most regular service benefits (no EL, HBA, vehicle advance, MPA, CCL etc.). Medical fitness required at time of engagement.", "key_points": ["Fixed-term contract only", "Consolidated fee (not regular pay)", "Not eligible for most service benefits", "Medical fitness at time of PRCE"], "office_orders": [], "approval_authority": "MD / Competent Authority", "amounts_or_limits": ""},
                    {"rule_id": "H.14", "rule_title": "Compassionate Appointment", "applies_to": ["dependents of deceased/incapacitated employees"], "content": "Compassionate appointment for dependent family member (spouse or child) of DMRC employee who dies in harness or is permanently incapacitated on medical grounds. Subject to vacancy availability and Screening Committee recommendation. Minimum age 18.", "key_points": ["For dependents of deceased/incapacitated employees", "Subject to vacancy availability", "Screening Committee approval", "Min age 18"], "office_orders": [], "approval_authority": "Screening Committee / MD", "amounts_or_limits": "Min age 18"},
                ],
                "tables": [],
                "authority_index": [
                    {"action": "Direct recruitment", "authority": "Competent Authority / MD (as per SOP)", "rule_ref": "H.5"},
                    {"action": "Compassionate appointment", "authority": "Screening Committee → MD", "rule_ref": "H.14"},
                    {"action": "PRCE engagement", "authority": "MD / Competent Authority", "rule_ref": "H.10"},
                ],
                "office_order_index": [],
                "cross_references": [
                    {"from_rule": "H.10", "to_chapter": "F", "to_rule": "F.3.3", "relationship": "PRCE employees get 1 special leave/month; not regular EL"},
                    {"from_rule": "H.10", "to_chapter": "G", "to_rule": "G.1", "relationship": "PRCE employees not eligible for HBA"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "I": {
                "chapter_id": "I",
                "chapter_title": "Vehicle Advance Rules",
                "page_range": "289-299",
                "summary": "Governs monetary advance to confirmed DMRC employees for purchase of new motor car or two-wheeler, including eligibility, amounts, interest, repayment, and sanctioning authority.",
                "key_topics": ["Vehicle Advance Eligibility", "Motor Car Advance", "Two-Wheeler Advance", "Interest Rate", "Repayment", "Sanctioning Authority", "Prior Intimation"],
                "summary_chunk": (
                    "Chapter I — Vehicle Advance Rules: "
                    "(1) Eligibility: Regular confirmed employees with 2.5 years service and min 3 years remaining; excludes deputationist/temporary/ad-hoc/re-employed/contract. "
                    "(2) Motor Car Advance: Supervisors and below (≤Rs.37000-115000): Rs.1.5 lakh or 25 months basic pay, vehicle ceiling Rs.6.75 lakh; Sr. Supervisors: Rs.3.5 lakh, ceiling Rs.9 lakh; Executives: Rs.5 lakh, ceiling Rs.15 lakh. "
                    "(3) Two-Wheeler Advance: All grades — Rs.1.5 lakh or 10 months basic pay, ceiling Rs.1.5 lakh. "
                    "(4) Prior Intimation: Mandatory before purchase through ESS under Conduct Rules. "
                    "(5) New vehicles only — no used vehicles."
                ),
                "rules": [
                    {"rule_id": "I.2", "rule_title": "Eligibility for Vehicle Advance", "applies_to": ["regular confirmed employees"], "content": "Advance admissible to regular confirmed employees with 2.5 years service and minimum 3 years remaining service before superannuation. Excludes deputationists, temporary, ad-hoc, re-employed, contract. Advance for new vehicles only.", "key_points": ["2.5 years service + 3 years remaining", "Regular confirmed only", "New vehicles only", "Contract service @70% after regularization"], "office_orders": ["O.O. No. PP/1499/2012 dated 26.06.2012"], "approval_authority": "Sanctioning Authority", "amounts_or_limits": "Min 2.5 years service; min 3 years remaining"},
                    {"rule_id": "I.motor_car", "rule_title": "Motor Car Advance Limits", "applies_to": ["all eligible employees"], "content": "Motor car advance: Supervisors and below (≤Rs.37000-115000): Rs.1.5 lakh or 25 months basic pay (ceiling vehicle cost Rs.6.75 lakh); Sr. Supervisors (Rs.40000-125000 to Rs.50000-160000 non-exec): Rs.3.5 lakh (ceiling Rs.9 lakh); Executives (Rs.50000-160000 and above): Rs.5 lakh (ceiling Rs.15 lakh).", "key_points": ["Supervisor/below: Rs.1.5L advance / Rs.6.75L vehicle ceiling", "Sr. Supervisor: Rs.3.5L advance / Rs.9L vehicle ceiling", "Executive: Rs.5L advance / Rs.15L vehicle ceiling", "25 months basic pay alternate limit"], "office_orders": ["O.O. No. PP/3341/2023 dated 06.09.2023"], "approval_authority": "Director(F) / ED/HR / GM/O&M/HR", "amounts_or_limits": "Rs.1.5L to Rs.5L (grade-wise); Vehicle ceiling Rs.6.75L to Rs.15L"},
                    {"rule_id": "I.two_wheeler", "rule_title": "Two-Wheeler Advance Limits", "applies_to": ["all grades"], "content": "Two-wheeler (Motor Bike/Scooter) advance: All grades — Rs.1.5 lakh or 10 months basic pay, whichever less; vehicle ceiling Rs.1.5 lakh.", "key_points": ["Same for all grades", "Rs.1.5 lakh or 10 months basic pay", "Vehicle ceiling: Rs.1.5 lakh"], "office_orders": ["O.O. No. PP/2349/2017 dated 03.04.2017"], "approval_authority": "Director(F) / ED/HR / GM/O&M/HR", "amounts_or_limits": "Rs.1.5 lakh or 10 months basic pay"},
                ],
                "tables": [
                    {"table_id": "I.T1", "table_title": "Motor Car Advance Limits by Grade", "description": "Vehicle advance amount and vehicle cost ceiling for each grade", "data": [{"grade": "Supervisors and below (≤Rs.37000-115000 IDA)", "advance_limit": "Rs.1.5 lakh or 25 months basic pay (whichever less)", "vehicle_cost_ceiling": "Up to Rs.6.75 lakh"}, {"grade": "Sr. Supervisors (Rs.40000-125000 to Rs.50000-160000 non-exec)", "advance_limit": "Rs.3.5 lakh or 25 months basic pay (whichever less)", "vehicle_cost_ceiling": "Up to Rs.9 lakh"}, {"grade": "Executives (Rs.50000-160000 IDA and above)", "advance_limit": "Rs.5 lakh or 25 months basic pay (whichever less)", "vehicle_cost_ceiling": "Up to Rs.15 lakh"}]},
                    {"table_id": "I.T2", "table_title": "Two-Wheeler Advance Limits", "description": "Motor bike/scooter advance for all grades", "data": [{"grade": "All grades", "advance_limit": "Rs.1.5 lakh or 10 months basic pay (whichever less)", "vehicle_cost_ceiling": "Up to Rs.1.5 lakh"}]},
                ],
                "authority_index": [
                    {"action": "Vehicle advance for executives", "authority": "Director (Finance)", "rule_ref": "I.4"},
                    {"action": "Vehicle advance for non-executives (Project/Corporate)", "authority": "ED/HR", "rule_ref": "I.4"},
                    {"action": "Vehicle advance for non-executives (O&M)", "authority": "GM/O&M/HR", "rule_ref": "I.4"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/3341/2023", "date": "06.09.2023", "subject": "Motor car advance limits revision", "rule_ref": "I.motor_car"},
                    {"oo_number": "O.O. No. PP/2349/2017", "date": "03.04.2017", "subject": "Two-wheeler advance limits", "rule_ref": "I.two_wheeler"},
                    {"oo_number": "O.O. No. PP/1499/2012", "date": "26.06.2012", "subject": "No vehicle advance for used vehicles", "rule_ref": "I.2"},
                ],
                "cross_references": [
                    {"from_rule": "I.2", "to_chapter": "B", "to_rule": "B.16", "relationship": "Vehicle purchase requires prior intimation under Conduct Rules (movable property)"},
                    {"from_rule": "I.2", "to_chapter": "A", "to_rule": "A.3", "relationship": "Only confirmed employees eligible; confirmation in Chapter A"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "J": {
                "chapter_id": "J",
                "chapter_title": "Multi-Purpose Advance (MPA) Rules",
                "page_range": "300-310",
                "summary": "Governs the grant of Multi-Purpose Advance to confirmed DMRC employees for emergent financial needs like marriage, education, house furnishing, electronic appliances and other domestic contingencies.",
                "key_topics": ["MPA Eligibility", "MPA Amount", "Interest Rate", "Surety Bonds", "Repayment", "Sanctioning Authority"],
                "summary_chunk": (
                    "Chapter J — Multi-Purpose Advance (MPA) Rules: "
                    "(1) Objective: Grant monetary advance for emergent needs — marriage/social functions, education of children, house furnishing, electronic appliances, domestic requirements. "
                    "(2) Eligibility: Confirmed employees with 2.5 years service and more than 3 years remaining before superannuation. "
                    "(3) Amount: Up to Rs.2,00,000 or 5 times basic pay, whichever is less. "
                    "(4) Frequency: Maximum 3 occasions in entire service; next MPA only after 2 years from complete repayment of previous MPA. "
                    "(5) Interest: 7.5% simple interest. Principal recovered in max 30 installments; interest in max next 5 installments. "
                    "(6) Surety Bonds: One surety for MPA up to Rs.50,000; two sureties for above Rs.50,000."
                ),
                "rules": [
                    {"rule_id": "J.2", "rule_title": "MPA Eligibility", "applies_to": ["confirmed employees"], "content": "MPA to confirmed employees with 2.5 years service and more than 3 years remaining before superannuation. Excludes temporary, ad-hoc, daily-rated, re-employed, contract. Fresh cases prioritized over second/third MPA.", "key_points": ["Confirmed employees only", "2.5 years service + 3 years remaining", "Max 3 occasions in entire service", "2 years gap between MPAs", "Fresh cases get priority"], "office_orders": ["O.O. No. PP/538/2006 dated 30.10.2006", "O.O. No. PP/1520/2012 dated 22.10.2012"], "approval_authority": "HOD/HR", "amounts_or_limits": "2.5 years service minimum; max 3 times in career"},
                    {"rule_id": "J.3", "rule_title": "MPA Amount", "applies_to": ["eligible confirmed employees"], "content": "MPA admissible up to maximum Rs.2,00,000 or 5 times basic pay, whichever is less.", "key_points": ["Max Rs.2 lakh or 5x basic pay (lower of two)"], "office_orders": ["O.O. No. PP/2776/2018 dated 22.02.2019"], "approval_authority": "HOD/HR", "amounts_or_limits": "Max Rs.2,00,000 or 5x basic pay"},
                    {"rule_id": "J.5", "rule_title": "MPA Interest and Repayment", "applies_to": ["all MPA borrowers"], "content": "Interest rate: 7.5% simple. Principal: recovered in maximum 30 monthly installments. Interest: recovered in maximum next 5 installments after principal recovery. Total recovery (including all other deductions) must not exceed 50% of pay.", "key_points": ["Interest: 7.5% simple", "Principal: max 30 installments", "Interest: max 5 installments after principal", "Total recovery capped at 50% of pay"], "office_orders": ["O.O. No. PP/538/2006 dated 30.10.2006"], "approval_authority": "Finance Department", "amounts_or_limits": "7.5% interest; max 35 total installments; 50% pay cap"},
                ],
                "tables": [
                    {"table_id": "J.T1", "table_title": "MPA Key Parameters", "description": "Summary of Multi-Purpose Advance rules", "data": [{"parameter": "Maximum amount", "value": "Rs.2,00,000 or 5x basic pay (whichever less)"}, {"parameter": "Eligibility", "value": "Confirmed; 2.5 years service; 3 years remaining"}, {"parameter": "Maximum occasions", "value": "3 times in entire service"}, {"parameter": "Gap between MPAs", "value": "2 years after full repayment"}, {"parameter": "Interest rate", "value": "7.5% simple interest"}, {"parameter": "Principal repayment", "value": "Max 30 monthly installments"}, {"parameter": "Interest repayment", "value": "Max 5 installments after principal"}, {"parameter": "Surety", "value": "1 surety up to Rs.50,000; 2 sureties above Rs.50,000"}, {"parameter": "Total recovery cap", "value": "50% of pay"}]},
                ],
                "authority_index": [
                    {"action": "Sanction MPA (Project/Corporate office)", "authority": "HOD/HR", "rule_ref": "J.4"},
                    {"action": "Sanction MPA (O&M division)", "authority": "HOD/HR/O&M", "rule_ref": "J.4"},
                    {"action": "Rule interpretation", "authority": "Managing Director", "rule_ref": "J.7"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/538/2006", "date": "30.10.2006", "subject": "MPA Rules introduction", "rule_ref": "J.1"},
                    {"oo_number": "O.O. No. PP/2776/2018", "date": "22.02.2019", "subject": "MPA amount revision to Rs.2 lakh", "rule_ref": "J.3"},
                    {"oo_number": "O.O. No. PP/1520/2012", "date": "22.10.2012", "subject": "MPA 3-occasion limit and 2-year gap", "rule_ref": "J.2"},
                    {"oo_number": "O.O. No. PP/1572/2013", "date": "06.03.2013", "subject": "Surety bond requirements for MPA", "rule_ref": "J.6"},
                    {"oo_number": "O.O. No. PP/1782/2014", "date": "03.06.2014", "subject": "Contract service @70% for MPA eligibility", "rule_ref": "J.2"},
                ],
                "cross_references": [
                    {"from_rule": "J.2", "to_chapter": "A", "to_rule": "A.3", "relationship": "Confirmation is prerequisite for MPA eligibility"},
                    {"from_rule": "J.5", "to_chapter": "C", "to_rule": "C.1", "relationship": "50% pay cap calculated on basic pay"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "K": {
                "chapter_id": "K",
                "chapter_title": "Housing Allotment Rules",
                "page_range": "311-328",
                "summary": "Governs allotment, retention, surrender and management of DMRC staff quarters at various locations in Delhi/NCR.",
                "key_topics": ["Housing Eligibility", "Types of Accommodation", "Priority List", "License Fee", "Allotment Process", "Retention", "Subletting Prohibition", "Essential Quota", "HRA and Quarters"],
                "summary_chunk": (
                    "Chapter K — Housing Allotment Rules: "
                    "(1) Locations: Staff quarters at Ajronda, Bahadurgarh, Gurgaon, Mukundpur, Mundka, Najafgarh, New Ashok Nagar, Sarita Vihar, Shastri Park, Vinod Nagar, Yamuna Bank and Noida. "
                    "(2) Eligibility: All regular employees (including probationers); excludes casual/reemployed/deputationist/contract employees. "
                    "(3) Types: 7 types of accommodation — Type-II (1 BHK) for all grades up to Rs.35000-110000 Non-Supervisor, higher types for higher grades. "
                    "(4) HRA: Not payable if DMRC quarters are occupied. "
                    "(5) Subletting: Strictly prohibited; subletting = misconduct under Conduct Rules (B.5.24). "
                    "(6) Retention: Vacating required within one month of transfer/superannuation/resignation. "
                    "(7) Employees with own house at current station not eligible."
                ),
                "rules": [
                    {"rule_id": "K.1", "rule_title": "Applicability", "applies_to": ["all regular employees including probationers"], "content": "Rules apply to all residential buildings allotted to DMRC employees. Employees occupy quarters as licensees. No employee has right to be provided accommodation. Subject to availability.", "key_points": ["Occupants are licensees — not owners or tenants", "No right to accommodation", "Subject to availability", "Probationers included"], "office_orders": [], "approval_authority": "Estate Officer", "amounts_or_limits": ""},
                    {"rule_id": "K.3", "rule_title": "Types of Accommodation", "applies_to": ["all employees"], "content": "7 types of accommodation: Type-II Transit Flats (1 BHK+WC+Kitchen) for all grades up to Rs.35000-110000 non-supervisor; higher types for higher grades as per seniority and grade.", "key_points": ["7 types of quarters", "Grade-wise entitlement", "Type-II (1 BHK) for non-supervisors up to Rs.35000-110000", "Higher types for higher grades"], "office_orders": [], "approval_authority": "Estate Officer", "amounts_or_limits": ""},
                    {"rule_id": "K.12", "rule_title": "HRA, Subletting and Retention", "applies_to": ["all quarter occupants"], "content": "HRA not payable while occupying DMRC quarters; employee must forego HRA. Subletting of quarters strictly prohibited — constitutes misconduct under Rule B.5.24. Quarters must be vacated within one month of transfer/superannuation/resignation. Penal rent for unauthorized occupation. Employees with own house at current station not eligible.", "key_points": ["HRA not payable while in DMRC quarters", "Subletting = misconduct (B.5.24)", "Vacate within 1 month of transfer/superannuation", "Penal rent for unauthorized occupation", "Own house at station = not eligible"], "office_orders": [], "approval_authority": "Estate Officer / HR", "amounts_or_limits": "Vacate within 1 month"},
                ],
                "tables": [],
                "authority_index": [
                    {"action": "Quarter allotment", "authority": "Estate Officer", "rule_ref": "K.allotment"},
                    {"action": "Essential quota allotment", "authority": "Competent Authority / HOD", "rule_ref": "K.12"},
                    {"action": "Action for subletting", "authority": "Estate Officer / HR (Disciplinary)", "rule_ref": "K.12"},
                ],
                "office_order_index": [],
                "cross_references": [
                    {"from_rule": "K.12", "to_chapter": "C", "to_rule": "C.4", "relationship": "HRA not payable while DMRC quarters occupied; HRA rates in Chapter C"},
                    {"from_rule": "K.12", "to_chapter": "B", "to_rule": "B.5.24", "relationship": "Subletting quarters = misconduct under Conduct Rules"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "L": {
                "chapter_id": "L",
                "chapter_title": "Staff Welfare Fund Rules",
                "page_range": "329-340",
                "summary": "Governs the DMRC Staff Welfare Fund — its sources, management, objectives and welfare activities including marriage grants, child birth gifts, education assistance, sickness benefits and recreation.",
                "key_topics": ["Fund Sources", "Fund Management", "Welfare Activities", "Marriage Grant", "Child Birth Gift", "Education Grant", "Sickness Relief", "Sports & Recreation", "Disability Grant"],
                "summary_chunk": (
                    "Chapter L — Staff Welfare Fund Rules: "
                    "(1) Members: All regular and contract employees on regular pay scale; excludes deputationists, PRCE, consultants, daily-wage, apprentices. "
                    "(2) Fund Sources: (a) Monthly member contributions; (b) Voluntary donations; (c) Interest on investments; (d) Annual DMRC matching contribution (equal to members' total monthly contributions of previous year, credited every April). "
                    "(3) Welfare Activities: Marriage gift (member + first 2 children); Child birth gift (first 2 children only); Disabled child grant; Sports excellence cash award; Education grants (10th/12th + admission + Tablet PC for daughter + professional degree award); Recreation grants; Sickness (terminal disease assistance, artificial limbs, funeral expenses). "
                    "(4) Management: Committee nominated by MD — HOD-level Chairman, Dy.HOD Deputy Chairman; Tenure 2 years."
                ),
                "rules": [
                    {"rule_id": "L.2", "rule_title": "Membership and Family Definition", "applies_to": ["regular and contract employees on regular pay scale"], "content": "Members: regular and contract employees; excludes deputationists, PRCE, consultants, daily-wage, apprentices. Family: spouse, children (son <25/not employed; unmarried unemployed daughter), dependent parents (income <15% basic pay or Rs.9000+DR).", "key_points": ["Includes regular + contract on regular pay scale", "Excludes deputationist, PRCE, consultant", "Same family definition as medical/LTC rules"], "office_orders": [], "approval_authority": "Committee", "amounts_or_limits": "Parent income: <15% basic or Rs.9000+DR"},
                    {"rule_id": "L.5", "rule_title": "Fund Sources", "applies_to": ["all members"], "content": "Sources: (a) Monthly member contributions at approved rates; (b) Voluntary donations; (c) Miscellaneous receipts (interest, charity shows); (d) Annual DMRC matching contribution (equal to members' total monthly contributions of previous year), credited every April.", "key_points": ["Monthly member contributions", "Voluntary donations permitted", "DMRC annual matching contribution in April"], "office_orders": [], "approval_authority": "Committee / MD", "amounts_or_limits": "DMRC matches previous year's member contributions"},
                    {"rule_id": "L.6", "rule_title": "Welfare Activities", "applies_to": ["all members and their families"], "content": "Key welfare benefits: (1) Marriage gift — member's own marriage and first 2 children; (2) Child birth gift — first 2 children only; (3) Disabled child grant; (4) One-time grant to family of deceased member (when no compassionate appointment); (5) Sports excellence cash award; (6) Education grants — 10th/12th qualification, admission grant, Tablet PC (one daughter, non-supervisor), professional degree cash award for daughters; (7) Recreation — clubs, sports, cultural, picnics; (8) Sickness — terminal disease financial assistance, artificial limbs, funeral expenses.", "key_points": ["Marriage grant: member + first 2 children", "Child birth: first 2 children only", "Education: 10th/12th + admission + degree completion grants", "Tablet PC: one daughter, non-supervisor grade", "Terminal illness, artificial limb, funeral expenses covered"], "office_orders": [], "approval_authority": "Committee → MD approval", "amounts_or_limits": ""},
                ],
                "tables": [],
                "authority_index": [
                    {"action": "Approve fund allocation", "authority": "Committee → MD", "rule_ref": "L.7"},
                    {"action": "Disburse from fund", "authority": "Chairman + Secretary of Committee (joint)", "rule_ref": "L.9"},
                    {"action": "Nominate Committee members", "authority": "Managing Director", "rule_ref": "L.3"},
                ],
                "office_order_index": [],
                "cross_references": [
                    {"from_rule": "L.2", "to_chapter": "E", "to_rule": "E.family_def", "relationship": "Same family definition as Medical Attendance Rules"},
                    {"from_rule": "L.6.iv", "to_chapter": "H", "to_rule": "H.14", "relationship": "One-time grant to deceased member's family only where no compassionate appointment given"},
                ],
            },

            # ─────────────────────────────────────────────────────────────────
            "M": {
                "chapter_id": "M",
                "chapter_title": "Leave Travel Concession (LTC) Rules",
                "page_range": "341-352",
                "summary": "Governs the Leave Travel Concession entitlement for DMRC employees including home town LTC, all-India LTC, block years, travel entitlement, incidental charges, LTC advance, and special provisions for NER/J&K/A&N/Ladakh.",
                "key_topics": ["LTC Entitlement", "Home Town LTC", "All-India LTC", "Block Year", "Travel Entitlement", "Incidental Charges", "LTC Advance", "Special LTC (NER/J&K/A&N/Ladakh)", "Split LTC", "Home Town Declaration"],
                "summary_chunk": (
                    "Chapter M — Leave Travel Concession (LTC) Rules: "
                    "(1) Applicability: All regular employees and contractual on regular pay scale with minimum 1 year service; absorbed deputationists. "
                    "(2) LTC Types: (a) Home Town LTC — once in a block of 2 calendar years, shortest route to hometown and back; (b) All-India LTC — once in a block of 4 calendar years, anywhere in India and back. If All-India LTC not availed in 4-year block, one additional Home Town LTC allowed. "
                    "(3) Block Years: 4-year blocks — 01.01.2014-31.12.2017, 01.01.2018-31.12.2022, 01.01.2023-31.03.2025, etc. Minimum 6-month gap between two LTCs. "
                    "(4) Travel Entitlement: Non-Supervisors: 2nd Sleeper; Supervisors and executives as per TA/DA grade. Executives from Rs.50000-160000: Air Economy / AC-2 Tier. Higher executives: Air Business/Highest. "
                    "(5) Incidental Charges (All-India LTC only): Non-supervisors Rs.3750; Supervisors Rs.5250; Executives below HOD Rs.6000; HOD and above Rs.9000. "
                    "(6) LTC Advance: Up to 90% of estimated fare; settlement within 30 days; 10% p.a. interest on delayed settlement. "
                    "(7) Special LTC (NER/J&K/A&N/Ladakh): Air travel allowed to Non-Executives against conversion of one Home Town LTC; tickets booked 21 days in advance."
                ),
                "rules": [
                    {"rule_id": "M.1", "rule_title": "Applicability", "applies_to": ["all regular employees", "contractual on regular pay scale with 1 yr service", "absorbed deputationists"], "content": "LTC applies to all regular employees and contractual on regular pay scales who have completed at least 1 year of continuous service. Includes permanently absorbed deputationists. Excludes casual employees, retired personnel on re-employment/short-term contract.", "key_points": ["Min 1 year continuous service required", "Regular + contractual on regular pay scale", "Retired re-employed: excluded"], "office_orders": ["O.O. No. PP/1326/2011 dated 17.10.2011"], "approval_authority": "Competent Authority", "amounts_or_limits": "Min 1 year service"},
                    {"rule_id": "M.4", "rule_title": "LTC Entitlement — Types and Block Years", "applies_to": ["all eligible employees"], "content": "Home Town LTC: Once in a block of 2 years (direct/shortest route to hometown). All-India LTC: Once in a block of 4 years. If All-India LTC not availed in 4-year block: one extra Home Town LTC allowed. Minimum 6-month gap between two LTCs. LTC must be availed during leave. Employees whose hometown and headquarters are same: not eligible for hometown LTC.", "key_points": ["Home Town: once in 2-year block", "All-India: once in 4-year block", "If All-India not availed: extra Hometown LTC allowed", "Min 6-month gap between LTCs", "Must be on leave to avail LTC", "Same hometown + HQ = no hometown LTC"], "office_orders": ["O.O. No. PP/1751/2014 dated 07.03.2014", "O.O. No. PP/3236/2022 dated 16.12.2022"], "approval_authority": "HOD / Competent Authority", "amounts_or_limits": "1 Home Town per 2 years; 1 All-India per 4 years"},
                    {"rule_id": "M.4.2.2", "rule_title": "Special LTC — NER/J&K/A&N/Ladakh", "applies_to": ["all eligible employees"], "content": "Air travel permitted to Non-Executives visiting NER/J&K/A&N/Ladakh against conversion of one Home Town LTC. Executives entitled to air in entitled class. Tickets must be booked min 21 days in advance through authorized agents. LTC advance settlement within 30 days; 10% p.a. interest on delayed settlement.", "key_points": ["Non-executives can fly Economy to NER/J&K/A&N/Ladakh", "Against conversion of one Home Town LTC", "Tickets: min 21 days advance, authorized agents only", "Settlement within 30 days; 10% interest on delay"], "office_orders": ["O.O. No. PP/3234/2022 dated 14.12.2022", "O.O. No. PP/3284/2023 dated 01.05.2023"], "approval_authority": "Competent Authority / HOD", "amounts_or_limits": "Tickets: 21 days advance booking; Settlement: 30 days"},
                    {"rule_id": "M.incidentals", "rule_title": "Incidental Charges", "applies_to": ["employees availing All-India LTC"], "content": "Incidental charges for All-India LTC: Non-supervisors Rs.3750; Supervisors Rs.5250; Executives below HOD Rs.6000; Executives HOD and above Rs.9000. Only for All-India LTC (not Home Town LTC).", "key_points": ["Non-supervisors: Rs.3750", "Supervisors: Rs.5250", "Executives below HOD: Rs.6000", "HOD and above: Rs.9000", "Only for All-India LTC (not Hometown)"], "office_orders": ["O.O. No. PP/1987/2015 dated 22.05.2015"], "approval_authority": "Finance Department", "amounts_or_limits": "Rs.3750 to Rs.9000"},
                ],
                "tables": [
                    {"table_id": "M.T1", "table_title": "LTC Travel Entitlement by Pay Scale", "description": "Class of travel entitled during LTC by grade", "data": [{"pay_scale_ida": "16000-50000", "entitlement": "2nd Sleeper Class"}, {"pay_scale_ida": "20000-60000 to 35000-110000", "entitlement": "1st Class / AC 3-Tier"}, {"pay_scale_ida": "37000-115000 to 50000-160000 (Non-Exec)", "entitlement": "AC 2-Tier; Rajdhani-AC 3-Tier; AC Bus"}, {"pay_scale_ida": "50000-160000 (Exec) to 60000-180000", "entitlement": "AC 2-Tier; Air Economy"}, {"pay_scale_ida": "70000-200000 to 100000-260000", "entitlement": "1st AC; Air Economy (Y class)"}, {"pay_scale_ida": "120000-280000 to 150000-300000", "entitlement": "Air Domestic (Highest class)"}, {"pay_scale_ida": "MD and Directors", "entitlement": "Air Domestic (Highest class)"}]},
                    {"table_id": "M.T2", "table_title": "Incidental Charges for All-India LTC", "description": "Incidental charges by employee category", "data": [{"category": "Non-supervisors", "incidental_rs": "3750"}, {"category": "Supervisors", "incidental_rs": "5250"}, {"category": "Executives below HOD level", "incidental_rs": "6000"}, {"category": "Executives HOD and above", "incidental_rs": "9000"}]},
                ],
                "authority_index": [
                    {"action": "Sanction LTC leave", "authority": "Competent Authority (as per SOP)", "rule_ref": "M.4"},
                    {"action": "Approve Split LTC", "authority": "HOD", "rule_ref": "M.4.2"},
                    {"action": "Approve change of Home Town", "authority": "MD / Functional Director", "rule_ref": "M.3.4"},
                    {"action": "Sanction LTC advance", "authority": "Finance Department", "rule_ref": "M.advance"},
                ],
                "office_order_index": [
                    {"oo_number": "O.O. No. PP/1326/2011", "date": "17.10.2011", "subject": "LTC applicability and rules", "rule_ref": "M.1"},
                    {"oo_number": "O.O. No. PP/1751/2014", "date": "07.03.2014", "subject": "LTC block year change + extra hometown LTC", "rule_ref": "M.4"},
                    {"oo_number": "O.O. No. PP/3234/2022", "date": "14.12.2022", "subject": "Special LTC NER/J&K/A&N/Ladakh extension", "rule_ref": "M.4.2.2"},
                    {"oo_number": "O.O. No. PP/3284/2023", "date": "01.05.2023", "subject": "Special LTC reimbursement at LTC-80 rates", "rule_ref": "M.4.2.2"},
                    {"oo_number": "O.O. No. PP/1987/2015", "date": "22.05.2015", "subject": "LTC travel entitlement and incidental charges", "rule_ref": "M.incidentals"},
                    {"oo_number": "O.O. No. PP/3236/2022", "date": "16.12.2022", "subject": "LTC eligibility for same hometown and HQ", "rule_ref": "M.4"},
                ],
                "cross_references": [
                    {"from_rule": "M.4", "to_chapter": "F", "to_rule": "F.3.12", "relationship": "LTC can be availed while on Child Care Leave (CCL)"},
                    {"from_rule": "M.4", "to_chapter": "D", "to_rule": "D.6", "relationship": "LTC travel entitlement follows same grade-wise mode as TA/DA tour entitlement"},
                    {"from_rule": "M.3.2", "to_chapter": "E", "to_rule": "E.family_def", "relationship": "Same family definition as Medical Attendance Rules"},
                ],
            },
        },
    }

    # ── Master indexes ──────────────────────────────────────────────────────
    kb["master_authority_index"] = [
        {"action": "All rule interpretations/relaxations", "authority": "Managing Director", "chapters": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]},
        {"action": "Superannuation extension", "authority": "Board of Directors", "chapter": "A"},
        {"action": "EOL sanction for non-supervisors (1st time)", "authority": "HOD", "chapter": "F"},
        {"action": "EOL sanction for Supervisors/Execs up to Manager", "authority": "Director", "chapter": "F"},
        {"action": "EOL sanction for Dy.HOD and above", "authority": "Managing Director", "chapter": "F"},
        {"action": "Study Leave sanction", "authority": "Managing Director", "chapter": "F"},
        {"action": "Ex-India leave (Non-exec/AM/Manager ≤10 days)", "authority": "HOD", "chapter": "F"},
        {"action": "Ex-India leave (AM/Mgr >10 days; Dy.HOD/HOD any)", "authority": "Director", "chapter": "F"},
        {"action": "HBA sanction for executives", "authority": "Director (Finance)", "chapter": "G"},
        {"action": "Vehicle advance for executives", "authority": "Director (Finance)", "chapter": "I"},
        {"action": "Vehicle advance for non-executives (O&M)", "authority": "GM/O&M/HR", "chapter": "I"},
        {"action": "MPA sanction", "authority": "HOD/HR", "chapter": "J"},
        {"action": "Quarter allotment", "authority": "Estate Officer", "chapter": "K"},
        {"action": "Prolonged medical treatment approval", "authority": "HOD (non-exec) / Director (exec)", "chapter": "E"},
        {"action": "WRIIL approval", "authority": "HOD (non-exec) / Director (exec)", "chapter": "F"},
        {"action": "LTC advance sanction", "authority": "Finance Department", "chapter": "M"},
        {"action": "Change of Home Town (LTC)", "authority": "MD / Functional Director", "chapter": "M"},
        {"action": "Major penalty (dismissal/removal)", "authority": "As per Schedule A, Chapter B", "chapter": "B"},
        {"action": "Minor penalty (censure etc.)", "authority": "As per Schedule A, Chapter B", "chapter": "B"},
        {"action": "Staff Welfare Fund allocation", "authority": "Committee → Managing Director", "chapter": "L"},
    ]

    # Build master OO index from all chapters
    kb["master_oo_index"] = []
    for ch_id, ch_data in kb["chapters"].items():
        for oo in ch_data.get("office_order_index", []):
            entry = dict(oo)
            entry["chapter"] = ch_id
            kb["master_oo_index"].append(entry)

    # Build master cross-reference index from all chapters
    kb["master_cross_reference"] = []
    for ch_id, ch_data in kb["chapters"].items():
        for cr in ch_data.get("cross_references", []):
            entry = dict(cr)
            entry["source_chapter"] = ch_id
            kb["master_cross_reference"].append(entry)

    # Consolidated leave types summary
    kb["leave_types_complete"] = {
        "summary_for_chatbot": (
            "DMRC employees are entitled to the following 13 types of leave under Chapter F of the HR Compendium: "
            "(1) Casual Leave — 8 days/year (office, 5-day week) or 12 days/year (O&M/field, 6-day week); "
            "(2) Special Casual Leave — up to 30 days/year for specific approved purposes; "
            "(3) Earned Leave — 30 days/year credited half-yearly, max 300 days accumulation; "
            "(4) Half Pay Leave — 20 days/year, leave salary at 50% of pay; "
            "(5) Leave Not Due — on medical grounds, max 360 days in career; "
            "(6) Commuted Leave — on medical grounds or approved study, charged at double HPL; "
            "(7) Extra Ordinary Leave — when no other leave due, max 2 years career, no pay; "
            "(8) Work Related Illness and Injury Leave (WRIIL) — for job-related injury/illness, full pay during hospitalization and 6 months after; "
            "(9) Quarantine Leave — up to 21 days for infectious disease in household; "
            "(10) Maternity Leave — 182 days (26 weeks) for up to 2 children; 12 weeks for more than 2 children; "
            "(11) Paternity Leave — 15 days for male employees with less than 2 children; "
            "(12) Child Care Leave — 730 days (2 years) in entire career for confirmed female employees; "
            "(13) Study Leave — after 3 years service, max 24 months in career, MD approval required."
        ),
        "count": 13,
        "types": [
            "Casual Leave", "Special Casual Leave", "Earned Leave", "Half Pay Leave",
            "Leave Not Due", "Commuted Leave", "Extra Ordinary Leave", "WRIIL",
            "Quarantine Leave", "Maternity Leave", "Paternity Leave", "Child Care Leave", "Study Leave",
        ],
    }

    return kb


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DMRC HR Compendium structured knowledge base JSON")
    parser.add_argument(
        "--out",
        default="data/dmrc_hr_knowledge_base.json",
        help="Output path for the JSON file (default: data/dmrc_hr_knowledge_base.json)",
    )
    args = parser.parse_args()

    kb = build()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(kb, fh, indent=2, ensure_ascii=False)

    size_kb = out_path.stat().st_size / 1024
    chapters = len(kb["chapters"])
    oo_count = len(kb["master_oo_index"])
    xref_count = len(kb["master_cross_reference"])

    print(f"Knowledge base written to: {out_path}")
    print(f"  Chapters         : {chapters}")
    print(f"  Master OO index  : {oo_count} entries")
    print(f"  Cross-references : {xref_count} entries")
    print(f"  File size        : {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
