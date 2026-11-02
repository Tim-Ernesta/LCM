---
name: ernesta-attribution-clock
description: The one correct way to compare Marketing Cloud event times against Shopify order times in Ernesta's Snowflake warehouse (PROD_DW), and the canonical attributed-orders table to defer to. Use for ANY influenced-rug, LCM attribution, holdout, intro-offer-test, weekly-dashboard or ledger query that matches an email open or click to an order — and before writing any CONVERT_TIMEZONE against ORDERS or SFMC_EVENTS. Do not re-derive this rule.
---

# Ernesta attribution clock

**Do not re-derive this.** The rule below was verified against the warehouse on 2026-11-02 and
matches `PROD_DW.MAIN.ORDER_LIFECYCLE_ATTRIBUTION` exactly, on 3,451 of 3,451 joined October rows.
If a result looks wrong, check the data before changing the clock.

## The canonical table

`PROD_DW.MAIN.ORDER_LIFECYCLE_ATTRIBUTION` — Rohit's attributed-orders model, one row per
attributed order. **Rebuilds hourly and is current.** This is the reference for the clock rule and
the first place to look before hand-building attribution.

Do **not** use `PROD_DW.SANDBOX_ROHIT.ORDER_LIFECYCLE_ATTRIBUTION`. Same model, but frozen since
2026-10-01 (last open event 2026-09-30). It carries one extra column, `SUBSCRIBER_KEY_PATH`,
useful for understanding how identity resolves; its data is stale.

Both tables use the identical clock. An older note claimed production carried a DST defect that
the sandbox fixed — **that is no longer true**; production has been corrected.

## The rule

### 1. Marketing Cloud event times: constant +6 hours, never a named zone

SFMC stamps every event on a **fixed UTC−6** clock that does not observe daylight saving.

```
SFMC_EVENTS_V2.EVENT_DATE        -- SFMC's own fixed-CST stamp
SFMC_EVENTS_V2.EVENT_DATE_UTC    -- = EVENT_DATE + 6 hours, exactly. Already true UTC.
```

`DATEDIFF('minute', EVENT_DATE, EVENT_DATE_UTC)` is **360 in every row of the warehouse** — in
winter, in summer, and across the DST boundary. The same holds for `SEND_EVENT_DATE` /
`SEND_EVENT_DATE_UTC`.

**Use the `_UTC` columns as-is. They are already UTC — do not convert them again.**

**Never use `America/Chicago`.** It observes DST and will be one hour out for half the year. That
error reads opens *earlier* than they happened, which credits post-purchase opens as pre-purchase
— the false-positive defect found on 2026-09-30 that had inflated every month by 0.2–3.3%.

Verified independently: for the 10/23 burn send, SFMC's own data-extension export shows
`SentDate 2026-10-23 07:09:32` (fixed CST) and the warehouse shows
`SEND_EVENT_DATE_UTC 2026-10-23 13:09:54` — exactly +6:00.

### 2. Order times: `CREATED_AT_UTC` is TIMESTAMP_LTZ, so use the TWO-argument form

```sql
-- the comparison instant (UTC), to compare against EVENT_DATE_UTC
CONVERT_TIMEZONE('UTC', o.CREATED_AT_UTC)::TIMESTAMP_NTZ

-- the ET calendar date, for bucketing an order into a day or month
CONVERT_TIMEZONE('America/New_York', o.CREATED_AT_UTC)::DATE
```

The three-argument form on an LTZ column re-interprets a value that already carries a zone and
renders it **8 hours early** — four from the session offset plus four from the double conversion:

```
raw LTZ                        2026-10-28 00:09:35 -0400
2-arg -> UTC   (correct)       2026-10-28 04:09:35
3-arg -> ET    (WRONG)         2026-10-27 20:09:35    <- wrong time AND wrong day
```

Landing on the wrong day moves orders across month boundaries, so this corrupts monthly totals as
well as the match.

### 3. Send/open ET day keys: THREE-argument, because the SFMC columns are NTZ

```sql
CONVERT_TIMEZONE('UTC','America/New_York', e.SEND_EVENT_DATE_UTC)::DATE
```

The asymmetry is the whole point and it comes from the column types:

| Column | Type | Correct form |
|---|---|---|
| `ORDERS.CREATED_AT_UTC` | `TIMESTAMP_LTZ` | **two**-argument |
| `SFMC_EVENTS_V2.EVENT_DATE_UTC` | `TIMESTAMP_NTZ` | **three**-argument, from `'UTC'` |
| `SFMC_EVENTS_V2.SEND_EVENT_DATE_UTC` | `TIMESTAMP_NTZ` | **three**-argument, from `'UTC'` |

An LTZ already knows its zone; an NTZ does not and must be told it is UTC.

### 4. The comparison itself

This reproduces `DAYS_FROM_EMAIL_OPEN_TO_ORDER` in the attribution table on every row:

```sql
DATEDIFF('day',
         e.EVENT_DATE_UTC,                                        -- already UTC
         CONVERT_TIMEZONE('UTC', o.CREATED_AT_UTC)::TIMESTAMP_NTZ) -- LTZ -> UTC
```

Comparing the SFMC local stamp against an ET-rendered order matches only ~80% of rows. Both sides
must be in UTC.

## Why the margin is thin

Across Jan 2025 – Oct 2026, the winning open falls within **6 hours** of the order for **37.5%** of
credited orders (10,085 of 26,844; range 34.3–44.0% by month). A six-hour clock error moves about
a third of the series. This is not hypothetical — it is the exact size of the September 2026
defect.

## Checklist before shipping an attribution query

1. Order instant: `CONVERT_TIMEZONE('UTC', CREATED_AT_UTC)` — two arguments.
2. Order ET date: `CONVERT_TIMEZONE('America/New_York', CREATED_AT_UTC)` — two arguments.
3. Event times: use `*_DATE_UTC` directly; do not convert.
4. Event ET day key: `CONVERT_TIMEZONE('UTC','America/New_York', *_DATE_UTC)` — three arguments.
5. No `America/Chicago` anywhere.
6. Event scan upper bound: order cut **+2 days** in UTC, or the last day loses rugs.
7. Assert zero credited opens at or after the order instant. It should be exactly zero.

## Related standing facts

- Influenced rug order: `RUG_QUANTITY > 0`, not `IS_CANCELLED` / `IS_INTERNAL_USE` /
  `IS_FREE_RUG_WARRANTY` / `IS_FREE_RUG_APPEASEMENT`; open within 14 days before the order **and**
  the send inside those same 14 days; last touch; credited to the ET month of the winning send.
- The LCM ledger deliberately omits the same-calendar-month constraint the Sigma dashboard applies,
  which is why it sits ~12% above it on a settled month. Its "In-month rugs" column adds that
  constraint back.
- A month is not settled until about **day 14** after it closes. Re-read before quoting it as final.
