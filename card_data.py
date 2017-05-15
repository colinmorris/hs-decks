import json
import numpy as np


class DeckDB(object):

    def __init__(self, classfilter=None, fname='decks.json'):
        self.card_to_id = {}
        self._next_card_id = 0
        self.cards = None
        self.decknames = []
        self.decks = None  # np array of shape (decks, cards)

        self.load_json(fname, classfilter)


    def id_for_card(self, cardname):
        if cardname not in self.card_to_id:
            self.card_to_id[cardname] = self._next_card_id
            self._next_card_id += 1
        return self.card_to_id[cardname]

    def card_for_id(self, cardid):
        return self.cards[cardid]

    def debug_deck(self, i):
        print "Deck {} contains...".format(self.decknames[i])
        for cardid, count in enumerate(self.decks[i]):
            if count > 0:
                print "\t{} x{}".format(self.card_for_id(cardid), count)



    def load_json(self, fname, classfilter):
        f = open(fname)
        decks = []
        for line in f:
            deck = {}
            raw_deck = json.loads(line)
            if classfilter and raw_deck['class'].lower() != classfilter.lower():
                continue
            # TODO: experimental
            yr = raw_deck['date'].split('/')[0]
            if int(yr) < 2015:
                continue

            for card_str, count in raw_deck['cards'].iteritems():
                deck[self.id_for_card(card_str)] = count
            decks.append(deck)
            self.decknames.append(raw_deck['name'])

        # Our card-id mapping is done, so let's build the reverse lookerupper
        self.cards = [None for _ in range(len(self.card_to_id))]
        for (card, id) in self.card_to_id.iteritems():
            self.cards[id] = card

        # Now that we're done, we know how many cards and decks. Let's store in a np array.
        # These are going to be pretty sparse. Should take advantage of that, but eh.
        shape = (len(decks), len(self.card_to_id))
        self.decks = np.zeros(shape, dtype=np.int8)

        for i, deck in enumerate(decks):
            for (cardid, count) in deck.iteritems():
                self.decks[i][cardid] = count
