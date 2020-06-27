from setuptools import find_packages, setup

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='routes-18xx',
    version='0.1',
    author="Austin Noto-Moniz",
    author_email="mathfreak65@gmail.com",
    description="Library for caluclating routes in 18xx train games.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/Auzzy/18xx-routes",
    packages=find_packages(),
    package_data={"routes18xx": ["data/1846/*", "data/1889/*"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "calc-routes = routes18xx.find_best_routes:main"
        ]
    }
)
