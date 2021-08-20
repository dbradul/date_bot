import datetime
import itertools
import os
import time
from contextlib import contextmanager
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils import logger, call_retrier, dump_exception_stack

load_dotenv()

TIMEOUT = 16
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
BASE_URL = os.getenv('BASE_URL')
RESUME_PARSING_FROM_ID = ''

AGE_RANGE_MAP = {
    (18, 29): 15,
    (30, 39): 10,
    (40, 49): 5,
    (50, float('inf')): 0,
}


# ----------------------------------------------------------------------------------------------------------------------
def get_delta_from_age_range(age):
    for (range_from, rage_to), delta in AGE_RANGE_MAP.items():
        if range_from <= age <= rage_to:
            return delta
    return 0


# ----------------------------------------------------------------------------------------------------------------------
class EmptyIntroLetterException(Exception):
    pass


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

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)

        yield driver

    finally:
        if driver:
            driver.quit()


def login(driver):
    driver.get(BASE_URL)
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

    # TODO:
    # here we can add handling of Limit exceeding error:
    # subject = driver.find_element_by_css_selector('div[id="msg_max_intros_reached"]')

    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[id="btn_submit"]')))

    subject = driver.find_element_by_css_selector('input[id="mbox_subject"]').get_attribute('value')
    message = driver.find_element_by_css_selector('textarea[id="mbox_body"]').get_attribute('value')
    if not subject and not message:
        raise EmptyIntroLetterException()

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
        logger.info(f'No results for given search criteria -> proceed with another letter, if any')
        return

    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men"]')
    for send_intro_button in send_intro_buttons:
        gentleman_url = send_intro_button.get_attribute('href')

        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])

        try:
            process_gentleman(driver, gentleman_url)
        except EmptyIntroLetterException:
            raise
        finally:
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])


def process_lady(driver, lady_id, country, intro_letter):
    global RESUME_PARSING_FROM_ID
    if RESUME_PARSING_FROM_ID:
        if RESUME_PARSING_FROM_ID == lady_id:
            RESUME_PARSING_FROM_ID = ''
        else:
            return

    logger.info(f'Started processing lady with id={lady_id}, \'{intro_letter}\'')
    driver.get(f'{BASE_URL}/search_men_office/?women_id={lady_id}')

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="reg_date_from"]'))
    )

    reg_date_from = driver.find_element_by_css_selector('input[name="reg_date_from"]')
    reg_date_to = driver.find_element_by_css_selector('input[name="reg_date_to"]')
    last_login_from = driver.find_element_by_css_selector('input[name="date_from"]')
    last_login_to = driver.find_element_by_css_selector('input[name="date_to"]')

    countries = driver.find_element_by_css_selector('select[id="fk_countries"]')
    time.sleep(1)  # dropdown list is populated in deferred way
    countries.send_keys(country)

    age_from = driver.find_element_by_css_selector('select[name="age_from"]')
    lady_age = driver.find_elements_by_css_selector('p[class="small gray"]')[1].text.split(', ')[0]
    gentleman_age_from = int(lady_age) + get_delta_from_age_range(int(lady_age))
    age_from_options = age_from.find_elements_by_css_selector('option')
    for age_from_option in age_from_options[1:]:
        if int(age_from_option.text) == gentleman_age_from:
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

    for send_intro_button in send_intro_buttons:
        lady_id = send_intro_button.get_attribute('id')

        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])

        countries = ['United States', 'Canada', 'Australia', 'United Kingdom']
        letters = [
            'Send Fourth intro letter',
            'Send Third intro letter',
            'Send Second intro letter',
            'Send First intro letter',
        ]

        for country, intro_letter in itertools.product(countries, letters):
            try:
                process_lady(driver, lady_id, country, intro_letter)
            except EmptyIntroLetterException:
                logger.info(f'Empty letter \'{intro_letter}\' for lady id={lady_id} -> skipping')

        driver.close()
        driver.switch_to.window(driver.window_handles[-1])


# @call_retrier(max_retry_num=3, catched_exceptions=(TimeoutException,))
def run_parsing(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1[class="display_title"]'))
    )
    driver.get(f'{BASE_URL}/ppl')

    process_ladies(driver)

    pages = driver.find_elements_by_css_selector('a[class="navigation_on"]')
    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            process_ladies(driver)


def main():
    with create_driver() as driver:

        try:
            logger.info('STARTED NEW BOT RUN')
            login(driver)

            run_parsing(driver)

            logger.info('')
            logger.info('SUCCESSFULLY FINISHED!')
        except Exception as ex:
            logger.error(f'FINISHED WITH ERROR: {repr(ex)}')
            dump_exception_stack(ex)


if __name__ == "__main__":
    main()

