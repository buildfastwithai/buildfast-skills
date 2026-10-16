# Unbound

Turn any PDF into an interactive web book with Gemini 4 Argon.

Unbound is a static web app with no backend. Your PDF and API key go straight from the browser to Google's Gemini API.

## What it makes

Drop in a report, paper, manual, course notes or ebook. Unbound reads the whole PDF, maps its chapters, then writes them as a web book with:

- **Readable chapters** with key takeaways and page citations back to the PDF
- **Key terms** you can tap for a definition, plus a full glossary
- **Charts and tables** rebuilt from the numbers in the document
- **Think-it-through prompts** that ask the reader to predict before revealing the answer
- **Quizzes** with explanations, and **flashcards** per chapter and for the whole book
- **Search**, adjustable text size, and Light, Sepia and Dark page colours
- **Ask the book**: questions answered from the PDF, with page numbers

Export any book as a single HTML page that works offline and can be hosted anywhere.

## Run it

1. Get a free Gemini API key at https://aistudio.google.com/apikey
2. Host this folder on any static host (Netlify, Vercel, GitHub Pages, Cloudflare Pages), or open `index.html` locally.
3. Click **Add API key**, paste your key and press **Save key**.
4. Drop in a PDF and press **Build web book**.

## How it works

1. The PDF is uploaded once to the Gemini Files API (small files fall back to being sent inline).
2. Gemini 4 Argon reads the whole document and returns a chapter plan.
3. Chapters are written three at a time with structured JSON output. You can read finished chapters while the rest are written.
4. Books are saved in your browser's local storage, under "Your shelf".

## Notes

- Up to 50 MB per PDF.
- Gemini keeps uploaded files for 48 hours, so "Ask the book" and chapter retries work for two days after a build. Reading and exporting work forever.
- The model picker defaults to `gemini-4-argon` and lists every Gemini model your key can use.
- Your API key is stored only in this browser, and only if "Remember the key" is ticked.
