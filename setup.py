from setuptools import setup, find_packages

setup(
    name='finestock',
    version='1.0.1.0',
    description='Korean Stock OpenAPI Package(EBest, KIS, LS) creation written by alshin',
    author='A.Lok, Shin',
    author_email='shinalok357@gmail.com',
    url='https://github.com/shinalok/finestock',
    install_requires=['websockets', 'requests', 'loguru'],
    extras_require={
        # 예제 스크립트(example.py 등)의 .env 자동 로드용 선택 의존성.
        # 패키지 자체 동작에는 필요 없음.
        'examples': ['python-dotenv'],
    },
    packages=find_packages(exclude=[]),
    keywords=['ebest', 'kis', 'ls', 'kiwoom', 'openapi', 'stock', 'kr'],
    python_requires='>=3.7',
    package_data={},
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)