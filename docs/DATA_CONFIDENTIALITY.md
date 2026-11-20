# Confidentiality of HR and payroll data

> Rules applied in this repository (all people data is SIMULATED, with pseudonymous ids E0001...), and proposed for production.

## Rules
1. **Aggregates only.** Payroll cost, salary and headcount are published at company or department level. No person-level table leaves the warehouse (`int_employee_month` is internal; marts are aggregated).
2. **No group under 5 people.** Any payroll figure for a group of fewer than 5 paid people is blanked (`suppressed_small_group = true` in `fct_headcount_payroll`). Breakdowns that could isolate a person (department x level x location) are not built.
3. **Pseudonyms.** Employees are identified by an id (`E0001`), never by name, in analytics. The link id <-> person stays in the HRIS and the payroll tool.
4. **Restricted access.** Raw HRIS and payroll exports sit in a restricted schema (People team, Head of Finance, Finance Data Analyst). Metabase collections with payroll views are restricted to Finance leadership; everybody else sees headcount and FTE only.
5. **Minimum data.** Only the columns needed for headcount and cost: no address, birth date, social security number, bank details or health data are loaded.
6. **Retention and logs.** Raw payroll extracts are deleted after the close is validated (the ledger keeps the totals); access to the restricted schema is logged.
7. **Tested.** Two automated tests run with every build: no payroll figure for a group under 5 people; no person-level column (`employee*`, `person*`, salary, name, email) in any exported mart.

## What a request looks like
- "Average salary of the 3 people in Legal" -> refused (group < 5), offered at G&A level.
- "Payroll cost by department vs budget" -> provided (all departments >= 5 people).
- "List of leavers with their final pay" -> stays in the payroll tool; Finance sees the total of final settlements only.
