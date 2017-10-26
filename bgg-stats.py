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

def sort(d):
    return OrderedDict(sorted(d.items(), key=lambda t: t[1], reverse=True))


def generate_chart(values, title):
    return render_template('horizontal-bar-chart.html', values=values.values(), labels=values.keys(), title=title)


def fetch_user_data(username):
    url = 'https://boardgamegeek.com/xmlapi2/collection?username=%s&excludesubtype=boardgameexpansion&wanttoplay=0&wishlist=0' % username
    xml_obj = parse_xml(url)
    if xml_obj.tag == 'message':
        # Request is probably being queued, try again
        xml_obj = parse_xml(url)
    coll_items = xml_obj.findall('item')

    categories = defaultdict(int)
    mechanics = defaultdict(int)

    for chunk in chunks(coll_items, 15):
        request_item_ids = ','.join((item.attrib['objectid'] for item in chunk))
        res = parse_xml('https://boardgamegeek.com/xmlapi2/thing?id=%s' % request_item_ids)
        items = res.findall('item')

        for item in items:
            item_name = item.find('name').attrib['value']
            for category in item.findall('link[@type="boardgamecategory"]'):
                cat_name = category.attrib['value']
                categories[cat_name] += 1
            for mechanic in item.findall('link[@type="boardgamemechanic"]'):
                mech_name = mechanic.attrib['value']
                mechanics[mech_name] += 1

    return categories, mechanics


@app.route('/mechanics/<username>')
def mechanics_chart(username):
    categories, mechanics = fetch_user_data(username)
    return generate_chart(sort(mechanics), "Mechanics")


@app.route('/categories/<username>')
def categories_chart(username):
    categories, mechanics = fetch_user_data(username)
    return generate_chart(sort(categories), "Categories")

@app.route('/')
def homepage():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <title>BGG stats generator</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>
    <div id="form">
        <label for="username">BGG Username:&nbsp;</label>
        <input type="text" name="username" id="username" value=""><br>
        <a href="#" id="stats_button" onClick="getStats();" >Get some stats!</a><br />
    </div>
    <div id="loader" style="display: none;">
        Loading...
    </div>
    <script language="javascript">
        document.getElementById("username")
            .addEventListener("keyup", function(event) {
            event.preventDefault();
            if (event.keyCode === 13) {
                document.getElementById("stats_button").click();
            }
        });

        function getStats() {
            var iframe = document.getElementById("resultIframe");
            var username = document.getElementById("username").value;
            var loader = document.getElementById("loader");
            var form = document.getElementById("form");
            form.style.display = "none"
            loader.style.display = "block"
            iframe.src = "mechanics/"+username;
            iframe.onload= function() {
                loader.style.display = "none"
                window.history.pushState(iframe.src,"", iframe.src);
            };
        }
    </script>
    <iframe  src="" frameBorder="0" seamless='seamless' name="resultIframe" id="resultIframe" scrolling="no" style="border: none; width: 100%; height: -webkit-fill-available;">
        <p>iframes are not supported by your browser.</p>
    </iframe>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host= '0.0.0.0')
