import logging
import asyncio

# set logger
log = logging.getLogger(__file__)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(lineno)d %(message)s', '%H:%M:%S')
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(formatter)
log.addHandler(log_handler)
log.setLevel(logging.DEBUG)

# get loop
loop = asyncio.get_event_loop()
