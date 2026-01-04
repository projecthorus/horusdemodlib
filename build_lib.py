import pathlib
import os
import horusdemodlib.horus_api_build as horus_api_build

def build(setup_kwargs):
    setup_kwargs.update(
        {"ext_modules": [
            horus_api_build.ffibuilder.distutils_extension(),
        ]},
    )
    