#!/usr/bin/env python3
"""Setup configuration for openclaw-cron-scheduler."""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

setup(
    name='openclaw-cron-scheduler',
    version='0.1.0',
    description='Intelligent cron task scheduler for OpenClaw with queue-based rate limiting',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='OpenClaw Contributors',
    author_email='',
    url='https://github.com/Fourier7754/openclaw-cron-scheduler',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'click>=7.0.0',
        'pyyaml>=5.4.0',
    ],
    entry_points={
        'console_scripts': [
            'openclaw-scheduler=openclaw_cron_scheduler.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords=['cron', 'scheduler', 'queue', 'openclaw', 'rate-limiting'],
    include_package_data=True,
)
