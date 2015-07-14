
import sys
#from os.path import abspath, dirname
import json

from bottle import default_app, request, route, run, static_file, view

from minidelphin import loads_one, nodes, links, AceParser

#cwd = abspath(dirname(__file__))
#staticdir = pjoin(cwd, 'static')
app = default_app()

with open('./demophin.json') as fp:
    app.config.load_dict(json.load(fp))

ace_options = {
    'executable': app.config['demophin.ace.executable'],
    'cmdargs': app.config['demophin.ace.cmdargs']
}

def jsonify_dmrs(x):
    data = {'nodes': [], 'links': []}
    x = loads_one(x)
    for node in nodes(x):
        cfrom, cto = node[3][1] if node[3] is not None else -1, -1
        cvarsort = node[2].get('cvarsort') if node[2] is not None else None
        data['nodes'].append({
            'id': node[0],
            'pred': node[1].short_form(),
            'cfrom': cfrom,
            'cto': cto,
            'cvarsort': cvarsort
        })
    for link in links(x):
        data['links'].append({
            'start': link[0],
            'end': link[1],
            'rargname': link[2] or "",
            'post': link[3]
        })
    return json.dumps(data)


def parse_sentence(sent):
    if not sent:
        return None
    grm = app.config['demophin.grammar']
    with AceParser(grm, **ace_options) as parser:
        result = parser.interact(sent)
    if not result:
        return None
    result['RESULTS'] = [jsonify_dmrs(res['MRS'])
                         for res in result['RESULTS']]
    return result


@route('/', method='GET')
@route('/', method='POST')
@view('main')
def index():
    sent = request.forms.get('sentence')
    result = parse_sentence(sent)
    return {
        'title': app.config['demophin.title'],
        'sentence': sent,
        'result': result
    }


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static')


if __name__ == '__main__':
    run()
