# Fiverr gig + Upwork blurb: DocExtract

Launch positioning (from `freelance_biz/research/competitors-docextract.md`, 2026-10-30): a new seller with zero reviews, so low visible entry prices, "every total checked" as the one claim in the title, and the live demo plus a free 10-document test as the way to get over the trust gap. Price per batch; **1 document = 1 invoice or receipt, up to 3 pages.**

## Gig title (max 80 characters)
```
I will extract invoice data from PDFs to Excel with every total checked
```
(71 characters. Keywords: invoice data, PDF to Excel, total checked. Nobody on Fiverr puts validation in the title, so this is the differentiated one.)

Other titles to test, one at a time for 2-3 weeks each:
- `I will convert invoices and scanned receipts to Excel using AI OCR` (66 characters; the keyword-safe option: invoice, Excel, AI and OCR all hit the most common title words)
- `I will extract PDF invoice data to Excel, CSV or QuickBooks, validated` (70 characters)

**Category:** Data -> Data Entry (or Programming & Tech -> AI Services -> Data extraction, whichever is live on your account).
**Search tags (5):** `invoice data extraction` | `pdf to excel` | `invoice ocr` | `receipt to excel` | `ai data extraction`

## Packages (launch prices)

Pricing unit: per batch. **1 document = 1 invoice or receipt, up to 3 pages.** Show "From $45" as the entry price.

| | **Basic - $45** | **Standard - $99** | **Premium - $249** |
|---|---|---|---|
| Documents per batch | Up to **50** | Up to **200** | Up to **500** |
| Files in | PDFs with selectable text | Basic + **scans and phone photos** (scanned PDF, PNG, JPG), read by OCR; a photo that cannot be read is flagged, not guessed | Standard + **ZIP intake** (one ZIP of a whole folder) |
| Fields | Vendor, number, date, currency, subtotal, tax, tip, total, payment method | same + **line items sheet** and a **tax / VAT % column** | same |
| Output | Excel + CSV with a **Needs review** sheet | Basic + **summary tab** + **Google Sheets** push | Standard + **"match my template"** column layout + **QuickBooks / Xero / Zoho import CSV** |
| Validation | **Every total cross-checked**; doubtful rows go to Needs review with the reason | same + **duplicate-invoice check** | same + a **check report** listing every flagged row and why, and a **second pass by me on all flagged rows** |
| Revisions | 1 | 2 | 3 |
| Support after delivery | - | 7 days | 7 days of free fixes |
| **Delivery** | **2 days** | **3 days** | **5 days** |

**Custom offer (not a visible tier, send on request):**
- 2,000+ documents, or monthly volume: about **$0.30-0.40 per document** (2,000 documents is roughly $600-$800), quoted after the free 10-document test.
- Your own hosted copy of the tool with a watched folder or inbox, and a 30-minute handover call. Priced by quote.

**Add-ons:**
- +100 documents: **$40**
- +500 documents: **$89**
- 24-hour rush: **$40**
- Extra custom field (PO number, cost centre, GL category): **$15**
- Automated folder / inbox flow (n8n, Make or a small script): **$120**

## When to raise prices

| Stage | Basic | Standard | Premium |
|---|---|---|---|
| Launch (first 5-10 orders) | $45 | $99 | $249 |
| After 3-5 five-star reviews | $59 | $129 | $299 |
| After about 10-15 reviews at 4.9+ (or Level 1) | $79 | $169 | $349 |
| Later target (the earlier draft, needs roughly 15+ reviews or Level 1-2) | $120 | $350 | $800 |

The earlier draft was written for different volumes (100 / 500 / 2,000 documents), so re-check the document counts when you get to that row.

**Upwork Project Catalog:** list at $79 / $199 / $499 (about 1.5-2x the Fiverr launch prices) and keep the pilot-first framing: the first step is always "send 10 documents, I return the Excel free", then the batch.
**Contra:** list from $300 per project, quoted after the free 10-document test.

## Description (about 800 characters)
```
I turn invoice and receipt PDFs, scans and phone photos into Excel with every total cross-checked, doubtful rows on a Needs review sheet.
Not sure it fits your documents? Send 10 of your documents, I return the Excel free so you can judge it.
Try the tool yourself: https://docextract-9vrp.onrender.com

Each flagged row says why it was flagged, so a wrong number does not slip into your books.

What you get:
- One row per document: vendor, number, date, currency, subtotal, tax, tip, total
- Line items on their own sheet
- USD, GBP and EUR kept separate, never added together
- Scans and phone photos read by OCR, marked as such
- Excel, CSV, Google Sheets, or a QuickBooks / Xero / Zoho import CSV
- Columns matched to your template

1 document = 1 invoice or receipt, up to 3 pages. Handwritten invoices: send a sample first.
```

