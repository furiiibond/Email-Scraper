import csv
import argparse
from bs4 import BeautifulSoup
import requests
import requests.exceptions
import urllib.parse
from collections import deque
import re
import phonenumbers

def scrape_website(user_url, max_urls):
    # add https:// if not present
    if not user_url.startswith('http'):
        user_url = 'https://' + user_url

    user_url = user_url + '/impressum'

    urls = deque([user_url])
    scraped_urls = set()
    emails = set()
    phone_numbers = set()
    count = 0

    try:
        while len(urls):
            count += 1
            if count == max_urls:
                break
            url = urls.popleft()
            scraped_urls.add(url)

            parts = urllib.parse.urlsplit(url)
            base_url = '{0.scheme}://{0.netloc}'.format(parts)

            path = url[:url.rfind('/')+1] if '/' in parts.path else url

            try:
                response = requests.get(url, timeout=10)
                if response.url == 'https://www.coachy.net/404':
                    continue
            except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
                continue

            new_emails = set(re.findall(r'[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+', response.text, re.I))
            emails.update(new_emails)

            new_phone_numbers = set(re.findall(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', response.text, re.I))
            phone_numbers.update(new_phone_numbers)

            soup = BeautifulSoup(response.text, features="lxml")

            for anchor in soup.find_all("a"):
                link = anchor.attrs['href'] if 'href' in anchor.attrs else ''
                if link.startswith('/'):
                    link = base_url + link
                elif not link.startswith('http'):
                    link = path + link
                if "javascript" not in link and not link in urls and not link in scraped_urls:
                    urls.append(link)

    except Exception as e:
        # send to error output
        print(e)
        print('[-] Closing!')

    valid_phone_numbers = set()
    for match in phone_numbers:
        try:
            parsed_number = phonenumbers.parse(match, None)
            if phonenumbers.is_possible_number(parsed_number):
                valid_phone_numbers.add(match)
        except phonenumbers.NumberParseException:
            pass

    return emails, valid_phone_numbers

def main():
    parser = argparse.ArgumentParser(description="Web scraper for emails and phone numbers")
    parser.add_argument("--file", required=True, help="Path to the file containing the list of URLs")
    args = parser.parse_args()

    file_path = args.file

    with open(file_path, 'r') as file:
        urls = [line.strip() for line in file]

    with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['url', 'emails', 'phone_numbers']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for user_url in urls:
            print(f"Processing: {user_url}")
            emails, phone_numbers = scrape_website(user_url, 5)  # You can adjust max_urls here
            if len(emails) == 0 and len(phone_numbers) == 0:
                print(f"No emails or phone numbers found for {user_url}")
                continue
            result = {'url': user_url, 'emails': list(emails), 'phone_numbers': list(phone_numbers)}
            writer.writerow(result)
            csvfile.flush()  # Force writing the output immediately


if __name__ == "__main__":
    main()
