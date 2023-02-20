$(document).ready(function () {
  /**
   * This little script simply hooks onto the request download button on the multisearch DOI
   * landing page and makes it submit a download request when clicked.
   */
  const downloadButton = $('#download-button');
  // this data is added in the template, extract it and parse the JSON data
  const query = JSON.parse(downloadButton.attr('data-query'));
  const queryVersion = downloadButton.attr('data-query-version');
  const resourceIdsAndVersions = JSON.parse(
    downloadButton.attr('data-resources-and-versions'),
  );

  downloadButton.on('click', function () {
    // pull out the form data
    const format = $('#download-format').val();
    const separate = $('#download-sep').is(':checked');
    const empty = $('#download-empty').is(':checked');

    const payload = {
      file: {
        format: format,
        separate_files: separate,
        ignore_empty_fields: empty,
      },
      query: {
        query: query,
        query_version: queryVersion,
        resource_ids_and_versions: resourceIdsAndVersions,
      },
      notifier: {
        type: 'none',
      },
    };
    fetch('/api/3/action/datastore_queue_download', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (json) {
        if (json.success) {
          $('.flash-messages').append(
            `<div class="alert alert-success">Download queued. Check the <a href="/status/download/${json.result.download_id}">status page</a> to follow its progress.</div>`,
          );
          $('#download-button')
            .replaceWith(`<a id="download-button" href="/status/download/${json.result.download_id}" class="btn btn-primary text-right">
                    <i class="fas fa-arrow-circle-right"></i> Download status</a>`);
        } else {
          $('.flash-messages').append(
            '<div class="alert alert-error">Something went wrong, try again later</div>',
          );
        }
      });
  });
});
