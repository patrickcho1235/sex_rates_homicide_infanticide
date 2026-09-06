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
- `population_denominated_filicide_rates_2016_2025.csv`: annual under-18
  filicide offender-record counts, Census coresident-parent denominators, and
  reported records per million parent-years by sex.
- `population_denominated_filicide_rate_ratio_2016_2025.csv`: pooled rates and
  the female:male rate ratio, a count-only Poisson interval, and the primary
  year-adjusted quasi-Poisson interval corrected for overdispersion.
- `population_denominated_homicide_rates_2016_2025.csv`: annual female and male
  general-homicide offender-record rates using Census resident-population
  exposure.
- `relative_filicide_vs_homicide_rate_ratio_2016_2025.csv`: the year-adjusted
  ratio of rate ratios: mother:father filicide divided by female:male homicide,
  with a year-cluster-robust confidence interval.
- `census_parent_denominator_method_validation_2023.csv`: comparison of the
  published 2023 parent totals with the CPS ASEC microdata reconstruction.
- `figures/figure_1_primary_comparison_2016_2025.{png,svg}`: linked panels for
  female proportion, the actual within-group female:male ratio, and the
  adjusted comparative odds ratio.
- `figures/figure_2_period_sensitivity_2016_2025.{png,svg}`: adjusted estimates
  for 2016-2020 and 2021-2025.
- `figures/figure_3_annual_female_proportion_2016_2025.{png,svg}`: annual
  proportions and Wilson intervals by analytic group.
- `figures/figure_4_unknown_sex_2016_2025.{png,svg}`: unknown-sex prevalence by
  analytic group.
- `figures/figure_5_denominator_contrast_2016_2025.{png,svg}`: contrast between
  the conditional odds among homicide offender records and reported-record
  rates using Census coresident-parent exposure.
- `figures/figure_6_conditional_waffle_2016_2025.{png,svg}`: one-thousand-dot
  unit charts showing how concentrated under-18 filicide is within female and
  male homicide offender records.
- `figures/figure_7_denominator_switch_2016_2025.{png,svg}`: editorial-style
  graphic contrasting the 7.64 conditional odds ratio with the 0.78
  parent-exposure rate ratio.
- `figures/figure_8_annual_population_rate_dumbbell_2016_2025.{png,svg}`:
  annual paired rates demonstrating the consistency of the population-
  denominated direction across all ten years.
- `figures/figure_9_relative_female_filicide_elevation_2016_2025.{png,svg}`:
  large-font direct answer showing how many times higher the female:male rate
  ratio is for filicide than for homicide generally.

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
- `census_coresident_parent_denominators_2016_2025.csv`: sex-specific parent
  estimates from published CPS ASEC Table AD-2 for 2016-2023 and a validated
  public-use-microdata reconstruction for 2024-2025.
- `census_resident_population_by_sex_2016_2025.csv`: official annual Census
  resident-population estimates used for the general-homicide rate denominator.

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

The first four figures and the homicide-composition tables are descriptive
proportions, not population offending rates. Figure 5 adds a deliberately
bounded population-denominated comparison using Census estimates of people
with a coresident child under 18. It is a reported offender-record rate per
national coresident parent-year, not a complete U.S. incidence rate or an
individual probability.

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

The population denominator excludes nonresident parents, but the SHR does not
identify whether the offender and victim were coresident. The Census counts
are also national rather than restricted to SHR-reporting jurisdictions.
Those scope mismatches mean that Figure 5 must not be described as the chance
that an arbitrary mother or father will commit filicide. Its confidence
interval reflects numerator count variation only; it does not incorporate CPS
survey error or uncertainty from SHR undercoverage and missing relationships.

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
- [Census historical living arrangements of adults, including Table AD-2](https://www.census.gov/data/tables/time-series/demo/families/adults.html)
- [Census 2025 CPS ASEC public-use data and documentation](https://www.census.gov/data/datasets/2025/demo/cps/cps-asec-2025.html)

## Primary RStudio workflow

Open `sex_rates_homicide_infanticide.rmd` in RStudio and select **Knit**. The
document reads the cached FBI SHR ZIP archives directly using base R, derives
both the general-homicide reference and infant-filicide counts from the same
2016-2025 source files, calculates the descriptive and inferential comparisons,
and writes the documented CSVs and knitted HTML report to `output/`.

The R Markdown analysis does not import a Python-generated analytic table. Its
descriptive parsing uses base R; the inferential section additionally requires
the `sandwich` package for source-record-clustered covariance estimates. The
population-denominator section requires `readxl`; on a clean clone, it
downloads the official 2023-2025 CPS ASEC fixed-width files directly from the
Census Bureau. Figure generation requires `ggplot2`, `scales`, and `patchwork`.

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
