import datetime
import math

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TIMEOUT = 16

# ----------------------------------------------------------------------------------------------------------------------
def create_driver(attach_mode=True, download_dir=None):
    """
    :param attach_mode: Attach to existing browser or create new instance from scratch?
    :param download_dir: Where downloaded files are saved
    :return:
    """
    # def _get_screenshot_as_file(func):
    #
    #     def wrapper(filepath, date_value=None):
    #         if date_value:
    #             if isinstance(date_value, str):
    #                 date_value = date_value.replace('/', '').replace('.', '')
    #             elif isinstance(date_value, date_type):
    #                 date_value = date_value.strftime('%Y%m%d')
    #             filepath_base, _, file_extention = filepath.rpartition('.')
    #             filepath = '%s_%s.%s' % (filepath_base, date_value, file_extention)
    #         func(filepath)
    #
    #     return wrapper

    # try:
    options = webdriver.ChromeOptions()
    options.add_argument('window-size=1200x600')
    options.add_argument('disable-gpu')
    options.add_argument("remote-debugging-port=9222")
    options.add_argument('no-sandbox')
    options.add_argument('disable-dev-shm-usage')

    driver = webdriver.Chrome(
        executable_path='/usr/lib/chromium-browser/chromedriver',
        chrome_options=options
    )

    # except Exception as ex:
    #     print(ex)

    return driver
    # download_dir = download_dir or BROWSER_DOWNLOAD_DIR

    # try:
    #     # if attach_mode:
    #     #     # Start real browser and attach to it.
    #     #     # We don't use 'headless' mode, because sites recognize this and ask to resolve captchas, etc.
    #     #     # To display its UI browser, uses virtual display server: xvfb
    #     #     browser = subprocess.Popen(
    #     #         BROWSER_START_SCRIPT,
    #     #         stdout=subprocess.PIPE,
    #     #         preexec_fn=os.setsid,
    #     #         shell=True
    #     #     )
    #     #
    #     #     # wait some time until browser is started
    #     #     sleep(2)
    #
    #     # options.add_argument('window-size=1200x600')
    #     # options.add_argument('disable-gpu')
    #     # options.add_argument("remote-debugging-port=9222")
    #
    #     if attach_mode:
    #         # options.add_argument('remote-debugging-address=127.0.0.1:9222')
    #         options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    #     else:
    #         options.add_argument('no-sandbox')
    #         options.add_argument('disable-dev-shm-usage')
    #
    #     # start up a chrome
    #     driver = webdriver.Chrome(
    #         executable_path=EXECUTABLE_PATH,
    #         chrome_options=options
    #     )
    #
    #     driver.download_dir = download_dir
    #     driver.get_screenshot_as_file = _get_screenshot_as_file(driver.get_screenshot_as_file)
    #
    #     yield driver
    #
    # finally:
    #     if driver:
    #         driver.quit()
    #     if browser:
    #         os.killpg(os.getpgid(browser.pid), signal.SIGTERM)




def login(driver):
    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[class="do_ajax"]')))
    signin_button = driver.find_element_by_css_selector('a[class="do_ajax"]')
    signin_button.click()
    WebDriverWait(driver, TIMEOUT).until(EC.visibility_of_element_located((
        By.CSS_SELECTOR, 'input[id="ajax_office_login_logins_ident"]')))
    username = driver.find_element_by_css_selector('input[id="ajax_office_login_logins_ident"]')
    username.send_keys('Odessaloveme2@Odafa2')
    password = driver.find_element_by_css_selector('input[id="ajax_office_login_logins_password"]')
    password.send_keys('Odessaloveme2')
    submit = driver.find_element_by_css_selector('button[class="btn"]')
    submit.click()


def _cleanup_input_field(input_field):
    _ = [input_field.send_keys(Keys.BACKSPACE) for _ in range(10)]


def process_gentleman(driver, url):
    driver.get(url)
    submit_button = driver.find_element_by_css_selector('button[id="btn_submit"]')
    submit_button.click()


def process_gentlemen(driver):
    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men"]')
    for send_intro_button in send_intro_buttons:
        gentleman_url = send_intro_button.get_attribute('href')

        driver.execute_script('window.open()')
        driver.switch_to_window(driver.window_handles[-1])

        process_gentleman(driver, gentleman_url)

        driver.close()
        driver.switch_to_window(driver.window_handles[-1])


def process_lady(driver, lady_id):
    driver.get(f'http://office.loveme.com/search_men_office/?women_id={lady_id}')

    reg_date_from = driver.find_element_by_css_selector('input[name="reg_date_from"]')
    reg_date_to = driver.find_element_by_css_selector('input[name="reg_date_to"]')
    last_login_from = driver.find_element_by_css_selector('input[name="date_from"]')
    last_login_to = driver.find_element_by_css_selector('input[name="date_to"]')

    countries = driver.find_element_by_css_selector('select[id="fk_countries"]')
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
    send_intro_buttons = driver.find_elements_by_css_selector('a[class="default_photo link_options search_men_office"]')
    for send_intro_button in send_intro_buttons:
        lady_id = send_intro_button.get_attribute('id')

        driver.execute_script('window.open()')
        driver.switch_to_window(driver.window_handles[-1])

        process_lady(driver, lady_id)

        driver.close()
        driver.switch_to_window(driver.window_handles[-1])

        print()

def main():
    driver = create_driver()
    driver.get('http://office.loveme.com/')

    login(driver)

    driver.get('http://office.loveme.com/ppl')

    process_ladies(driver)


    print()

if __name__ == "__main__":
    main()

