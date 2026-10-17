"""Code-only answers can inherit Python context from earlier fenced code."""
import copy
import translate as t


def test_python_context():
    messages = [
        {'role': 'user', 'content': 'Filter the numbers.'},
        {'role': 'assistant', 'content': 'Here is the code:\n```python\nx = [1, 2]\n```'},
        {'role': 'user', 'content': 'Now sort them.'},
        {'role': 'assistant', 'content': 'result = sorted(x)\nprint(result)'},
    ]
    assert t.is_python_answer(messages, messages[-1])
    assert not t.is_python_answer(messages, messages[1])
    translated = copy.deepcopy(messages)
    translated[0]['content'] = '筛选数字。'
    translated[1]['content'] = '代码如下：\n```python\nx = [1, 2]\n```'
    translated[2]['content'] = '现在将它们排序。'
    assert t.language_flags(messages, translated) == []
    changed = copy.deepcopy(translated)
    changed[-1]['content'] = 'result = sorted(x, reverse=True)'
    assert 'python_code_changed_requires_review' in t.language_flags(messages, changed)
    prose = {'role': 'assistant', 'content': 'The result is sorted in ascending order.'}
    assert not t.is_python_answer(messages, prose)
    plain_context = copy.deepcopy(messages)
    plain_context[1]['content'] = 'A Python programmer can help.'
    assert not t.is_python_answer(plain_context, plain_context[-1])


if __name__ == '__main__':
    test_python_context()
    print('PASS inherited Python context, exact code preservation, prose rejection')
