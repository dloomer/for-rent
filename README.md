# for-rent
Google App Engine app that intends to save you a lot of work in apartment-hunting. Makes Craigslist less spammy by ignoring re-posts of the same property. Correlates properties from CL, Zillow, and Knock into a single feed that is spit out in the form of email alerts.

### Required Python libraries
Place the following in your `third_party` folder before deploying to App Engine:
* [BeatifulSoup 4](https://www.crummy.com/software/BeautifulSoup/bs4/download/) (`bs4` folder from the repo)
* [Google Cloud Storage Client Library](https://developers.google.com/api-client-library/python/apis/storage/v1#installing-the-client-library) (`cloudstorage` folder)
* [feedparser](https://pypi.python.org/pypi/feedparser) (just the `feedparser.py` file)

### Craigslist web proxy
Craigslist blocks all web traffic bearing an appengine user-agent string. It might also block traffic from App Engine-hosted IP addresses (due to the user-agent issue, I never got far enough as to find this out). As a result you will need to set up a reverse proxy on your own web server (Apache, etc.) which replaces the user-agent header (`mod_headers`?). Then, in your `feeds.yaml`, configure the `hostname_proxy` property of each Craigslist feed to reference the domain name via which your proxy can be reached. Do the same for the `images_hostname_proxies/craigslist` configuration. See below for more info on `feeds.yaml`.

In summary, you will need one proxy to redirect to a Craigslist region-specific web domain (e.g. `seattle.craigslist.org`) and one to their image host (`images.craigslist.org`).

### Setting up feeds.yaml
Each `feeds` entry represents a search query to public APIs (or in the case of Craigslist, an RSS feed) of various apartment search services. The expectation is that each query will represent a different geographic area (or neighborhood), although you may adjust the query parameters as you wish.

Currently the list of available feed sources is limited to Craigslist, Zillow, and Knock Rentals, although the addition of other services will be fairly straightforward with enhancements to `app/lib/services/feed_ingestor.py` and `app/lib/services/feed_item_parsers.py` (enter a pull request to this repo).

The best way to understand the structure of the feed configurations is to have a look at `feeds.sample.yaml` at the root of this repo.

### Contributing
1. Fork the repository on Github
2. Create a named feature branch (like `add_component_x`)
3. Write your change
4. Write tests for your change (if applicable)
5. Run the tests, ensuring they all pass
6. Submit a Pull Request using Github
