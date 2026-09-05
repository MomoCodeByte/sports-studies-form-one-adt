# Sports Studies Form One — Accessible Digital Textbook

This repository contains the text/HTML-based Accessible Digital Textbook (ADT) conversion of *Sports Studies for Secondary Schools: Student's Book Form One*.

## Open the book

Use the GitHub Pages link shown in the repository description after deployment.

For local preview, run this command from the repository root:

```powershell
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/`.

The book must be served through HTTP. Opening `index.html` directly with a `file://` URL may prevent localization, audio, navigation and offline resources from loading correctly.

## Accessibility and interaction

- Text-first HTML pages following the original book's reading order
- Keyboard-accessible navigation and interactive activities
- Image and table descriptions for learners with visual disabilities
- Read-aloud audio generated with the `en-TZ-ImaniNeural` voice
- Front and back book covers
- Offline-preload support
- Responsive layout for desktop, tablet and mobile screens

## Main validation files

- `index.html` — reader entry point
- `content/pages.json` — canonical reading order
- `content/toc.json` — table of contents
- `assets/config.json` — ADT feature and language configuration
- `imsmanifest.xml` — package manifest
- `content/i18n/en-US/` and `content/i18n/en-KE/` — text, speech, audio mappings and glossary data

## Course-validator checks

The published book should meet these gates:

- No missing reader pages or broken image references
- Unique `page-section-id` values matching `content/pages.json`
- No missing text, speech, audio mappings or referenced audio files
- Correct Previous/Next navigation from the first page through the back cover
- Working activities and quizzes
- No blocking browser-console errors

## Repository scope

Local backups, temporary page renders and the original PDF source are intentionally excluded from Git. The repository contains the files required to run and validate the final ADT web reader.

