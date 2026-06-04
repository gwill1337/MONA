import time
from tasks import collect_and_save

while True:
    collect_and_save()
    time.sleep(5)