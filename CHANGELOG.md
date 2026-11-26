# Changelog

## v1.0.1 - 2026-11-26

- Added optional CookieCloud account loading with `PyCookieCloud==1.0.4`.
- Added single-profile and multi-profile environment variables with static-cookie priority and `wps_sid` deduplication.
- Added same-domain `wps_sid`/`uid` pairing, per-profile failure isolation, a 30-second fetch limit, recursive JSONL redaction, safe push-error logging, and Python 3.8/3.11 CI coverage.

## v1.0.0 - 2026-11-24

- Added multi-account WPS Lingxi check-in.
- Added `daily_check_in` task extraction, date selection, claim, and strict task/balance readback.
- Added primary/fallback domain handling, JSONL results, GitHub Actions, offline tests, and six-language docs.
