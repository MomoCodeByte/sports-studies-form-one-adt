# ADT Textbook Conversion and Repair Standard

## 1. Kusudi la guide hii

Guide hii inaeleza standard ya kubadilisha kitabu cha PDF kuwa ADT ya `text/html`, kukirekebisha page-to-page, kukiongezea interactivity, accessibility, audio na offline support, halafu kukifanyia quality assurance.

Project ya Sports Studies Form One ndiyo reference ya standard hii:

`CONVERTED- ADT/SPORTS-STUDIES-FORM-ONE-adt`

## 2. Definition of Done

Kitabu hakijakamilika mpaka masharti yote yafuatayo yapite:

- Content ya kila PDF page imefananishwa na HTML page inayolingana nayo.
- Kitabu ni text/HTML based; maandishi hayajafichwa ndani ya full-page screenshot.
- Headings, paragraphs, lists, tables, captions, questions na figures zote zipo.
- Muonekano wa chapter opener, activities na revision exercises unafuata original.
- Reading order, Contents, page counter, Previous na Next zinafanya kazi.
- Kila meaningful image ina maelezo yanayosomeka na screen reader na read-aloud.
- Kila table ina caption, headings na scopes sahihi.
- Audio zote zinazofikiwa zinatumia `en-TZ-ImaniNeural`.
- `en-US` na `en-KE` zina text, speech na audio mappings zinazolingana.
- Offline preloader ina data ya mwisho, si data ya zamani.
- Hakuna broken image, duplicate page ID, missing audio au browser console error.
- Front cover ipo mwanzo na back cover ipo mwisho bila kufuta title/copyright pages.

## 3. Kanuni zisizobadilika

### 3.1 Content fidelity

- Linganisha PDF na ADT page moja baada ya nyingine.
- Usifupishe, kutafsiri au kuandika upya content bila ruhusa.
- Hifadhi spelling, numbering, figure labels na table data ya original.
- Rekebisha OCR error tu baada ya kuthibitisha neno kwenye PDF.
- Crop marks, printer registration marks na duplicate decorative assets si learning content; ziondoe.

### 3.2 HTML-first

- Paragraphs ziwe `<p>`, headings ziwe `<h1>` hadi `<h6>`, lists ziwe `<ol>`/`<ul>`, na tables ziwe `<table>`.
- Tumia image kwa cover, illustration, photograph, diagram au graphic ambayo haiwezi kujengwa vizuri kwa HTML/CSS.
- Usitumie screenshot ya PDF page nzima kama replacement ya text content.

### 3.3 Safe editing

- Tengeneza backup kabla ya batch edit, consolidation, deletion au audio regeneration.
- Usifute page mpaka uhakikishe si sehemu ya original content.
- Usihariri compiled runtime files kama:
  - `assets/base.bundle.local.js`
  - `assets/modules.bundle.local.js`
  - `content/tailwind_output.css`
- Tumia source HTML, JSON manifests na project helper scripts.

## 4. Workspace setup

Anza PowerShell ndani ya book root:

```powershell
$bookRoot = (Get-Location).Path
$python = 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
```

Expected folders:

```text
book/                         Original PDF and cover PDF
images/                       Extracted figures and covers
content/pages.json            Reader order
content/toc.json              Contents navigation
content/i18n/en-US/           Text, speech and audio mappings
content/i18n/en-KE/           Text, speech and audio mappings
assets/offline-preloader.js   Offline copy of pages and JSON
tools/                        Audit and controlled repair scripts
backups/                      Pre-change snapshots
```

Run a local preview from the book root:

```powershell
& $python -m http.server 8934 --bind 127.0.0.1
```

Open:

`http://127.0.0.1:8934/index.html`

## 5. Inventory kabla ya conversion

Rekodi vitu hivi:

1. Jina la original PDF.
2. Idadi ya PDF pages.
3. Kama cover ipo kwenye PDF tofauti.
4. Chapters na printed page ranges zake.
5. Pages zenye tables, figures, activities na revision exercises.
6. Languages zinazotakiwa.
7. Voice ya read-aloud.

Tengeneza page mapping table:

| PDF page | Printed page | ADT section ID | HTML file | Status |
|---:|---:|---|---|---|
| 1 | - | `pg001_sec001` | `pg001_sec001.html` | Pending |
| 2 | i | `pg002_sec001` | `pg002_sec001.html` | Pending |

