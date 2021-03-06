from contextlib import contextmanager
from collections import defaultdict

import datetime
import math
import itertools
import os
import re
import socket
import time
from dotenv import load_dotenv
from functools import lru_cache
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config
import db
from exceptions import (
    EmptyIntroLetterException,
    LimitIsExceededException,
    DailyLimitForALadyIsExceededException,
    msg_id_exception_map,
)
from models import GentlemanInfo, LadyInfo
from utils import logger, dump_exception_stack, Screener

load_dotenv()

# ----------------------------------------------------------------------------------------------------------------------
TIMEOUT = 16
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
CHROME_REMOTE_DEBUG_PORT = os.getenv('CHROME_REMOTE_DEBUG_PORT')
BASE_URL = os.getenv('BASE_URL')
SITE_URL = os.getenv('SITE_URL')
RESUME_FROM_LADY_ID = 0
BLACK_LIST_LADIES = [128289, 191124, 143427, 143602]
AGE_RANGE_MAP = {
    (18, 22): 25,
    (23, 29): 20,
    (30, 39): 10,
    (40, 49): 5,
    (50, float('inf')): 0,
}
DAILY_LETTERS_PER_LADY_LIMIT = 100


# ----------------------------------------------------------------------------------------------------------------------
class RunContext:
    ladies = defaultdict(int)

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
        options.add_argument("--incognito")
        options.add_argument(f"remote-debugging-port={CHROME_REMOTE_DEBUG_PORT}")
        options.add_experimental_option(
            "debuggerAddress", f"{socket.gethostbyname('browser')}:{CHROME_REMOTE_DEBUG_PORT}"
        )

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        driver.context = RunContext()

        yield driver

    finally:
        if driver:
            driver.quit()


# ----------------------------------------------------------------------------------------------------------------------
def login(driver):
    driver.get(BASE_URL)
    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="do_ajax"]')))
    signin_button = driver.find_element(By.CSS_SELECTOR, 'a[class="do_ajax"]')
    signin_button.click()
    # signin_button.send_keys(Keys.ENTER)
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[id="ajax_office_login_logins_ident"]'))
    )
    username = driver.find_element(By.CSS_SELECTOR, 'input[id="ajax_office_login_logins_ident"]')
    _cleanup_input_field(username)
    username.send_keys(os.getenv('LOGIN', ''))

    password = driver.find_element(By.CSS_SELECTOR, 'input[id="ajax_office_login_logins_password"]')
    _cleanup_input_field(password)
    password.send_keys(os.getenv('PASSWORD', ''))

    submit = driver.find_element(By.CSS_SELECTOR, 'button[class="btn"]')
    submit.click()
    # submit.send_keys(Keys.ENTER)
    WebDriverWait(driver, TIMEOUT).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn"]')))


# ----------------------------------------------------------------------------------------------------------------------
def _cleanup_input_field(input_field):
    value = input_field.get_attribute('value')
    _ = [input_field.send_keys(Keys.BACKSPACE) for _ in range(len(value))]


# ----------------------------------------------------------------------------------------------------------------------
def process_gentleman_in_new_window(driver, url, lady_id):
    def _process_gentleman(driver, url, lady_id):
        driver.get(url)

        for k, v in msg_id_exception_map.items():
            if driver.find_elements(By.CSS_SELECTOR, f'div[id="{k}"]'):
                elem = driver.find_elements(By.CSS_SELECTOR, f'div[id="{k}"]')[0]
                raise v(elem.text)

        WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[id="btn_submit"]')))

        subject = driver.find_element(By.CSS_SELECTOR, 'input[id="mbox_subject"]').get_attribute('value')
        message = driver.find_element(By.CSS_SELECTOR, 'textarea[id="mbox_body"]').get_attribute('value')
        if not subject and not message:
            raise EmptyIntroLetterException()

        attach_photo_button = driver.find_elements(By.CSS_SELECTOR, 'a[id="choose_photos_attached"]')
        if attach_photo_button:
            attach_photo_button[0].click()
            WebDriverWait(driver, TIMEOUT).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="fk_files[]"]'))
            )
            attach_photo_checkboxes = driver.find_elements(By.CSS_SELECTOR, 'input[name="fk_files[]"]')
            for attach_photo_checkbox in attach_photo_checkboxes[:4]:
                try:
                    attach_photo_checkbox.click()
                except Exception as ex:
                    pass

        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[id="btn_submit"]')
        submit_button.click()
        driver.context.ladies[lady_id]  += 1

        if driver.context.ladies[lady_id] == DAILY_LETTERS_PER_LADY_LIMIT:
            raise DailyLimitForALadyIsExceededException()

    driver.execute_script('window.open()')
    driver.switch_to.window(driver.window_handles[-1])

    try:
        _process_gentleman(driver, url, lady_id)
    except:
        # Screener.push_screen(driver)
        raise
    finally:
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])


