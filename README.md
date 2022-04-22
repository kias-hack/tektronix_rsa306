# Пример использования модуля

```python
from RSA306.reader import get_reader

rsafile = get_reader('path/to/file.r3f')

adc, center_frequency, if_center_frequency = rsafile.read()
```

# Readers

## Reader
Читает r3f файлы. Доступны Footer данные
```python
...
footer : List[Footer] = r3ffile.footerData
...
```

## RawReader
По мимо файла r3a рядом должен лежать файл с заголовками r3h. Класс также может отработать и с передачей ему пути к 
r3h файлу, автоматически открыв нужные файлы 