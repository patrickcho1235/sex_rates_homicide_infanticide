# CSV data dictionary

## Shared count and percentage fields

- `male_offender_records`, `female_offender_records`: counts explicitly coded
  male or female.
- `unknown_or_not_specified_offender_records`: all other raw SHR sex values,
  including unknown, not specified, and blank values.
- `known_sex_offender_records`: male plus female records.
- `total_offender_records`: male plus female plus unknown/not specified.
- `male_percent_known_sex`, `female_percent_known_sex`: sex share after
  excluding unknown/not-specified records from the denominator.
- `male_percent_all_records`, `female_percent_all_records`: sex share with all
  offender records in the denominator.
- `unknown_or_not_specified_percent_all_records`: missing/unknown sex share.
- `male_to_female_ratio_known_sex`: male records divided by female records; is
  blank when the female count is zero.

Percent fields are numeric percentages on a 0-100 scale and are rounded to
three decimal places.

## Age-bin fields

- `standard_nonoverlap`: under 1, 1-4, 5-9, 10-14, and 15-17 years.
- `detailed_nonoverlap`: 0-6 days, 7-364 days, 1-4, 5-9, 10-14, and 15-17
  years. This appears in the pooled period file.
- `overall`: all qualifying records with a first-listed victim under 18.

Do not sum rows across different `age_bin_scheme` values; the schemes overlap.
Within one `standard_nonoverlap` or `detailed_nonoverlap` scheme, the bins do
not overlap.

## Broad homicide file

`homicide_offender_sex_by_year.csv` retains the FBI API’s `Unknown` and `Not
Specified` categories separately. `other_offender_records` captures any future
API category not currently named by the pipeline. `api_last_refresh_date`
records the FBI’s own data refresh date returned with the query.

## Filicide files

`parent_type=parent` corresponds to SHR victim relationship `SO` (son) or `DA`
(daughter). `parent_type=stepparent` corresponds to `SS` (stepson) or `SD`
(stepdaughter). The relationship is phrased from victim to offender.

The tidy file preserves raw offender sex and victim age codes for auditing.
Counts in all filicide files are restricted to first-listed victims because
the fixed-width SHR master layout does not provide relationships for additional
victims.

## Census coresident-parent denominator file

`census_coresident_parent_denominators_2016_2025.csv` contains one row per
year and parent sex:

- `parent_count`: estimated number of people with at least one coresident,
  never-married biological, step, or adopted child under age 18.
- `source_method`: distinguishes published Census CPS ASEC Table AD-2 values
  (2016-2023) from estimates reconstructed from CPS ASEC person records using
  child-to-parent pointers and `MARSUPWT` (2024-2025).
- `source_url`: official Census workbook or public-use microdata URL.
- `source_file_md5`: checksum of the cached source file used when knitting.
- `denominator_definition`: the denominator universe in plain language.

These counts represent unique coresident parents in each survey year, not
parent-child dyads. They exclude nonresident parents and should not be treated
as a perfect exposure match for the SHR numerator.