# ----------------------------------------------------------------------------------------------------------------------
@lru_cache()
def fetch_gentleman_profile_info(gentleman_id, driver):
    profile_link = f'{BASE_URL}/profile?id={gentleman_id}'
    gentleman_info = db.get_gentleman_info_by_profile_id(gentleman_id)

    # if gentleman_info.age_from is None or gentleman_info.age_to is None:
    if (gentleman_info is None) or (gentleman_info.age_from is None or gentleman_info.age_to is None):
        if gentleman_info is None:
            gentleman_info = GentlemanInfo(profile_id=gentleman_id)

        gentleman_info.age_to = 0
        gentleman_info.age_from = 0

        try:
            driver.execute_script('window.open()')
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(profile_link)

            xpath_deleted = "//p[text()=\"The user that you're looking for could not be found.\"]"
            if driver.find_elements(By.XPATH, xpath_deleted):
                gentleman_info.deleted = True
                logger.info(f'This gentleman is marked as deleted and will not be processed anymore: {gentleman_info}')
            else:
                xpath = "//span[text()='I am interested in ladies between:']"
                WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                info_text = driver.find_element(By.XPATH, xpath).find_element(By.XPATH, '..').text.replace('\n', '')
                patterns = [
                    '.* (\d+) - (\d+)',
                    '.* -- - (\d+)',
                ]

                for pattern in patterns:
                    if m := re.match(pattern, info_text):
                        age_from, age_to = m.groups() if len(m.groups()) == 2 else [0, m.groups()[0]]
                        gentleman_info.age_from = int(age_from)
                        gentleman_info.age_to = int(age_to)
                        gentleman_info.priority = 0
                        break

            db.upsert_gentlemen_by_profile_id(gentleman_info)

        finally:
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])

    return gentleman_info


# ----------------------------------------------------------------------------------------------------------------------
@lru_cache()
def fetch_lady_profile_info(lady_id, driver):
    lady_profile_link = f'{SITE_URL}/women/info{lady_id}.htm'
    lady_info = db.get_lady_info_by_profile_id(lady_id)

    if not lady_info:
        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(lady_profile_link)

        lady_info = driver.find_element(By.CSS_SELECTOR, 'div[class="desktop-description"]').text
        # TODO: collect the rest of info and save as json
        lady_age = int(lady_info.split('\n')[0].split(':')[1])

        lady_info = LadyInfo(
            profile_id=lady_id,
            age=lady_age,
        )

        db.put_lady_info(lady_info)

        driver.close()
        driver.switch_to.window(driver.window_handles[-1])

    return lady_info


