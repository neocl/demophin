<!DOCTYPE HTML>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="/static/dmrs.css"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.6/d3.min.js" charset="utf-8"></script>
  <!-- if no access to internet, back off to local version -->
  <script>window.d3 || document.write('<script src="/static/d3.min.js">\x3C/script>')</script>
  <script src="/static/dmrs.js"></script>
  <title>{{title}}</title>
</head>
<body style="background-color: #DDD">
  <div class="header controls">
    <form id="parseform" onsubmit="parseSentence(this); return false;">
      <input id="sentenceinput" type="text" name="sentence" placeholder="Enter a sentence" style="width: 500px;" />
      <input id="parsesubmit" type="submit" value="Parse"/>
      <input id="nresultsinput" type="number" name="nresults" value="{{ nresults }}" style="width:3em;"/> results
      <br/>
      <!--output:
       <input id="outputcheckbox" type="checkbox" name="output" value="dmrs" checked>dmrs</input>
       <input id="outputcheckbox" type="checkbox" name="output" value="tree">tree</input> -->
    </form>
    <div id="sentence" class="sentence"></div>
  </div>
  <div id="parseresults" class="body results">
    <div style="text-align: center; font-size: larger; font-weight: bold;">
      % if 'description' in grammar:
        {{ grammar['description'] }}
      % else:
        {{ grammar['name'] }}
      % end
      <br/>
      Enter a sentence above to parse using this grammar.
    </div>
  </div>
  <div id="tooltip" class="tooltip"></div>
  <div id="parsestatus" class="footer status"></div>
  % if query:
    <script>
      document.getElementById("sentenceinput").value = "{{query}}";
      parseSentence(document.getElementById("parseform"));
    </script>
  % end

</body>
</html>
