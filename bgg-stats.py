from flask import Flask
from collections import defaultdict
import certifi
import urllib3
import time
import xml.etree.ElementTree
import matplotlib.pyplot as plt
import mpld3

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


def generate_chart(values, title):
    fig, ax = plt.subplots()
    fig.suptitle(title)
    fig.set_size_inches(10, 10)
    ax.barh(range(len(values)), values.values(), align='center', color='blue')
    ax.set_yticks(range(len(values)))
    ax.set_yticklabels(values.keys())

    return mpld3.fig_to_html(fig, template_type="simple")


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
            print("Filling details for item: '%s'" % item_name)
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
    return generate_chart(mechanics, "Mechanics")


@app.route('/categories/<username>')
def categories_chart(username):
    categories, mechanics = fetch_user_data(username)
    return generate_chart(categories, "Categories")

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
