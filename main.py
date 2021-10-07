import re
import datetime
import itertools
import os
import time
import db
from functools import lru_cache
from contextlib import contextmanager

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from models import GentlemanInfo
from utils import logger, dump_exception_stack, Screener
from exceptions import (
    EmptyIntroLetterException,
    LimitIsExceededException,
    DirectSendLetterException,
    msg_id_exception_map,
)

load_dotenv()

# ----------------------------------------------------------------------------------------------------------------------
TIMEOUT = 16
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
BASE_URL = os.getenv('BASE_URL')
RESUME_PARSING_FROM_ID = 0
BLACK_LIST_LADIES = [128289, 191124, 203801]
GENTLEMAN_PROFILE_INFO_MAP = {}
AGE_RANGE_MAP = {
    (18, 22): 25,
    (23, 29): 20,
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


# ----------------------------------------------------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------------------------------------------------
def _cleanup_input_field(input_field):
    _ = [input_field.send_keys(Keys.BACKSPACE) for _ in range(10)]


# ----------------------------------------------------------------------------------------------------------------------
def process_gentleman(driver, url):
    driver.get(url)

    for k, v in msg_id_exception_map.items():
        if driver.find_elements_by_css_selector(f'div[id="{k}"]'):
            elem = driver.find_elements_by_css_selector(f'div[id="{k}"]')[0]
            raise v(elem.text)

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
        for attach_photo_checkbox in attach_photo_checkboxes[:4]:
            try:
                attach_photo_checkbox.click()
            except Exception as ex:
                pass

    submit_button = driver.find_element_by_css_selector('button[id="btn_submit"]')
    submit_button.click()


# ----------------------------------------------------------------------------------------------------------------------
@lru_cache()
def fetch_gentleman_profile_info(profile_link, driver):
    profile_id = int(profile_link.split('=')[1])
    gentleman_info = db.get_gentleman_info_by_profile_id(profile_id)

    if not gentleman_info:
        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(profile_link)
        xpath = "//span[text()='I am interested in ladies between:']"
        WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        info_text = (
            driver.find_element(By.XPATH, xpath)
            .find_element_by_xpath('..')
            .text.replace('\n', '')
        )
        patterns = [
            '.* (\d+) - (\d+)',
            '.* -- - (\d+)',
        ]

        gentleman_info = GentlemanInfo(
            profile_id=profile_id,
        )
        for pattern in patterns:
            m = re.match(pattern, info_text)
            if m:
                age_from, age_to = m.groups() if len(m.groups()) == 2 else [0, m.groups()[0]]
                gentleman_info.age_from = int(age_from)
                gentleman_info.age_to = int(age_to)
                gentleman_info.priority = 0
                break

        db.put_gentleman_info(gentleman_info)

        driver.close()
        driver.switch_to.window(driver.window_handles[-1])

    return gentleman_info


# ----------------------------------------------------------------------------------------------------------------------
def process_gentlemen(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1[class="display_title"]'))
    )

    error_msg = driver.find_elements_by_css_selector('div[class="error_msg"]')

    lady_info = [
        e.text for e in driver.find_elements_by_css_selector('p[class="small gray"]') if e.text.endswith('Ukraine')
    ]
    lady_age = int(lady_info[0].split(', ')[0])

    if error_msg and error_msg[0].text == 'Your search returned no results. Please try again using different criteria':
        # no results -> just return
        logger.info(f'No results for given search criteria -> proceed with another letter, if any')
        return

    profile_links = [e.get_attribute('href') for e in driver.find_elements_by_css_selector('a[target="_blank"]')]
    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men"]')
    for profile_link, send_intro_button in zip(profile_links[2:][::2], send_intro_buttons):
        profile_info = fetch_gentleman_profile_info(profile_link, driver)
        if profile_info.age_to:
            matched_age = profile_info.age_from <= lady_age <= profile_info.age_to
            if not matched_age:
                logger.info(
                    f'Not matched age -> skipped. Lady link = {profile_links[0]}, gentleman link = {profile_link}'
                )
                continue

        gentleman_url = send_intro_button.get_attribute('href')

        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])

        try:
            process_gentleman(driver, gentleman_url)
        except:
            Screener.push_screen(driver)
            raise
        finally:
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])


