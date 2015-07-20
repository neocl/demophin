
import sys
import os.path
#from os.path import abspath, dirname
import json

from bottle import (
    abort, default_app, request, route, run, static_file, view
)

from minidelphin import loads_one, nodes, links, AceParser, AceGenerator

#cwd = abspath(dirname(__file__))
#staticdir = pjoin(cwd, 'static')
app = default_app()

with open('./demophin.json') as fp:
    app.config.load_dict(json.load(fp))

ace_options = {
    'executable': app.config['demophin.ace.executable'],
    'cmdargs': app.config['demophin.ace.cmdargs']
}


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static')


@route('/')
@view('main')
def index():
    data = {'title': app.config['demophin.title'], 'errors': []}
    if not os.path.exists(app.config['demophin.grammar']):
        data['errors'].append('Grammar not available.')
    return data


@route('/parse', method='POST')
def parse():
    sent = request.forms.get('sentence')
    result = parse_sentence(sent)
    return {
        'sentence': sent,
        'result': result
    }


def parse_sentence(sent):
    if not sent:
        return None
    grm = app.config['demophin.grammar']
    with AceParser(grm, **ace_options) as parser:
        result = parser.interact(sent)
    if not result:
        return None
    result['RESULTS'] = [d3ify_dmrs(res['MRS'])
                         for res in result['RESULTS']]
    return result


def d3ify_dmrs(x):
    data = {'nodes': [], 'links': [], 'mrs': x}
    x = loads_one(x)
    nodeidx = {0: 0}
    for i, node in enumerate(nodes(x)):
        cfrom, cto = node[3][1] if node[3] is not None else -1, -1
        cvarsort = node[2].get('cvarsort') if node[2] is not None else None
        carg = node[6] if len(node) >= 7 else None

        data['nodes'].append({
            'id': node[0],
            'pred': node[1].short_form(),
            'cfrom': cfrom,
            'cto': cto,
            'cvarsort': cvarsort,
            'carg': carg
        })
        nodeidx[node[0]] = i+1
    for link in links(x):
        data['links'].append({
            'source': nodeidx[link[0]],
            'target': nodeidx[link[1]],
            'start': link[0],
            'end': link[1],
            'rargname': link[2] or "",
            'post': link[3]
        })
    return data


@route('/generate', method='POST')
def generate():
    mrs = request.forms.get('mrs')
    return generate_sentences(mrs)


def generate_sentences(mrs):
    if not mrs:
        return None
    grm = app.config['demophin.grammar']
    with AceGenerator(grm, **ace_options) as generator:
        return generator.interact(mrs)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        app.config['demophin.grammar'] = sys.argv[1]
    run()
