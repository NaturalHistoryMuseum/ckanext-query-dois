# ckanext-query-dois

Creates DOIs for queries on resources. By recording the query parameters used and the exact version
of the data at the time of the query, this allows precise retrieval of the data as it looked when
the DOI was minted.

Must be used in conjunction with the
[ckanext-versioned-datastore](https://github.com/NaturalHistoryMuseum/ckanext-versioned-datastore).

To get DOIs for downloads
[ckanext-ckanpackager](https://github.com/NaturalHistoryMuseum/ckanext-versioned-datastore) should
be used (this extension automatically hooks into it's interface if it finds the plugin is active in
the running CKAN environment).


# Setup

1. Clone the repository into the virtual env's `src` folder:

  ```bash
  cd /usr/lib/ckan/default/src/
  git clone https://github.com/NaturalHistoryMuseum/ckanext-query-dois.git
  ```

2. Activate the virtual env:

  ```bash
  . /usr/lib/ckan/default/bin/activate
  ```

3. Run setup.py:

  ```bash
  cd /usr/lib/ckan/default/src/ckanext-query-dois
  python setup.py develop
  ```

4. Add 'query_dois' to the list of plugins in your config file:

  ```ini
  ckan.plugins = ... query_dois
  ```

5. Install the requirements from requirements.txt:

  ```bash
  cd /usr/lib/ckan/default/src/ckanext-query-dois
  pip install -r requirements.txt
  ```
