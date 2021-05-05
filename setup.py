import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(name='framboesa',
  version='0.1',
  description='A plugin to get framboesa stats',
  url='http://github.com/averissimo',
  author='André Veríssimo',
  author_email='afsverissimo@gmail.com',
  long_description=long_description,
  long_description_content_type="text/markdown",
  license='MIT',
  install_requires=[
    "psutil",
    "influxdb_client",
    "requests"
  ],
  package_dir={"": "src"},
  py_modules=["framboesa"],
  python_requires=">=3.6",
)
