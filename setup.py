from setuptools import setup
from setuptools import find_packages

short_description = \
    'TODO'

long_description = '''
PRETOR - PRogram Evaluation TOol Rebuilt
'''.lstrip()  # remove leading newline

classifiers = [
    # see http://pypi.python.org/pypi?:action=list_classifiers
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Topic :: Communications :: File Sharing'
    ]

setup(name="pretor",
      version="TODO",
      description=short_description,
      long_description=long_description,
      author="Charles Daniels",
      author_email="cdaniels@fastmail.com",
      url="TODO",
      license='BSD',
      classifiers=classifiers,
      keywords='TODO',
      packages=find_packages(),
      entry_points={'console_scripts':
          ['pretor-psf=pretor.psf:psf_cli',
           'pretor-plugin=pretor.plugin:plugin_cli',
           'pretor-grade=pretor.grader:repl']},
      package_dir={'pretor': 'pretor'},
      platforms=['POSIX'],
      install_requires=['toml', 'tabulate']
      )