## FAQ (8)
**1. Which files can you handle?**
PDFs (digital or scanned), PNG, JPG and phone photos. Basic covers PDFs with selectable text; scans and phone photos start at Standard; Premium adds ZIP intake (one ZIP of a whole folder). Digital PDFs (with selectable text) are the easiest and most accurate. Scans and photos have no text to read, so they are read by OCR (the live demo does this for phone photos and scanned PDFs) or by an image-reading model first, and the text is then extracted like any digital PDF. Accuracy on blurry, skewed or low-light photos is lower than on digital PDFs, which is why every OCR'd row is marked `source: ocr` with its confidence capped, and rows are flagged for review whenever the sums disagree; anything that cannot be read at all is flagged instead of guessed. By default I read the first 3 pages of each document; longer ones are fine, just tell me.

**2. How accurate is it?**
AI extraction is very good on clean documents but can misread blurry photos or unusual layouts, so I do not promise a magic number. Instead, every total is cross-checked and doubtful rows are separated on a Needs review sheet, with the reason in plain English. One limit to know about: a misread digit that still keeps a document's arithmetic consistent can pass the check, so skim the totals on high-value documents (Premium includes a second pass by me on every flagged row). Send 10 of your own documents first and judge the result yourself, free.

**3. Is my data safe?**
Your files are used only for your order, shared with nobody, and deleted within 7 days of delivery. I will sign a simple NDA on request. Extraction uses AI (Groq or Gemini, with your key if you prefer), so the document text (including the OCR text of scans and photos) is sent to that provider's API, and page images are sent only if the Gemini image route is used; if you want data handling to follow your own agreement with the provider, I use your API key. Please do not upload real client documents to the public demo; use its sample files.

**4. Other currencies or languages?**
Currencies (USD, GBP, EUR, CAD, AUD and others) are fine; each total is kept in its own currency and currencies are never added together. English-language documents work best; other Latin-script languages usually work for digital PDFs, but the OCR used for scans and photos is tuned for English, so accented names on a photo may come out approximated. Send a sample.

**5. Can it plug into QuickBooks, Xero or Google Sheets, or run automatically?**
Yes. Standard includes a Google Sheets push. Premium adds an import CSV for QuickBooks, Xero or Zoho in the layout your accounting software expects. For files that arrive on their own (a watched folder or an inbox processed into your Sheet) there is an automated-flow add-on at $120, or a custom offer. Direct API integrations with accounting software are a custom quote, so message me first.

**6. Will I pay extra for the AI?**
No separate AI bill for typical batches: I use Groq's free-tier API, which covers an order of this size (it is rate-limited, so very large batches simply take longer). For big or recurring volumes you can supply your own Groq or Gemini key, or a paid key, and the provider bills you directly at its published rates; I give you an estimate before starting.

**7. Handwritten invoices?**
Case by case. Send a sample and I will tell you before you order. Handwriting usually fails OCR, so those documents are normally flagged for manual entry rather than guessed.

**8. Can you match my existing spreadsheet layout or my accounting import?**
Yes, from Premium: your column order and names, and an import CSV for QuickBooks, Xero or Zoho. For other layouts or volumes, ask for a custom offer.

## Upwork portfolio blurb
> **DocExtract: invoice and receipt data extraction with every total cross-checked.** I turn batches of invoice and receipt PDFs, scans and phone photos into one Excel/CSV row per document, with line items and USD, GBP and EUR kept separate. Text PDFs are read with Groq, scans and photos with OCR. Rows that do not add up go to a "Needs review" sheet with the reason instead of being trusted silently. Optional Google Sheets push. Pilot first: send 10 documents and I return the Excel free. Live demo: https://docextract-9vrp.onrender.com · Source: https://github.com/shivam911898/docextract

## Gig checklist before publishing
- [x] Live demo deployed on Render's free tier: https://docextract-9vrp.onrender.com (URL is in the description and the Upwork blurb). It sleeps after about 15 minutes idle and the first load can take about a minute, so open it before sharing it with a buyer. The web UI takes 10 documents per batch (the command-line version I run for orders has no cap).
- [ ] Record the Loom (`DEMO_SCRIPT.md`), 45-60 seconds, no face needed: drop 5 mixed invoices into the live demo, show the Excel appear, open the Needs review sheet, show one flagged row and why. End card: "Send 10 documents, get a free test." Add it as the gig video.
- [x] Screenshots are current and in `docs/` (`screenshot-upload.png`, `screenshot-results.png`, `screenshot-needs-review.png`; taken with a Groq key, green status pill, OCR on). Upload them to the gig gallery.
- [ ] Make the gig thumbnail: messy stack of invoice and receipt images on the left, a clean Excel grid on the right with one red "Needs review" row (the Greenleaf invoice, `subtotal+tax 1158.84 != total 1196.34`), headline "EVERY TOTAL CHECKED", small line "PDF + scans to Excel / Sheets".
- [ ] Other gallery images: before/after sample, the Needs review explainer, the tier comparison, the privacy and deletion note, the FAQ.
- [ ] Pricing: publish at $45 / $99 / $249 and keep the custom offer ready for 2,000+ documents; raise per "When to raise prices" above.
- [ ] Title test: run the main title for 2-3 weeks, then swap in one alternate at a time.
- [ ] First message to every buyer: ask for 10 sample documents and return the Excel free.