Status inayopendekezwa: `Pending`, `Converted`, `Compared`, `Fixed`, `Passed`.

## 6. Page and ID standard

### 6.1 Section IDs

- Main page: `pgNNN_sec001`
- Additional section ya physical page hiyo: `pgNNN_sec002`, `pgNNN_sec003`
- Quiz: `qzNNN`
- Front cover: `fc001_sec001`
- Back cover: `bc001_sec001`

### 6.2 Content IDs

- Text: `pgNNN_nNNNN`
- Image: `pgNNN_imNNN`
- Table description: `pgNNN_tbNNN`
- Quiz question: `qzNNN_que`
- Quiz option: `qzNNN_o0`, `qzNNN_o1`, `qzNNN_o2`

IDs lazima:

- Ziwe unique ndani ya kitabu.
- Zibaki stable baada ya styling changes.
- Zilingane katika HTML, `texts.json`, `speech_texts.json`, `audios.json` na MP3 filename.

## 7. Base HTML page template

```html
<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Book title</title>
  <meta name="title-id" content="pg001_sec001" />
  <meta name="page-section-id" content="1" />
  <link href="./content/tailwind_output.css" rel="stylesheet">
  <link href="./assets/libs/fontawesome/css/all.min.css" rel="stylesheet">
  <link href="./assets/fonts.css" rel="stylesheet">
</head>
<body class="min-h-screen">
  <main class="w-full">
    <div id="content" class="container opacity-0">
      <section data-section-type="text_only" data-section-id="pg001_sec001">
        <!-- Accessible HTML content -->
      </section>
    </div>
  </main>
  <div class="relative z-50" id="interface-container"></div>
  <div class="relative z-50" id="nav-container"></div>
  <script src="./assets/offline-preloader.js"></script>
  <script src="./assets/scorm.js"></script>
  <script src="./assets/base.bundle.local.js"></script>
</body>
</html>
```

`page-section-id` ni position ya page katika `content/pages.json`, inaanza na `1`.

## 8. Page-to-page comparison procedure

Kwa kila PDF page:

1. Render PDF page kuwa PNG kwa visual comparison.
2. Extract text ya PDF kwa quick text comparison.
3. Fungua HTML page kwenye browser.
4. Linganisha kwa mpangilio huu:
   - Chapter/page heading
   - Introductory box
   - Paragraphs
   - Numbered and bulleted lists
   - Figures and captions
   - Tables and all cells
   - Activities and questions
   - Printed page number
5. Rekebisha missing content kabla ya styling.
6. Kisha rekebisha spacing, colours, borders, proportions na responsive layout.
7. Mark page `Passed` baada ya content na visual QA zote mbili.

Kipaumbele ni:

1. Content correctness
2. Reading order
3. Accessibility
4. Interactivity
5. Visual fidelity

## 9. Chapter opener standard

Chapter opener ifuate structure ya original:

1. Chapter banner yenye chapter number na title.
2. Introduction box.
3. Compact `Think` callout.
4. First topic heading na body text.

`Think` callout ni prompt fupi, si activity answer form. Usiongeze textarea ndani ya `Think` isipokuwa original au product requirement inaitaka.

Recommended proportions kwa desktop:

- Think pill width: takribani `18rem`
- Think pill height: takribani `4rem`
- Circular icon: takribani `5rem × 5rem`
- Icon i-overlap pill kwa kiasi kidogo
- Question ibaki ndani ya pale bordered box

Chapter One iliyothibitishwa:

`CONVERTED- ADT/SPORTS-STUDIES-FORM-ONE-adt/pg007_sec001.html`

## 10. Interactivity standard

### 10.1 Think

- Ionyeshe prompt kama ilivyo original.
- Isiwe na textarea kwa default.
- Icon na prompt lazima ziwe accessible na read-aloud.

### 10.2 Open-ended activity

Tumia label inayohusishwa na textarea:

```html
<label for="activity-answer-1" class="sr-only">
  Explain the importance of warming up.
</label>
<textarea
  id="activity-answer-1"
  data-activity-item="item-1"
  aria-label="Explain the importance of warming up."
  class="w-full min-h-28 rounded-md border bg-white px-4 py-3">
</textarea>
```

- Kila field iwe na unique ID.
- `data-activity-item` iwe stable kwa answer persistence.
- Usiongeze answer field kwenye ordinary paragraph, figure caption au Think prompt.

