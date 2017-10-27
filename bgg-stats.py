from flask import Flask
from flask import render_template
from collections import defaultdict
from collections import OrderedDict
import certifi
import urllib3
import time
import xml.etree.ElementTree

app = Flask(__name__)
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

def parse_xml(url):
    response = http.request('GET', url)
    data = response.data
    time.sleep(1) # Big sleep here as BGG is quite harsh on rate limiting
    return xml.etree.ElementTree.XML(data)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def sort(d, reverse=True, by_value=True):
    return OrderedDict(sorted(d.items(), key=lambda t: t[1 if by_value else 0], reverse=reverse))


def generate_chart(values, title, games, horizontal=True):
    return render_template('bar-chart.html', values=values, title=title, games=games, horizontal=horizontal)


def fetch_user_data(username):
    url = 'https://boardgamegeek.com/xmlapi2/collection?username=%s&excludesubtype=boardgameexpansion&wanttoplay=0&wishlist=0' % username
    xml_obj = parse_xml(url)
    if xml_obj.tag == 'message':
        # Request is probably being queued, try again later
        time.sleep(2)
        xml_obj = parse_xml(url)
    coll_items = xml_obj.findall('item')

    categories = defaultdict(int)
    mechanics = defaultdict(int)
    year_published = defaultdict(int)
    games_by_mechanics = defaultdict(list)
    games_by_categories = defaultdict(list)
    games_by_year_published = defaultdict(list)

    for chunk in chunks(coll_items, 15):
        request_item_ids = ','.join((item.attrib['objectid'] for item in chunk))
        res = parse_xml('https://boardgamegeek.com/xmlapi2/thing?id=%s' % request_item_ids)
        items = res.findall('item')

        for item in items:
            item_name = item.find('name').attrib['value']
            item_year = item.find('yearpublished').attrib['value']
            year_published[item_year] += 1
            games_by_year_published[item_year].append(item_name)
            for category in item.findall('link[@type="boardgamecategory"]'):
                cat_name = category.attrib['value']
                games_by_categories[cat_name].append(item_name)
                categories[cat_name] += 1
            for mechanic in item.findall('link[@type="boardgamemechanic"]'):
                mech_name = mechanic.attrib['value']
                games_by_mechanics[mech_name].append(item_name)
                mechanics[mech_name] += 1

    return categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published


@app.route('/api/mechanics/<username>')
def mechanics_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published = fetch_user_data(username)
    return generate_chart(sort(mechanics), "Mechanics", games_by_mechanics)

@app.route('/mechanics/<username>')
def mechanics_page(username):
    return render_template("stats_loader.html", stats_name="mechanics", username=username)


@app.route('/api/release_year/<username>')
def release_year_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published = fetch_user_data(username)
    return generate_chart(sort(year_published, reverse=False, by_value=False), "Release year", games_by_year_published, horizontal=False)

@app.route('/release_year/<username>')
def release_year_page(username):
    return render_template("stats_loader.html", stats_name="release_year", username=username)


@app.route('/api/categories/<username>')
def categories_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published = fetch_user_data(username)
    return generate_chart(sort(categories), "Categories", games_by_categories)

@app.route('/categories/<username>')
def categories_page(username):
    return render_template("stats_loader.html", stats_name="categories", username=username)


@app.route('/')
def homepage():
    return render_template("home.html")

if __name__ == '__main__':
    app.run(host= '0.0.0.0')
