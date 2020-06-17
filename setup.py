from setuptools import setup

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='routes-18xx',
    version='0.1',
    author="Austin Noto-Moniz",
    author_email="metalnut4@netscape.net",
    description="Library for caluclating routes in 18XX train games.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Auzzy/18xx-routes",
    packages=['routes18xx'],
    package_data={"routes18xx": ["data/*"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ]
)
