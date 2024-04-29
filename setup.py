from setuptools import setup, find_packages

setup(
    name='finestock',
    version='0.0.3',
    description='Korean Stock OpenAPI Package(EBest, KIS) creation written by alshin',
    author='A.Lok, Shin',
    author_email='shinalok357@gmail.com',
    url='https://github.com/shinalok/fine-stock-api',
    install_requires=['websockets','asyncio', 'requests',],
    packages=find_packages(exclude=[]),
    keywords=['ebest', 'kis', 'openapi', 'stock', 'kr'],
    python_requires='>=3.6',
    package_data={},
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)