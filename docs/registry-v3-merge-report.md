# Registry v3 merge report

- base: `tajweed_error_registry_v2.json` (34 entries)
- patch: `tajweed_registry_v3_patch.json`
- result: `tajweed_error_registry_v3.json` (36 entries)
- source: Тажвид қоидалари — Зиёвуддин Раҳим; Одилхон қори Юнусхон ўғли, «Тошкент ислом университети» нашриёт-матбаа бирлашмаси, 2011, ISBN 978-9943-390-26-3

## A. Terminology corrections applied to uz blocks

122 substitutions across 29 entries.

| replacement | count |
|---|---|
| `qalin -> yo'g'on` | 43 |
| `madd -> mad` | 20 |
| `makhraj -> maxraj` | 14 |
| `Qalin -> Yo'g'on` | 7 |
| `nun sokin -> sukunli «nuvn»` | 7 |
| `Nun sokin -> Sukunli «nuvn»` | 5 |
| `Madd -> Mad` | 5 |
| `shadid -> shiddat` | 4 |
| `Makhraj -> Maxraj` | 3 |
| `mufaxxam -> iste'lo harfi` | 3 |
| `ikhfo -> ixfo` | 3 |
| `rixv -> raxovat` | 2 |
| `safir -> sofiyr` | 2 |
| `Shadid -> Shiddat` | 2 |
| `Ikhfo -> Ixfo` | 2 |

Map keys that matched nothing: `moraqaq`, `safeer`, `tikraar`, `tafashie`, `mim sokin`, `nun harfi`, `mim harfi`, `seen`.
These are still correct to carry - they guard future entries.

## B. Entries

- added (6): `MAKHARIJ_SHEEN_TO_JEEM`, `MAKHARIJ_THAL_TO_ZAA_CONFUSION`, `MAKHARIJ_WAW_TO_FA`, `MIM_IDGHAM_MISLAYN_MISSING`, `MIM_IKHFA_SHAFAWIYA_MISSING`, `MIM_IZHAR_SHAFAWIYA_WRONG`
- rewritten (4): `GHUNNA_MISSING`, `QALQALAH_EXCESSIVE`, `SHIDDA_LOST`, `TAFKHEEM_LOST`


## D. Structural amendments

**Deleted**

- `GHUNNA_ADDED` — The signal is unimplementable, not merely imprecise. It asks for expected 'not_maghnoon' surfacing as 'maghnoon' at izhar positions - but the reference marks even an izhar noon 'maghnoon', because ghunnah is a property of the LETTER nuvn/miym, not of the ruling. There is no ṣifa flip to detect anywhere in the Quran, so the entry could never fire correctly no matter how the precondition was narrowed.
- `MAKHARIJ_THAL_TO_ZAY` — Merged into MAKHARIJ_INTERDENTAL_TO_ZAY - see merges below.
- `MAKHARIJ_ZAA_TO_ZAY` — Merged into MAKHARIJ_INTERDENTAL_TO_ZAY - see merges below.
- `HAMS_LOST` — SCOPE DECISION, NOT A DEFECT. Requested by Rahmatulloh 2026-08-07. Hams/jahr is lahn khafiy khafiy - a refinement most reciters cannot hear, which changes neither meaning nor the validity of the recitation. This app's current purpose is correcting mistakes that change meaning or break a required rule, and this entry is not one of those. The entry was detectable and its precondition was sound (95.6% -> 41.4%); it is being removed because it is out of scope, not because it did not work.
- `JAHR_LOST` — SCOPE DECISION, NOT A DEFECT. Requested by Rahmatulloh 2026-08-07. Same ruling as HAMS_LOST - the other direction of the same ṣifa, and the same lahn khafiy khafiy classification. Removed for scope, not for accuracy: its precondition was the most restrictive of the four ṣifa narrowings (100% -> 8.8%, the sakin voiced obstruents ذ ز ض ظ غ).
- `SHIDDA_LOST` — SCOPE DECISION, NOT A DEFECT. Requested by Rahmatulloh 2026-08-07. Shidda/rakhawa is lahn khafiy khafiy on the same grounds: a shadeed letter read slightly loose is audible to a trained ear and to almost nobody else, and it does not change the word. Its precondition was sound (97.3% -> 17.7%, sakin ء ك ت after the qalqalah letters are removed).

**Merged**

- `MAKHARIJ_INTERDENTAL_TO_ZAY` ← `MAKHARIJ_THAL_TO_ZAY`, `MAKHARIJ_ZAA_TO_ZAY` — **NEEDS_UPDATE**

**Split**

- `MADD_ADDED_LEEN` — NEEDS_AUTHORING
- `MADD_ADDED` — kept + overridden


## C. Safety gate

Every entry status is `draft`.

**1 entries have no authored uz body**: `MADD_ADDED_LEEN`.

This is deliberate, not an omission. Decision 4 forbids an LLM authoring a tajweed rule, so a split or merge that needs new text leaves it unwritten. `content.render()` returns None for these and `pipeline.analyze()` files them under `silent_errors`.

Nothing here is shown to a learner. `content/rules.json` is the learner-facing file and this merge does not touch it.
