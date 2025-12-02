import re
from selenium.webdriver.common.by import By

def parse_tweet(article):
    """
    article: selenium web element for the tweet article
    returns: dict
    """
    data = {
        "username": "",
        "handle": "",
        "text": "",
        "timestamp": "",
        "media_urls": [],
        "hashtags": [],
        "mentions": []
    }
    try:
        text_el = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
        data["text"] = text_el.text
    except Exception:
        try:
            data["text"] = article.text
        except Exception:
            data["text"] = ""

    try:
        data["username"] = article.find_element(By.XPATH, './/div[@dir="auto"]/span').text
    except Exception:
        pass

    try:
        data["handle"] = article.find_element(By.XPATH, './/div[@dir="ltr"]').text
    except Exception:
        pass

    try:
        time_el = article.find_element(By.XPATH, './/time')
        data["timestamp"] = time_el.get_attribute("datetime")
    except Exception:
        pass

    try:
        imgs = article.find_elements(By.XPATH, './/img[contains(@src,"twimg.com/media")]')
        for img in imgs:
            src = img.get_attribute("src")
            if src:
                data["media_urls"].append(src)
    except Exception:
        pass

    data["hashtags"] = re.findall(r"#(\w+)", data["text"])
    data["mentions"] = re.findall(r"@(\w+)", data["text"])
    return data
