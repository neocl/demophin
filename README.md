Demophin
========

A DELPH-IN Web Demo

## Quick Start

Ensure [ACE][] is installed and available on PATH; e.g., on Linux, add
the following to your `.bashrc` file:

```
export PATH=/path/to/ace:"$PATH"
```


Clone this repository:

```bash
$ git clone https://github.com/goodmami/demophin.git
```

Get the ERG image (from the [ACE][] website) and move it to the demophin
directory as `erg.dat`. E.g., something like this (using the URL
appropriate for your installed version of ACE):

```bash
$ wget -O - http://sweaglesw.org/linguistics/ace/download/erg-1214-x86-64-0.9.22.dat.bz2 | bunzip2 > demophin/erg.dat
```

Run Demophin locally:

```bash
$ cd demophin
$ python demophin.py
```

Visit <http://127.0.0.1:8080/>

## Requirements

Demophin depends on several pieces of software:

* [Bottle][] (included)
* [pyDelphin][] (included as `minidelphin.py`)
* [ACE][]

In addition, Demophin requires a grammar file compiled with [ACE][].

## Configuration

The file `demophin.json` is used to add grammars and configure ACE. If
ACE is downloaded but not on PATH, the path to the ACE executable can
be given at `demophin.ace.executable`. For example:

```json
{
    "demophin": {
        ...
        "ace": {
            "executable": "/opt/ace-0.9.20/ace"
        }
    }
}
```

Additional grammars can be configured at `demophin.grammars`:

```json
{
    "demophin": {
        "grammars": [
            ...,
            {
                "name": "Jacy",
                "path": "/home/goodmami/repos/jacy/jacy.dat",
                "description": "The Jacy Japanese Grammar"
            },
            ...
        ]
    }
}
```

The `name` field should be short and contain no spaces as it is used in
the URL scheme (e.g. `.../demophin/jacy/`).

## Compatibility

Demophin is tested on Linux but should also work on Mac. Windows is not
supported because ACE does not run on Windows. Python versions 2.7 and
3.3+ should all work.

[Bottle]: bottlepy.org
[pyDelphin]: https://github.com/goodmami/pydelphin
[ACE]: http://sweaglesw.org/linguistics/ace/
