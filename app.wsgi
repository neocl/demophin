
import sys, os

# Add the path on the server to the demophin installation
# sys.path.insert(0, '')

# Change working directory so relative paths (and template lookup) work again
os.chdir(os.path.dirname(__file__))

# ... build or import your bottle application here ...
import demophin

# Do NOT use bottle.run() with mod_wsgi
application = demophin.app
