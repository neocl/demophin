
import sys
from delphin.interfaces import ace
from flask import Flask, render_template, request
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired

app = Flask(__name__)
parser = None

class ActionForm(Form):
    sentence = StringField('sentence', validators=[DataRequired()])

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ActionForm()
    if request.method == 'POST' and parser is not None:
        sent = request.form['sentence']
        result = parser.interact(sent)
    else:
        result = None
    return render_template('base.html', form=form, result=result)

if __name__ == '__main__':
    app.secret_key = '\xa0k\xbd\xab\x16\xd7\xa6\x97\ri\xc1\xb2\x1e\xee\xb2\x06\xcc\x8e\xc8\xe6\xf4%\x17\xa6'
    with ace.AceParser(sys.argv[1]) as parser:
        app.run(debug=True)
