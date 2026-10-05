# Final backend verification against ToC Assignment 1_2569.pdf

Date: 2026-10-05. Branch: `fix/assignment-masking`.
Both pages of the assignment PDF were read. This report supersedes the earlier
pre-fix and partial-fix reports for the current backend.

## Outcome

All five assignment examples pass. All **100/100 existing CSV cases** pass,
including **73/73 required** and **27/27 optional/decision** cases.
The expanded verification passes **68,178/68,178 assertions**, with no failures.
The focused unittest suite passes all **6 test methods**, including three
overlapping-input cases under all **120 rule orderings each**.

| Assignment rule | Verified behavior |
| --- | --- |
| Card | `1234-5678-9012-3456` → `XXXX-XXXX-XXXX-3456` |
| Email | `somchai.d@company.com` → `s*******d@company.com` |
| Phone | `093-245-7894` → `XXX-XXX-7894` |
| DOB | `DOB:25/12/2549` → `DOB:XX/XX/25XX` |
| Address | Only the house number is hidden; soi, road, administrative names and postal codes remain unchanged in tested examples. |

Every detector and its rule-specific masking uses Python's standard-library `re`,
as required by the PDF. The backend accepts text and returns masked text.

## Corrections

- Email punctuation, phone/date boundaries, DOB/address whitespace, slash-address
  masking, and house-number prefix collisions are fixed.
- Both endpoints now use one shared detector over the original text. Masking
  combines the hidden characters required by all enabled rules. Transforming one
  match can no longer invalidate another match or leave DOB day/month visible.
- Rule order is irrelevant, duplicate rule IDs are counted once, an empty list
  disables every rule, and omitted/null selection enables all five rules.
- Malformed double-@ email substrings are rejected by the tested boundary rule.
  Service imports no longer print sample logs. Published patterns match tested
  implementation behavior.

The previous leaking input now behaves as follows:

```text
Input:  DOB:25/12/2549@mail.com
Output: DOB:XX/XX/2**X@mail.com
```

This applies both rules' protections. If one rule retains a character but another
requires hiding it, the character stays hidden. At a shared masked position,
email's `*` wins a marker conflict with `X`.

Real original-text detection spans are intentionally retained even when they
overlap. The original design's no-overlap promise was corrected rather than
discarding valid detections. Verification now checks both detections and their
combined masking output. The PDF does not prescribe match metadata or overlap
precedence. The phone-in-email case uses an already-accepted CSV alternative;
no existing CSV expected values were modified.

## Verification coverage

The expanded suite includes all 100 CSV cases through HTTP; both endpoints and
match flags; all 32 rule subsets; all 120 full-rule orderings on independent
examples; malformed JSON and request-type/length validation; metadata consistency;
numeric boundaries; Thai, emoji and punctuation wrappers; whitespace; and
prefix collisions. All 1,768 HTTP invariant assertions and all 43,826 service
span/idempotence assertions pass.

Finite generated domains include all 1,296 card and 216 phone group-length
combinations in 1..6, all 10,000 four-digit years, and all 10,000 two-digit
day/month pairs independently. The latter checks regex shape, not calendar
validity. All eight 50,000-character payload checks pass. Observed local request
times were approximately 10–37 ms, not a concurrency/load guarantee.

Assertions include repeated invariants; their count is not a count of distinct
inputs or proof over every possible Unicode log. Unsupported alternative data
formats remain outside the PDF's prescribed formats.

## Reproduction

With the existing development dependencies installed:

```powershell
python -X utf8 -m unittest discover -s test -p test_masking_regressions.py
python -X utf8 test/verify_assignment.py
python -X utf8 test/run_pipeline.py
```

All three checks pass. The existing pipeline was run with its output path
redirected to `test/data/result_fixed.csv` to preserve the user's existing modified
`result.csv`; running it normally writes `result.csv`. Expanded results are in
`test/data/assignment_verification.json`. The temporary tool cache was removed
after verification. No project dependency was added.

## Remaining submission work outside this backend

The PDF also requires a web-app URL with a GitHub source link on its page, a
YouTube presentation of at most 10 minutes emphasizing regex, a group of 10–12,
and an explanation of member responsibilities. Its deadline is **14 October
2026 before 09:00**. The team's **7 October, 14:30** meeting deadline is separate.

Those UI, deployment, presentation, and group requirements cannot be certified
from this backend repository. Browser rendering, frontend UTF-16 offset handling,
Docker's Python 3.12 runtime, and concurrent/adversarial load were not verified.
The passing checks establish the tested backend behavior, not a guaranteed grade
or universal production-security claim.
