import importlib.metadata
try:
    __version__ = importlib.metadata.version(__package__)
except:
    # during build the package is imported before being installed so we don't have metadata yet
    __version__ = 'unknown'