# ----------------------------------------------------------------------------------------------------------------------
def process_gentlemen(driver, lady_id):
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1[class="display_title"]'))
    )

    error_msg = driver.find_elements(By.CSS_SELECTOR, 'div[class="error_msg"]')
    if error_msg and error_msg[0].text == 'Your search returned no results. Please try again using different criteria':
        # no results -> just return
        logger.info(f'No results for given search criteria -> proceed with another letter, if any')
        return

    lady_profile_info = fetch_lady_profile_info(lady_id, driver)

    profile_links = [e.get_attribute('href') for e in driver.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')]
    send_intro_buttons = driver.find_elements(By.CSS_SELECTOR, 'a[class="default_photo link_options search_men"]')
    for profile_link, send_intro_button in zip(profile_links[2:][::2], send_intro_buttons):
        profile_id = int(profile_link.split('=')[1])
        profile_info = fetch_gentleman_profile_info(profile_id, driver)

        if not has_match(lady_profile_info, profile_info):
            logger.info(f'Not matched age -> skipped. Lady={lady_profile_info}, gentleman={profile_info}')
            continue

        gentleman_url = send_intro_button.get_attribute('href')

        process_gentleman_in_new_window(driver, gentleman_url, lady_id)

        # driver.execute_script('window.open()')
        # driver.switch_to.window(driver.window_handles[-1])
        #
        # try:
        #     process_gentleman_in_new_window(driver, gentleman_url, lady_id)
        # except:
        #     Screener.push_screen(driver)
        #     raise
        # finally:
        #     driver.close()
        #     driver.switch_to.window(driver.window_handles[-1])


# ----------------------------------------------------------------------------------------------------------------------
def process_lady(driver, lady_id, online_status, country, intro_letter, register_range, login_range, age_policy, search_mode):
    logger.info(f'Started processing lady with id={lady_id}, country={country}, letter=\'{intro_letter}\'')
    driver.get(f'{BASE_URL}/search_men_office/?women_id={lady_id}')

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="reg_date_from"]'))
    )

    is_online = driver.find_element(By.CSS_SELECTOR, 'input[id="is_online"]')
    if is_online.get_attribute('checked') == 'true' and not online_status:
        is_online.click()
    elif is_online.get_attribute('checked') is None and online_status:
        is_online.click()

    # TODO: Replace with Wait-method
    if country:
        countries = driver.find_element(By.CSS_SELECTOR, 'select[id="fk_countries"]')
        time.sleep(3)  # dropdown list is populated in deferred way
        countries.send_keys(country)

    if age_policy:
        age_from = driver.find_element(By.CSS_SELECTOR, 'select[name="age_from"]')
        lady_age = driver.find_elements(By.CSS_SELECTOR, 'p[class="small gray"]')[1].text.split(', ')[0]
        gentleman_age_from = int(lady_age) + get_delta_from_age_range(int(lady_age))
        age_from_options = age_from.find_elements(By.CSS_SELECTOR, 'option')
        for age_from_option in age_from_options[1:]:
            if int(age_from_option.text) == gentleman_age_from:
                age_from_option.click()
                break
        age_to = driver.find_element(By.CSS_SELECTOR, 'select[name="age_to"]')
        age_to.find_elements(By.CSS_SELECTOR, 'option')[-1].click()

    if register_range:
        register_from, register_to = register_range
        reg_date_from = driver.find_element(By.CSS_SELECTOR, 'input[name="reg_date_from"]')
        reg_date_to = driver.find_element(By.CSS_SELECTOR, 'input[name="reg_date_to"]')
        _cleanup_input_field(reg_date_from)
        reg_date_from.send_keys(register_from)
        _cleanup_input_field(reg_date_to)
        # reg_date_to.send_keys(current_datetime.date().strftime('%Y-%m-%d'))
        reg_date_to.send_keys(register_to)

    if login_range:
        login_from, login_to = login_range
        last_login_from = driver.find_element(By.CSS_SELECTOR, 'input[name="date_from"]')
        last_login_to = driver.find_element(By.CSS_SELECTOR, 'input[name="date_to"]')
        _cleanup_input_field(last_login_from)
        last_login_from.send_keys(login_from)
        _cleanup_input_field(last_login_to)
        last_login_to.send_keys(login_to)

    intro_types = driver.find_element(By.CSS_SELECTOR, 'select[name="intro_type"]')
    intro_types_options = intro_types.find_elements(By.CSS_SELECTOR, 'option')

    for intro_types_option in intro_types_options:
        if intro_types_option.text == intro_letter:
            intro_types_option.click()
            break

    if search_mode:
        search_modes = driver.find_element(By.CSS_SELECTOR, 'select[name="search_mode"]')
        search_mode_options = search_modes.find_elements(By.CSS_SELECTOR, 'option')

        for search_mode_option in search_mode_options:
            if search_mode_option.text == search_mode:
                search_mode_option.click()
                break

    submit = driver.find_element_by_css_selector('button[class="btn"]')
    submit.click()

    process_gentlemen(driver, lady_id)

    pages = driver.find_elements(By.CSS_SELECTOR, 'a[class="navigation_on"]')

    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            process_gentlemen(driver, lady_id)


