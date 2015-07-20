<!DOCTYPE HTML>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="static/dmrs.css"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.6/d3.min.js" charset="utf-8"></script>
  <!-- if no access to internet, back off to local version -->
  <script>window.d3 || document.write('<script src="static/d3.min.js">\x3C/script>')</script>
  <script src="static/d3.arcdiagram.js"></script>
  <script src="static/dmrs.js"></script>
  <title>{{title}}</title>
</head>
<body style="background-color: #DDD">
  % if errors:
      <p class="error">Could not run Demophin with the given settings due to the
        following errors:</p>
      <ul>
      % for error in errors:
        <li class="error">{{error}}</li>
      % end
      </ul>
  % else:
    <div style="text-align: center">
      <form id="parseform" action="parse" onsubmit="parseSentence(this); return false;">
        <input id="sentenceinput" type="text" name="sentence" placeholder="Enter a sentence" style="width: 500px;" />
        <input type="submit" value="Parse">
      </form>
    </div>
  % end
  <div id="sentence" class="sentence"></div>
  <div id="parseresults"></div>
  <div id="parsestatus" class="status"></div>
</body>
</html>
