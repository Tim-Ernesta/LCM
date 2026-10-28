---
name: "ernesta-monthly-lifecycle-wrapup"
description: "Build Ernesta's monthly lifecycle email marketing wrap-up (top journeys by clicks/influenced rugs, A/B test recap, creative insights, and optional top/bottom creative screenshot pages) as a Word doc. Use only when Tim explicitly asks for the monthly wrap-up / marketing recap for a given month — this is a manual, on-demand report, never run on a schedule."
---


# Ernesta Monthly Lifecycle Marketing Wrap-Up

Produces a Word doc recapping email/lifecycle marketing performance for a given month at Ernesta (rug e-commerce company). Run this ONLY when Tim explicitly asks for it (e.g. "prepare the wrap-up for August", "do the monthly wrap-up"). Do NOT set this up as a scheduled/recurring task — Tim pulls this manually as needed.

Company context: Ernesta sells rugs. Primary conversion metric is "influenced rug orders" (email-attributed rug orders). Tool stack: SFMC (email platform), Snowflake (warehouse), Notion (A/B test tracker), Sigma (BI dashboards).

## Step 0: Determine the month and date range

Ask or infer which month to report on (default: the current/most recent month, month-to-date if not yet closed). Compute the date range as `[YYYY-MM-01, next-month-01)` in UTC. Note in the doc header how many days remain if the month isn't closed yet — figures will keep shifting until month-end.

## Step 1: Query Snowflake (PROD_DW.MAIN)

Use the `sql-executor` MCP tool (search ToolSearch for "sql-executor" if not loaded). Key tables:
- `SFMC_EVENTS` — one row per SFMC event. Columns include `EVENT_TYPE` ('Sent','Open','Click','Unsubscribe','SoftBounce','HardBounce','OtherBounce'), `EVENT_DATE`, `SEND_EVENT_DATE` (date of the original Sent event for that subscriber/send), `JOURNEY_ID`, `JOURNEY_NAME`, `SUBSCRIBER_KEY`, `ID`.
- `ORDER_LIFECYCLE_ATTRIBUTION` — one row per rug order that had an email touch. Columns: `ORDER_ID`, `ORDER_CREATED_AT_UTC`, `SFMC_EVENT_ID` (joins to `SFMC_EVENTS.ID`), `RUG_QUANTITY`, `IS_CANCELLED`, `IS_FREE_RUG_WARRANTY`, `IS_FREE_RUG_APPEASEMENT`, `IS_INTERNAL_USE`, `DAYS_FROM_SEND_TO_ORDER`, `DAYS_FROM_EMAIL_OPEN_TO_ORDER`.
- `ORDERS` — all orders, for computing total rug order volume as a denominator.

### Influenced Rug Orders — IMPORTANT: use the Sigma-aligned definition

Ernesta's official Sigma "SFMC Reporting" dashboard defines Influenced Rug Orders as:
```
CountDistinctIf([Order Id],
  [Rug Quantity] > 0
  and Not([Is Cancelled])
  and Not([Is Free Rug Warranty])
  and Not([Is Free Rug Appeasement])
  and Not([Is Internal Use])
  and Month([Order Created at Utc]) = Month([Send Event Date])
  and Year([Order Created at Utc]) = Year([Send Event Date])
)
```
The key nuance: the order counts as "influenced" for a given month ONLY IF the attributing email's **Send Event Date** (not the order date alone, and not the open/click date) falls in that SAME calendar month as the order. An order placed in month M but attributed to an email sent in month M-1 does NOT count toward month M. Always replicate this exact rule — do not just filter on order date. This matters especially for month-boundary campaigns (e.g. a "MonthX_Launch" journey that actually sent on the last day of the prior month).

Reference SQL for total influenced rugs in the target month:
```sql
SELECT COUNT(DISTINCT ola.ORDER_ID)
FROM PROD_DW.MAIN.ORDER_LIFECYCLE_ATTRIBUTION ola
JOIN PROD_DW.MAIN.SFMC_EVENTS e ON ola.SFMC_EVENT_ID = e.ID
WHERE ola.ORDER_CREATED_AT_UTC >= '{month_start}' AND ola.ORDER_CREATED_AT_UTC < '{next_month_start}'
  AND ola.RUG_QUANTITY > 0 AND ola.IS_CANCELLED = FALSE AND ola.IS_INTERNAL_USE = FALSE
  AND ola.IS_FREE_RUG_APPEASEMENT = FALSE AND ola.IS_FREE_RUG_WARRANTY = FALSE
  AND MONTH(ola.ORDER_CREATED_AT_UTC) = MONTH(e.SEND_EVENT_DATE)
  AND YEAR(ola.ORDER_CREATED_AT_UTC) = YEAR(e.SEND_EVENT_DATE)
```
Add `AND e.JOURNEY_ID IS NOT NULL GROUP BY e.JOURNEY_NAME` (and swap COUNT for the per-journey breakdown) to get influenced rugs by journey.

