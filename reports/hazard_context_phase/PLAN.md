# Independent Indian labels and background research plan

**Confidential: do not publish before IP review.** Initial baseline `bc1d8be` on main is frozen; test-only GCC portability repair `1e67bd9` is verified by successful GitHub CI; source/model/export and report hashes are recorded in baseline.json. Work is additive in ml/hazard_context, reports/hazard_context_phase and new configs/docs/tests. No sensor-only or disaster deployment behavior changes.

1. Audit weak/independent labels, source rights and real ERA5 files/credentials before any fit. Review primary provider documentation; retain unavailable/uncertain data as candidates.
2. Add nullable event/source/monitoring schemas, evidence admission and minimum support gates. Deduplicate reports conservatively; ambiguous nearby reports group together for leakage prevention without asserting identical events.
3. Match events geodesically to fixed physical sites and observed UTC windows. Explicit monitoring is required for negatives; pre/post/event-exclusion periods remain unknown. Whole event-connected station/time groups and buffered episodes stay in one role.
4. Verify the unchanged 24 CDS requests, provide dry-run/explicit authenticated downloader and manual instructions. Build robust local NetCDF normalization and exact backward completed-hour joins with provenance. Retrospective context stays named and isolated; online mode requires verified publication times.
5. Add matched S/SB research comparison and episode scoring tools. No hazard fitting unless independently admitted positives, monitored negatives, rights, support and split coverage pass. No real S/SB comparison without real ERA5 files.
6. Test normalization, grouping, negative handling, geodesy, causal joins, tracks, safety and reproducibility. Check baseline hashes and update additive docs/report with explicit blockers and exact commands.
