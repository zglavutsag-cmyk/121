from setuptools import setup, find_packages

setup(
    name='vk-farm-bot',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'vk-api',
    ],
)