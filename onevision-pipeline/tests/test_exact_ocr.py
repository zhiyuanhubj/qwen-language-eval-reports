import copy
from translate import language_flags, is_exact_ocr_task
q='<image>\nWhat is written in the image? Answer this question using the text in the image directly.'
a=[{'role':'user','content':q},{'role':'assistant','content':'WWW.POPULARONLINE.COM.MY'}]
b=copy.deepcopy(a);b[0]['content']='<image>\n图片中写了什么？请直接使用图片中的文字回答。'
assert is_exact_ocr_task(a)
assert not language_flags(a,b)
assert 'untranslated_english_message' in language_flags(a,a)
c=copy.deepcopy(b);c[1]['content']='大众在线网站'
assert 'ocr_literal_answer_changed_requires_review' in language_flags(a,c)
for question in [q+' Translate it.',q.replace('<image>\n',''),'<image>\nWhat color is the car?']:
 c=copy.deepcopy(a);c[0]['content']=question
 assert not is_exact_ocr_task(c)
assert not is_exact_ocr_task(a+a)
print('PASS: literal OCR preserved, translated question required, changed answer rejected, unrelated tasks excluded')
