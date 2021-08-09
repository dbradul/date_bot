import datetime
import os
import time
from contextlib import contextmanager

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TIMEOUT = 16
CHROME_DRIVER_PATH = '/usr/lib/chromium-browser/chromedriver'
RESUME_PARSING_FROM_ID = ''

# ----------------------------------------------------------------------------------------------------------------------
@contextmanager
def create_driver(attach_mode=True, download_dir=None):
    """
    :param attach_mode: Attach to existing browser or create new instance from scratch?
    :param download_dir: Where downloaded files are saved
    :return:
    """
    driver = None

    try:
        options = webdriver.ChromeOptions()
        options.add_argument('window-size=1200x600')
        options.add_argument('disable-gpu')
        options.add_argument("remote-debugging-port=9222")
        options.add_argument('no-sandbox')
        options.add_argument('disable-dev-shm-usage')

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, chrome_options=options)

        yield driver

    finally:
        if driver:
            driver.quit()




def login(driver):
    driver.get('http://office.loveme.com/')
    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="do_ajax"]')))
    signin_button = driver.find_element_by_css_selector('a[class="do_ajax"]')
    signin_button.click()
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[id="ajax_office_login_logins_ident"]'))
    )
    username = driver.find_element_by_css_selector('input[id="ajax_office_login_logins_ident"]')
    username.send_keys(os.getenv('LOGIN', ''))
    password = driver.find_element_by_css_selector('input[id="ajax_office_login_logins_password"]')
    password.send_keys(os.getenv('PASSWORD', ''))
    submit = driver.find_element_by_css_selector('button[class="btn"]')
    submit.click()
    WebDriverWait(driver, TIMEOUT).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn"]')))


def _cleanup_input_field(input_field):
    _ = [input_field.send_keys(Keys.BACKSPACE) for _ in range(10)]


def process_gentleman(driver, url):
    driver.get(url)
    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[id="btn_submit"]')))

    attach_photo_button = driver.find_elements_by_css_selector('a[id="choose_photos_attached"]')
    if attach_photo_button:
        attach_photo_button[0].click()
        WebDriverWait(driver, TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="fk_files[]"]'))
        )
        attach_photo_checkboxes = driver.find_elements_by_css_selector('input[name="fk_files[]"]')
        for attach_photo_checkbox in attach_photo_checkboxes[:2]:
            try:
                attach_photo_checkbox.click()
            except Exception as ex:
                pass

    submit_button = driver.find_element_by_css_selector('button[id="btn_submit"]')
    submit_button.click()


def process_gentlemen(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1[class="display_title"]'))
    )

    error_msg = driver.find_elements_by_css_selector('div[class="error_msg"]')
    if error_msg and error_msg[0].text == 'Your search returned no results. Please try again using different criteria':
        # no results -> just return
        return

    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men"]')
    for send_intro_button in send_intro_buttons:
        gentleman_url = send_intro_button.get_attribute('href')

        driver.execute_script('window.open()')
        driver.switch_to_window(driver.window_handles[-1])

        process_gentleman(driver, gentleman_url)

        driver.close()
        driver.switch_to_window(driver.window_handles[-1])


def process_lady(driver, lady_id, intro_letter):
    global RESUME_PARSING_FROM_ID
    if RESUME_PARSING_FROM_ID:
        if RESUME_PARSING_FROM_ID == lady_id:
            RESUME_PARSING_FROM_ID = ''
        else:
            return

    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    print(f'{current_time}:     Started parsing lady with id={lady_id}')
    driver.get(f'http://office.loveme.com/search_men_office/?women_id={lady_id}')

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="reg_date_from"]'))
    )

    reg_date_from = driver.find_element_by_css_selector('input[name="reg_date_from"]')
    reg_date_to = driver.find_element_by_css_selector('input[name="reg_date_to"]')
    last_login_from = driver.find_element_by_css_selector('input[name="date_from"]')
    last_login_to = driver.find_element_by_css_selector('input[name="date_to"]')

    countries = driver.find_element_by_css_selector('select[id="fk_countries"]')
    time.sleep(2)
    countries.send_keys('United States')

    age_from = driver.find_element_by_css_selector('select[name="age_from"]')
    lady_age = driver.find_elements_by_css_selector('p[class="small gray"]')[1].text.split(', ')[0]
    gentelman_age_from = int(lady_age) + 20
    age_from_options = age_from.find_elements_by_css_selector('option')
    for age_from_option in age_from_options[1:]:
        if int(age_from_option.text) == gentelman_age_from:
            age_from_option.click()
            break
    age_to = driver.find_element_by_css_selector('select[name="age_to"]')
    age_to.find_elements_by_css_selector('option')[-1].click()

    current_datetime = datetime.datetime.now()
    _cleanup_input_field(reg_date_from)
    reg_date_from.send_keys('2020-08-01')
    _cleanup_input_field(reg_date_to)
    reg_date_to.send_keys(current_datetime.date().strftime('%Y-%m-%d'))
    _cleanup_input_field(last_login_from)
    last_login_from.send_keys((current_datetime - datetime.timedelta(days=7)).strftime('%Y-%m-%d'))
    _cleanup_input_field(last_login_to)
    last_login_to.send_keys(current_datetime.date().strftime('%Y-%m-%d'))

    intro_types = driver.find_element_by_css_selector('select[name="intro_type"]')
    intro_types_options = intro_types.find_elements_by_css_selector('option')

    for intro_types_option in intro_types_options:
        if intro_types_option.text == intro_letter:
            intro_types_option.click()
            break

    submit = driver.find_element_by_css_selector('button[class="btn"]')
    submit.click()

    process_gentlemen(driver)

    pages = driver.find_elements_by_css_selector('a[class="navigation_on"]')

    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            process_gentlemen(driver)


def process_ladies(driver):

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]'))
    )
    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men_office"]')

    for send_intro_button in send_intro_buttons[:]:
        lady_id = send_intro_button.get_attribute('id')

        driver.execute_script('window.open()')
        driver.switch_to_window(driver.window_handles[-1])

        for intro_letter in [
            # 'Send Fourth intro letter',
            'Send Third intro letter',
            'Send Second intro letter',
            'Send First intro letter',
        ]:
            process_lady(driver, lady_id, intro_letter)

        driver.close()
        driver.switch_to_window(driver.window_handles[-1])


def run_parsing(driver):
    driver.get('http://office.loveme.com/ppl')

    process_ladies(driver)

    pages = driver.find_elements_by_css_selector('a[class="navigation_on"]')
    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            process_ladies(driver)


def main():
    with create_driver() as driver:

        login(driver)

        run_parsing(driver)


if __name__ == "__main__":
    main()

