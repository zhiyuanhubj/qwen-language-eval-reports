import copy
from translate import language_flags
def pair(question,answer='Left.'):
 return [{'role':'user','content':question},{'role':'assistant','content':answer}]
s=pair('<image> What is the label of the second bar from the left in each group?')
t=pair('<image> 每组中从左数第二根柱子的标签是什么？','Left。')
assert not language_flags(s,t)
u=copy.deepcopy(t);u[1]['content']='左。'
assert 'image_chart_label_changed_requires_review' in language_flags(s,u)
assert 'untranslated_english_message' in language_flags(s,s)
s=pair('<image> Which direction does the arrow point?');t=pair('<image> 箭头指向哪个方向？','Left。')
assert 'untranslated_english_message' in language_flags(s,t)
s=pair('What is the label of the second bar from the left in each group?')
assert 'untranslated_english_message' in language_flags(s,t)
print('PASS: synthetic regression, literal label, changed label review, untranslated question, ordinary direction, image requirement')
