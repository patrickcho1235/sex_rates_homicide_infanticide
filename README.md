# U.S. homicide and filicide offender-sex data

This project creates source-traceable CSV files about the recorded sex of
homicide offenders in the United States, with separate cross-tabulations for
filicide by victim age.

The project does **not** analyze any individual criminal case. Its purpose is
to make the base-rate evidence and its limitations clear enough for public
discussion.

## Current outputs

The primary RStudio workflow writes these finished deliverables to `output/`:

- `sex_rates_homicide_infanticide.html`: the knitted analysis report.
- `homicide_subtype_sex_comparison_2016_2025.csv`: the unrounded result of the
  primary R Markdown comparison. It contains female proportion, female:male
  odds, and the odds ratio relative to general homicide for filicide from
  birth through age 17, including the two recorded infant-age subdivisions.
- `inferential_model_input_2016_2025.csv`: annual counts for six mutually
  exclusive filicide age groups and an all-other-homicide reference group.
- `inferential_model_results_2016_2025.csv`: year-adjusted odds ratios with
  source-record-clustered confidence intervals and Holm-adjusted p-values.
- `inferential_model_diagnostics_2016_2025.csv`: convergence, sparse-cell,
  overdispersion, goodness-of-fit, influence, temporal-heterogeneity, and
  missing-sex checks.
- `inferential_model_cell_diagnostics_2016_2025.csv`: fitted values and
  residual/influence diagnostics for every year-by-group cell.
- `inferential_model_missingness_2016_2025.csv`: unknown-sex proportions and
  worst-case female-proportion bounds for the disjoint groups.
- `inferential_model_period_sensitivity_2016_2025.csv`: separate adjusted
  estimates for 2016-2020 and 2021-2025 when testing reporting-period
  heterogeneity.
- `inferential_model_leave_one_year_out_2016_2025.csv`: influence sensitivity
  estimates obtained by omitting each data year in turn.
- `figures/figure_1_primary_comparison_2016_2025.{png,svg}`: female-proportion
  and adjusted-odds-ratio panels for the primary comparison.
- `figures/figure_2_period_sensitivity_2016_2025.{png,svg}`: adjusted estimates
  for 2016-2020 and 2021-2025.
- `figures/figure_3_annual_female_proportion_2016_2025.{png,svg}`: annual
  proportions and Wilson intervals by analytic group.
- `figures/figure_4_unknown_sex_2016_2025.{png,svg}`: unknown-sex prevalence by
  analytic group.

Supporting prepared data remain in `data/processed/`:

- `homicide_offender_sex_by_year.csv`: FBI national expanded-homicide offender
  counts and percentages, 1985-2025. These values come from the current FBI
  Crime Data Explorer API.
- `filicide_offender_sex_counts_tidy.csv`: reusable counts by year, exact SHR
  age code, parent/stepparent relationship code, and offender sex.
- `filicide_offender_sex_by_age_year.csv`: yearly parent/stepparent offender-sex
  summaries for standard, nonoverlapping child age bins.
- `filicide_offender_sex_by_age_period.csv`: pooled summaries, including a
  separate 0-6-day and 7-364-day breakdown. Use the latest-ten-year rows for a
  recent, more stable comparison than a single rare-event year.
- `filicide_offender_sex_by_age_parent_type_period.csv`: pooled summaries that
  keep parent and stepparent records separate.
- `source_inventory.csv`: FBI archive key, SHA-256 checksum, file size, record
  counts, retrieval time, and parser diagnostics for every annual master file.

## Operational definitions

- **Homicide** in the broad file means murder and nonnegligent manslaughter as
  presented by the FBI Expanded Homicide API. It does not mean homicide arrest
  data.
- **Infanticide** is represented by the SHR age codes `NB` (birth through 6
  days) and `BB` (7 through 364 days). The standard bin combines both as
  `under 1 year`; the period file also preserves the two subdivisions.
- **Filicide** here means a victim under 18 whose relationship to a recorded
  offender is son (`SO`), daughter (`DA`), stepson (`SS`), or stepdaughter
  (`SD`). The parent category should not be relabeled “biological parent”: the
  SHR layout does not establish that distinction. Stepparents are separately
  identifiable and are included in the combined age summaries.
- Counts are **offender records**, not unique incidents or unique people across
  years. A multi-offender incident can contribute more than one offender.
- `male_percent_known_sex` and `female_percent_known_sex` use only records coded
  male or female as the denominator. The files also report percentages of all
  records and retain unknown/not-specified counts.

These are descriptive proportions, not population offending rates. Creating a
sex-specific offending rate would require defensible population denominators
and additional assumptions that are outside this first data release.

## Important limitations

The annual SHR master-file layout contains a relationship between each listed
offender and the **first-listed victim**. It contains demographics, but not
victim-offender relationships, for additional victims. The filicide files
therefore do not capture a child who appears only as an additional victim in a
multi-victim incident. This can undercount family-annihilation and other
multi-victim events.

The filicide numerator is also restricted to cases with a qualifying recorded
relationship. Unknown offenders and unknown relationships cannot be classified
as filicide. A mother’s or father’s boyfriend/girlfriend is not counted unless
the record specifically codes that person as a stepparent. Foster parents and
guardians are not separately identifiable in this SHR layout.

UCR participation is voluntary, missingness is substantial in offender and
relationship fields, and the FBI transition toward NIBRS beginning with the
2021 data year affects comparability. These CSVs are reported-data summaries,
not complete enumerations of every U.S. homicide. Small annual filicide cells
are volatile; pooled periods are generally the sounder descriptive view.

The API and master files can differ because the API is refreshed with later
agency corrections while an annual archive is a fixed download. This is why
the broad file uses the current API and the cross-tab files carry archive
checksums rather than mixing the two without disclosure.

## Sources

- [FBI Crime Data Explorer](https://cde.ucr.cjis.gov/LATEST/)
- [FBI documents and downloads](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads)
- [FBI Expanded Homicide API endpoint](https://cde.ucr.cjis.gov/LATEST/shr/national?from=01-2025&to=12-2025&type=totals)
- [OJJDP explanation of SHR data and victim/offender file structure](https://www.ojjdp.ojp.gov/statistical-briefing-book/data-analysis-tools/ezashr/methods)
- [CDC WISQARS NVDRS help on the direction of parent/child relationship coding](https://wisqars.cdc.gov/help/national-violent-death-reporting-system/)

## Primary RStudio workflow

Open `sex_rates_homicide_infanticide.rmd` in RStudio and select **Knit**. The
document reads the cached FBI SHR ZIP archives directly using base R, derives
both the general-homicide reference and infant-filicide counts from the same
2016-2025 source files, calculates the descriptive and inferential comparisons,
and writes the documented CSVs and knitted HTML report to `output/`.

The R Markdown analysis does not import a Python-generated analytic table. Its
descriptive parsing uses base R; the inferential section additionally requires
the `sandwich` package for source-record-clustered covariance estimates. Figure
generation requires `ggplot2`, `scales`, and `patchwork`.

## Source archive acquisition

The FBI archives are already cached in `data/raw/fbi_shr/`. The original
acquisition and full-series CSV preparation script uses only the Python
standard library and is retained for source provenance:

```bash
python3 scripts/build_fbi_shr_csvs.py
```

It caches the FBI annual ZIP archives in `data/raw/fbi_shr/`, obtains temporary
signed download URLs from the FBI, validates the fixed record length, and
rebuilds every CSV. The default range is 1985-2025, the full range currently
offered in the FBI master-file catalog.
