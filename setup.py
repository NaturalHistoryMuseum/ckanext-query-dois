from setuptools import setup, find_packages

version = '0.1'

setup(
    name='ckanext-query-dois',
    version=version,
    description='Query DOIs',
    long_description='Allows the creation of DOIs for queries on resources',
    classifiers=[],
    keywords='',
    author=['Josh Humphries'],
    author_email='data@nhm.ac.uk',
    url='https://github.com/NaturalHistoryMuseum/ckanext-query-dois',
    license='',
    packages=find_packages(exclude=['ez_setup', 'list', 'tests']),
    namespace_packages=['ckanext', 'ckanext.query_dois'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'datacite==1.0.1',
        'bcrypt==3.1.4',
    ],
    entry_points= \
        """
        [ckan.plugins]
        query_dois=ckanext.query_dois.plugin:QueryDOIsPlugin
        [paste.paster_command]
        initdb=ckanext.query_dois.commands:QueryDOIsInitDBCommand
        """,
)
