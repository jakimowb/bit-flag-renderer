from .bitflagrenderer.plugin import BitFlagRendererPlugin


def classFactory(*args, **kwds):  # pylint: disable=invalid-name
    """Loads the Bit Flag Renderer Plugin.
    """
    return BitFlagRendererPlugin(*args, **kwds)
