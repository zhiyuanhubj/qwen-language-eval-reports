"""Regression coverage for exact image book-title transcription."""
import copy
import translate as t


def test_book_title_validation():
    original = [
        {'role': 'user', 'content': '<image>What is the title of this book?\nAnswer the question with a short phrase.'},
        {'role': 'assistant', 'content': 'On Immunity: An Inoculation'},
    ]
    translated = copy.deepcopy(original)
    translated[0]['content'] = '<image>这本书的标题是什么？\n用短语回答这个问题。'
    assert t.language_flags(original, translated) == []
    assert 'untranslated_english_message' in t.language_flags(original, original)
    changed = copy.deepcopy(translated)
    changed[1]['content'] = '虚构书名'
    assert 'image_book_title_changed_requires_review' in t.language_flags(original, changed)
    # Similar-looking visual questions must still translate ordinary answers.
    color = copy.deepcopy(original)
    color[0]['content'] = '<image>What color is this book?'
    color[1]['content'] = 'dark red'
    color_out = copy.deepcopy(color)
    color_out[0]['content'] = '<image>这本书是什么颜色？'
    assert 'untranslated_english_message' in t.language_flags(color, color_out)
    # The exception requires the image marker and the exact known task wording.
    no_image = copy.deepcopy(original)
    no_image[0]['content'] = no_image[0]['content'].replace('<image>', '')
    assert 'untranslated_english_message' in t.language_flags(no_image, translated)
    extended = copy.deepcopy(original)
    extended[0]['content'] += ' Explain why the title is appropriate.'
    assert 'untranslated_english_message' in t.language_flags(extended, translated)


if __name__ == '__main__':
    test_book_title_validation()
    print('PASS book-title transcription and ordinary untranslated-answer guards')
