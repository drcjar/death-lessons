# deathlessons.org — data-quality audit of judiciary.uk PFD reports

Scope: **6340 report pages** scraped from the judiciary.uk Prevention of Future Deaths listing. Findings below are issues in the *published* data (URLs, titles, metadata) that may be worth correcting at source.

## 1. Duplicate reference numbers (45 refs on >1 page)

The same PFD reference number appears on multiple distinct report pages (different deceased). This may be legitimate (one report covering several co-reported deaths) or a reference-number collision / duplicate publication — worth reviewing.

- **2013-0239** → jones-2013-0239 , shokri-gharab-2013-0239
- **2013-0360** → lynne-dring , john-lansdowne
- **2013-0361** → simon-sankey , timothy-clayton
- **2013-0362** → roy-frank-fletcher , ethel-cross
- **2014-0301** → komba-kpakiwa , josephine-foday
- **2014-0332** → ming-cheung , anthony-ponting
- **2014-0336** → charles-pierson , molly-keen
- **2014-0386** → stephen-farrar , ashley-ponsonby
- **2014-0556** → dean-hutchinson , robert-wood
- **2014-0558** → rhys-williams , christopher-ayaji
- **2014-0560** → joanne-nobbs , sandra-bodrozic
- **2015-0204** → mark-foley , elizabeth-lester
- **2015-0315** → lorraine-bird , james-adams
- **2015-0389** → erich-speilmann , john-roberts
- **2015-0421** → david-pooley , jacqueline-williams
- **2015-0446** → imran-douglas , neil-garry
- **2016-0001** → matthew-wood , peter-barnes
- **2016-0007** → nicholas-milligan , emily-milligan
- **2016-0030** → lee-hoyle , edward-haughey , carl-dickerson
- **2016-0145** → jaroslaw-rogala , adele-blakeman
- **2016-0146** → corey-price , alesha-oconnor , margaret-challis , rhodri-miller-binding
- **2016-0436** → cameron-forster , ajvir-sandhu
- **2017-0076** → catherine-roberts , derek-turnbull
- **2017-0157** → blaise-alvares , sharon-soares
- **2017-0210** → anne-marie-james , melvin-james
- …and 20 more

## 2. Name disagreements between URL and page (68)

The name in the page URL disagrees with the page's own published *Deceased name* field (e.g. `linda-books` vs *Linda Brooks*). In most cases the URL appears to be the misspelling, but either field could be wrong — worth reconciling, as the URL is the permanent shareable link.

