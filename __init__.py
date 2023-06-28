import pathlib
import site


def classFactory(*args, **kwds):  # pylint: disable=invalid-name
    """Loads the Bit Flag Renderer Plugin.
    """
    site.addsitedir(pathlib.Path(__file__).parent)
    from bitflagrenderer.plugin import BitFlagRendererPlugin
    return BitFlagRendererPlugin(*args, **kwds)
