
import sys
import os
import json

from bottle import (
    abort, error, default_app, redirect, request, route, run, static_file, view
)

from minidelphin import loads_one, nodes, links, AceParser, AceGenerator

app = default_app()

cwd = os.path.abspath(os.path.dirname(__file__))
#staticdir = pjoin(cwd, 'static')
with open(os.path.join(cwd, 'demophin.json')) as fp:
    app.config.load_dict(json.load(fp))

ace_env = dict(os.environ)
ace_env['LANG'] = 'en_US.UTF-8'  # change as necessary
ace_options = {
    'executable': app.config.get('demophin.ace.executable', 'ace'),
    'cmdargs': app.config.get('demophin.ace.cmdargs', []),
    'env': ace_env
}

grammars = {}
for gramdata in app.config['demophin.grammars']:
    grammars[gramdata['name'].lower()] = gramdata


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=os.path.join(cwd, 'static'))


@route('/')
@view('index')
def index():
    return {
        'title': app.config['demophin.title'],
        'grammars': grammars
    }


@route('/<grmkey>')
def bare_grmkey(grmkey):
    redirect('%s/' % grmkey)


@route('/<grmkey>/')
@route('/<grmkey>/parse')
@view('main')
def main(grmkey):
    grm = get_grammar(grmkey)
    sent = request.query.get('sentence')
    n = request.query.get('n', 5)
    return {
        'title': '%s | %s' % (grm['name'], app.config['demophin.title']),
        'grammar': grm,
        'query': '' if sent is None else sent,
        'nresults': n
    }


@route('/<grmkey>/parse', method='POST')
def parse(grmkey):
    grm = get_grammar(grmkey)
    sent = request.forms.get('sentence')
    n = request.forms.get('nresults', 5)
    result = parse_sentence(grm, sent, n=n)
    return {
        'sentence': '' if sent is None else sent,
        'nresults': n,
        'result': result
    }


def get_grammar(grmkey):
    grmkey = grmkey.lower()  # normalize key
    if grmkey not in grammars:
        abort(404, 'No grammar is specified for "%s".' % grmkey)
    grm = grammars.get(grmkey)
    if not os.path.exists(grm.get('path')):
        abort(404, 'The grammar could not be found.')
    return grm


def parse_sentence(grm, sent, n=None):
    if not sent:
        return None
    # update cmdargs as necessary
    opts = dict(ace_options)
    if n is not None:
        opts['cmdargs'] = opts['cmdargs'] + ['-n', str(n)]
    # now try to get a parse
    with AceParser(grm['path'], **opts) as parser:
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
        cfrom, cto = node[3][1] if node[3] is not None else (-1, -1)
        cvarsort = node[2].get('cvarsort') if node[2] is not None else None
        varprops = x.properties(node[0])
        carg = node[6] if len(node) >= 7 else None

        data['nodes'].append({
            'id': node[0],
            'pred': node[1].short_form(),
            'cfrom': cfrom,
            'cto': cto,
            'cvarsort': cvarsort,
            'carg': carg,
            'varprops': varprops
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


@route('/<grmkey>/generate', method='POST')
def generate(grmkey):
    grm = get_grammar(grmkey)
    mrs = request.forms.get('mrs')
    return generate_sentences(grm, mrs)


def generate_sentences(grm, mrs):
    if not mrs:
        return None
    with AceGenerator(grm['path'], **ace_options) as generator:
        return generator.interact(mrs)

@error(404)
@view('error404')
def error404(error):
    return {'error': error.body}


if __name__ == '__main__':
    if len(sys.argv) > 1:
        app.config['demophin.grammars'] = [{
            "name": os.path.basename(sys.argv[1]),
            "path": sys.argv[1]
        }]
        grammars = {}
        for gramdata in app.config['demophin.grammars']:
            grammars[gramdata['name'].lower()] = gramdata

    run()
