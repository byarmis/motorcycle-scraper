import requests
from dataclasses import dataclass
import pathlib
from bs4 import BeautifulSoup as bs
from datetime import datetime as dt

from typing import List, Set

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

try:
    from secrets import API_KEY, FROM_EMAIL, TO_EMAILS

    has_secrets = True
except ImportError:
    has_secrets = False

BASE_URL = "https://www.af1racingaustin.com"
CWD = pathlib.Path(__file__).parent.resolve()


@dataclass
class Bike:
    title: str
    price: str = None

    def __str__(self):
        return f"{self.price} - {self.title}"


class BikeType:
    def __init__(self, url_addition: str, bike_type: str):
        self.url = "/".join((BASE_URL, url_addition))
        self.file_name = f"{bike_type.lower()}.txt"
        self.bike_type = bike_type

        self.new = None
        self.removed = None

    def get_soup(self):
        res = requests.get(self.url)
        res.raise_for_status()
        return bs(res.text, "html.parser")

    @staticmethod
    def get_bikes(soup) -> List[Bike]:
        prices = [
            p.text.strip() for p in soup.find_all("div", {"class": "product-price"})
        ]
        titles = [
            p.text.strip() for p in soup.find_all("div", {"class": "product-title"})
        ]

        d = [Bike(title=t.strip(), price=p.strip()) for t, p in zip(titles, prices)]
        d.sort(key=lambda x: x.title)

        return d

    def get_last_line(self) -> Set[str]:
        try:
            with open(f"{CWD}/{self.file_name}", "r") as f:
                last_line = ""
                for line in f.readlines():
                    last_line = line

        except FileNotFoundError:
            return set()

        return set(l.strip() for l in last_line.split("\t"))

    def write_line(self, output):
        with open(f"{CWD}/{self.file_name}", "a") as f:
            f.write("\t".join(output) + "\n")

    def do(self):
        soup = self.get_soup()
        bikes = self.get_bikes(soup)

        output = [f"{b.title} - {b.price}" for b in bikes]

        prev = self.get_last_line()
        self.write_line(output)

        current = set(output)

        self.new = current - prev
        self.removed = prev - current

    def get_html(self) -> str:
        footer = "\n</ul>"

        added_header = "<h2>Added</h2>\n<ul>\n"
        added_body = [f"<li>{b}</li>" for b in self.new if b]
        added_html = added_header + "\n".join(added_body) + footer

        removed_header = "<h2>Removed</h2>\n<ul>\n"
        removed_body = [f"<li><s>{b}</s></li>" for b in self.removed if b]
        removed_html = removed_header + "\n".join(removed_body) + footer

        output = []

        if added_body:
            output.append(added_html)
        if removed_body:
            output.append(removed_html)

        if output:
            o = "\n".join(output)
            return f"<h1>{self.bike_type.title()}</h1>\n{o}"
        else:
            return ""

    def __bool__(self):
        if self.new is None or self.removed is None:
            raise ValueError("I gotta do first")

        return bool(self.new) or bool(self.removed)


def send_email(message):
    current_time = dt.now().strftime("%Y-%m-%d %I:%M %p")
    m = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAILS,
        subject=f"AF1 Update {current_time}",
        html_content=message,
    )

    sg = SendGridAPIClient(API_KEY)
    sg.send(m)


if __name__ == "__main__":
    types = [
        BikeType(
            bike_type="used",
            url_addition="used-inventory",
        ),
        BikeType(
            bike_type="new",
            url_addition="aprilia-inventory-1?category=RS660",
        ),
        BikeType(
            bike_type="demo",
            url_addition="aprilia-inventory-1?category=DEMO+MODEL+SALE",
        ),
    ]

    [b.do() for b in types]
    message = [b.get_html() for b in types]

    if any(message) and has_secrets:
        send_email("\n".join(message))
    elif any(message) and not has_secrets:
        print("\n".join(message))
