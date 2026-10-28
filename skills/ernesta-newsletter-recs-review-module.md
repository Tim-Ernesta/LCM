---
name: ernesta-newsletter-recs-review-module
description: Build or fix the dynamic "Recommended for you" module and the "review on customer (UGC) photo" module in an Ernesta SFMC newsletter (NL### VA/VB), including the Recs_ByStyle, RevUgc and audience data-extension logic, the audience query wrapper and the AMPscript. Use when a review is not one of the recommended rugs, a customer photo is missing behind a review, or when setting up these modules for a new newsletter. Not for static layout of other modules (use ernesta-email-design-system) or journey/send setup (use ernesta-newsletter-send).
---

# Recommended for you + review-on-customer-photo module

## Inputs and sources
- **Newsletter key** `Newsletter_NNN_Topic_MMDDYY` (the audience DE name). Helper DEs: `<key>_Recs_ByStyle` and `<key>_RevUgc`.
- **Top 3 recs per rug class:** skill `newsletter-recommended-styles` (by email clicks, last 30 days), expanded to per-source-style rows. The previous newsletter's `_Recs_ByStyle` is the column template.
- **Review and customer photo source:** the `Sample_Rundown_Content` data extension (from the Sample, Delivery and Return Day 1 V5 Rundown email), keyed by Style + Color. Fields used: ReviewQuote, ReviewName, ReviewId, ReviewMatch (Exact / Style / None), ReviewIncentivized, ImageType (UGC / PDP), ImageMatch, ImageUrl, UgcBy. Never use influencer UGC.
- SFMC REST access (skill `ernesta-newsletter-send` scripts: `sfmc.py`, `render_previews.py`, `refresh_email_activities.py`). Images are uploaded to Content Builder folder 27275 (image.m.ernesta.com URLs).

## Data model
1. **Audience DE** (`<key>`): per recipient SignalStyle/SignalColor, HasRecs, Rec1-3 Style/Color/Url/Img, HasReview, RevStyle, RevColor, RevUrl, RevImg, RevQuote, RevName.
2. **`_Recs_ByStyle`** (PK SourceStyle): Rec1-3 Style/Color/Url/Img/Clicks and Rev* columns (RevStyle, RevColor, RevUrl with `&element=review`, RevImg, RevQuote <= 500 chars, RevName, RevReviewId). Plus ONE special row `SourceStyle = '__FALLBACK__'` holding only the Rev* fields for the static fallback recs.
3. **`_RevUgc`** (PK RevStyle + RevColor): ImgUrl, UgcBy. ImgUrl is a 600x450 JPG of the customer photo: cover-crop, top-to-bottom black scrim from 55% to 12% opacity burned in (so cream text is legible), uploaded to Content Builder folder 27275.

## Rules (decisions Tim has made)
- The review MUST be for one of the rugs shown to that recipient in Recommended for you. Never choose a review by rug class independently of the recs.
- Per source style choose among Rec1-3: first recs with an exact-colour UGC photo (ImageType = UGC and ImageMatch = Exact) AND a review; then recs with a review only. Ties: ReviewMatch Exact first, then rec order. If none of the three has a review, leave Rev* empty so HasReview = No (module hidden).
- **Incentivized reviews are allowed.** Do not filter on ReviewIncentivized.
- Photo behind the review whenever a `_RevUgc` row exists for the review rug AND colour; otherwise a solid ink (#262933) background with the same text layout.
- Static fallback (HasRecs = No, e.g. no browse/purchase signal or fewer than 3 in-stock recs): show the fixed three fallback rugs. The review must be for one of them, chosen with the same rule over those three (NL217: Fleur Champagne, Tallulah Silver, Marks Teal -> Tallulah Silver, which has a photo).
- HasRecs = Yes only if all three recs are Custom-size, active, not archived and in stock (Product2_Salesforce: Out_of_Stock__c is null or Back_In_Stock__c > Out_of_Stock__c). The review rug is one of the stock-checked recs. For the fallback, stock-check the fallback review rug in the query.

## Build steps
1. Load `_Recs_ByStyle` rows and the Sample_Rundown_Content rows (keyed Style + Color). Remove any featured styles from recs for this newsletter first, so reviews match the final recs.
2. Select the review per source row with the rule above and write Rev* back to `_Recs_ByStyle`. **Exclude the existing `__FALLBACK__` row from the per-style loop** (an earlier run treated it as a source style and blanked the review for about 77% of the audience), then compute and write the fallback row separately.
3. For every selected pair with a UGC photo, ensure a `_RevUgc` row exists. For new pairs generate the 600x450 scrimmed JPG, upload it, and upsert `{RevStyle, RevColor, ImgUrl, UgcBy}`. DE upserts use `PUT /data/v1/async/dataextensions/key:<DE>/rows` with `{"items":[{field:value,...}]}` (flat, proper-case field names; omit empty Number fields such as Rec*Clicks).
4. Audience query: join `_Recs_ByStyle` on SourceStyle = SignalStyle for HasRecs and Rec*. Wrap the whole original query:
   ```sql
   select x.<all non-review cols>,
     case when x.HasRecs = 'Yes' then (case when isnull(x.RevStyle,'') = '' then 'No' else 'Yes' end)
          when isnull(fb.RevStyle,'') = '' then 'No'
          when not exists (<fallback review rug stock check against fb.RevStyle / fb.RevColor>) then 'No'
          else 'Yes' end as HasReview,
     case when x.HasRecs = 'Yes' then x.RevStyle else isnull(fb.RevStyle,'') end as RevStyle,
     -- same pattern for RevColor, RevUrl, RevImg, RevQuote, RevName
     x.Promo_Code, x.Creative_Variant
   from ( <original query> ) x
   left join <key>_Recs_ByStyle fb on fb.SourceStyle = '__FALLBACK__'
   ```
   Update the query with `PATCH /automation/v1/queries/<id>` (not PUT; drop `validatedQueryText` from the body), then run it with `POST /automation/v1/queries/<id>/actions/start`.
5. Email AMPscript: if `@hasReview == "Yes"`, `LookupRows("<key>_RevUgc", "RevStyle", @revStyle, "RevColor", @revColor)`. If a row exists use ImgUrl as the table-cell `background` image with a VML fallback and the review inside a `gmail-blend-screen` wrapper; otherwise the solid ink version. Link the quote and attribution through `RedirectTo(v(@revUrl))` with unique aliases (`review_quote`, `review_attribution`, `review_link`). Hide the whole module when HasReview is not Yes. Recs use `rec{i}_image/_name/_cta` aliases.
6. PATCH both emails' html view, then refresh the draft journey's email activities (`refresh_email_activities.py <journey name>`) so Journey Builder does not send old snapshots.

## Verify before reporting done
- Wait until the query finishes. The audience DE is empty or partial while it overwrites: check a known recipient first, then audit. Never send or test during that window.
- Load all audience rows and confirm every HasReview = Yes row has a (RevStyle, RevColor) that is in its displayed recs (or the fallback trio when HasRecs = No). NL217 result: 0 mismatches of 173,117 rows.
- Count HasReview = No rows and name the source styles with no qualifying review.
- Render real recipient previews (`render_previews.py <key> <outdir>`) and confirm the customer photo sits behind the review for at least one VA and one VB case.
- Report how many recipients get the fallback recs and whether the fallback review has a photo.

## Gotchas
- Review quotes contain HTML entities (e.g. `&#8217;`): leave them as is in HTML.
- A pre-existing `__FALLBACK__` row is loaded with all other rows: always filter it out before the per-style loop.
- A review for the same style in a different colour is acceptable only when no exact-colour review exists.
- If a rec has a photo but no review, the module cannot use that photo; prefer the rec with both.
