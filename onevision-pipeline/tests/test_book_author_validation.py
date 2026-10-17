import copy
import translate as t


def test_book_author_validation():
    for prompt in ['Who wrote this book?', 'Who is the author of this book?']:
        original = [
            {'role': 'user', 'content': '<image>' + prompt + '\nAnswer the question with a short phrase.'},
            {'role': 'assistant', 'content': 'Howard Massey'},
        ]
        translated = copy.deepcopy(original)
        translated[0]['content'] = '<image>这本书的作者是谁？\n用短语回答。'
        assert not t.language_flags(original, translated)
        assert 'untranslated_english_message' in t.language_flags(original, original)
        changed = copy.deepcopy(translated)
        changed[1]['content'] = 'Another Author'
        assert 'image_book_author_changed_requires_review' in t.language_flags(original, changed)
        no_image = copy.deepcopy(original)
        no_image[0]['content'] = no_image[0]['content'].replace('<image>', '')
        assert 'untranslated_english_message' in t.language_flags(no_image, translated)
    prose = [
        {'role': 'user', 'content': '<image>Describe the author of this book.'},
        {'role': 'assistant', 'content': 'A famous writer'},
    ]
    translated = copy.deepcopy(prose)
    translated[0]['content'] = '<image>描述这本书的作者。'
    assert 'untranslated_english_message' in t.language_flags(prose, translated)


if __name__ == '__main__':
    test_book_author_validation()
    print('PASS exact image-author task, unchanged name, untranslated prose guards')