# ----------------------------------------------------------------------------------------------------------------------
def has_match(lady_info, gentleman_info):
    result = True
    if gentleman_info.age_to:
        result &= lady_info.age <= gentleman_info.age_to
    if gentleman_info.age_from:
        result &= gentleman_info.age_from <= lady_info.age
    return result


# ----------------------------------------------------------------------------------------------------------------------
def process_queue_of_received_intros(driver):
    PAGE_SIZE = 20

    def _process_queue_of_received_intros():
        WebDriverWait(driver, TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'li[class="new_mail"]'))
        )
        WebDriverWait(driver, TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[target="_blank"]'))
        )
        WebDriverWait(driver, TIMEOUT).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'span[class="bold"]'))
        )

        sent_intro_infos = driver.find_elements(By.CSS_SELECTOR, 'li[class="new_mail"]')
        for sent_intro_info in sent_intro_infos:
            if sent_intro_info.find_elements(By.CSS_SELECTOR, 'span[class="bold"]'):
                lady_id = sent_intro_info.find_element(By.CSS_SELECTOR, 'a[target="_blank"]').text
                gentleman_id = sent_intro_info.find_element(By.CSS_SELECTOR, 'span[class="bold"]').text[1:-1]
                url = f'{BASE_URL}/send?mid={gentleman_id}&wid={lady_id}'
                try:
                    process_gentleman_in_new_window(driver, url, lady_id)
                    logger.info(f'Sent letter for lady id={lady_id}, gentleman id = {gentleman_id} SUCCESSFULLY!')

                except EmptyIntroLetterException:
                    logger.info(f'Empty letter for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')
                except LimitIsExceededException:
                    raise
                except Exception as ex:
                    logger.error(f'Exception \'{ex}\' for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')

    driver.get(f'{BASE_URL}/mailbox?folder=sent&type=intro')
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="nav_container"]'))
    )
    total_number_text = driver.find_element(By.CSS_SELECTOR, 'div[class="nav_container"]')\
                              .find_element(By.CSS_SELECTOR, 'div[class="f_left"]').text
    total_number = int(total_number_text.split('from ')[-1])
    pages = math.ceil(total_number/PAGE_SIZE)

    for page_num in range(pages):
        url = f'{BASE_URL}/mailbox?folder=sent&type=intro&_start={page_num*PAGE_SIZE}'
        logger.info(f'Starting next page: {page_num+1}/{pages}, {url}')
        _process_queue_of_received_intros()
        driver.get(url)



# ----------------------------------------------------------------------------------------------------------------------
def process_ladies_prio(driver, lady_ids):
    # gentlemen_ids = [g.profile_id for g in db.get_active_gentlemen_info_by_priority(priority=1)]
    sent_count = 0
    lady_id_prev = None

    # for lady_id, gentleman_id in itertools.product(lady_ids, gentlemen_ids):
    for lady_id in lady_ids:

        lady_profile_info = fetch_lady_profile_info(lady_id, driver)
        gentlemen_ids = [
            g.profile_id
            for g in db.get_gentlemen_by_filter(
                priority=1,
                age_from=lady_profile_info.age,
                age_to=lady_profile_info.age,
                deleted=False,
            )
        ]

        for gentleman_id in gentlemen_ids:
            url = f'{BASE_URL}/send?mid={gentleman_id}&wid={lady_id}'

            if lady_id_prev != lady_id:
                lady_id_prev = lady_id
                sent_count = 0

            if sent_count == DAILY_LETTERS_PER_LADY_LIMIT:
                logger.info(f'Reached limit of {DAILY_LETTERS_PER_LADY_LIMIT} daily email for lady id={lady_id}.')
                continue

            try:
                fetch_gentleman_profile_info(gentleman_id, driver)

                process_gentleman_in_new_window(driver, url, lady_id)
                logger.info(f'Sent letter for lady id={lady_id}, gentleman id = {gentleman_id} SUCCESSFULLY!')
                sent_count += 1
            except EmptyIntroLetterException:
                logger.info(f'Empty letter for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')
            except LimitIsExceededException:
                raise
            except Exception as ex:
                logger.error(f'Exception {ex} for lady id={lady_id}, gentleman id = {gentleman_id} -> skipping')


