import copy
from translate import language_flags,is_exact_formula_task
q='<image>\nPlease write out the expression of the formula in the image using LaTeX format.'
a=[{'role':'user','content':q},{'role':'assistant','content':r'( B _ { E } ) ^ { j }'}]
b=copy.deepcopy(a);b[0]['content']='<image>\n请用LaTeX格式写出图片中公式的表达式。'
assert is_exact_formula_task(a)
assert not language_flags(a,b)
assert 'untranslated_english_message' in language_flags(a,a)
c=copy.deepcopy(b);c[1]['content']='不同的公式'
assert 'formula_answer_changed_requires_review' in language_flags(a,c)
c=copy.deepcopy(a);c[0]['content']=q+' Explain your answer.'
assert not is_exact_formula_task(c)
assert not is_exact_formula_task(a+a)
c=copy.deepcopy(a);c[0]['content']=q.replace('<image>\n','')
assert not is_exact_formula_task(c)
print('PASS: exact task, faithful formula, changed formula review, untranslated question, extra instruction, extra turns, missing image')
