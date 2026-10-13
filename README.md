# North Macedonia — legislation as Markdown (LawCodex)

Laws of the **Republic of North Macedonia** (Република Северна Македонија) as plain Markdown,
generated from **LDBIS** — "База на закони, подзаконски акти и други прописи", the legislation
database of the **Ministry of Justice** (https://ldbis.pravda.gov.mk). Language: Macedonian
(`mk`).

Part of [LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

## What is covered

| Directory | Content | Files |
|---|---|---|
| `ustav/` | Устав на Република Македонија (1991, original text as published) and its constitutional amendments (Амандмани) and constitutional laws | 12 |
| `zakoni/<year>/` | Laws in force: 1,528 base laws (original text), 104 LDBIS consolidated versions ("Пречистена верзија"), 3,132 amending laws | 4,764 |

Of the 5,560 law records found, 274 were no longer in force, 459 had a PDF without a text layer
(scans) or a truncated PDF, 41 record pages could not be read and 10 had no PDF.

Files: `<year>-<gazette issue>-<LDBIS id>-<transliterated title>.md` (year of publication in the
*Службен весник*). Front matter: `title`, `identifier` (gazette and issue), `ldbis_id`,
`type`, `date` (publication), `in_force_from`, `status`, `text_version`
(`original` = text as published; `amendment` = an amending law, as published;
`consolidated` = LDBIS "Пречистена верзија"), `source`, `retrieved`.

## How the corpus was selected

LDBIS's own search for "закон" and "устав", tab **"Влезени во сила"** (acts in force), gave
the list of acts; those whose title starts with Закон / Устав / Уставен закон / Амандман were
kept (5,560: 2,330 base laws incl. 1,053 ratification laws, and 3,230 amending laws). Each act's
record page gives its status; acts whose "Датум на престанок на важење" is not "Активен" were
dropped. Laws and their amendments are separate files: there is no general consolidated
version — LDBIS has "Пречистена верзија" (consolidated) records for a minority of laws only,
and the official gazette publishes official consolidated texts (пречистен текст) only
occasionally.

Text was extracted with `pdftotext` from the PDF that LDBIS serves for each record; the
gazette heading, the promulgation decree (Указ) and the act follow in order. Article labels
(Член N) are `####` headings; all-caps divisions `###`.

## What is NOT covered / problems

- Acts whose LDBIS PDF is a scanned image without a text layer (mostly older laws) — no OCR
  was done (459 acts, see above).
- Albanian versions (LDBIS has an Albanian interface and some texts), English translations.
- Secondary legislation (правилници, уредби, одлуки…), available in LDBIS but skipped.
- Official sources not used: the Official Gazette (https://slvesnik.com.mk) sells its database
  and gives free access only to whole-issue PDFs of past years; ENER (ener.gov.mk) was
  unreachable and hosts draft regulations.

## Licence

Laws and other official texts are not protected by copyright in North Macedonia (Закон за
авторското право и сродните права). Texts as published in LDBIS.

## Regenerating

```
python scripts/mk_fetch.py  ../_raw/mk
python scripts/mk_convert.py ../_raw/mk .
```

Needs `pdftotext` (poppler) and `scripts/requirements.txt`. Retrieved 2026-10-12.