| URL slug | Published name | URL token | name-field token |
|---|---|---|---|
| `edward-hand-prevention-of-future-deaths-report` | Edward Hands | hand | hands |
| `linda-books-prevention-of-future-deaths-report` | Linda Brooks | books | brooks |
| `micheala-finch-prevention-of-future-deaths-report` | Michaela Finch | micheala | michaela |
| `maria-theobald-prevention-of-future-deaths-report` | Marie Theobald | maria | marie |
| `margaret-reece-prevention-of-future-deaths-report` | Margaret Reeves | reece | reeves |
| `rosemary-mcandrew-prevention-of-future-deaths-report` | Rosemary MacAndrew | mcandrew | macandrew |
| `adulrahman-alajmi-prevention-of-future-deaths-report` | Abdulrahman Alajmi | adulrahman | abdulrahman |
| `patricia-cattherall-prevention-of-future-deaths-report` | Patricia Catterall | cattherall | catterall |
| `muhammed-and-naemat-esmael-prevention-of-future-deaths-report` | Muhammad & Naemat Esmael | muhammed | muhammad |
| `wayne-bailey-prevention-of-future-deaths-report` | Wayne Bayley | bailey | bayley |
| `george-dillion-prevention-of-future-deaths-report-2` | George Dillon | dillion | dillon |
| `george-dillion-prevention-of-future-deaths-report-1` | George Dillon | dillion | dillon |
| `phephisa-mabusa-prevention-of-future-deaths-report` | Phephisa Mabuza | mabusa | mabuza |
| `frederick-dunbavin-prevention-of-future-deaths-report` | Fredrick Dunbavin | frederick | fredrick |
| `philip-evans-prevention-of-future-deaths-report` | Philips Evans | philip | philips |
| `anna-elliott-prevention-of-future-deaths-report` | Anna Elliot | elliott | elliot |
| `megan-davidson-prevention-of-future-deaths-report` | Megan Davison | davidson | davison |
| `alan-kingsbury-prevention-of-future-deaths-report` | Alan Kinsbury | kingsbury | kinsbury |
| `roberto-bettello-prevention-of-future-deaths-report` | Roberto Bottello | bettello | bottello |
| `sylvia-daniel-prevention-of-future-deaths-report` | Sylvia Davies | daniel | davies |
| `geoffery-hoad-prevention-of-future-deaths-report` | Geoffrey Hoad | geoffery | geoffrey |
| `elliott-harrett-prevention-of-future-deaths-report` | Elliott Harratt | harrett | harratt |
| `sean-heeny-prevention-of-future-deaths-report` | Sean Heeney | heeny | heeney |
| `chrisitian-tuvi-prevention-of-future-deaths-report` | Christian Tuvi | chrisitian | christian |
| `brenda-shield-prevention-of-future-deaths-report` | Brenda Shields | shield | shields |
| `kaiustutt-prevention-of-future-deaths-report` | Kaius Tutt | kaiustutt | kaius |
| `john-ibbotson-prevention-of-future-deaths-report` | John Ibboston | ibbotson | ibboston |
| `jamie-woods-prevention-of-future-deaths-report` | Jamie Wood | woods | wood |
| `ann-daghlain-prevention-of-future-deaths-report` | Ann Daghlian | daghlain | daghlian |
| `glenys-roberts-prevention-of-future-deaths-report` | Glendys Roberts | glenys | glendys |
| `deline-etienne-prevention-of-future-deaths-report` | Delina Etienne | deline | delina |
| `muhammad-hasan-prevention-of-future-deaths-report` | Muhammad Hassan | hasan | hassan |
| `antony-mclellan-prevention-of-future-deaths-report` | Anthony McLellan | antony | anthony |
| `mena-teferi-prevention-of-future-deaths-report` | Mena Terefi | teferi | terefi |
| `neville-bardoliwala` | Neville Bardoliwalla | bardoliwala | bardoliwalla |
| `agnes-marchessou` | Agnès Marchessou | agnes | agn |
| `sian-hewitt` | Siân Hewitt | sian | si |
| `shante-turay-thomas` | Shanté Turay-Thomas | shante | shant |
| `jane-livington-2` | Jane Livingston | livington | livingston |
| `kenneth-daly` | KennethDaly | kenneth | kennethdaly |
| `jennifer-witney` | Jennifer Withey | witney | withey |
| `williams-vickers` | William Vickers | williams | william |
| `sabastian-hibberd` | Sebastian Hibberd | sabastian | sebastian |
| `christopher-kierman` | Christopher Kiernan | kierman | kiernan |
| `joseph-tamowski` | Joseph Tarnowski | tamowski | tarnowski |
| `james-pashley` | Jamie Pashley | james | jamie |
| `sheila-stokes` | Shelia Stokes | sheila | shelia |
| `dorothea-parr` | Dorethea Parr | dorothea | dorethea |
| `kyle-lowes` | Kyles Lowes | kyle | kyles |
| `michael-mcmonigle` | Micael McMonigle | michael | micael |

…and 18 more.

## 3. Same deceased on multiple report pages (124 names)

Often legitimate (several reports about one death, refs differ), but worth checking for true duplicates. Examples:

- **Ellen Taylor**: ellen-taylor-prevention-of-future-deaths-report-2 (2026-0236) , ellen-taylor-prevention-of-future-deaths-report (2026-0079)
- **James Stewart**: james-stewart-prevention-of-future-deaths-report (2026-0221) , james-stewart (2014-0526)
- **Mark Smith**: mark-smith-prevention-of-future-deaths-report-2 (2026-0205) , mark-smith-prevention-of-future-deaths-report (2025-0478)
- **Roman Barr**: roman-barr-prevention-of-future-deaths-report-2 (2026-0197) , roman-barr-prevention-of-future-deaths-report (2026-0148)
- **Jardine Williams**: jardine-williams-1-prevention-of-future-deaths-report (2026-0173) , jardine-williams-2-prevention-of-future-deaths-report (2026-0174)
- **Thomas Ruggiero**: thomas-ruggiero-3-prevention-of-future-deaths-report (2026-0172) , thomas-ruggiero-2-prevention-of-future-deaths-report (2026-0171) , thomas-ruggiero-1-prevention-of-future-deaths-report (2026-0170)
- **Lee Adams**: lee-adams-2-prevention-of-future-deaths-report (2026-0157) , lee-adams-prevention-of-future-deaths-report (2026-0156)
- **Wendy Eyles**: wendy-eyles-prevention-of-future-deaths-report (2026-0153) , wendy-eyles-prevention-of-future-death-report (2025-0641)
- **Darren Dickson**: darren-dickson-prevention-of-future-deaths-report-2 (2026-0151) , darren-dickson-prevention-of-future-deaths-report-1 (2026-0150)
- **Susan Samson**: susan-samson-prevention-of-future-deaths-report-2 (2026-0120) , susan-samson-prevention-of-future-deaths-report (2026-0112)
- **John Franklin**: john-franklin-prevention-of-future-deaths-report-2 (2026-0110) , john-franklin-prevention-of-future-deaths-report (2025-0474)
- **Edward Jones**: edward-jones-prevention-of-future-deaths-report-2 (2026-0096) , edward-jones-prevention-of-future-deaths-report (2025-0633)

