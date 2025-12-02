import os, time, json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def build_driver(settings: dict):
    chrome_options = Options()

    # Use headless optionally
    if settings.get("headless"):
        chrome_options.add_argument("--headless=new")

    # Clean noise and disable notifications
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })

    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=site-per-process,TranslateUI")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--window-size=1400,900")

    # optional user agent
    ua = settings.get("user_agent")
    if ua:
        chrome_options.add_argument(f"--user-agent={ua}")

    # reduce webdriver-manager logs
    os.environ["WDM_LOG_LEVEL"] = "0"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # minimal waits
    driver.implicitly_wait(int(settings.get("implicit_wait", 5)))
    return driver

def add_cookies(driver, cookies):
    """
    cookies: list of cookie dicts (name,value,domain,path,...)
    Selenium expects at minimum: name, value, path (default '/'), domain optional
    """
    if not cookies:
        return
    # Visit domain to set cookies
    driver.get("https://x.com")
    time.sleep(1)
    for c in cookies:
        cookie = {"name": c.get("name"), "value": c.get("value"), "path": c.get("path", "/")}
        if c.get("domain"): cookie["domain"] = c.get("domain")
        if c.get("expiry") or c.get("expirationDate"):
            try:
                cookie["expiry"] = int(c.get("expiry") or c.get("expirationDate"))
            except Exception:
                pass
        try:
            driver.add_cookie(cookie)
        except Exception:
            # ignore cookies that cannot be added
            pass
    driver.refresh()
    time.sleep(1)
