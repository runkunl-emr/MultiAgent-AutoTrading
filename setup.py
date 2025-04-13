from setuptools import setup, find_packages

setup(
    name="quant_trading_bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "websocket-client>=1.4.0",
        "pyyaml>=6.0.0",
        "requests>=2.28.0",
    ],
) 