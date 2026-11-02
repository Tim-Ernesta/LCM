---
name: sample-rundown-content-refresh
description: Refresh the Sample_Rundown_Content SFMC data extension (review quote + UGC image per Style/Color) from Yotpo data in Snowflake. Use to rebuild or re-run the Mon/Thu scheduled cloud task, or whenever editing the review/image rules for the Day 1 sample rundown email.
---

# Sample_Rundown_Content refresh

Twice-weekly unattended cloud task that fills and upgrades the review and UGC image fields in the SFMC
data extension `Sample_Rundown_Content`, which feeds the email **"Sample, Delivery, and Return (Day 1) V5_Rundown"**
(SFMC asset 133862). The email prints `ReviewQuote` in full in a card with no truncation, so length is capped at the source.

The exact task prompt is in [`prompt.md`](prompt.md). It is the source of truth: paste it unchanged as the task prompt.
Helper functions for SFMC REST are in [`scripts/sfmc_de.py`](scripts/sfmc_de.py).

## Rebuild the scheduled task (another device / account)
1. Create a scheduled cloud task named "Sample_Rundown_Content review & UGC refresh".
2. Schedule: Mon and Thu at 6:45 AM ET (`CRON_TZ=America/New_York 45 6 * * 1,4`). Avoid 6-9 AM Pacific start times (delays).
3. Fresh session per run (not a persistent session); push notifications on, email off.
4. Attach the **Snowflake** and **Notion** connectors. Without Snowflake the run cannot find reviews. Connectors cannot be passed through the
   task-creation tool in this org; attach them in the claude.ai routines UI (or edit an existing task that already has them).
5. Set environment variables in the cloud environment: `SFMC_CLIENT_ID`, `SFMC_CLIENT_SECRET`, `SFMC_AUTH_BASE_URL`. Never commit these.
6. Paste `prompt.md` as the prompt. Do not do a live test without expecting real writes to the DE.

## Rules (current)
- DE key is **Style + Color** (one row per colorway, ~550 rows), not SKU. Map to Yotpo with `lower(REVIEW_PRODUCTS_V2.NAME) = lower(Style || ' ' || Color)`.
- Only touch review fields (`ReviewQuote, ReviewName, ReviewId, ReviewColor, ReviewMatch, ReviewExcerpt, ReviewIncentivized`),
  image fields (`ImageUrl, ImageType, ImageMatch, ImageColor, UGCBy, UGCReviewId`) and `UpdatedDate`. Never delete rows or change keys.
- **Target** = blank review, blank/broken image, or weak content (quote over 230 chars, not 5-star, not about the rug, or image failing the quality bar).
- **No minimum review length. Maximum 230 characters** (email limit; the field itself allows 500; longest existing quote was 226).
- **Incentivized reviews are fine** (set `ReviewIncentivized` accurately). **Service-oriented reviews are fine.**
  Reviews from another colorway of the same style (`ReviewMatch = Style`) are not weak. Never swap an acceptable review for another acceptable one.
- Exclude: not 5-star, deleted/archived/blocklisted, profanity, complaints, personal data (emails, phones, full last names),
  reviews naming design assistants/staff, reviews written by Ernesta employees or executives (e.g. the CEO).
- **Excerpts**: if the best review is over 230 chars, keep whole verbatim sentences up to 230 chars and set `ReviewExcerpt = Yes`.
  Cut only preamble/backstory/secondary detail; **never drop the actual verdict** (praise, quality, look, fit, closing recommendation or repeat purchase).
  Verify in code that each kept sentence appears verbatim in the original.
- UGC images: exact colorway, 5-star photo review or social field, URL 200, short side >= 800px, rug clearly visible, no screenshot/collage/packaging/face-as-subject/text overlay. View every candidate before choosing. PDP-image colorways historically have no exact-colorway photo reviews.
- Backup every row before writing, read back after writing, report only what the read-back confirmed.

## Snowflake gotchas
- The Snowflake tool returns results only into the model context (no Python connection), so pass target keys with
  `split_to_table('Style|Color;Style|Color', ';')` and keep result sets small.
- Yotpo tables in `PROD_DW`: `MAIN.REVIEWS_V2`, `MAIN.REVIEW_PRODUCTS_V2`, `MAIN.REVIEW_IMAGES_V2`, `MAIN_STAGING.STG_YOTPO__REVIEWS`. `SENTIMENT` is always 0; ignore it.

## History
- 2026-11-02: first run. 7 blank colorways filled; ~131 still blank (no usable exact-colorway review found under the earlier, stricter rules). Early over-eager swaps of acceptable reviews were reverted; rules above reflect the corrections.
