# Draft email to the judiciary.uk PFD reports team

**To:** Chief Coroner's Office / PFD reports publications team (via the judiciary.uk contact form, https://www.judiciary.uk/contact-us/)
**Subject:** Data-quality observations on the published Prevention of Future Death reports

---

Dear Sir or Madam,

I run [deathlessons.org](https://deathlessons.org), a free tool that makes the published Prevention of Future Death (PFD) reports full-text searchable, so that researchers, clinicians and journalists can find relevant reports more easily.

While rebuilding our index of all ~6,340 report pages, we ran an automated data-quality check and noticed a number of small inconsistencies in the published URLs and metadata that you may wish to correct at source. They are minor individually, but a few affect the permanent shareable links, and one attaches the wrong document. I'm sharing them in case they're useful, and I'd be glad to send the full machine-readable list.

A few highlights:

- **~68 report-page URLs misspell the deceased's name** relative to the page's own "Deceased name" field (e.g. `…/linda-books…` for *Linda Brooks*; `…/adulrahman-alajmi…` for *Abdulrahman Alajmi*). As the URL is the permanent citation link, these are the most worth correcting.
- **~34 reports where the reference in the PDF filename differs from the page's Ref field.** In one case (Maxine Davison and others, 2023-0085) the attached PDF appears to be an unrelated "firearms-licensing thematic report".
- **One page serves a 0-byte PDF**, and **one report page has no PDF attached** (john-ibbotson-…).
- **~45 reference numbers appear on more than one report page** (some may be legitimate co-reported deaths, but worth a check).
- **~21 URLs use non-standard spellings** of "prevention-of-future-deaths-report" (missing "of", singular "death", etc.).

Full details, with examples for each category, are here:
https://github.com/drcjar/death-lessons/blob/master/data_quality_report.md

We are admirers of this resource and simply want to help keep it accurate and findable. Please do let me know if it would help to receive the underlying data in any particular format.

With thanks and best wishes,

[Your name]
deathlessons.org

---

*Notes for sending:*
- *Fill in `[Your name]` (and any title/affiliation you'd like to add for credibility).*
- *No single published email address for PFD reports; the judiciary.uk contact form or the Chief Coroner's Office is the right route.*
- *Counts are from `data_quality_report.md` (6,340 report pages): 45 duplicate refs, 68 URL-name typos, 124 deceased-on-multiple-pages, 34 filename/Ref mismatches, 1 missing PDF, 1 empty PDF, 21 malformed URLs.*
