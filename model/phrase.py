import random
from webapp2_extras.appengine.auth.models import Unique

foods = [
    'onion',
    'carrot',
    'pear',
    'bean',
    'corn',
    'bread',
    'apple',
    'banana',
    'fig',
    'grape',
    'lemon',
    'lime',
    'orange',
    'peach',
    'plum',
]

adjectives = [
    'tall',
    'short',
    'up',
    'down',
    'fancy',
    'busy',
    'loud',
    'crazy',
    'kind',
    'nice',
    'real',
    'speedy',
    'handy',
    'active',
    'alert',
    'bold',
    'brave',
    'bright',
    'calm',
    'clever',
    'cool',
    'free',
    'grand',
    'great',
    'happy',
    'jolly',
    'lucky',
    'spicy',
    'sunny',
    'super',
    'wise',
]

animals = [
    'bat',
    'bear',
    'bird',
    'cat',
    'cow',
    'deer',
    'dog',
    'dove',
    'dragon',
    'duck',
    'eagle',
    'fish',
    'fox',
    'frog',
    'goose',
    'lion',
    'mouse',
    'owl',
    'pig',
    'rat',
    'seal',
    'shark',
    'sheep',
    'snake',
    'spider',
    'tiger',
    'turkey',
    'viper',
    'whale',
    'wolf',
]

colors = [
    'blue',
    'bronze',
    'fire',
    'forest',
    'gold',
    'gray',
    'green',
    'navy',
    'purple',
    'red',
    'silver',
    'sky',
    'yellow',
    'neon',
]


def generate_phrase(n=2):
    """Randomly generate a simple memorable phrase.

    Args:
        n: int, number of words in the phrase, default 2, max 4.
    """
    if n not in range(1, 5):
        raise Exception("Invalid number of words for phrase: {}.".format(n))

    lists = [foods, animals, colors, adjectives]

    return ' '.join([random.choice(l) for l in random.sample(lists, n)])


def generate_unique_phrase(namespace='Phrase', n=2):
    """Use the datastore to create a phrase within a namespace."""
    max_attempts = 10
    phrase = None
    for x in range(max_attempts):
        p = generate_phrase(n=2)
        p_is_unique = Unique.create(namespace + ':' + p)
        if p_is_unique:
            phrase = p
            break
    if phrase is None:
        raise Exception("Could not generate a unique phrase after {} "
                        "attempts.".format(max_attempts))

    return phrase


def print_many(m, n):
    """Print m phrases, each of length n."""
    print '\n'.join([generate_phrase(n) for x in range(m)])
