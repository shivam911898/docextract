# Fiverr gig + Upwork blurb: DocExtract

## Gig title (max 80 characters)
```
I will do AI document data extraction, invoice to Excel and PDF to Excel
```
(72 characters. Keywords: AI document data extraction, invoice to Excel, PDF to Excel.)

**Category:** Data -> Data Entry (or Programming & Tech -> AI Services -> Data extraction, whichever is live on your account).
**Search tags (5):** `invoice to excel` | `pdf to excel` | `receipt data entry` | `data extraction` | `document automation`

## Packages

| | **Basic - $120** | **Standard - $350** | **Premium - $800** |
|---|---|---|---|
| Document volume | Up to **100** invoices / receipts, one batch | Up to **500** documents, up to 3 batches | Up to **2,000** documents, or one month of ongoing processing |
| Formats in | PDF (digital is fastest and most accurate; scanned PDFs, PNG, JPG and phone photos are read with OCR or an image-reading model, so send samples first), ZIP | same | same |
| Standard fields | Vendor, number, date, currency, line items, subtotal, tax, tip, total, payment method | same | same |
| Custom fields | - | Up to **3** (e.g. PO number, cost centre, GL category) | Up to **10** + simple category-mapping rules |
| Output | Excel + CSV, with a separate **Needs review** sheet and a line-items sheet | Basic + **Google Sheets** push **or** a **QuickBooks / Xero / Zoho-ready import CSV** in the layout you specify | Standard + both of the above |
| Validation | Every total cross-checked; doubtful rows flagged | same + I send a short review-summary of flagged rows | same + a second pass on all flagged rows by me |
| **Automation hookup** | - | - | **One automated flow**: new files in a Google Drive / Dropbox folder or an email inbox are processed into your Sheet (Make / Zapier / n8n or a small script), with setup guide and a 30-minute handover call |
| Source / hosting | - | - | Source code **or** your own private hosted copy of the app, plus run-book |
| Revisions | 1 | 2 | 3 |
| Support after delivery | - | 7 days | 30 days |
| **Delivery** | **3 days** | **5 days** | **10 days** |

Add-ons to offer: extra 100 documents (+$25), 24-hour rush (+$40), extra custom field (+$15).

## Description (about 800 characters)
```
Stop retyping invoices and receipts. I turn your PDFs, scans and phone photos into a clean, validated Excel or Google Sheet using AI document data extraction.

Each document becomes one tidy row: vendor, invoice or receipt number, date, currency, line items, subtotal, tax, tip and total. Every total is cross-checked (items + tax = total). Anything that does not add up goes to a separate "Needs review" sheet, so mistakes never slip into your books.

You get:
- Invoice to Excel and PDF to Excel/CSV, plus a line-items sheet
- Invoices and receipts in USD, GBP, EUR and more
- Columns matched to your template or accounting import
- Optional automation: new files in a folder or inbox processed on their own

Not sure it will work on your documents? Send 10 samples before ordering and I will show you the result for free.
```

## FAQ (6)
**1. Which files can you handle?**
PDFs (digital or scanned), PNG, JPG and phone photos, loose or in a ZIP. Digital PDFs (with selectable text) are the easiest and most accurate. Scans and photos have no text to read, so they go through OCR or an image-reading model first; I tell you up front which route your batch needs, and anything that cannot be read is flagged instead of guessed. By default I read the first 3 pages of each document; longer ones are fine, just tell me.

**2. How accurate is it?**
AI extraction is very good on clean documents but can misread blurry photos or unusual layouts, so I do not promise a magic number. Instead, every total is cross-checked and doubtful rows are separated for review. Send 10 of your own documents first and judge the result yourself, free.

**3. Is my data safe?**
I process files only for your order, share them with nobody, and delete your files and outputs when the order is complete (or after 7 days). Extraction uses AI (Groq or Gemini, with your key if you prefer), so the document text (or page images for photos and scans) is sent to that provider's API; if you want data handling to follow your own agreement with the provider, I use your API key. I am happy to sign a simple NDA.

**4. Other currencies or languages?**
Currencies (USD, GBP, EUR, CAD, AUD and others) are fine; each total is kept in its own currency. English-language documents work best; other Latin-script languages usually work too, so send a sample.

**5. Can it plug into QuickBooks, Xero or Google Sheets, or run automatically?**
Yes. Standard includes a Google Sheets push or an import-ready CSV in the layout your accounting software expects. Premium adds an automated flow (watched folder or inbox to Sheet). Direct API integrations with accounting software are a custom quote, so message me first.

**6. Will I pay extra for the AI?**
No separate AI bill for typical batches: I use Groq's free-tier API, which covers an order of this size (it is rate-limited, so very large batches simply take longer). For big or recurring volumes you can supply your own Groq or Gemini key, or a paid key, and the provider bills you directly at its published rates; I give you an estimate before starting.

## Upwork portfolio blurb
> **DocExtract: AI invoice and receipt data extraction.** Built a tool that turns batches of invoice and receipt PDFs, scans and photos (USD/GBP/EUR, mixed layouts, ZIP upload) into validated Excel/CSV and Google Sheets rows, with every total cross-checked and doubtful documents routed to a "Needs review" sheet instead of being silently trusted. Python, Streamlit, AI (Groq or Gemini, your key) with an offline fallback; live demo and source available. Typically replaces hours of manual data entry per hundred documents.

## Gig checklist before publishing
- [ ] Deploy the live demo on Render's free tier (see `DEPLOY.md`) and paste the live URL in the gig description and the Upwork portfolio item. It sleeps after about 15 minutes idle, so open it a minute before sharing it with a buyer.
- [ ] Record the Loom (`DEMO_SCRIPT.md`) and add it as the gig video.
- [ ] Screenshots exist in `docs/` (upload, results, needs-review; taken in no-key demo mode). Retake them from the live demo once the green AI banner shows, for the gig gallery.
- [ ] Make a gig thumbnail: Needs review tab with the flagged Greenleaf row visible.
