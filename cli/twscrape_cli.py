import click, json, os
from scraper.scraper import TweetScraper
from scraper.cookies import load_cookies
from scraper.logger import get_logger
import queue

@click.command()
@click.option("--keyword", "-k", required=True, help="Keyword to search")
@click.option("--max", "-m", "max_tweets", default=100, help="Max tweets to scrape")
@click.option("--cookies", "-c", default="config/cookies.json", help="Path to cookies file")
def run_cli(keyword, max_tweets, cookies):
    LOG_Q = queue.Queue()
    logger = get_logger(LOG_Q)
    settings_path = os.path.join("config", "settings.json")
    settings = {}
    if os.path.exists(settings_path):
        settings = json.load(open(settings_path))
    c = None
    if os.path.exists(cookies):
        try:
            c = json.load(open(cookies))
        except Exception:
            c = None

    s = TweetScraper(keyword=keyword, max_tweets=max_tweets, log_queue=LOG_Q, settings=settings, cookies=c)
    s.run()

if __name__ == "__main__":
    run_cli()
