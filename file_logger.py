"""File logger."""
import logging
import io

LOG = None
_stream = None


def open():
    """Open file logger."""
    global _stream
    global LOG
    _stream = io.open('system.log', mode='wa')
    logging.basicConfig(level=logging.INFO, stream=_stream)
    LOG = logging.getLogger("system")


def close():
    """Close file logger."""
    global _stream
    if _stream is not None:
        _stream.close()


def info(msg, *args):
    """Log at info level."""
    LOG.info(msg, *args)


def exc(e, msg, *args):
    """Log exception."""
    LOG.exc(e, msg, *args)
