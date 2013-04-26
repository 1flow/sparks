from distutils.core import setup
VERSION = '0.1.0'
setup(name='sparks',
      version=VERSION,
      author='Olivier Cortès',
      author_email='contact@oliviercortes.com',
      url='https://github.com/Karmak23/sparks',
      description='My foundations repository, which I use to bootstrap '
      'any new project or machine',
      license='New BSD',
      long_description="""

My foundations repository, which I use to bootstrap any new project or machine.
 Helps for django projects, too.

""",
      packages=['sparks'],
      classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Web Environment',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: New BSD',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
      'Topic :: Internet :: WWW/HTTP',
      'Topic :: Software Development :: Libraries',
      ],
      )
