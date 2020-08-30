"""File logger."""
import io
import logging


class File:
    """Singleton file logger class."""

    __logger = None
    __instance = None

    @staticmethod
    def logger():
        """Static method to obtain the file logger."""
        if File.__logger is None:
            File()
        return File.__logger

    @staticmethod
    def close_log():
        """Static method to close the file logger."""
        if File.__instance is not None:
            File.__instance.__close_file()
            File.__instance = None
        File.__logger = None

    def __init__(self):
        """Virtually private constructor."""
        if File.__logger is not None:
            raise Exception("This class is a singleton!")
        else:
            self.__stream = io.open('system.log', mode='a')
            logging.basicConfig(level=logging.INFO, stream=self.__stream)
            File.__logger = logging.getLogger('system')
            File.__instance = self

    def __close_file(self):
        if self.__stream is not None:
            self.__stream.close()
            self.__stream = None
