import logging, time, json

def get_queue_logger(queue):
    class QHandler(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                payload = {"time": time.time(), "level": record.levelname, "msg": msg}
                queue.put(payload, block=False)
            except Exception:
                pass

    logger = logging.getLogger("twscrape")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = QHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger
