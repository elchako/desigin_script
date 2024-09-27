import configparser
from datetime import datetime
from os import listdir, makedirs, path, remove

from pdf2image import convert_from_path
from PIL import Image

config_name = 'conf.ini'
conf_init = '''# позиция B на холсте A относительно левого верхнего угла
[POSITION]
x = 100
y = 150


[IMAGE]
# максимальный размер B относительно размера A
max_overlay_width = 0.40
max_overlay_height = 0.30
# размер конвертируемого изображения из PDF в PNG (можно не менять)
png_size = 120

# имена папок
[DIRS]
dir_a = A
dir_b = B
'''

if not path.exists(config_name):
    with open(config_name, 'w') as conf:
        conf.write(conf_init)

config = configparser.ConfigParser()
config.read(config_name)
DIR_A = config.get('DIRS', 'DIR_A')
DIR_B = config.get('DIRS', 'DIR_B')
POS_X = int(config.get('POSITION', 'x'))
POS_Y = int(config.get('POSITION', 'y'))
WIDTH_B = float(config.get('IMAGE', 'max_overlay_width'))
HEIGHT_B = float(config.get('IMAGE', 'max_overlay_height'))
PNG_SIZE = int(config.get('IMAGE', 'png_size'))


def create_folders():
    '''Создание папок под файлы'''
    makedirs(DIR_A, exist_ok=True)
    makedirs(DIR_B, exist_ok=True)


def list_files(dir_name):
    '''Чтение списка файлов из папки'''
    files = listdir(dir_name)
    if len(files) == 0:
        print(f'В папке {dir_name} пусто. Выходим')
        exit(1)
    return files


def overlay_images(
        base_image_path, overlay_image_path,
        output_path, position=(POS_X, POS_Y)):
    '''Накладывает изображение (в формате PNG)
    на базовое изображение на указанной позиции.'''
    # Открываем базовое изображение и накладываемое изображение
    base_image = Image.open(base_image_path).convert('RGBA')
    overlay_image = Image.open(overlay_image_path).convert('RGBA')
    # Получаем размеры базового изображения
    base_width, base_height = base_image.size
    # Вычисляем максимальные размеры для накладываемого изображения (15% от базового изображения)
    max_overlay_width = int(base_width * WIDTH_B)
    max_overlay_height = int(base_height * HEIGHT_B)
    # Получаем текущие размеры накладываемого изображения
    overlay_width, overlay_height = overlay_image.size
    # Если накладываемое изображение больше 15% от базового по одному из измерений, уменьшаем его
    if overlay_width > max_overlay_width or overlay_height > max_overlay_height:
        # Сохраняем пропорции накладываемого изображения
        overlay_image.thumbnail((max_overlay_width, max_overlay_height))
    # Накладываем уменьшенное изображение на базовое
    base_image.paste(overlay_image, position, overlay_image)
    # Сохраняем результат
    base_image.save(output_path)
    print(f'Изображение наложено и сохранено в {output_path}')


def convert_pdf_to_image(pdf_path, output_path, dpi=PNG_SIZE):
    '''Конвертирует первую страницу PDF в изображение PNG
    с указанным разрешением (dpi).'''
    images = convert_from_path(pdf_path, dpi)
    # Сохраняем первое изображение в формате RGBA (чтобы поддерживалась прозрачность)
    img = images[0].convert("RGBA")
    # Загружаем пиксели изображения
    datas = img.getdata()

    new_data = []
    for item in datas:
        # Порог белого цвета — можно подправить (например, все светлые оттенки белого)
        if item[0] > 200 and item[1] > 200 and item[2] > 200:  # RGB > 200 (близко к белому)
            # Заменяем белый фон на прозрачный
            new_data.append((255, 255, 255, 0))  # Прозрачность
        else:
            new_data.append(item)

    # Применяем изменения к изображению
    img.putdata(new_data)
    img.save(output_path, 'PNG')
    print(f'{pdf_path} сконвертирован в {output_path}')


def convert_package_pdf_to_image(files_b):
    '''Пакетная конвертация PDF в PNG'''
    for pdf_path in files_b:
        pdf_path = path.join(DIR_B, pdf_path)
        if pdf_path.endswith('.png'):
            # print(f'Файл {pdf_path} уже сконвертирован в png')
            continue
        elif not pdf_path.endswith('.pdf'):
            print(f'Файл {pdf_path} должен быть в формате PDF')
        else:
            new_name = path.join(path.splitext(pdf_path)[0])
            # Конвертация PDF в изображение
            convert_pdf_to_image(pdf_path, f'{new_name}.png')
            remove(pdf_path)
    return sorted(list_files(DIR_B))


def process_files(output_dir):
    '''Применяет функции наложения изображений
    ко всем файлам в заданных директориях.'''
    makedirs(output_dir, exist_ok=True)

    base_images = sorted(list_files(DIR_A))
    files_b = list_files(DIR_B)
    vector_images = convert_package_pdf_to_image(files_b)

    for base_image, png_overlay_path in zip(base_images, vector_images):
        # Накладываем PDF-изображение на базовое изображение
        output_image = path.join(
            output_dir, f'{path.splitext(base_image)[0]}.png')
        overlay_images(
            path.join(DIR_A, base_image),
            path.join(DIR_B, png_overlay_path),
            output_image
        )
        # print(f'Файл {output_image} создан')


if __name__ == '__main__':
    create_folders()
    # имя папки выходных файлов
    output_dir = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    process_files(output_dir)
