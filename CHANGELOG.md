# Changelog

## v4.1.1 (2024-08-20)

### Chores/Misc

- add build section to read the docs config

## v4.1.0 (2023-12-04)

### Feature

- use the new datastore_multisearch_counts action to speed up resource hits counting

### Refactor

- remove a datastore_multisearch call by summing the individual resource counts

## v4.0.1 (2023-10-05)

### Fix

- generate doi in download init, not manifest generation

### Docs

- specify vds version 5.2+ in the README

### Chores/Misc

- add regex for version line in citation file
- add citation.cff to list of files with version
- add contributing guidelines
- add code of conduct
- add citation file
- update support.md links

## v4.0.0 (2023-07-18)

### Breaking Changes

- remove support for ckanpackager

### Feature

- use versioned_datastore download button snippet
- set query_version for old queries to v0, add resource_counts

### Fix

- don't load the download button if vds not available
- old query versions should now be v0

### Refactor

- **dependencies**: remove support for ckanpackager

### Docs

- update version of vds in readme and clarify statement

### Chores/Misc

- add migration to set the default query version to v0

## v3.0.5 (2023-07-17)

### Docs

- update logos

## v3.0.4 (2023-04-11)

### Build System(s)

- fix postgres not loading when running tests in docker

### Chores/Misc

- add action to sync branches when commits are pushed to main

## v3.0.3 (2023-02-20)

### Docs

- fix api docs generation script

### Style

- reformat with prettier

### Chores/Misc

- small fixes to align with other extensions

## v3.0.2 (2023-01-31)

### Docs

- **readme**: change logo url from blob to raw

## v3.0.1 (2023-01-31)

### Docs

- **readme**: direct link to logo in readme
- **readme**: fix github actions badge

## v3.0.0 (2023-01-31)

### Breaking Changes

- now requires version 4 or later of ckanext-versioned-datastore

### Feature

- replace download button with link to status when download queued
- record stat in new download_after_run hook

### Fix

- update the multisearch landing page with new download options
- update vds hooks

### Refactor

- **stats**: allow saving stats without email addresses

### Tests

- spell notifier correctly
- change references to old interface method

### Build System(s)

- **docker**: use 'latest' tag for test docker image

### Chores/Misc

- remove references to v2.4.0

## v2.3.0 (2022-12-13)

### Feature

- add the total dois to the query doi sidebar
- add the new get_doi_count helper to the plugin helpers list
- add a new helper that returns the DOI count for a package

### Refactor

- changes existing function to use common util function

### Tests

- move unit tests into a unit subdir
- remove skip mark on broken test
- add tests for get_most_recent_dois before refactor
- add test for new doi count helper

### Chores/Misc

- reword the recent DOI explainer text
- add conftest to setup database model as fixture

## v2.2.2 (2022-12-12)

### Docs

- **readme**: add instruction to install lessc globally

### Style

- change quotes in setup.py to single quotes

### Build System(s)

- remove local less installation
- add package data

## v2.2.1 (2022-12-01)

### Docs

- **readme**: fix table borders
- **readme**: format test section
- **readme**: update installation steps
- **readme**: update ckan patch version in header badge

## v2.2.0 (2022-11-28)

### Refactor

- convert to less

### Docs

- add section delimiters and include-markdown

### Style

- apply formatting

### Build System(s)

- set changelog generation to incremental
- pin ckantools minor version

### CI System(s)

- add cz-nhm dependency

### Chores/Misc

- use cz_nhm commitizen config
- improve commitizen message template
- standardise package files

## v2.1.1 (2022-06-13)

## v2.1.0 (2022-03-21)

## v2.0.4 (2022-03-07)

## v2.0.3 (2021-10-19)

## v2.0.2 (2021-03-11)

## v2.0.1 (2021-03-10)

## v2.0.0 (2021-03-09)

## v1.0.0-alpha (2019-08-16)

## v0.1.1 (2019-05-21)

## v0.1.0 (2019-04-15)
