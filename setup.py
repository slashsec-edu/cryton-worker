from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='cryton_worker',
      version='2020.4.1',
      description='Cryton Worker - Attack scenario automation toolset',
      url='https://gitlab.ics.muni.cz/beast-public/cryton/cryton-worker',
      author='Ivo Nutar, Jiri Raja, Andrej Tomci',
      author_email='nutar@ics.muni.cz, 469429@mail.muni.cz, 469192@mail.muni.cz',
      packages=find_packages(),
      python_requires='>3.8',
      install_requires=requirements,
      entry_points={
          'console_scripts': [
              'cryton-worker=cryton_worker.cli:cli'
          ]
      },
      zip_safe=False,
      data_files=[
            ('/etc/cryton/', []),
            ('/etc/cryton', ['cryton_worker/etc/config-worker.ini']),
            ('/etc/cryton', ['cryton_worker/etc/logging_config_worker.yaml']),
      ])
