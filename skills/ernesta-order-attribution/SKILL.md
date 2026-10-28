---
name: "ernesta-order-attribution"
description: "Use when attributing Shopify orders/revenue to subscribers, leads, or marketing sends in Ernesta's Snowflake warehouse (PROD_DW) — e.g. lifecycle/journey A/B reports, campaign ROI, conversion tracking."
---

# Order attribution: email-first join, then ID trace

When a report needs to answer "did this subscriber/lead go on to place an order" against `PROD_DW.MAIN.ORDERS`, a plain email match under-counts. Marketing sends are keyed by `SUBSCRIBER_KEY` (from SFMC), which for lead-sourced audiences is a Salesforce **Lead ID** (`00Q...` prefix). A lead can check out under a different email than the one they were emailed at (guest checkout, a personal vs. work address, a partner's email, etc.), and the subscriber-email lookup table (`SFMC_EXT_ALL_SUBSCRIBERS_DEDUPED`) is often stale or missing entirely for recently-created leads. Either failure mode silently drops real conversions from the report with no error — the query just returns fewer rows than actually exist.

**Standard process going forward: always run both matching paths, not email alone.**

## 1. Email-first join (cheap, catches most of the volume)

```sql
sub_email AS (
  SELECT SUBSCRIBER_KEY, EMAIL
  FROM PROD_DW.MAIN.SFMC_EXT_ALL_SUBSCRIBERS_DEDUPED
  WHERE EMAIL IS NOT NULL AND EMAIL != ''
),
entries_with_email AS (
  SELECT re.*, se.EMAIL
  FROM relevant_entries re
  LEFT JOIN sub_email se ON re.SUBSCRIBER_KEY = se.SUBSCRIBER_KEY
)
```

## 2. ID trace (catches lead conversions under a different checkout email)

Follow the Lead → converted Contact → Order trail as a second, additive path:

```sql
lead_contact AS (
  SELECT ID as SUBSCRIBER_KEY, CONVERTED_CONTACT_ID
  FROM PROD_DW.MAIN.LEADS
  WHERE IS_CONVERTED = TRUE AND CONVERTED_CONTACT_ID IS NOT NULL
),
entries_with_email AS (
  SELECT re.*, se.EMAIL, lc.CONVERTED_CONTACT_ID
  FROM relevant_entries re
  LEFT JOIN sub_email se ON re.SUBSCRIBER_KEY = se.SUBSCRIBER_KEY
  LEFT JOIN lead_contact lc ON re.SUBSCRIBER_KEY = lc.SUBSCRIBER_KEY
)
```

## 3. Match on EITHER path, dedupe by order id

```sql
influenced_orders AS (
  SELECT DISTINCT ewe.JOURNEY_NAME, ewe.EMAIL_NAME, ewe.SUBSCRIBER_KEY, o.ID as order_id
  FROM entries_with_email ewe
  JOIN PROD_DW.MAIN.ORDERS o
    ON (
      (ewe.EMAIL IS NOT NULL AND LOWER(o.EMAIL) = LOWER(ewe.EMAIL))
      OR (ewe.CONVERTED_CONTACT_ID IS NOT NULL AND o.CONTACT_ID = ewe.CONVERTED_CONTACT_ID)
    )
    AND o.CREATED_AT_UTC > ewe.send_date   -- or whatever attribution window applies
    AND o.IS_CANCELLED = FALSE AND o.IS_INTERNAL_USE = FALSE
    -- add revenue-type-specific filters here, e.g. for rug purchases:
    -- AND o.RUG_QUANTITY > 0 AND o.IS_FREE_RUG_APPEASEMENT = FALSE AND o.IS_FREE_RUG_WARRANTY = FALSE
)
```

`SELECT DISTINCT` (or an equivalent dedupe) matters here: if a lead's email happens to still match directly AND the ID trace also resolves to the same order, the OR-joined condition can otherwise double-count that order.

## Notes

- This is safe to always include, even for journeys whose `SUBSCRIBER_KEY` is *not* a Lead ID (e.g. already-a-customer journeys keyed by Contact/Customer). The `lead_contact` join just returns no match for those, so the email path alone still governs — no regression risk.
- Swap `RUG_QUANTITY > 0` for whatever quantity/revenue column defines a "conversion" for the report at hand (sample orders, total revenue, etc.) — the join *mechanism* is what's standard, not the specific rug filter.
- If a report still seems to under-count conversions after applying both paths, the next things to check are: (a) whether the lead's `CONVERTED_CONTACT_ID` is populated yet (Salesforce sync lag), and (b) matching by normalized phone number or shipping name as a last-resort third path — this has occasionally surfaced one more match but is noisier and should only be added when specifically asked for.