from setuptools import setup

setup(
    name='flask_page',
    packages=['flask_page'],
    include_package_data=True,
    install_requires=[
        'flask',
        'oauth2client',
        'google-api-python-client'
    ],
)
