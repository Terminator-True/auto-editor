import os
import pytest

from event_categorization import canonical_labels


def test_normalize_simple_token():
    assert canonical_labels.normalize_label('We got a double kill!', game='generic') == 'double_kill'
    assert canonical_labels.normalize_label('PENTAKILL! amazing', game='generic') == 'pentakill'


def test_game_specific_rules():
    # lol contains 'baron' token
    assert canonical_labels.normalize_label('Baron Nashor slain', game='lol') == 'baron'
    # generic still recognizes baron token from generic.json
    assert canonical_labels.normalize_label('baron!', game='generic') == 'baron'


def test_regex_label_named_group():
    # the lol.json has a regex with named group 'label' for pentakill
    res = canonical_labels.normalize_label('pentakill: triple!', game='lol')
    assert res == 'pentakill'


def test_none_for_unknown():
    assert canonical_labels.normalize_label('something unrelated', game='generic') is None