## 4. Report pages with no attached PDF (1)

- john-ibbotson-prevention-of-future-deaths-report

## 5. Missing published metadata fields

| Field | Pages missing it | % |
|---|---|---|
| ref | 97 | 1.5% |
| name_of_deceased | 31 | 0.5% |
| date_of_report | 29 | 0.5% |
| category | 28 | 0.4% |
| coroner_name | 20 | 0.3% |
| coroner_area | 17 | 0.3% |

## 6. Filename ref ≠ page Ref field (34)

The reference baked into the PDF filename disagrees with the page's Ref.

- kore-padgett-prevention-of-future-deaths-report: page says **2025-0441**, file is `Kore-Elizabeth-Padgett-Prevention-of-future-deaths-report-2025-0411.pdf`
- patrick-viles-prevention-of-future-deaths-report: page says **2025-0313**, file is `Patrick-Viles-Prevention-of-Future-Deaths-Report-2025-0312.pdf`
- lewis-johnson-2-prevention-of-future-deaths-report: page says **2025-0242**, file is `Lewis-Johnson-Narrative-Prevention-of-Future-Deaths-Report-2025-0241-1.pdf`
- simon-harding-prevention-of-future-deaths-report: page says **2025-0065**, file is `Simon-Harding-Prevention-of-Future-Deaths-Report-2024-0065.pdf`
- wyllow-raine-swinburn-prevention-of-future-deaths-report: page says **2025-0064**, file is `Wyllow-Raine-Lawson-Swinburn-Prevention-of-Future-Deaths-Report-2024-0064.pdf`
- jean-thomas-prevention-of-future-deaths-report-2: page says **2025-0059**, file is `Jean-Thomas-Prevention-of-Future-Deaths-Report-2024-0059.pdf`
- susan-karakoc-prevention-of-future-deaths-report: page says **2024-0702**, file is `Susan-Karakoc-Prevention-of-Future-Deaths-Report-2024-0703.pdf`
- gabrielle-steel-prevention-of-future-deaths-report: page says **2024-0526**, file is `Gabrielle-Steel-Prevention-of-Future-Deaths-Report-2024-0256.pdf`
- dave-onawelo-prevention-of-future-deaths-report: page says **2024-0470**, file is `Dave-Onawelo-Prevention-of-Future-Deaths-Report-2024-0469.pdf`
- tony-williams-prevention-of-future-deaths-report: page says **2024-0385**, file is `Tony-Williams-Prevention-of-Future-Deaths-Report-2024-0835.pdf`
- james-furlong-joseph-ritchie-bennett-and-david-wails-prevention-of-future-deaths-report: page says **2024-0276**, file is `James-Furlong-Joseph-Ritchie-Bennett-and-David-Wails-Prevention-of-future-deaths-report-2024-0232.pdf`
- maxine-davison-lee-martyn-sophie-martyn-stephen-washington-and-kate-shepherd-prevention-of-future-deaths-report: page says **2023-0085**, file is `firearms-licensing-thematic-report-20020101.pdf`
- joanna-daly-prevention-of-future-deaths-report: page says **2021-0245**, file is `Joanna-Daly-Prevention-of-future-deaths-report-2021-0242.pdf`
- stephen-thurm: page says **2021-0155**, file is `Stephen-Thurm-2021-0154-Redacted.pdf`
- costel-stancu: page says **2019-0379**, file is `Costal-Stancu-2010-0379.pdf`
- shaun-neal: page says **2019-0009**, file is `Shaun-Neal-2019-0138.pdf`
- nora-bruton: page says **2019-0090**, file is `Nora-Bruton-2019-0099.pdf`
- mary-johnson: page says **2019-0495**, file is `Mary-Johnson-2019-0458.pdf`
- irene-baker: page says **2017-0363**, file is `Irene-Baker-2017-0362.pdf`
- john-nichols: page says **2017-0344**, file is `John-Nichols-2017-0345.pdf`

## 7. Empty (0-byte) PDFs served (1)

- `2015-0149-Response-Brighton-and-Sussex-University-Hospitals-NHS-Trust.pdf`

## 8. Inconsistent report-phrase spelling in URLs (4 variants)

The canonical phrase is `prevention-of-future-deaths-report`, but URLs use several spellings (missing “of”, singular “death”, etc.):

| phrase in URL | # URLs |
|---|---|
| `prevention-of-future-deaths-report` | 2708 |
| `prevention-of-future-death-report`  ⚠ | 18 |
| `prevention-future-deaths-report`  ⚠ | 2 |
| `prevent-of-future-deaths-report`  ⚠ | 1 |

---

### Summary counts

- report pages: 6340
- duplicate reference numbers: 45
- likely URL-name typos: 68
- deceased names on multiple pages: 124
- pages with no PDF: 1
- filename/Ref mismatches: 34
- empty PDFs: 1
- malformed report-phrase URLs: 21