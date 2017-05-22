from datetime import date, timedelta, datetime
from multiprocessing.dummy import Pool as ThreadPool
from lxml.html import fromstring as parse_html
from urllib.request import urlopen
from zipfile import ZipFile
from urllib.error import URLError
from retrying import retry


def mwf(start_date, end_date=date.today()):
    """
    Generator that returns a string for every Monday, Wednesday, or Friday between start and end date.
    """
    while start_date <= end_date:
        if start_date.weekday() in [0, 2, 4]:
            yield f"{start_date:%Y%m%d}"
        start_date += timedelta(days=1)

@retry(stop_max_attempt_number=3, retry_on_result=lambda x: x is None)
def get_links_for_date(date):
    """
    Function to retrieve the image links for a given date.
    """
    comic_url = f"http://www.girlgeniusonline.com/comic.php?date={date}"
    try:
        resp = urlopen(comic_url)
        if (resp.status == 200):
            doc = parse_html(resp.read())
            return doc.xpath('//img[@src and @alt="Comic"]/@src')
    except (TimeoutError, URLError):
        print(f"Error getting comic for {date}")

@retry(stop_max_attempt_number=3, retry_on_result=lambda x: x is None)
def download_image(url):
    """
    Function to download a given url and return the results.
    """
    print(f"Downloading {url}")
    try:
        resp = urlopen(url)
        if (resp.status == 200):
            return resp.read()
    except (TimeoutError, URLError):
        print(f"Download of {url} failed.")

def parse_comment(comment):
    """
    Function to parse the comment from the zipfile
    """
    try:
        last_date, start_index = comment.decode('utf-8').split()
        start_index = int(start_index) + 1
        start_date = datetime.strptime(last_date, "%Y%m%d").date()
    except ValueError as e:
        start_date = date(2002, 11, 4)
        start_index = 0
    return start_date, start_index

def flatten(in_list):
    """
    Generator to take a nested list and return a flat list
    """
    return (item for listitem in in_list for item in listitem)

def create_cbz_from_dates(start_date=None, end_date=date.today(), cbz_location='girlgenius.cbz'):
    """
    Function to download all comics after a given date.
    """
    print("Getting Image URLs")
    with ZipFile(cbz_location, "a") as zf:
        if start_date is None:
            start_date, start_index = parse_comment(zf.comment)
        fetch_pool = ThreadPool(8)
        link_pool = ThreadPool(8)
        for i, file in enumerate(fetch_pool.imap(
                download_image,
                flatten(link_pool.imap(
                            get_links_for_date,
                            mwf(start_date, end_date)
                            )),
                chunksize=100
                )):
            zf.writestr(f"{(i + start_index):04}.jpg", file)
        try:
            zf.comment = bytes(f"{end_date:%Y%m%d} {i + start_index}", "utf-8")
        except UnboundLocalError:
            print("No new comics.")

if __name__ == "__main__":
    try:
        create_cbz_from_dates()
    except OSError as e:
        print(f"Could not delete cbz, please delete manually before running.")
        print(e)
    except PermissionError as e:
        print(f"Permission denied to cbz, please ensure you have permissions and run again.")
        print(e)