Total rug orders (denominator for "influenced share"):
```sql
SELECT COUNT(*) FROM PROD_DW.MAIN.ORDERS
WHERE CREATED_AT_UTC >= '{month_start}' AND CREATED_AT_UTC < '{next_month_start}'
  AND RUG_QUANTITY > 0 AND IS_CANCELLED = FALSE AND IS_INTERNAL_USE = FALSE
  AND IS_FREE_RUG_APPEASEMENT = FALSE AND IS_FREE_RUG_WARRANTY = FALSE
```

### Clicks and Delivered (by journey)

For the main "Top Journeys" tables, raw click-event counts are fine (they're just a volume/engagement ranking, and this report's methodology footnote already discloses that raw counts run higher than Sigma's dashboard rollup):
```sql
-- Clicks per journey (raw click events)
SELECT JOURNEY_NAME, COUNT(*) as clicks
FROM PROD_DW.MAIN.SFMC_EVENTS
WHERE EVENT_TYPE = 'Click' AND JOURNEY_ID IS NOT NULL
  AND EVENT_DATE >= '{month_start}' AND EVENT_DATE < '{next_month_start}'
GROUP BY JOURNEY_NAME

-- Delivered per journey
SELECT JOURNEY_NAME, COUNT(*) as delivered
FROM PROD_DW.MAIN.SFMC_EVENTS
WHERE EVENT_TYPE IN ('Sent','Delivery') AND JOURNEY_ID IS NOT NULL
  AND EVENT_DATE >= '{month_start}' AND EVENT_DATE < '{next_month_start}'
GROUP BY JOURNEY_NAME
```

### Click RATE — IMPORTANT: always use unique/distinct clickers, never raw click events

Whenever computing a **click rate** (clicks ÷ delivered, e.g. for ranking newsletters or creatives by performance), the numerator MUST be distinct clicking subscribers, not raw click-event rows. A subscriber who clicks the same email 3 times, or clicks 3 different links in one email, is one "click" for rate purposes — using raw event counts inflates the rate by roughly 3x and can even change the ranking order. Confirmed via direct comparison on August 2026 data: raw-event click rate for the top newsletter was 3.13%, unique-clicker click rate was 1.02% — and the #2/#3 ranking flipped between the two methods. Always use:
```sql
SELECT JOURNEY_NAME, COUNT(DISTINCT SUBSCRIBER_KEY) as unique_clickers
FROM PROD_DW.MAIN.SFMC_EVENTS
WHERE EVENT_TYPE = 'Click' AND JOURNEY_ID IS NOT NULL
  AND EVENT_DATE >= '{month_start}' AND EVENT_DATE < '{next_month_start}'
GROUP BY JOURNEY_NAME
```
and divide by `COUNT(DISTINCT SUBSCRIBER_KEY)` (or plain delivered count, they're equivalent in practice — verify with a quick distinct-vs-total check) from the Sent/Delivery events for that journey. Raw click *counts* (not rates) are still fine to use for volume-based rankings like "Top Journeys by Clicks" — just never divide a raw count by delivered and call it a rate.

Build two rankings: **Top 10 journeys by Clicks** and **Top 10 journeys by Influenced Rugs**, each showing Journey / primary metric / secondary metric / Delivered.

"Journeys" in this SFMC instance includes both always-on triggered flows (e.g. "Sample Delivery and Return", "Lead Nurture Journey _v2", "Add_to_Cart_Reengagement") AND one-off newsletter broadcasts (e.g. "Newsletter_183_Marks_080426") — everything sent through Journey Builder gets a JOURNEY_ID. This is expected; call out in the narrative that small triggered/lifecycle journeys typically convert at much higher rug-rates (rugs/delivered) than broadcast newsletters despite tiny reach — this has held true every month so far.

## Step 2: Query the Notion A/B Testing Tracker

Database: "Lifecycle AB Testing Tracker", data source URL `collection://1961ed10-13ea-4d20-ab17-b33e4571e188`. Use `notion-query-data-sources` (SQL mode). Schema: `Test #` (title), `Campaign`, `Element` (multi-select JSON array: Timing/Content/Subject/Layout/CTA/Imagery/Segmentation/Copy/Offer/Campaign/Headline/SL/Sender/etc.), `Variable`, `Version`, `Deliveries`, `Opens`, `Clicks`, `Click rate lift %`, `Significant?`, `createdTime`.

Query tests logged in the target month:
```sql
SELECT "Test #", "Campaign", "Element", "Variable", "Version", "Deliveries", "Opens", "Clicks", "Click rate lift %", "Significant?", createdTime
FROM "collection://1961ed10-13ea-4d20-ab17-b33e4571e188"
WHERE datetime(createdTime) >= datetime('{month_start}') AND datetime(createdTime) < datetime('{next_month_start}')
ORDER BY createdTime
```

Each test has 2 rows (A/B variants) sharing a `Test #`. **The row carrying non-null `Click rate lift %` / `Significant?` is always the winning (higher-CTR) variant** — its lift is expressed relative to the other variant. Compute each row's CTR as Clicks/Deliveries to double check which row is actually higher before calling it the winner (in rare cases, e.g. very small samples or SMS tests, treat as inconclusive if the split looks unreliable — flag with a footnote rather than force a winner).

Watch for tests whose `Campaign` name encodes a date outside the target month (e.g. logged in August but campaign name suggests a May send) — these are backfilled/late-logged entries, not actual tests from that month. Exclude from the count and footnote them.

Build an A/B test recap table: `#, Campaign, Element, Winning Version, Lift, Significant?`. Summarize the element-type mix (Subject/CTA/Content/Copy/Layout/Segmentation/etc.) and call out the significant winners.

## Step 3: Creative Performance Insights section

Write 4-6 bullets synthesizing patterns across the month's A/B tests — not just restating the table, but drawing out themes: what kind of imagery wins (UGC/authentic vs. staged), copy/tone patterns (urgency framing, personal vs. formal, specific vs. vague CTAs), layout/simplicity findings, and segmentation/personalization results. Compare to prior months' patterns if known (e.g. historically subject-line tests are over-indexed at ~34% of all tests; content/dynamic-product tests deliver the highest lift).

## Step 4: Build the Word doc

Read the `docx` skill (SKILL.md) for docx-js mechanics (US Letter page size, table column widths, etc.) before building. Core structure, in order:
1. Header: "Ernesta Lifecycle Marketing" / "{Month} {Year} Monthly Wrap-Up" / data-as-of line noting days remaining if month is open.
2. **Month at a Glance** — 3-stat box row (Emails Sent, Total Clicks, Influenced Rug Orders) + one summary sentence with the influenced share %.
3. **Top Journeys — Clicks & Influenced Rugs** — the two top-10 tables, plus a paragraph calling out journeys that appear in both top-5s, and the lifecycle-vs-broadcast efficiency gap (cite specific rug-rate percentages, not vague multipliers).
4. **{Month} A/B Test Recap** — element-mix summary sentence, the full test table, footnotes for excluded/inconclusive tests, and a paragraph on the month's significant winner(s).
5. **Creative Performance Insights** — the bulleted synthesis from Step 3.
6. Closing italic **Methodology** footnote: state the same-month attribution rule used for Influenced Rug Orders, the raw-click-events-vs-Sigma caveat, the as-of date/days-remaining caveat if applicable, and data sources (Snowflake tables + Notion tracker).

### Optional: Top/Bottom performing creative screenshot pages

If Tim asks to include actual creative screenshots ranked by performance (has happened before — e.g. "pull in the top 4 and bottom 4 performing email creatives"), follow this pattern:

- **Ask or infer scope carefully.** Confirm whether the ranking metric should be click *volume* or click *rate* (default to click **rate** using unique clickers per the rule above unless Tim asks for volume), and whether it should span all journeys or just the `Newsletter_` series specifically (Tim has previously wanted it scoped to newsletters only, excluding promotional/trade sends, since mixing programs with very different audience sizes skews the comparison).
- **Locate screenshots.** They live in a user-connected folder (e.g. `email_screenshots`) — request folder access if not already connected. Match campaign/journey names to filenames by date pattern (MMDDYY in the journey name, e.g. `_081126`) and/or keyword — filenames don't follow a single consistent convention, so check both. Not every campaign will have a screenshot on file; only include ones that do, and explicitly disclose which qualifying campaigns were excluded for lack of an image (don't silently drop them).
- **Handle small candidate pools honestly.** If fewer than 8 campaigns in scope have screenshots, a clean top-4/bottom-4 split isn't possible without overlap. Show the true top 4 and true bottom 4 among available-with-screenshot campaigns (substituting the next-best-available candidate when the "true" 4th-best/4th-worst has no screenshot), and add a footnote spelling out exactly which substitution happened and why. Do not quietly reduce to top-3/bottom-3 without flagging it.
- **Use full screenshots, not cropped banners**, unless Tim asks otherwise — he's asked for full-length screenshots before. Since these are typically very tall (4000-5300px), lay out up to 4 per page as a side-by-side row (not a 2x2 grid), scaled to a fixed display height (~620px at 96dpi) so width varies naturally with each email's aspect ratio; caption each with campaign name + the ranking metric value. Read images directly via Node `fs.readFileSync` from the bash-mounted screenshots path (not through the Read tool, which is expensive for images) when generating the docx-js script.
- Add these as new pages appended to the end of the doc via docx-js `PageBreak`, after the closing methodology footnote.

Save as `outputs/{Month}_{Year}_Monthly_Wrapup.docx` (e.g. `September_2026_Monthly_Wrapup.docx`). Render to PDF and visually check all pages (per the docx skill's verification step) before presenting. Use `present_files` to deliver it, with a short 1-2 sentence summary — do not restate the whole doc in chat.

## Reminders

- This is a manual, on-demand workflow. Never create a scheduled task for it unless Tim explicitly asks to schedule it (he has said he does not want it scheduled — he'll invoke it himself each month).
- Always re-query Snowflake and Notion fresh each time this is run — don't reuse numbers from a prior month's run or from memory.
- If the target month is still in progress, clearly label all figures as month-to-date and note how many days remain.
- Never compute a click *rate* from raw click-event counts — always use distinct/unique clicking subscribers as the numerator.

