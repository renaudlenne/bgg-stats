#!/usr/bin/env python3
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
    time.sleep(1)  # Big sleep here as BGG is quite harsh on rate limiting
    return xml.etree.ElementTree.XML(data)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def first_elem(d, n):
    res = {}
    for key in list(d)[0:n]:
        res[key] = d[key]
    return res


def release_dates_filled(init_d):
    d = sort(init_d, reverse=False, by_value=False)
    keys_list = list(d.keys())
    first_year = int(keys_list[0])
    last_year = int(keys_list[len(d.keys()) - 1])
    year_list = list(range(first_year, last_year + 1))
    result = []
    for year in year_list:
        year_val = d[str(year)] if str(year) in d else 0
        result.append((year, year_val))
    return OrderedDict(result)


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
    nb_games = len(coll_items)

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

    return categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published, nb_games


@app.route('/api/mechanics/<username>')
def mechanics_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published, nb_games = fetch_user_data(
        username)
    return generate_chart(sort(mechanics), "Mechanics", games_by_mechanics)


@app.route('/mechanics/<username>')
def mechanics_page(username):
    return render_template("stats_loader.html", url="/api/mechanics/%s" % username, title=username)


@app.route('/api/radar/<username>')
def radar_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published, nb_games = fetch_user_data(
        username)
    top10 = first_elem(sort(mechanics), 10)
    labels = []
    for key in top10.keys():
        labels.append(key)
    labels = sorted(labels)
    dataset = {"title": username, "values": [], "color": "75, 192, 192"}
    for key in labels:
        if key in mechanics.keys():
            dataset["values"].append(mechanics[key] / nb_games * 100)
        else:
            dataset["values"].append(0.0)
    return render_template('radar-chart.html', labels=labels, datasets=[dataset])


@app.route('/radar/<username>')
def radar_page(username):
    return render_template("stats_loader.html", url="/api/radar/%s" % username, title=username)


@app.route('/api/versus/<username1>/<username2>')
def versus_chart(username1, username2):
    categories1, mechanics1, year_published1, games_by_mechanics1, games_by_categories1, games_by_year_published1, nb_games1 = fetch_user_data(
        username1)
    categories2, mechanics2, year_published2, games_by_mechanics2, games_by_categories2, games_by_year_published2, nb_games2 = fetch_user_data(
        username2)
    top10_1 = first_elem(sort(mechanics1), 10)
    top10_2 = first_elem(sort(mechanics2), 10)
    labels = []
    for key in top10_1.keys():
        labels.append(key)
    for key in top10_2.keys():
        if key not in labels:
            labels.append(key)
    labels = sorted(labels)
    dataset1 = {"title": username1, "values": [], "color": "75, 192, 192"}
    dataset2 = {"title": username2, "values": [], "color": "255, 74, 243"}
    for key in labels:
        if key in mechanics1.keys():
            dataset1["values"].append(mechanics1[key] / nb_games1 * 100)
        else:
            dataset1["values"].append(0.0)
    for key in labels:
        if key in mechanics2.keys():
            dataset2["values"].append(mechanics2[key] / nb_games2 * 100)
        else:
            dataset2["values"].append(0.0)
    return render_template('radar-chart.html', labels=labels, datasets=[dataset1, dataset2])


@app.route('/versus/<username1>/<username2>')
def versus_page(username1, username2):
    return render_template("stats_loader.html", url="/api/versus/%s/%s" % (username1, username2),
                           title="%s vs %s" % (username1, username2))


@app.route('/api/release_year/<username>')
def release_year_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published, nb_games = fetch_user_data(
        username)
    return generate_chart(release_dates_filled(year_published), "Release year", games_by_year_published,
                          horizontal=False)


@app.route('/release_year/<username>')
def release_year_page(username):
    return render_template("stats_loader.html", url="/api/release_year/%s" % username, title=username)


@app.route('/api/categories/<username>')
def categories_chart(username):
    categories, mechanics, year_published, games_by_mechanics, games_by_categories, games_by_year_published, nb_games = fetch_user_data(
        username)
    return generate_chart(sort(categories), "Categories", games_by_categories)


@app.route('/categories/<username>')
def categories_page(username):
    return render_template("stats_loader.html", url="/api/categories/%s" % username, title=username)


@app.route('/')
def homepage():
    return render_template("home.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0')
