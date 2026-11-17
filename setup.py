from setuptools import setup, find_packages

setup(
    name="espcua",
    version="1.0.0",
    description="Host Adapter and CUA-Driver Bridge for ESP32-P4 IP-KVM",
    author="Zhihan Zheng",
    license="MIT",
    url="https://github.com/chnzzh/espcua-driver",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "espcua-driver = espcua.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: System :: Hardware",
    ],
)
