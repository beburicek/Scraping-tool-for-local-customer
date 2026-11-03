Bazos to Notion Scraper

A Python script that automatically monitors auto.bazos.sk for new car listings and saves them into a Notion database in real time.

Features

Custom search filters based on your Bazos search URL.

Automatic duplicate detection by checking existing links in Notion.

User-Agent rotation to keep requests natural.

Scheduled checks every few minutes.

Setup & Usage

Install the dependencies:

pip install requests beautifulsoup4 schedule


Add your credentials in the script:

NOTION_TOKEN: Your integration token.

DATABASE_ID: The ID of your Notion database.

URL_BAZOS: Your target search URL with desired filters.

Run the script:

python main.py
