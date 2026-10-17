# dual-ocr

Lee una página escaneada con dos motores de OCR, Tesseract y RapidOCR, y combina las dos lecturas palabra por palabra para quedarse con el texto más limpio.

## Para qué sirve

Sirve para sacar texto de páginas escaneadas o fotografiadas, sobre todo de libros viejos, donde la tipografía no es limpia. Devuelve el texto ya separado en párrafos, listo para leer, traducir o buscar.

## Por qué existe

Ningún motor de OCR acierta siempre. En las pruebas que hicimos con un libro escaneado pasó lo siguiente:

- Tesseract separa bien los párrafos y lee bien el cuerpo del texto, pero a veces confunde letras parecidas y se pierde en portadas con tipografía decorativa.
- RapidOCR acierta más en las letras, pero a veces pega en un solo párrafo lo que debería ir separado.

Cuando uno falla, el otro suele acertar, y no siempre son las mismas palabras. Por eso el proyecto lee la página con los dos y compara. Donde las lecturas coinciden, se toma la palabra y se conservan los saltos de párrafo que marque cualquiera de los dos. Donde difieren, gana la lectura que tiene más palabras válidas en inglés: si uno lee «LNountains» y el otro «mountains», se queda con «mountains».

Esto no reemplaza la revisión humana. El criterio es un diccionario, así que se equivoca cuando los dos motores fallan igual, con nombres propios que el diccionario no trae, o con símbolos que parecen palabras. Si vas a publicar o traducir el resultado, lee las páginas con texto raro.

## Cómo funciona

1. La imagen se prepara: escala de grises, autocontraste, enderezado fino y binarización con OpenCV.
2. Tesseract lee la página (antes se corrige la orientación de 90 o 180 grados).
3. RapidOCR lee la misma página, sin esa corrección porque su modelo ya clasifica la orientación.
4. Las dos lecturas se alinean palabra por palabra con `difflib` de la biblioteca estándar y se fusionan con las reglas de arriba.

Si uno de los dos motores no está instalado, el proyecto usa solo el otro. Si no hay ninguno, lanza un error claro.

## Instalación

Necesitas Python (lo probamos con la versión 3.11) y el programa de Tesseract en tu sistema:

- macOS: `brew install tesseract`
- Debian o Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-eng`
- Windows: el instalador de UB Mannheim

Después, en el directorio del proyecto:

```
pip install -r requirements.txt
```

## Uso

Desde la línea de comandos, con una imagen de página:

```
python dual_ocr.py pagina.png
python dual_ocr.py pagina.png --engine tesseract
python dual_ocr.py pagina.png --engine rapid
```

Desde Python:

```python
from dual_ocr import read_page

with open("pagina.png", "rb") as handle:
    paragraphs = read_page(handle.read())

for paragraph in paragraphs:
    print(paragraph)
```

El modo también se puede fijar con la variable de entorno `DUAL_OCR_ENGINE` (`dual`, `tesseract` o `rapid`). Por defecto es `dual`.

Si tienes un PDF escaneado, primero conviértelo en imágenes, por ejemplo con PyMuPDF (`page.get_pixmap(dpi=300).tobytes("png")`). Lo usual es 300 ppp.

## Pruebas

```
python -m unittest discover -s tests -v
```

Las pruebas cubren la fusión de lecturas, el descarte de símbolos sueltos, la detección de palabras válidas y la separación de párrafos por sangría y por huecos verticales. No prueban los motores de OCR en sí.

## Limitaciones

- Los errores que comparten los dos motores no se corrigen.
- Los nombres propios que no están en el diccionario se conservan tal como los lee el motor, pero no se pueden corregir con certeza.
- El diccionario sale de `/usr/share/dict/words` (macOS y Linux). En Windows no existe, y entonces se usa una regla simple que solo mira si la palabra tiene vocales. Es más flojo.
- Las portadas con letras decorativas siguen siendo difíciles para cualquier motor.

## Créditos

Este proyecto no existiría sin el trabajo de otras personas y comunidades. Gracias a todas:

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract), al que le debemos años de trabajo abierto en reconocimiento de texto. Nació en HP y lo mantienen Google y la comunidad. Licencia Apache-2.0.
- [pytesseract](https://github.com/madmaze/pytesseract), el puente que hace posible usar Tesseract desde Python. Licencia Apache-2.0.
- [RapidOCR](https://github.com/RapidAI/RapidOCR), que pone los modelos PP-OCR a correr sobre ONNX sin depender de PaddlePaddle. Licencia Apache-2.0.
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) y el equipo de PaddlePaddle en Baidu, autores de los modelos PP-OCR que usa RapidOCR. Licencia Apache-2.0.
- [ONNX Runtime](https://github.com/microsoft/onnxruntime), de Microsoft. Licencia MIT.
- [OpenCV](https://github.com/opencv/opencv), para el preprocesado de imágenes. Licencia Apache-2.0.
- [Pillow](https://github.com/python-pillow/Pillow) y [NumPy](https://github.com/numpy/numpy), base de todo el manejo de imágenes y de arreglos. Licencias permisivas.

## Licencia

MIT. Consulta el archivo `LICENSE`.