### 10.3 Quiz

- Question, options na explanations ziwe kwenye i18n JSON.
- Correct answer iwe defined kwenye page script/data.
- Test correct answer, wrong answer, retry na navigation.

## 11. Image accessibility standard

Kila meaningful image lazima iwe na:

```html
<img
  data-id="pg021_im001"
  src="images/pg021_im001.png"
  alt="Three views of a knee show the kneecap displaced to the side and in its normal position.">
```

ID hiyo hiyo iwe katika:

```text
content/i18n/en-US/texts.json
content/i18n/en-US/speech_texts.json
content/i18n/en-US/audios.json
content/i18n/en-US/audio/pg021_im001.mp3
content/i18n/en-KE/texts.json
content/i18n/en-KE/speech_texts.json
content/i18n/en-KE/audios.json
content/i18n/en-KE/audio/pg021_im001.mp3
```

Description nzuri ieleze:

- Nani au nini kinaonekana.
- Kitendo au body position.
- Direction ya arrows.
- Labels muhimu.
- Measurements muhimu kwenye diagram.
- Tofauti kati ya stages/panels.

Epuka descriptions kama:

- `Image`
- `Figure 3.2`
- `Illustration from page 17`
- `Sports picture`

Decorative image ambayo haina learning meaning:

```html
<img src="images/decoration.png" alt="" role="presentation" aria-hidden="true">
```

Decorative image isiwe na speakable `data-id`.

## 12. Table accessibility standard

```html
<table aria-describedby="pg095_tb001_desc">
  <caption class="sr-only">
    <span id="pg095_tb001_desc" data-id="pg095_tb001">
      Glossary terms and their definitions for key words used in the book.
    </span>
  </caption>
  <thead>
    <tr>
      <th scope="col">Term</th>
      <th scope="col">Definition</th>
    </tr>
  </thead>
  <tbody>...</tbody>
</table>
```

- Tumia `<caption>` kueleza table inahusu nini.
- Tumia `<th scope="col">` au `<th scope="row">`.
- Usitumie `data-id` kwenye `<table>` yenyewe kama runtime inaweza kureplace table content; iweke kwenye caption `<span>`.
- Caption ID iwe na text, speech, audio mapping na MP3.

## 13. Read-aloud and Imani audio

Standard voice:

`en-TZ-ImaniNeural`

Files:

- `texts.json`: displayed/localised text.
- `speech_texts.json`: version iliyotayarishwa kusomwa.
- `audios.json`: mapping ya ID kwenda MP3.
- `audio/{id}.mp3`: generated voice file.

Mfano wa mapping:

```json
{
  "pg021_im001": "pg021_im001.mp3"
}
```

Speech text iandike abbreviations na numbers kwa namna ambayo voice itatamka vizuri. Mfano, `4 × 100 m` inaweza kuwa `four-by-one-hundred-metre relay`.

Dry-run ya audio inventory:

```powershell
& $python .\tools\regenerate_imani_audio.py
```

Generate and install audio baada ya backup:

```powershell
& $python .\tools\regenerate_imani_audio.py --apply --concurrency 8
```

Usitumie `--apply` mpaka text na speech content zikamilike; otherwise utalipa muda wa kurudia audio generation.

## 14. Cover placement

Kama cover PDF ina back na front kwenye spread moja:

1. Soma `TrimBox` ya PDF.
2. Crop back cover kutoka upande wa kushoto.
3. Crop front cover kutoka upande wa kulia.
4. Ondoa crop/registration marks.
5. Hifadhi images kwa resolution nzuri.
6. Tumia front cover kama `index.html` page ya kwanza.
7. Hamisha title/certificate page iliyokuwa `index.html` kwenda page inayofuata; usiifute.
8. Weka back cover baada ya final content page.
9. Update root `cover.png` kwa actual front cover.

Recommended order:

```text
1. Front cover
2. Title/certificate page
3. Copyright and prelim pages
4. Chapters
5. Glossary/Bibliography
6. Back cover
```

## 15. Reading order and package files

Baada ya kuongeza, kuondoa au kuunganisha page, update zote:

### `content/pages.json`

- Ina authoritative reader order.
- Kila `section_id` na `href` iwe unique.
- `page_number` ni printed page number, si lazima ilingane na reader position.

### HTML meta

