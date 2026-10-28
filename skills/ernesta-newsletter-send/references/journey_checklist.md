# Journey Builder checklist (standard for ALL NL journeys)

Source: Tim's Google Sheet "Journey Builder Checklist" (12vACxeciVDEQcvbNPvPmtdt9HQI_zLjKWVPizT2UHa0). Item numbers are Tim's (there is no item 7).
Run `scripts/journey_checklist.py <journey name> <copy file>` for everything verifiable over the API; the rest is MANUAL for Tim.

| Item | Type | Description | Notes |
|---|---|---|---|
| 1 | Blast | No filters on entry data extension |  |
| 2 | Blast | Check Message Configuration for each send and ensure subject line is accurate (the same as the current version of the email) |  |
| 3 | Blast | Send live email for each variation from Content Studio |  |
| 4 | Blast | Confirm checkout link functions with utms |  |
| 5 | Blast | Dedupe on email address or mobilephone (for SMS) in campaign (for newsletters) | ie ensure that Email or EmailAddress or MobilePhone is Primary Key in target DE |
| 6 | Blast | Confirm unsubscribe link works (must send live test) |  |
| 8 | Blast | Make sure Journey settings are "No reentry" unless otherwise specified |  |
| 9 | Automation | Add exit criteria to Journey | Should exit once they have reached goal. Not necessary for Newsletters or one-time blasts |
| 10 | Blast | Make sure test variants are correct, i.e. right version mapped to right audience |  |
| 11 | Blast | Verify that linked data extension is correct for target audience | ie should be Trade only if email is Trade-focused |
| 12 | Blast | Check that mobile images are the same as desktop | Sometimes rug styles do not match what's on desktop on mobile, doublecheck that the images are the same across both |
| 13 | Blast | Delete and re-add emails when you've updated content |  |
| 14 | Automation | Check automation and confirm Journey entry activity is included as last step |  |
| 15 | Automation | Check "Evaluate all records" for journeys with no re-entry |  |
| 16 | Automation | Exit wait only 3 minutes to conserve processing |  |
| 17 | All | Check ALL COPY against original copy document to ensure that language is correct |  |
| 18 | Blast | Run query just before send to make sure data is up to date |  |
| 19 | Blast | Make sure all SKUs are in stock before launch | If check out button on live site is greyed out and says "Out of stock", product should not be included |
| 20 | All | Remove '&shape=rectangle', '&size=custom' from urls | These parameters can interfere with url resolution |
| 21 | Blast | Check footer and ensure aligned with the rest of the content |  |
| 22 | Blast | Check darkmode hack on darkmode and ensure it's rendering properly | Focus on darkmode on mobile Apple iOS |
| 23 | Blast | Check that mobile links are the same as desktop | An image may link to one color of a rug on desktop and another color on mobile: they should always be the same on both: ex: if an image is https://www.ernestarugs.com/products/bobbie-indoor-outdoor-rug?Color=Ocean on destop and https://www.ernestarugs.com/products/bobbie-indoor-outdoor-rug?Color=Linen on mobile, that FAILS |
| 24 | All | Preheader text renders correctly without strange spacing or unusual characters |  |
| 25 | All | Check that in the target data extension, Id or SubscriberKey relates to Subscribers on Subscriber Key | This will prevent any incorrect sends to opt outs |
| 26 | Blast | Make sure that in each journey branch a customer receives an email only once, ie watch where joins end up | If a join is meant to add to a processing step, make sure there is not more than 1 email on that path (ie if there are multiple versions of an email with a join, ensure only ONE is sent to each contact) |
| 27 | Blast | Sender should ALWAYS be Default Sender Profile (not Fairfax, etc) unless otherwise noted | Should not be using localized senders for non-local sends |

## How each item is covered

- Automated (PASS/FAIL): 1, 2, 4, 13, 5, 8, 10, 12, 14, 15, 17, 20, 24, 25, 26, 27 and 23.
- Notes for Tim to confirm: 11 (audience matches the email), 16 (what the 3-minute exit wait means).
- Claude does item 13 itself on a draft journey: `scripts/refresh_email_activities.py <journey>` rebuilds every email activity from the current assets (new ids, no stale triggered-send reference); the checklist script then verifies it. Re-run it any time the emails are edited after the journey was built.
- Manual: 3 and 6 (live test sends, never sent by Claude), 18 and 19 (send morning), 21 (footer by eye), 22 (iOS dark mode test send).
- Added by Tim's rules (not in the sheet): item L (every image, headline and subhead linked), 14b (one event definition), 24 now also requires the preview-text hack (90 filler pairs), plus send_readiness_check.py and darkmode_check.py.
- N/A for newsletters: 9.

## Lessons

- The site returns 403 to plain scripts: check links in a real browser (`linkcheck.js`).
- A 200 is not enough for filter URLs `/shop-custom-rugs/f/1/<name>-<n>~<code>`: the code decides the filter (14~1401 is Animal Pattern, not plush wool). Prefer class pages: /shop-custom-rugs/textural-rugs, /plush-wool-rugs, /natural-fiber-rugs, /wool-flatweave-rugs, /indoor-outdoor-rugs, /lustrous-rugs, /easy-care-rugs.
- The editorial template's footer URLs (/pages/...) and social handles are placeholders. Live ones: /custom-rug-samples, /shop-custom-rugs?index=shopify_products, /locations, /trade-program, /contact-us, /privacy-policy, facebook.com/ErnestaRugs, instagram.com/ernesta_inc, youtube.com/channel/UCk1f7uN-0O3TfuujLMlVbdQ. Other live pages: /custom-rug-size-guide, /services, /custom-rug-samples, /guide.