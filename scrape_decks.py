"""
Scrape a bunch of decks and serialize them to... json I guess?
"""

import scrapy
import re

# Site claims to have 5380 decks. I only found 2816. I expected to get less because of some
# scaping errors, but not that much less. To investigate.
# TODO: They have a sitemap that lists decks. Probably easier to just go through that than to scrape the lists.

BASE_DECKLIST_URL = 'http://www.hearthstonetopdeck.com/index/wild/'

class NoTournamentException(Exception):
    pass


# NTS: scrapy shell is really useful for figuring out selectors and stuff
class TopDeckSpider(scrapy.Spider):
    name = 'topdeck'
    start_urls = [BASE_DECKLIST_URL]
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': 1,
    }

    def __init__(self, *args, **kwargs):
        super(TopDeckSpider, self).__init__(*args, **kwargs)
        self.seen = set()
        self.max_page = None
        self.current_page = 1 # HTD starts counting from 1 (the first url doesn't have an explicit # though)
        self.decks_scraped = 0
        self.decks_saved = 0

    def parse(self, response):
        if self.max_page is None:
            # Pagination buttons. Should be of the form [2, 3, <max>, next]. (1 - the current page - is a different class)
            pagin = response.css('.pagin::text')
            assert len(pagin) == 4
            self.max_page = int(pagin[2].extract())
            self.logger.info("Scraping up to page {}".format(self.max_page))

        # Each decklist has around ~120 decks
        self.logger.info("Beginning scrape of page {}".format(self.current_page))
        i = 0
        for deck_url in response.css('.col-lg-push-4').xpath('//a[contains(@href, "/deck/wild/")]/@href').extract():
            # Haha, hacky hacks
            if deck_url.count('/') != 6:
                continue
            yield scrapy.Request(deck_url, callback=self.parse_deck)

        # Move on to the next page of decks
        self.current_page += 1
        if self.current_page <= self.max_page:
            yield scrapy.Request(BASE_DECKLIST_URL + '/' + str(self.current_page), callback=self.parse)

    def parse_deck(self, response):
        """
        Want to know:
         x player name
         x cards (duh)
         x class
         x date
         x tournament name
         x dust cost, I guess?
         x archetype? don't know if this is curated or set automatically
         - name
        """
        # Text at the very top. e.g. "#1 - Druid Ramp - Fibonacci"
        # TODO: There are some weird cases where this crashes because of unescaped special chars in title
        # e.g. the '<3' here: http://www.hearthstonetopdeck.com/deck/wild/3877/sol-%3C3-pini
        title = response.css('.panel-title')[0]
        deckname = re.search(r'- ([^-]*) -', title.extract()).group(1)
        player = title.xpath('a/text()').extract_first().strip()

        # Next we have a section that looks something like...
        #   Druid Ramp - Druid - Mid-Range
        #   Cost: 4380
        #   Format: Wild - Updated: 2016 / 02 / 29
        # This stuff is all pretty important
        banner = response.css('.deck_banner_description')

        nameB, class_, archetype = banner.css('.midlarge').xpath('span/text()').extract()
        # Name appears in two places and can vary slightly for some reason.
        if nameB != deckname:
            self.logger.warning("Name mismatch: <{}> vs <{}>. Taking the first one.".format(deckname, nameB))

        cost = int(re.search(
            r'Cost:</b> (\d+)',
            banner.xpath('div/div').extract_first()
        ).group(1))

        bannertext = banner.css('.small').extract_first()
        date = re.search(r'Updated:.*(\d\d\d\d/\d\d/\d\d)', bannertext).group(1)

        # Next, some text like "Here is the Warlock - Aggro deck list, played by BunnyHoppor during the European Winter Preliminaries"
        # This text is missing for 'decks to beat' decks
        try:
            hereis = response.css('.helper').extract_first()
            m = re.search(r'Here is the (\w+) - (.+) deck list, played by <b>(.+)</b> during the <b>(.+)</b>', hereis)
            if m is None:
                raise NoTournamentException
            c, arch, p, tournament = m.groups()
            # Only tournament is new information, but we should make sure the rest is consistent with what we found earlier
            assert c == class_
            assert arch == archetype
            assert p == player

        except NoTournamentException:
            tournament = None

        # TODO: should probably use card ids rather than strings. But NBD. Total size for 10k decks should still be under 10 MB.
        cards = {}
        for card in response.css('.cardname').xpath('span/text()').extract():
            count = int(card[0])
            name = card[2:]
            assert name not in cards
            cards[name] = count
        assert sum(cards.values()) == 30

        deck = {
            'class': class_,
            'archetype': archetype,
            'player': player,
            'tournament': tournament,
            'date': date,
            'cards': cards,
            'cost': cost,
            'name': deckname,
            'url': response.url,
        }
        self.decks_scraped += 1
        if (self.decks_scraped % 100 == 0):
            self.logger.info("Scraped {} deck pages, and saved {} decks".format(self.decks_scraped, self.decks_saved))
        # Don't record what looks like the same deck twice
        # TODO: minor optimization - dedupe before loading deck page
        deck_hash = hash((deck['player'], deck['class'], deck['cost'], deck['name']))
        if deck_hash not in self.seen:
            self.seen.add(deck_hash)
            self.decks_saved += 1
            yield deck
        else:
            self.logger.info("Skipping previously seen deck: {} from {}".format(deck['name'], deck['player']))

