import configparser
from datetime import datetime
from os import listdir, makedirs, path, remove
import sys

from pdf2image import convert_from_path
from PIL import Image

config_name = 'conf.ini'
conf_init = '''# позиция B на холсте A относительно левого верхнего угла
[POSITION]
x = 100
y = 50

[IMAGE]
# максимальный размер B относительно размера A
max_overlay_width = 0.50
max_overlay_height = 0.50
# размер конвертируемого изображения из PDF в PNG (можно не менять)
png_size = 100
# поворот изображения
rotate = 0

[DIRS]
# имена папок
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
ROTATE = int(config.get('IMAGE', 'rotate'))


def stop():
    input('Для выхода нажмите: ENTER')
    sys.exit(0)


def create_folders():
    '''Создание папок под файлы'''
    makedirs(DIR_A, exist_ok=True)
    makedirs(DIR_B, exist_ok=True)


def list_files(dir_name):
    '''Чтение списка файлов из папки'''
    files = listdir(dir_name)
    if len(files) == 0:
        print(f'В папке {dir_name} пусто. Выходим')
        stop()
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
    # если нужно повернем картинку
    if ROTATE != 0:
        overlay_image = overlay_image.rotate(ROTATE, expand=True)
    # Накладываем уменьшенное изображение на базовое
    base_image.paste(overlay_image, position, overlay_image)
    # Сохраняем результат
    base_image.save(output_path)
    print(f'Изображение наложено и сохранено в {output_path}')


def convert_pdf_to_image(pdf_path, output_path, dpi=PNG_SIZE):
    '''Конвертирует первую страницу PDF в изображение PNG
    с указанным разрешением (dpi).'''
    images = convert_from_path(pdf_path, dpi, thread_count=2, poppler_path=r'C:\poppler\Library\bin')
    # Сохраняем первое изображение в формате RGBA (чтобы поддерживалась прозрачность)
    img = images[0].convert('RGBA')
    # Загружаем пиксели изображения
    datas = img.getdata()

    new_data = []
    for item in datas:
        # Порог белого цвета — можно подправить (например, все светлые оттенки белого)
        # RGB > 200 (близко к белому)
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            # Заменяем белый фон на прозрачный
            new_data.append((255, 255, 255, 0))  # Прозрачность
        else:
            new_data.append(item)

    # Применяем изменения к изображению
    img.putdata(new_data)
    img.save(output_path, 'PNG')
    print(f'{pdf_path} сконвертирован в {output_path}')
    remove(pdf_path)


def process_files(base_image_dir, overlay_image_dir, output_dir):
    '''Применяет функции наложения изображений ко всем файлам в заданных директориях.
    Накладывает только файлы с одинаковыми именами, игнорируя расширения.'''

    # Получаем списки файлов
    base_images = [f for f in listdir(
        base_image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    overlay_files = [f for f in listdir(
        overlay_image_dir) if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]

    # Создаем директорию для сохранения выходных файлов, если она не существует
    makedirs(output_dir, exist_ok=True)

    # Преобразуем списки в словари с ключами, являющимися именами файлов без расширений
    base_images_dict = {path.splitext(f)[0]: f for f in base_images}
    overlay_files_dict = {path.splitext(f)[0]: f for f in overlay_files}

    # Проходим по всем файлам базовых изображений
    for base_name, base_file in base_images_dict.items():
        # Проверяем, есть ли соответствующее накладываемое изображение с таким же именем
        if base_name in overlay_files_dict:
            base_image_path = path.join(base_image_dir, base_file)
            overlay_image_path = path.join(
                overlay_image_dir, overlay_files_dict[base_name])

            # Если накладываемое изображение в формате PDF, конвертируем его
            if overlay_image_path.lower().endswith('.pdf'):
                converted_overlay_image = path.join(
                    DIR_B, f'{base_name}.png')
                try:
                    convert_pdf_to_image(overlay_image_path,
                                        converted_overlay_image)
                except Exception as e:
                    print(e)
                    continue
                # Обновляем путь к изображению после конвертации
                overlay_image_path = converted_overlay_image

            # Генерируем путь для выходного файла
            output_image_path = path.join(output_dir, f'{base_name}_final.png')

            # Накладываем изображения
            overlay_images(base_image_path, overlay_image_path,
                           output_image_path)
        else:
            print(
                f'Файл {base_name} не имеет соответствующего накладываемого изображения, пропускаем.')


if __name__ == '__main__':
    create_folders()
    base_images = sorted(list_files(DIR_A))
    files_b = list_files(DIR_B)
    if not base_images or not files_b:
        stop()
    # имя папки выходных файлов
    output_dir = path.join(
        'result', datetime.now().strftime('%Y-%m-%d %H-%M-%S'))
    process_files(DIR_A, DIR_B, output_dir)
    stop()