- `page-section-id` iwe sequential na 1-based.
- Ilingane na position katika `pages.json`.

### `content/toc.json`

- Update href ya moved page.
- Ondoa entry ya deleted page.
- Add front/back cover entries kama zinahitajika.
- Tumia levels kwa hierarchy ya chapter/topic.

### `imsmanifest.xml`

- Kila HTML page mpya iwe listed.
- Cover images na essential new assets ziwe listed.
- Entry point ibaki `index.html`.

### `assets/offline-preloader.js`

- Refresh baada ya HTML au JSON edit.
- Lazima iwe na latest `pages.json`, `toc.json`, texts, speech, audio mappings na reader HTML.

Kwa Sports Studies project:

```powershell
$code = "import json; from tools.convert_missing_pages_to_interactive_html import ROOT, update_page_section_ids, refresh_offline_preloader; pages=json.loads((ROOT/'content'/'pages.json').read_text(encoding='utf-8')); update_page_section_ids(pages); refresh_offline_preloader(ROOT,pages)"
& $python -c $code
```

Kabla ya kutumia helper hii kwenye book nyingine, badilisha `ROOT` na uhakikishe preloader format inafanana.

## 16. Removing generated or duplicate pages

Usiondoe page kwa kuangalia reader number peke yake. Fanya hivi:

1. Tafuta reader position katika `pages.json`.
2. Rekodi `section_id`, `href` na printed page number.
3. Linganisha na original PDF.
4. Hakikisha content yake ipo kwenye page nyingine au haipo kwenye original.
5. Tengeneza backup.
6. Ondoa entry katika `pages.json` na `toc.json`.
7. Ondoa file katika `imsmanifest.xml`.
8. Renumber `page-section-id`.
9. Refresh offline preloader.
10. Test Previous/Next kwenye pages zinazozunguka sehemu iliyoondolewa.

## 17. Consolidating chapter pages

Ukihitaji kupunguza reader pages bila kupoteza content:

- Unganisha sections zinazotoka kwenye physical PDF page moja.
- Hifadhi kila original `data-section-id` ndani ya merged HTML.
- Hifadhi text IDs, image IDs, answers na activity field IDs.
- Redirect TOC entries za removed HTML kwenda canonical merged HTML.
- Usichanganye content ya physical pages mbili tofauti kwa sababu ya kupunguza number tu.
- Kagua scroll length na responsive layout baada ya merge.

## 18. Browser QA matrix

Test angalau ukubwa huu:

| View | Suggested size | Check |
|---|---:|---|
| Desktop | 1280 × 720 | Main layout, navigation, audio controls |
| Compact laptop | 1088 × 500 | Overflow, chapter banner, Think box |
| Mobile | 390 × 844 | Wrapping, images, forms, horizontal scroll |

Kwa representative pages test:

- Front cover
- Title page
- Contents
- Kila chapter opener
- Page yenye many images
- Page yenye long table
- Open-ended activity
- Quiz
- Glossary
- Bibliography
- Back cover

Browser checklist:

- `#content` inaonekana; opacity si `0` baada ya runtime load.
- Hakuna image yenye `naturalWidth = 0`.
- Hakuna unwanted horizontal scroll.
- Previous/Next zinaenda kwenye correct pages.
- Page counter inalingana na `pages.json`.
- First page Previous ni disabled.
- Last page Next ni disabled.
- Contents links zinafungua correct section.
- Image description inaonekana katika accessibility tree.
- Table caption inaonekana katika accessibility tree.
- Read-aloud controls zinapata audio.
- Console errors ni `0`.

## 19. Automated audits

### Canonical content and bundle audit

```powershell
& $python .\tools\audit_canonical_content.py
```

Expected final lines:

```text
LOW_COVERAGE
BROKEN_IMAGES
DUPLICATE_PAGE_IDS
missing_text=0
missing_speech=0
missing_audio_map=0
missing_audio_files=0
```

Values baada ya labels tatu za kwanza lazima ziwe tupu.

### General book content audit

```powershell
& $python .\tools\audit_book_content.py --root . --threshold 0.98
```

### Page-section ID audit

