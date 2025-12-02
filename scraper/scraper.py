import time, csv, os, json, traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import build_driver, add_cookies
from .cookies import load_cookies

class TweetScraper:
    def __init__(self, keyword, max_tweets, settings, log_queue, tweets_list):
        self.keyword = keyword
        self.max_tweets = int(max_tweets)
        self.settings = settings or {}
        self.log_queue = log_queue
        self.tweets = tweets_list      # shared list (thread-safe append expected)
        self.driver = None
        self.stopped = False

        # output files
        os.makedirs("downloads", exist_ok=True)
        self.csv_path = os.path.join("downloads", "tweets.csv")
        self.json_path = os.path.join("downloads", "tweets.json")
        # initialise csv header
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Username", "Handle", "Tweet_Text", "Timestamp", "Media_URLs", "Hashtags", "Mentions", "URL"])

    def log(self, level, msg):
        payload = {"time": time.time(), "level": level, "msg": msg}
        try:
            self.log_queue.put(payload, block=False)
        except Exception:
            pass

    def stop(self):
        self.stopped = True
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    def run(self, cookies=None):
        try:
            self.log("INFO", f"Building browser (headless={self.settings.get('headless')})")
            self.driver = build_driver(self.settings)

            # load cookies (param overrides file)
            if cookies:
                self.log("INFO", "Adding cookies provided via UI")
                add_cookies(self.driver, cookies)
            else:
                file_cookies = load_cookies()
                if file_cookies:
                    self.log("INFO", f"Loading cookies from config/cookies.json")
                    add_cookies(self.driver, file_cookies)
                else:
                    self.log("WARN", "No cookies found. You may be redirected to login.")

            # Navigate to home and wait until logged in
            self.log("INFO", "Navigating to home to verify login")
            self.driver.get("https://x.com/home")

            try:
                # Wait up to 15 seconds for the compose button or profile to appear
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/compose')]"))
                )
                self.log("OK", "Login confirmed — compose button detected")
            except:
                self.log("WARN", "Login not confirmed, you may be redirected or login failed")
                # optional: wait a few more seconds to allow user to manually login
                time.sleep(5)

            # begin scraping
            self._scrape_loop()
        except Exception as e:
            self.log("ERROR", f"Fatal error in scraper: {e}")
            self.log("DEBUG", traceback.format_exc())
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass

    def _scrape_loop(self):
        self.log("INFO", f"Searching for keyword: {self.keyword}")
        q = self.keyword.replace(" ", "%20")
        url = f"https://x.com/search?q={q}&f=live"
        self.driver.get(url)

        # wait for tweets feed to load (first article)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )
            self.log("INFO", "Tweet feed loaded")
        except:
            self.log("WARN", "Tweet feed not detected, proceeding anyway")

        time.sleep(float(self.settings.get("initial_feed_delay", 2)))  # optional extra wait

        tweets_scraped = 0
        seen = set()
        scrolls = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        max_scrolls = int(self.settings.get("max_consecutive_scrolls", 40))
        scroll_delay = float(self.settings.get("scroll_delay", 2))

        while tweets_scraped < self.max_tweets and not self.stopped and scrolls < max_scrolls:
            articles = self.driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
            self.log("INFO", f"Found {len(articles)} articles on current view (scraped so far {tweets_scraped})")

            for article in articles:
                if tweets_scraped >= self.max_tweets or self.stopped:
                    break
                try:
                    # parse text
                    try:
                        text_el = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                        text = text_el.text
                    except:
                        text = article.text[:500]

                    # username & handle
                    username = ""
                    handle = ""
                    try:
                        username = article.find_element(By.XPATH, './/div[@dir="auto"]/span').text
                    except: pass
                    try:
                        handle = article.find_element(By.XPATH, './/div[@dir="ltr"]').text
                    except: pass

                    # timestamp & tweet url
                    timestamp = ""
                    url_link = ""
                    try:
                        t_el = article.find_element(By.XPATH, './/time')
                        timestamp = t_el.get_attribute("datetime")
                        parent = t_el.find_element(By.XPATH, "./ancestor::a[1]")
                        url_link = parent.get_attribute("href")
                    except:
                        pass

                    # media urls
                    media = []
                    try:
                        imgs = article.find_elements(By.XPATH, './/img[contains(@src,"twimg.com/media")]')
                        for im in imgs:
                            s = im.get_attribute("src")
                            if s and s not in media:
                                media.append(s)
                    except:
                        pass

                    hashtags = []
                    mentions = []
                    try:
                        import re
                        hashtags = re.findall(r"#(\w+)", text)
                        mentions = re.findall(r"@(\w+)", text)
                    except:
                        pass

                    key_id = url_link or (username + text[:40])
                    if key_id in seen:
                        continue
                    seen.add(key_id)

                    # store
                    row = {
                        "username": username,
                        "handle": handle,
                        "text": text,
                        "timestamp": timestamp,
                        "media": media,
                        "hashtags": hashtags,
                        "mentions": mentions,
                        "url": url_link
                    }
                    self.tweets.append(row)
                    tweets_scraped += 1

                    # append to CSV
                    with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            username, handle, text.replace("\n"," "), timestamp,
                            ";".join(media), ";".join(hashtags), ";".join(mentions), url_link
                        ])
                    # write JSON incremental
                    try:
                        with open(self.json_path, "w", encoding="utf-8") as jf:
                            json.dump(self.tweets, jf, ensure_ascii=False, indent=2)
                    except:
                        pass

                    self.log("TWEET", f"#{tweets_scraped} {text[:80].replace('\\n',' ')}")
                    if tweets_scraped >= self.max_tweets:
                        break

                except Exception as e:
                    self.log("ERROR", f"Skipping an article due to: {e}")
                    self.log("DEBUG", traceback.format_exc())

            # scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_delay)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scrolls += 1
            if new_height == last_height:
                self.log("INFO", "Reached page end or no more content.")
                break
            last_height = new_height

        self.log("INFO", f"Scraping finished — tweets collected: {tweets_scraped}")
        # final JSON write
        try:
            with open(self.json_path, "w", encoding="utf-8") as jf:
                json.dump(self.tweets, jf, ensure_ascii=False, indent=2)
        except:
            pass

        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
