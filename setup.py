from setuptools import setup
import os

setup(
    extras_require={
        "plotting": [
            "networkx",
            "matplotlib"
        ],
        "test": [
            "pytest>=4.4.2",
            "pandas>=1.0.3"
        ]
    },
    package_data={
        "opendp.smartnoise": [
            os.path.join("core", "lib", filename) for filename in [
                "libsmartnoise_ffi.dll",
                "libsmartnoise_ffi.so",
                "libsmartnoise_ffi.dylib",
            ]
        ]
    }
)