```powershell
$pages = Get-Content .\content\pages.json -Raw | ConvertFrom-Json
$bad = @()
for ($i = 0; $i -lt $pages.Count; $i++) {
  $html = Get-Content (Join-Path $bookRoot $pages[$i].href) -Raw
  $match = [regex]::Match($html, '<meta\s+name="page-section-id"\s+content="(\d+)"')
  if (-not $match.Success -or [int]$match.Groups[1].Value -ne ($i + 1)) {
    $bad += $pages[$i].href
  }
}
if ($bad.Count) { $bad; throw 'Invalid page-section-id values' }
```

## 20. Project script safety

Scripts katika `tools/` zinaweza kuwa book-specific. Soma source kabla ya kuzitumia kwenye project nyingine.

| Script | Default behaviour | Standard |
|---|---|---|
| `audit_canonical_content.py` | Read-only audit | Safe baada ya paths kuthibitishwa |
| `audit_book_content.py` | Read-only audit | Safe kutumia `--root` |
| `regenerate_imani_audio.py` | Dry-run bila `--apply` | `--apply` baada ya backup |
| `improve_visual_accessibility.py` | Dry-run bila `--apply` | Descriptions zake ni Sports Studies specific |
| `convert_missing_pages_to_interactive_html.py` | Legacy immediate conversion | Usii-run kwa `--help`; copy na adapt kwanza |
| `consolidate_chapter_pages.py` | Book-specific mutation/validation | Tumia baada ya backup na expected page count update |
| `remove_generated_quiz_pages.py` | Book-specific page removal | Tumia baada ya exact target verification |

Never assume script ina `--help` au dry-run. Thibitisha `argparse`/main function kwenye source kwanza.

## 21. Backup standard

Backup name ieleze checkpoint:

```text
backups/before-cover-placement/
backups/before-chapter-consolidation/
backups/before-accessibility/
backups/before-audio-regeneration/
backups/before-final-cleanup/
```

Backup angalau:

- HTML pages zitakazobadilishwa
- `pages.json`
- `toc.json`
- `imsmanifest.xml`
- i18n JSON files
- audio files zitakazoregenerated
- `offline-preloader.js`

## 22. Final sign-off checklist

### Content

- [ ] PDF pages zote zimefananishwa page-to-page.
- [ ] Hakuna heading, paragraph, list, figure, table au question iliyopotea.
- [ ] Printed page numbers na figure labels zimethibitishwa.

### Visual

- [ ] Chapter openers zinafanana na original.
- [ ] Think boxes ni compact na consistent.
- [ ] Images hazijastretch, crop vibaya au kuvunjika.
- [ ] Tables zinasomeka desktop na mobile.

### Interactivity

- [ ] Activities zina labelled answer controls pale zinapohitajika.
- [ ] Think prompts hazina unnecessary textarea.
- [ ] Quizzes zimejaribiwa.
- [ ] Answer persistence imejaribiwa.

### Accessibility

- [ ] Meaningful images zote zina useful alt/description.
- [ ] Decorative images zina empty alt na hazisomwi.
- [ ] Tables zote zina caption na correct header scopes.
- [ ] Keyboard focus na labels zimejaribiwa.

### Audio

- [ ] Imani voice imetumika.
- [ ] `texts`, `speech_texts`, `audios` na MP3 zina IDs zinazolingana.
- [ ] Missing audio counts ni zero.

### Packaging

- [ ] `pages.json` order ni sahihi.
- [ ] `page-section-id` ni sequential.
- [ ] TOC links ni sahihi.
- [ ] `imsmanifest.xml` ina new pages/assets.
- [ ] Offline preloader imerefreshiwa.
- [ ] Front na back covers zipo sehemu sahihi.

### Browser QA

- [ ] Desktop passed.
- [ ] Compact laptop passed.
- [ ] Mobile passed.
- [ ] Broken images ni zero.
- [ ] Console errors ni zero.
- [ ] First/last navigation states ni sahihi.

## 23. Recommended delivery report

Mwisho wa project, report iwe fupi na yenye evidence:

```text
PDF pages checked: ___
Reader pages: ___
Pages fixed: ___
Images described: ___
Tables described: ___
Audio voice: en-TZ-ImaniNeural
Missing text: 0
Missing speech: 0
Missing audio mappings: 0
Missing audio files: 0
Broken images: 0
Duplicate page IDs: 0
Browser console errors: 0
Backup checkpoint: ___
Preview URL: ___
```

Guide hii ndiyo baseline. Book-specific design inaweza kutofautiana, lakini content fidelity, accessibility, audio completeness, navigation integrity na QA gates hazipaswi kupunguzwa.


