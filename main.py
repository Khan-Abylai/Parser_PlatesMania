import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

save_folder = "plates_numbers"

if not os.path.exists(save_folder):
    os.makedirs(save_folder)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def download_image(image_url, referer_url, save_path):
    headers = {
        'Referer': referer_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    }
    try:
        response = requests.get(image_url, headers=headers, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Изображение номера сохранено: {save_path}")
    except Exception as e:
        print(f"Ошибка при загрузке изображения {image_url}: {e}")


def get_plate_image_links(page_url):
    driver.get(page_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img.img-responsive.center-block'))
        )

        plate_images = driver.find_elements(By.CSS_SELECTOR, 'img.img-responsive.center-block.margin-bottom-10')
        plate_image_urls = [img.get_attribute('src') for img in plate_images]

        plate_annotations = [img.get_attribute('alt').strip() for img in plate_images]

        return plate_image_urls, plate_annotations
    except (NoSuchElementException, TimeoutException) as e:
        print(f"Ошибка при получении данных с {page_url}: {e}")
        return [], []


def clean_annotation(annotation):
    return re.sub(r'\W+', '', annotation)


def parse_gallery(base_url, total_pages):
    file_counter = {}  # Словарь для хранения счетчиков для каждого номера
    seen_urls = set()  # Множество для хранения уникальных ссылок

    for page_num in range(total_pages):
        if page_num == 0:
            page_url = f"{base_url}?gal=kg&ctype=10"  # Первая страница
        else:
            page_url = f"{base_url}?&ctype=10&start={page_num}"  # Для последующих страниц
        print(f"Парсинг страницы: {page_url}")

        plate_image_urls, plate_annotations = get_plate_image_links(page_url)

        if plate_image_urls and plate_annotations:
            for i in range(len(plate_image_urls)):
                plate_image_url = plate_image_urls[i]

                # Проверка на дублирование URL
                if plate_image_url in seen_urls:
                    continue
                seen_urls.add(plate_image_url)

                annotation = clean_annotation(plate_annotations[i])

                # Если аннотация уже есть, увеличиваем счётчик
                if annotation in file_counter:
                    file_counter[annotation] += 1
                else:
                    file_counter[annotation] = 1

                # Уникальное имя файла с учетом счетчика
                plate_image_name = f"{annotation}_{file_counter[annotation]}_plate.png"
                plate_save_path = os.path.join(save_folder, plate_image_name)

                download_image(plate_image_url, page_url, plate_save_path)
        else:
            print(f"Нет данных на странице {page_url}")


base_url = "https://platesmania.com/kg/gallery.php"
total_pages = 31

parse_gallery(base_url, total_pages)

driver.quit()
