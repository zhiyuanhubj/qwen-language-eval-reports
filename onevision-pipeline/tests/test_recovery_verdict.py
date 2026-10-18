import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean import parse_verdict
from recovery_verdict_parser import parse_recovery_verdict
class RecoveryVerdictTests(unittest.TestCase):
    def setUp(self):
        self.verdict={'fully_correct':False,'grounded':False,'complete':False,'language_clean':False,'high_quality':False,'confidence':0.95,'reason':'explanation with a\ttab'}
        self.raw=json.dumps(self.verdict).replace('\\t','\t')
    def test_preserves_explanation_and_all_scores(self):
        self.assertEqual(parse_recovery_verdict(self.raw,parse_verdict),self.verdict)
        self.assertEqual(parse_recovery_verdict(json.dumps(self.verdict),parse_verdict),self.verdict)
    def test_rejects_malformed_verdicts(self):
        cases=[self.raw+' {}',self.raw.replace('false','"false"',1),self.raw.replace('0.95','1.95'),self.raw.replace('\t','\x00'),self.raw.replace('\t','\x08')]
        for text in cases:
            with self.subTest(text=repr(text)):
                with self.assertRaises((ValueError,TypeError)):
                    parse_recovery_verdict(text,parse_verdict)
if __name__=='__main__':unittest.main()
