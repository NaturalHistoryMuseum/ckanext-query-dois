$(document).ready(function () {
    /**
     * This little script simply hooks onto the request download button on the multisearch DOI
     * landing page and makes it submit a download request when clicked.
     */
    const downloadButton = $('#download-button');
    // this data is added in the template, extract it and parse the JSON data
    const query = JSON.parse(downloadButton.attr('data-query'));
    const queryVersion = downloadButton.attr('data-query-version');
    const resourceIdsAndVersions = JSON.parse(downloadButton.attr('data-resources-and-versions'));

    downloadButton.on('click', function () {
        // pull out the form data
        const email = $('#download-email').val();
        const format = $('#download-format').val();
        const separate = $('#download-sep').is(":checked");
        const empty = $('#download-empty').is(":checked");

        if (!email) {
            // this one is required so show an error if they haven't given us what we need
            $('.flash-messages').append('<div class="alert alert-error">Please enter an email address</div>');
        } else {
            const payload = {
                'email_address': email,
                'format': format,
                'separate_files': separate,
                'ignore_empty_files': empty,
                'query': query,
                'query_version': queryVersion,
                'resource_ids_and_versions': resourceIdsAndVersions,
            };
            fetch('/api/3/action/datastore_queue_download', {
                method: 'POST',
                body: JSON.stringify(payload),
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(function (response) {
                return response.json();
            }).then(function (json) {
                if (json.success) {
                    $('.flash-messages').append('<div class="alert alert-success">Download queued, you will be emailed once the data is ready</div>');
                } else {
                    $('.flash-messages').append('<div class="alert alert-error">Something went wrong, try again later</div>');
                }
            });
        }
    });
});
