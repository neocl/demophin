
import sys
import json
from delphin.mrs import simplemrs
from delphin.interfaces import ace
from flask import Flask, render_template, request
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired

app = Flask(__name__)
parser = None

class ActionForm(Form):
    sentence = StringField('sentence', validators=[DataRequired()])

def jsonify_dmrs(x):
    data = {'nodes': [], 'links': []}
    x = simplemrs.loads_one(x)
    for node in x.nodes:
        data['nodes'].append({
            'id': node.nodeid,
            'pred': node.pred.short_form(),
            'cfrom': node.cfrom,
            'cto': node.cto,
            'cvarsort': node.cvarsort
        })
    for link in x.links:
        data['links'].append({
            'start': link.start,
            'end': link.end,
            'rargname': link.argname or "",
            'post': link.post
        })
    return json.dumps(data)

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ActionForm()
    if request.method == 'POST' and parser is not None:
        sent = request.form['sentence']
        result = parser.interact(sent)
        result['RESULTS'] = [jsonify_dmrs(res['MRS'])
                             for res in result['RESULTS']]
    else:
        result = None
    return render_template('base.html', form=form, result=result)

if __name__ == '__main__':
    app.secret_key = '\xa0k\xbd\xab\x16\xd7\xa6\x97\ri\xc1\xb2\x1e\xee\xb2\x06\xcc\x8e\xc8\xe6\xf4%\x17\xa6'
    with ace.AceParser(sys.argv[1], cmdargs=['-n', '5']) as parser:
        app.run(port=5050, debug=True)
