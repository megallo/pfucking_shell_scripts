from setuptools import setup, find_packages

with open('requirements.txt') as file_requirements:
    requirements = file_requirements.read().splitlines()

setup(
    name='pfucking_shell_scripts',
    version='1.0.0',
    packages=find_packages(),
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        pfucking_shell_scripts=pfucking_shell_scripts:main
    ''',
)
