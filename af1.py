import requests
import pathlib
import os
from bs4 import BeautifulSoup as bs
from datetime import datetime as dt

from typing import Tuple, List

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from secrets import API_KEY, FROM_EMAIL, TO_EMAILS


BASE_URL = 'https://www.af1racingaustin.com'
CWD = pathlib.Path(__file__).parent.resolve()


def get_soup(url: str):
    res = requests.get(url)
    res.raise_for_status()

    return bs(res.text, 'html.parser')


def get_used_products(soup) -> List[str]:
    products = soup.find_all('div', {'class': 'product-title'})
    titles = [p.text.strip() for p in products if p.text]
    titles.sort()

    return titles


def get_last_line(file: str, cols: int=2) -> str:
    with open(f'{CWD}/{file}', 'r') as f:
        last_line = ''
        for line in f.readlines():
            last_line = line

        return last_line.strip()


def do_used() -> Tuple[str]:
    url = f'{BASE_URL}/used-inventory'
    soup = get_soup(url)
    products = get_used_products(soup)

    output = '\t'.join(products)
    last_line = get_last_line('used.txt')

    with open(f'{CWD}/used.txt', 'a') as f:
        f.write(output + '\n')

    current = set(products)
    prev = set(l.strip() for l in last_line.split('\t'))

    return current - prev, prev - current


def get_new_products(soup):
    prices = [p.text.strip() for p in soup.find_all('div', {'class': 'product-price'})]
    titles = [p.text.strip() for p in soup.find_all('div', {'class': 'product-title'})]
    d = [{'title': t, 'price':p} for t, p in zip(titles, prices)]
    d.sort(key=lambda x: x['title'])

    return d


def get_new_output(titles) -> str:
    prices_titles = {}
    for tp in titles:
        prices_titles[tp['price']] = tp['title'].split('-')[1]

    out = [f"{key} - {value}" for key, value in prices_titles.items()]

    return out


def do_new() -> List[str]:
    url = f'{BASE_URL}/aprilia-inventory-1?category=RS660'
    soup = get_soup(url)
    products = get_new_products(soup)

    output = get_new_output(products)
    last_line = get_last_line('new.txt')

    with open(f'{CWD}/new.txt', 'a') as f:
        f.write('\t'.join(output) + '\n')

    current = set(o.strip() for o in output)
    prev = set(l.strip() for l in last_line.split('\t'))

    return current - prev, prev - current


def do_demo() -> List[str]:
    url = f'{BASE_URL}/aprilia-inventory-1?category=DEMO+MODEL+SALE'
    soup = get_soup(url)
    products = get_used_products(soup)

    output = '\t'.join(products)
    last_line = get_last_line('demo.txt')

    with open(f'{CWD}/demo.txt', 'a') as f:
        f.write('\t'.join(output) + '\n')

    current = set(o.strip() for o in output.split('\t'))
    prev = set(l.strip() for l in last_line.split('\t'))

    return current - prev, prev - current


def get_html(
        added_bikes: List[str], 
        removed_bikes: List[str],
        ) -> str:

    added_header = '<h2>Added</h2>\n<ul>'
    footer = '</ul>'
    added_body = [f'<li>{b}</li>' for b in added_bikes if b]
    added_html = added_header + '\n'.join(added_body) + footer

    removed_header = '<h2>Removed</h2>\n<ul>'
    removed_body = [f'<li><s>{b}</s></li>' for b in removed_bikes if b]
    removed_html = removed_header + '\n'.join(removed_body) + footer

    output = []

    if added_body:
        output.append(added_html)
    if removed_body:
        output.append(removed_html)

    return '\n'.join(output)


def get_message(new, demo, used):
    message = []

    if any(new):
        message.append('<h1>New</h1>')
        message.append(get_html(*new))

    if any(demo):
        message.append('<h1>Demo</h1>')
        message.append(get_html(*demo))

    if any(used):
        message.append('<h1>Used</h1>')
        message.append(get_html(*used))

    return message


def send_email(message):
    current_time = dt.now().strftime('%Y-%m-%d %I:%M %p')
    m = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAILS,
        subject=f'AF1 Update {current_time}',
        html_content=message,
    )

    sg = SendGridAPIClient(API_KEY)
    response = sg.send(m)


if __name__ == '__main__':
    new = do_new()
    demo = do_demo()
    used = do_used()

    message = get_message(new, demo, used)

    if message:
        send_email('\n'.join(message))

