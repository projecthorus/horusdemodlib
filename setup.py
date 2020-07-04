import os
import re
from setuptools import setup, find_packages

regexp = re.compile(r".*__version__ = [\'\"](.*?)[\'\"]", re.S)

init_file = os.path.join(os.path.dirname(__file__), "src", "horusdemodlib", "__init__.py")
with open(init_file, "r") as f:
    module_content = f.read()
    match = regexp.match(module_content)
    if match:
        version = match.group(1)
    else:
        raise RuntimeError(f"Cannot find __version__ in {init_file}")


with open("README.md", "r") as f:
    readme = f.read()


with open("requirements.txt", "r") as f:
    requirements = []
    for line in f.read().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)


if __name__ == "__main__":
    setup(
        name="horusdemodlib",
        description="Project Horus Telemetry Decoding Library",
        long_description=readme,
        version=version,
        install_requires=requirements,
        keywords=["horus modem telemetry radio"],
        package_dir={"": "src"},
        packages=find_packages("src"),
        classifiers=[
            "Intended Audience :: Developers",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
        ]
    )
