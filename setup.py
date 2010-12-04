from setuptools import setup, find_packages
import sys, os

version = '1.1'
shortdesc = 'Handle web application parts as tiles.'
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
longdesc = open(os.path.join(os.path.dirname(__file__), 'src', 'bda', 'bfg',
                             'tile', '_api.txt')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'LICENSE.rst')).read()

setup(name='bda.bfg.tile',
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Web Environment',
            'Operating System :: OS Independent',
            'Programming Language :: Python', 
            'Topic :: Internet :: WWW/HTTP :: Dynamic Content',        
      ],
      keywords='',
      author='BlueDynamics Alliance',
      author_email='dev@bluedynamics.com',
      url=u'https://svn.bluedynamics.eu/svn/module/bda.bfg.tile/',
      license='GNU General Public Licence',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['bda', 'bda.bfg'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'repoze.bfg',
      ],
      dependency_links = [
          "http://dist.repoze.org/bfg/1.2/",
      ],
      extras_require = dict(
          test=['interlude']
      ),
      tests_require=['interlude'],
      test_suite="bda.bfg.tile.tests.test_suite",      
      )