# ----------------------------------------------------------------------------------------------------------------------
def process_ladies(driver, lady_ids):
    # online_statuses = [True, False]
    # countries = ['United States', 'Canada', 'Australia', 'United Kingdom', 'New Zealand']
    # register_range = ('2020-08-01', datetime.datetime.now().date().strftime('%Y-%m-%d'))
    # login_range = ((datetime.datetime.now().date() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
    #                datetime.datetime.now().date().strftime('%Y-%m-%d'))
    online_statuses = [True]
    countries = ['']
    intro_letters = [
        'Send First intro letter',
        'Send Second intro letter',
        'Send Third intro letter',
        'Send Fourth intro letter',
        'Send Fifth intro letter',
    ]
    register_range = None
    login_range = None
    age_policy = None
    search_mode = 'Basic'

    for online_status, country, lady_id, intro_letter in itertools.product(
        online_statuses, countries, lady_ids, intro_letters
    ):
        if driver.context.ladies[lady_id] >= DAILY_LETTERS_PER_LADY_LIMIT:
            logger.info(f'Skipping lady due to reached limit, id={lady_id}.')
            continue

        driver.execute_script('window.open()')
        driver.switch_to.window(driver.window_handles[-1])

        try:
            process_lady(driver, lady_id, online_status, country, intro_letter, register_range, login_range, age_policy, search_mode)
        except EmptyIntroLetterException:
            logger.info(f'Empty letter \'{intro_letter}\' for lady id={lady_id} -> skipping')
            Screener.pop_screen()
        except DailyLimitForALadyIsExceededException:
            logger.info(f'Reached limit of {DAILY_LETTERS_PER_LADY_LIMIT} daily email for lady id={lady_id}.')

        driver.close()
        driver.switch_to.window(driver.window_handles[-1])


# ----------------------------------------------------------------------------------------------------------------------
# @call_retrier(max_retry_num=3, catched_exceptions=(TimeoutException,))
def collect_lady_ids(driver):
    WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, "//a[text()='Correspondence']")))
    ppl_button = driver.find_element(By.XPATH, "//a[text()='Correspondence']")
    ppl_button.click()

    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]'))
    )
    send_intro_buttons = driver.find_elements(
        By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]'
    )
    lady_ids = [int(send_intro_button.get_attribute('id')) for send_intro_button in send_intro_buttons]

    pages = driver.find_elements(By.CSS_SELECTOR, 'a[class="navigation_on"]')
    if pages:
        page_urls = [page.get_attribute('href') for page in pages[:-1]]
        for page_url in page_urls:
            driver.get(page_url)
            WebDriverWait(driver, TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'a[class="default_photo link_options search_men_office"]')
                )
            )

            send_intro_buttons = driver.find_elements(
                By.CSS_SELECTOR,
                'a[class="default_photo link_options search_men_office"]',
            )
            lady_ids += [int(send_intro_button.get_attribute('id')) for send_intro_button in send_intro_buttons]

    # Pickup among available
    filtered_lady_ids = filter(lambda x: x not in BLACK_LIST_LADIES, lady_ids)
    resume_from_lady_id = config.get('RESUME_FROM_ID')
    resumed_and_filtered_lady_ids = itertools.dropwhile(
        lambda x: resume_from_lady_id and x != resume_from_lady_id, filtered_lady_ids
    )
    result = list(resumed_and_filtered_lady_ids)

    logger.info(f'Processing ladies in the following order: {result}')

    return result


# ----------------------------------------------------------------------------------------------------------------------
def run_sending(driver):
    lady_ids = collect_lady_ids(driver)
    # process_ladies(driver, lady_ids)
    # process_ladies_prio(driver, lady_ids)
    process_queue_of_received_intros(driver)
    process_ladies(driver, lady_ids)

# ----------------------------------------------------------------------------------------------------------------------
def main():
    with create_driver() as driver:
        try:
            logger.info('\n')
            logger.info('-------------------------------------')
            logger.info('STARTED NEW SENDER BOT RUN')
            login(driver)

            run_sending(driver)

            logger.info('')
            logger.info('SUCCESSFULLY FINISHED!')

        except LimitIsExceededException as ex:
            logger.error(f'LIMIT EXCEEDING ERROR: {repr(ex)}')
        except Exception as ex:
            logger.error(f'FINISHED WITH UNEXPECTED ERROR: {repr(ex)}')
            dump_exception_stack(ex)
            # Screener.push_screen(driver)


# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
