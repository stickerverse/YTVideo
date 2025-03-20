from setuptools import setup, find_packages
import os

# Create __init__.py files in necessary directories
directories = [
    'youtube_downloader',
    'youtube_downloader/downloaders',
    'youtube_downloader/services',
    'youtube_downloader/utils',
    'youtube_downloader/ui',
    'web',
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('# Auto-generated __init__.py file\n')

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="youtube_downloader",
    version="0.1.0",
    author="YourName",
    author_email="your.email@example.com",
    description="Advanced YouTube video downloader with multi-threading, proxy support, and CAPTCHA solving",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/youtube_downloader",
    
    # Explicitly specify packages to include
    packages=find_packages(include=['youtube_downloader', 'youtube_downloader.*', 'web', 'web.*']),
    
    # Include package data like static files
    include_package_data=True,
    
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ytdownloader=youtube_downloader.main:main",
        ],
    },
)
