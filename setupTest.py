# coding utf-8

from os.path import join, dirname, abspath
from pathlib import Path
from pathlib import Path
import sys

assert Path.cwd().resolve() == Path(__file__).resolve().parent
sys.path.insert(0, 'src')

from invoke import Exit, task
from rellu import initialize_labels, ReleaseNotesGenerator, Version
from rellu.tasks import clean
from robot.libdoc import libdoc

# dir_name = join(dirname(abspath(__file__)), 'README.rst')
# print(abspath(__file__))
# print(dirname(__file__))
# print(dirname(abspath(__file__)))
# print(dirname(abspath(__file__)))
# print(abspath("README.rst"))
# print(dir_name)
# print(join(dirname(abspath(__file__))))
# VERSION = '5.1.dev1'
# with open(join(dirname(abspath(__file__)), 'README.rst')) as f:
#     LONG_DESCRIPTION = f.read()
#     base_url = 'https://github.com/robotframework/robotframework/blob/master'
#     for text in ('INSTALL', 'CONTRIBUTING'):
#         search = '`<{0}.rst>`__'.format(text)
#         replace = '`{0}.rst <{1}/{0}.rst>`__'.format(text, base_url)
#         print(search)
#         print(replace)
#
# PACKAGE_DATA = [join('htmldata', directory, pattern)
#                 for directory in ('rebot', 'libdoc', 'testdoc', 'lib', 'common')
#                 for pattern in ('*.html', '*.css', '*.js')]
#
# print(PACKAGE_DATA)
print("*****************************************")
# print(Path(__file__))
# print(Path(__file__).resolve())
# print(Path(__file__).resolve().parent)
# print(Path)
# print(Path.cwd())
# print(Path.cwd().resolve() )
# print(Path('src/robot/version.py'))
# print(Path('setup.py'))
REPOSITORY = 'robotframework/robotframework'
VERSION_PATH = Path('src/robot/version.py')
VERSION_PATTERN = "VERSION = '(.*)'"
SETUP_PATH = Path('setup.py')
print(type(SETUP_PATH))
print(SETUP_PATH)
POM_VERSION_PATTERN = '<version>(.*)</version>'
RELEASE_NOTES_PATH = Path('doc/releasenotes/rf-{version}.rst')
RELEASE_NOTES_TITLE = 'Robot Framework {version}'
RELEASE_NOTES_INTRO = '''
`Robot Framework`_ {version} is a new release with **UPDATE** enhancements
and bug fixes. **MORE intro stuff...**

**REMOVE reference to tracker if release notes contain all issues.**
All issues targeted for Robot Framework {version.milestone} can be found
from the `issue tracker milestone`_.

Questions and comments related to the release can be sent to the
`robotframework-users`_ mailing list or to `Robot Framework Slack`_,
and possible bugs submitted to the `issue tracker`_.

**REMOVE ``--pre`` from the next command with final releases.**
If you have pip_ installed, just run

::

   pip install --pre --upgrade robotframework

to install the latest available release or use

::

   pip install robotframework=={version}

to install exactly this version. Alternatively you can download the source
distribution from PyPI_ and install it manually. For more details and other
installation approaches, see the `installation instructions`_.

Robot Framework {version} was released on {date}.

.. _Robot Framework: http://robotframework.org
.. _Robot Framework Foundation: http://robotframework.org/foundation
.. _pip: http://pip-installer.org
.. _PyPI: https://pypi.python.org/pypi/robotframework
.. _issue tracker milestone: https://github.com/robotframework/robotframework/issues?q=milestone%3A{version.milestone}
.. _issue tracker: https://github.com/robotframework/robotframework/issues
.. _robotframework-users: http://groups.google.com/group/robotframework-users
.. _Robot Framework Slack: https://robotframework-slack-invite.herokuapp.com
.. _installation instructions: ../../INSTALL.rst
'''
# version = 0.01
# version = Version(version, VERSION_PATH, VERSION_PATTERN)
# v = version.write()
# print(v)

