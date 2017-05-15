from sklearn.manifold import TSNE
from sklearn.decomposition import PCA, TruncatedSVD
import card_data
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import json
from adjustText import adjust_text

# TODO: What happens when adding in more sources of decks (e.g. not from tournaments)
# TODO: What about a graph-based visualization?
# TODO: Maybe some time thresholding. How has arcane reaper appeared in 50 decks?
# TODO: Separate visualizations for each class?
# TODO: Replace text with graphics/icons. Is there a better viz tool than matplotlib?
    # Maybe d3? https://bost.ocks.org/mike/fisheye/
    # https://bost.ocks.org/mike/nations/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ this would be esp. good for visualizing deck archetypes over time
    # http://bl.ocks.org/MoritzStefaner/1377729
    # http://cs.stanford.edu/people/karpathy/tsnejs/wordvecs.html
# Only consider cards appearing in at least this many decks
MIN_DECKS = 5

def repel_labels(ax, x, y, labels, k=0.01):
    G = nx.DiGraph()
    data_nodes = []
    init_pos = {}
    for xi, yi, label in zip(x, y, labels):
        data_str = 'data_{0}'.format(label)
        G.add_node(data_str)
        G.add_node(label)
        G.add_edge(label, data_str)
        data_nodes.append(data_str)
        init_pos[data_str] = (xi, yi)
        init_pos[label] = (xi, yi)

    pos = nx.spring_layout(G, pos=init_pos, fixed=data_nodes, k=k)

    # undo spring_layout's rescaling
    pos_after = np.vstack([pos[d] for d in data_nodes])
    pos_before = np.vstack([init_pos[d] for d in data_nodes])
    scale, shift_x = np.polyfit(pos_after[:,0], pos_before[:,0], 1)
    scale, shift_y = np.polyfit(pos_after[:,1], pos_before[:,1], 1)
    shift = np.array([shift_x, shift_y])
    for key, val in pos.iteritems():
        pos[key] = (val*scale) + shift

    for label, data_str in G.edges():
        ax.annotate(label,
                    xy=pos[data_str], xycoords='data',
                    xytext=pos[label], textcoords='data',
                    arrowprops=dict(arrowstyle="->",
                                    shrinkA=0, shrinkB=0,
                                    connectionstyle="arc3",
                                    color='red'), fontsize='small' )
    # expand limits
    all_pos = np.vstack(pos.values())
    x_span, y_span = np.ptp(all_pos, axis=0)
    mins = np.min(all_pos-x_span*0.15, 0)
    maxs = np.max(all_pos+y_span*0.15, 0)
    ax.set_xlim([mins[0], maxs[0]])
    ax.set_ylim([mins[1], maxs[1]])

def class_data():
    path = '../hearthstone-db/cards/all-cards.json'
    f = open(path)
    card_to_class = {}
    cards = json.load(f)
    for card in cards['cards']:
        card_to_class[card["name"].replace(' ', '').lower()] = card["hero"]
    return card_to_class

def card_to_color(classmap, cardname):
    c = classmap[cardname.replace(' ', '').lower()]
    if c is None:
        return (150/255.0, 150/255.0, 150/255.0) # Neutral
    class_to_color = {
        'priest': (220, 220, 220),
        'mage': (130, 160, 230),
        'warlock': (170, 70, 70),
        'druid': (190, 140, 75),
        'rogue': (220, 220, 90),
        'shaman': (50, 80, 65),
        'hunter': (110, 160, 60),
        'warrior': (230, 100, 90),
        'paladin': (230, 180, 90),
    }
    # Urgh
    for class_ in class_to_color:
        class_to_color[class_] = tuple([cval/255.0 for cval in class_to_color[class_]])
    return class_to_color[c]

def plot_decks(db):
    decks = db.decks
    #model = TSNE(n_components=2, perplexity=3)
    # model = PCA(n_components=2)
    model = TruncatedSVD(n_components=2)
    transformed = model.fit_transform(decks)
    plt.scatter(transformed[:,0], transformed[:,1])
    import random
    for i, (x, y) in enumerate(transformed):
        if random.random() < 0.55:
            continue
        plt.annotate(
            db.decknames[i],
            xy=(x, y),
            bbox=dict(boxstyle='round,pad=0.1', fc='yellow', alpha=0.3),
        )
    plt.show()

db = card_data.DeckDB(classfilter='mage')

if 0:
    plot_decks(db)
else:

    cards = db.decks.transpose()
    # Try only doing presence instead of counts
    #cards = cards > 0
    popular_card_indices = np.sum(cards, axis=1) > MIN_DECKS
    popular_cards = [db.cards[i] for i in range(len(db.cards)) if popular_card_indices[i]]
    cards = cards[popular_card_indices]
    print "Filtered down from {} cards to {}".format(len(db.cards), cards.shape[0])

    # TODO: Also try PCA
    # TODO: Also try LSA, LDA
    #model = TSNE(n_components=2, perplexity=3)
    #model = PCA(n_components=2)
    model = TruncatedSVD(n_components=2)
    transformed = model.fit_transform(cards)

    xs = transformed.transpose()[0]
    ys = transformed.transpose()[1]
    slack = .5
    axes = [xs.min()-slack,
            xs.max()+slack,
            ys.min()-slack,
            ys.max()+slack]
    plt.axis(axes)

    # Plot it
    cmap = class_data()
    txts = []
    for i, (x, y) in enumerate(transformed):
        color = card_to_color(cmap, popular_cards[i])
        t = plt.annotate(
            popular_cards[i],
            xy= (x, y),
            bbox=dict(boxstyle='round,pad=0.1', fc=color, alpha=0.3),
        )
        txts.append(t)

    #adjust_text(txts)
    #adjust_text(txts, arrowprops=dict(arrowstyle="-", color='k', lw=0.5),
    #            force_points=0.9, expand_points=(1.2, 1.3))
    #fig, ax = plt.subplots()
    # repel_labels(ax, xs, ys, popular_cards, k=0.005)


    plt.show()
    #plt.savefig('test.png')
