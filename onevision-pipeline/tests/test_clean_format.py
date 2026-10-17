"""Offline checks for actual input and verdict boundaries, not model accuracy."""
import asyncio
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clean
from PIL import Image


class FormatChecks(unittest.TestCase):
    def row(self, user='Question', answer='Answer', images=None):
        return {'messages': [{'role': 'user', 'content': user},
                             {'role': 'assistant', 'content': answer}],
                'images': images or []}

    def verdict(self):
        return {**dict.fromkeys(clean.FLAGS, True), 'confidence': .01,
                'reason': 'Evidence checked'}

    def test_missing_roles(self):
        for role, reason in [('user', 'missing_assistant_answer'),
                             ('assistant', 'missing_user_request')]:
            with self.assertRaisesRegex(ValueError, reason):
                clean.prepare({'messages': [{'role': role, 'content': 'x'}]}, Path('x'))

    def test_image_checks(self):
        with self.assertRaisesRegex(ValueError, 'image_placeholder_count_mismatch'):
            clean.prepare(self.row('<image>'), Path('x'))
        with self.assertRaisesRegex(ValueError, 'corrupt_image'):
            clean.prepare(self.row('<image>', images=[{'bytes': b'not an image'}]), Path('x'))
        buf = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buf, format='PNG')
        row = self.row('<image>', images=[{'bytes': buf.getvalue()}])
        content = clean.prepare(row, Path('x'))
        self.assertTrue(content[-1]['image_url']['url'].startswith('data:image/png;base64,'))

    def test_review_conditions(self):
        cases = [(self.row('<video>'), 'unsupported_media'),
                 (self.row('x' * 70001), 'context_requires_larger_server'),
                 (self.row('<image>' * 9, images=[{}] * 9), 'image_count_requires_larger_server'),
                 (self.row('<image>', images=[{}]), 'image_bytes_unavailable')]
        for row, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(LookupError, reason):
                clean.prepare(row, Path('x'))

    def test_empty_text_is_not_a_hard_filter(self):
        # Document the present limitation; do not claim role presence proves content.
        self.assertTrue(clean.prepare(self.row('', ''), Path('x')))

    def test_verdict_schema(self):
        v = self.verdict()
        self.assertTrue(clean.accepted(clean.parse_verdict(json.dumps(v))))
        self.assertEqual(clean.parse_verdict('```json\n' + json.dumps(v) + '\n```'), v)
        bad = [{**v, 'grounded': 1}, {**v, 'extra': 1},
               {**v, 'confidence': 1.1}, {**v, 'reason': ' '},
               {k: value for k, value in v.items() if k != 'complete'}]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                clean.parse_verdict(json.dumps(item))
        with self.assertRaises(ValueError):
            clean.parse_verdict(json.dumps(v) + '\nextra text')

    def test_disagreement_is_not_automatic_keep(self):
        yes = self.verdict()
        no = {**yes, 'grounded': False}
        async def third():
            return no
        status, _ = asyncio.run(clean.resolve_reviews(no, yes, third))
        self.assertEqual(status, 'review')


if __name__ == '__main__':
    unittest.main()
