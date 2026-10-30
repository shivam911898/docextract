# Loom demo script (75-90 seconds)

**Goal of the video:** a buyer who owns a small business watches it and thinks "that is my pile of invoices". Show the
result, show the safety net (Needs review), show the file they will actually receive (Excel). No code on screen.

## Before you hit record (2 minutes)
1. Open the **live demo on Render** (or `streamlit run app.py`) in a clean browser window, zoom 110-125%, close other tabs.
   Open the URL a few minutes early: the free Render instance sleeps after about 15 minutes idle and needs about a minute to wake.
2. Make sure the green status pill is showing (`AI mode: Groq ... | OCR: RapidOCR`; the `GROQ_API_KEY` environment variable
   is set in Render), not the amber `Demo mode` pill. **Groq reads text only**, but the image has RapidOCR built in, so the
   PNG receipt is OCR'd and exactly **1** document is flagged: the Greenleaf invoice (wrong total). The script below is
   written for that case. If the pill says `OCR: not installed` (an older image) the PNG is flagged too (`scanned image:
   needs a vision provider (Gemini) or an OCR backend`); use the alternative line in the 0:52 row.
3. Build a zip to drop in: `Compress-Archive samples\* samples.zip` (PowerShell, from the project folder).
4. Have an empty folder open to save the Excel file into, and Excel installed so you can open the download.
5. Loom: record **Screen + Cam bubble**, tab only, 1080p. Do one dry run.

## Script

| Time | On screen (exact actions) | Say (word for word is fine) |
|------|---------------------------|-----------------------------|
| 0:00-0:08 | App home page, cursor still. | "If you or your bookkeeper still type invoice and receipt numbers into a spreadsheet by hand, this takes minutes instead of hours. This is DocExtract." |
| 0:08-0:20 | Drag **samples.zip** onto the upload box. Click **Extract data**. Progress bar runs. | "I am dropping in one zip: nine documents. Invoices and receipts, US dollars, pounds and euros, all different layouts, and one of them is just a photo with no text inside. It processes each one." |
| 0:20-0:35 | Results appear. Point at the **summary cards**, then the **All documents** table. Scroll the table sideways once. | "Nine files processed, a total per currency, and one row per document: vendor, number, date, tax, total. It works out by itself which are invoices and which are receipts." |
| 0:35-0:52 | Click the **Needs review** tab. Hover the Greenleaf row and its reason. | "Here is the part that matters. This caterer's invoice says 1,196 dollars, but the items plus tax only add up to 1,158. The tool checks the arithmetic on every document and flags this one instead of silently trusting it. That is a 37 dollar mistake you would have paid." |
| 0:52-1:02 | Click **Preview**, pick `rcpt4_harbor_grill.png`. Image left, reason on the right. | **OCR on (1 flagged):** "And this receipt is only a photo, no text inside. It reads that too with OCR, marks it as read from an image and caps its confidence, and you can see the original next to what it extracted, so checking a row takes seconds." **No OCR in the image (2 flagged):** "This receipt is only a photo with no text in it. The tool does not guess: it parks it in Needs review, and you can see the original next to the reason. For batches with photos or scans I switch on OCR." |
| 1:02-1:15 | Click **Download XLSX**, open the file. Click through the sheets: documents, needs_review (red row), line_items. | "You get a clean Excel file, a separate sheet with only the rows to check, and every line item on its own sheet. CSV works too, and it can push straight into Google Sheets." |
| 1:15-1:28 | Back to the app, then cam full-screen or the gig page. | "I can match your exact columns, your accounting import format, and hook it to a folder or inbox so new invoices process themselves. Send me ten of your own documents and I will run them for free so you can see the result. Link below." |

## Delivery notes
- Keep the cursor slow and deliberate; pause one beat on the red flagged row.
- Do not narrate the tech stack. One optional sentence at 1:15 if the buyer is technical: "Under the hood it is an AI language
  model (Groq or Gemini, your choice of key) plus arithmetic checks."
- Title the Loom: "Invoice and receipt data to Excel in seconds (AI) - live demo". First comment: the live demo URL and gig link.
- Cut anywhere you stumble; the processing pause (progress bar) can be sped up 2x in Loom's editor.
- Thumbnail: the Needs review tab with the flagged row visible.

## Backup plan if the live demo misbehaves
- Free instance asleep or still cold-starting / quota hit (Groq's free tier is rate-limited): run locally (`streamlit run app.py`), same script.
- A different file gets flagged (model variance): say "it flags anything that does not add up" and show whichever row is flagged and why.
