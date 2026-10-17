import copy
import translate as t


def test_boolean_labels():
    original = [
        {'role': 'user', 'content': 'If yes, write "True", otherwise write "False". Is corn a plant?'},
        {'role': 'assistant', 'content': 'True'},
    ]
    translated = [
        {'role': 'user', 'content': '如果是，写“True”；否则写“False”。玉米是植物吗？'},
        {'role': 'assistant', 'content': 'True'},
    ]
    assert not t.language_flags(original, translated)
    assert 'untranslated_english_message' in t.language_flags(original, original)
    missing = copy.deepcopy(translated)
    missing[0]['content'] = missing[0]['content'].replace('“False”', '“假”')
    assert 'untranslated_english_message' in t.language_flags(original, missing)
    ordinary = copy.deepcopy(original)
    ordinary[0]['content'] = 'Is corn a plant?'
    assert 'untranslated_english_message' in t.language_flags(ordinary, translated)


if __name__ == '__main__':
    test_boolean_labels()
    print('PASS explicit boolean labels; missing labels and ordinary prose rejected')
