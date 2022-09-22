from bs4 import BeautifulSoup
from bs4.element import DEFAULT_OUTPUT_ENCODING
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import re
import json
from os import path


def get_brew_html(url):
    html_doc = requests.get(url).text
    soup = BeautifulSoup(html_doc, 'html.parser')
    title = soup.title.text.split(' | ')[1]
    soup = soup.find_all('html')[1]

    # Get the Brew's publication date
    date = ''
    for t in soup.find_all('td'):
        m = re.search('([A-z]* \d{1,2}, \d{4})', t.text)
        if m and m.groups(0):
            date = m.groups(0)[0]
            break

    return soup, title, date


def clean_brew_html(soup):
    # Remove scripts
    for s in soup.select('script'):
        s.extract()

    # Remove "TOGETHER WITH"
    for t in soup.find_all('table', {'align': 'center'}):
        if 'Together with' in t.text or 'TOGETHER WITH' in t.text:
            if len(t.find_all('table')) == 0:
                t.extract()
                break

    # Remove Sponsored and Sports blocks (old format)
    for b in soup.find_all('div', {'class': ['c6', 'c7']}):
        if 'SPONSORED' in b.text or 'SPORTS' in b.text:
            b.extract()

    # Remove Sponsored and Sports blocks (new format)
    for h in soup.find_all('h3'):
        if 'SPONSORED' in h.text or 'SPORTS' in h.text:
            h.find_parent('table').extract()

    # Remove Sponsored "BREW'S BETS"
    for p in soup.find_all('p'):
        if '.*' in p.text:
            p.extract()

    # Remove footer
    for t in soup.find_all('td', {'align': 'center'}):
        if 'ADVERTISE' in t.text:
            t.extract()

    # Return cleaned HTML
    return soup.prettify()


def send_email(html_body, config):
    msg = MIMEMultipart()
    msg.attach(MIMEText(html_body, 'html'))
    msg['Subject'] = config['subject']
    msg['From'] = config['from']
    msg['To'] = config['to']
    smtp = smtplib.SMTP(config['server'])
    smtp.starttls()
    smtp.login(config['username'], config['password'])
    smtp.send_message(msg)
    smtp.quit()


# Load the orders, a list of Brews to send and the last date that was sent
orders = []
orders_file = '/opt/morningbrew/orders'
if path.exists(orders_file):
    try:
        with open(orders_file) as f:
            orders = json.load(f)
    except:
        raise "Failed to load orders"
else:
    print('Orders file not found. Try copying "orders.example" to "orders" and editing it to match your desired brews')

# Send the orders if the date is different than the last one sent
for i in range(len(orders)):
    soup, title, date = get_brew_html(orders[i]['url'])
    html = clean_brew_html(soup)
    if not orders[i]['last_order'] == date:
        send_email(html, {
            'from': 'Morning Brew <noreply@jdgregson.com>',
            'to': orders[i]['email_to'],
            'subject': title,
            'server': 'email-smtp.us-west-2.amazonaws.com',
            'username': 'AKIA6G6V63JSIR7SFYII',
            'password': 'BJL4uFcg9BEv6vyVd00EBwbvCUqrmALAUuAKJj9rkxIP'
        })
        orders[i]['last_order'] = date

# Save the orders
with open(orders_file, 'w') as f:
    json.dump(orders, f, indent=4)
