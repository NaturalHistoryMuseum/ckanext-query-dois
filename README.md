<!--header-start-->
<img src=".github/nhm-logo.svg" align="left" width="150px" height="100px" hspace="40"/>

# ckanext-query-dois

[![Tests](https://img.shields.io/github/workflow/status/NaturalHistoryMuseum/ckanext-query-dois/Tests?style=flat-square)](https://github.com/NaturalHistoryMuseum/ckanext-query-dois/actions/workflows/main.yml)
[![Coveralls](https://img.shields.io/coveralls/github/NaturalHistoryMuseum/ckanext-query-dois/main?style=flat-square)](https://coveralls.io/github/NaturalHistoryMuseum/ckanext-query-dois)
[![CKAN](https://img.shields.io/badge/ckan-2.9.7-orange.svg?style=flat-square)](https://github.com/ckan/ckan)
[![Python](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue.svg?style=flat-square)](https://www.python.org/)
[![Docs](https://img.shields.io/readthedocs/ckanext-query-dois?style=flat-square)](https://ckanext-query-dois.readthedocs.io)

_A CKAN extension that creates DOIs for queries on resources._

<!--header-end-->

# Overview

<!--overview-start-->
This extension creates (mints) digital object identifiers (DOIs) for queries on resources. By recording the query parameters used and the exact version of the data at the time of the query, this allows precise retrieval of the data as it looked when the DOI was minted.

**Must be used in conjunction with the [ckanext-versioned-datastore](https://github.com/NaturalHistoryMuseum/ckanext-versioned-datastore).**

_Optionally:_ [ckanext-ckanpackager](https://github.com/NaturalHistoryMuseum/ckanext-ckanpackager) can be used to get DOIs for downloads (`query-dois` automatically hooks into the `ckanext-ckanpackager` interface if it finds the plugin is active in the running CKAN environment).

You will need an account with a DataCite DOI service provider to use this extension.

<!--overview-end-->

# Installation

<!--installation-start-->
Path variables used below:
- `$INSTALL_FOLDER` (i.e. where CKAN is installed), e.g. `/usr/lib/ckan/default`
- `$CONFIG_FILE`, e.g. `/etc/ckan/default/development.ini`

1. Clone the repository into the `src` folder:

  ```bash
  cd $INSTALL_FOLDER/src
  git clone https://github.com/NaturalHistoryMuseum/ckanext-query-dois.git
  ```

2. Activate the virtual env:

  ```bash
  . $INSTALL_FOLDER/bin/activate
  ```

3. Install the requirements from requirements.txt:

  ```bash
  cd $INSTALL_FOLDER/src/ckanext-query-dois
  pip install -r requirements.txt
  ```

4. Run setup.py:

  ```bash
  cd $INSTALL_FOLDER/src/ckanext-query-dois
  python setup.py develop
  ```

5. Add 'query_dois' to the list of plugins in your `$CONFIG_FILE`:

  ```ini
  ckan.plugins = ... query_dois
  ```

6. Initialise database tables

  ```bash
  ckan -c $CONFIG_FILE query-dois initdb
  ```

## Further setup

You need to sign up for an account with [DataCite](https://datacite.org) and provide the credentials in your configuration.

<!--installation-end-->

# Configuration

<!--configuration-start-->
These are the options that can be specified in your .ini config file.

## **[REQUIRED]**

Name|Description|Options
--|--|--
`ckanext.query_dois.prefix`|Prefix to use for the new DOIs|
`ckanext.query_dois.datacite_username`|Datacite account username|
`ckanext.query_dois.datacite_password`|Datacite account password|
`ckanext.query_dois.doi_title`|Template string for the DOI title: takes `count` as a format argument|
`ckanext.query_dois.publisher`|DOI publisher name|

## Other options

Name|Description|Options|Default
--|--|--|--
`ckanext.query_dois.test_mode`|Enable/disable using test DOIs (i.e. not creating real DOIs)|True/False|True

<!--configuration-end-->

# Usage

<!--usage-start-->
## Commands

### `initdb`
Initialises the database table.

1. `initdb`: initialise the database model
    ```bash
    ckan -c $CONFIG_FILE query-dois initdb
    ```

<!--usage-end-->

# Testing

<!--testing-start-->
There is a Docker compose configuration available in this repository to make it easier to run tests.

To run the tests against ckan 2.9.x on Python3:

1. Build the required images
```bash
docker-compose build
```

2. Then run the tests.
   The root of the repository is mounted into the ckan container as a volume by the Docker compose
   configuration, so you should only need to rebuild the ckan image if you change the extension's
   dependencies.
```bash
docker-compose run ckan
```

The ckan image uses the Dockerfile in the `docker/` folder.

<!--testing-end-->
