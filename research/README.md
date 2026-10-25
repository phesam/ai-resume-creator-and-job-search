# Research notes

The longer notes behind [docs/EVIDENCE.md](../docs/EVIDENCE.md) and the code, written in October 2026.

- [callback_timing_volume_referrals.md](callback_timing_volume_referrals.md): applicant volume, timing, referrals,
  ghost jobs and response rates, with every source and how strong it is. The ranking model's freshness curve and
  referral boost come from here.
- [ats_api_reference.md](ats_api_reference.md): the public job APIs of every supported applicant tracking system,
  verified live, with their gotchas. Read this before writing a new adapter in `jobhunt/ats_extra.py`.
- [company_registry_notes.md](company_registry_notes.md): how the first 270 entries of `data/companies.yaml` were
  found and checked (the registry has since grown to about 600). Its seed file is not included.
