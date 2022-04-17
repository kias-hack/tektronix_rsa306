from RSA306.exceptions import InvalidInputFileExtension
from .r3a import R3AFile
from .r3f import R3FFile
from .reader import RSAReader


def __isCompatibleExtension(extension):
    """Проверка на совместимость файлов (.3rf, .r3a, r3h)"""
    return extension in [".r3f", ".r3a", "r3h"]

def open(path) -> RSAReader:
    """
    Возвращает ридер в зависимости от файла который был передан.
    Проводится проверка на совместимость
    """

    extension = path[-4:]
    if not __isCompatibleExtension(extension):
        raise InvalidInputFileExtension()
    
    if extension == ".r3f":
        return R3FFile(path)
    
    return R3AFile(path)