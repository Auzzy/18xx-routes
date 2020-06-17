from setuptools import setup

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='routes-1846',
    version='0.21',
    author="Austin Noto-Moniz",
    author_email="metalnut4@netscape.net",
    description="Library for caluclating routes in 1846: The Race For The Midwest.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Auzzy/1846-routes",
    packages=['routes1846'],
    package_data={"routes1846": ["data/base-board.json", "data/tiles.json"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ]
)