# ----------------------------------------------------------------------------------------------------------------------
def process_lady(driver, lady_id, online_status, country, intro_letter):
    global RESUME_PARSING_FROM_ID
    if RESUME_PARSING_FROM_ID:
        if RESUME_PARSING_FROM_ID == lady_id:
            RESUME_PARSING_FROM_ID = ''
        else:
            return

    logger.info(f'Started processing lady with id={lady_id}, country={country}, letter=\'{intro_letter}\'')
    driver.get(f'{BASE_URL}/search_men_office/?women_id={lady_id}')

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="reg_date_from"]'))
    )

    is_online = driver.find_element_by_css_selector('input[id="is_online"]')
    if is_online.get_attribute('checked') == 'true' and not online_status:
        is_online.click()
    elif is_online.get_attribute('checked') is None and online_status:
        is_online.click()
    reg_date_from = driver.find_element_by_css_selector('input[name="reg_date_from"]')
    reg_date_to = driver.find_element_by_css_selector('input[name="reg_date_to"]')
    last_login_from = driver.find_element_by_css_selector('input[name="date_from"]')
    last_login_to = driver.find_element_by_css_selector('input[name="date_to"]')

    # TODO: Replace with Wait-method
    countries = driver.find_element_by_css_selector('select[id="fk_countries"]')
    time.sleep(3)  # dropdown list is populated in deferred way
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


# ----------------------------------------------------------------------------------------------------------------------
def process_ladies_prio(driver, lady_ids):
    gentlemen_ids = [g.profile_id for g in db.get_gentlemen_info_by_priority(priority=1)]
    filtered_lady_ids = filter(lambda l: l not in BLACK_LIST_LADIES, lady_ids)

    for lady_id, gentleman_id in itertools.product(filtered_lady_ids, gentlemen_ids):
        global RESUME_PARSING_FROM_ID
        if RESUME_PARSING_FROM_ID:
            if RESUME_PARSING_FROM_ID == lady_id:
                RESUME_PARSING_FROM_ID = ''
            else:
                continue

        url = f'{BASE_URL}/send?mid={gentleman_id}&wid={lady_id}'
        try:
            process_gentleman(driver, url)
            logger.info(f'Sent letter for lady id={lady_id}, gentleman id = {gentleman_id} SUCCESSFULLY!')
        except EmptyIntroLetterException:
            logger.info(f'Empty letter for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')
        except DirectSendLetterException as ex:
            logger.info(
                f'Couldn\'t send letter ({ex}) for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping'
            )
        except LimitIsExceededException:
            raise
        except Exception as ex:
            logger.error(f'Exception {ex} for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')


# ----------------------------------------------------------------------------------------------------------------------
def process_ladies(driver, lady_ids):
    filtered_lady_ids = filter(lambda l: l not in BLACK_LIST_LADIES, lady_ids)
    online_statuses = [True, False]
    countries = ['United States', 'Canada', 'Australia', 'United Kingdom', 'New Zealand']
    letters = [
        'Send Fourth intro letter',
        'Send Third intro letter',
        'Send Second intro letter',
        'Send First intro letter',
    ]

    for online_status, country, lady_id, intro_letter in itertools.product(
        online_statuses, countries, filtered_lady_ids, letters
    ):
        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])

        try:
            process_lady(driver, lady_id, online_status, country, intro_letter)
        except EmptyIntroLetterException:
            logger.info(f'Empty letter \'{intro_letter}\' for lady id={lady_id} -> skipping')
            Screener.pop_screen()

        driver.close()
        driver.switch_to.window(driver.window_handles[-1])


# ----------------------------------------------------------------------------------------------------------------------
# @call_retrier(max_retry_num=3, catched_exceptions=(TimeoutException,))
def run_parsing(driver):
    WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//a[text()='Correspondence']")))
    ppl_button = driver.find_element(By.XPATH, "//a[text()='Correspondence']")
    ppl_button.click()

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]'))
    )
    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men_office"]')
    lady_ids = [int(send_intro_button.get_attribute('id')) for send_intro_button in send_intro_buttons]

    pages = driver.find_elements_by_css_selector('a[class="navigation_on"]')
    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            WebDriverWait(driver, TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]')
                )
            )
            send_intro_buttons = driver.find_elements_by_css_selector(
                'a[class="default_photo link_options search_men_office"]'
            )
            lady_ids += [int(send_intro_button.get_attribute('id')) for send_intro_button in send_intro_buttons]

    process_ladies_prio(driver, lady_ids)
    process_ladies(driver, lady_ids)


# ----------------------------------------------------------------------------------------------------------------------
def main():
    with create_driver() as driver:

        try:
            logger.info('STARTED NEW BOT RUN')
            login(driver)

            run_parsing(driver)

            logger.info('')
            logger.info('SUCCESSFULLY FINISHED!')

        except LimitIsExceededException as ex:
            logger.error(f'LIMIT EXCEEDING ERROR: {repr(ex)}')
        except Exception as ex:
            logger.error(f'FINISHED WITH UNEXPECTED ERROR: {repr(ex)}')
            dump_exception_stack(ex)
            Screener.push_screen(driver)


if __name__ == "__main__":
    main()
