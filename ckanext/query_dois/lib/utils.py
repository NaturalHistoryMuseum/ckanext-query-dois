from ckan import model
from ckan.plugins import toolkit


def get_resource_and_package(resource_id):
    '''
    Given a resource ID, returns the resource's dict and the parent package's dict too.

    :param resource_id: the resource ID
    :return: a 2-tupple, containing the resource dict and the package dict
    '''
    resource = toolkit.get_action(u'resource_show')({}, {u'id': resource_id})

    package_id = resource.get(u'package_id', None)
    if package_id is None:
        query = model.Session.query(model.Package) \
            .join(model.ResourceGroup) \
            .join(model.Resource) \
            .filter(model.ResourceGroup.id == resource[u'resource_group_id'])
        package_id = query.first().id
    package = toolkit.get_action(u'package_show')({}, {u'id': package_id})
    return resource, package
