# Пример использования модуля

```python
from RSA306 import reader

rsafile = reader.open('path/to/file.r3f')

iqdata = rsafile.read()
adcdata = rsafile.ADC

print(rsafile.centerFrequency) # print the center frequency
```

# Readers

## R3FFile
Доступны Footer данные
```python
...
footerData : List[FooterClass] = r3ffile.footerData
...
```

## R3AFile
По мимо файла r3a рядом должен лежать файл с заголовками r3h. Класс также может отработать и с передачей ему пути к r3h файлу, автоматически открыв нужные файлы 