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
  <div class="header">{{header}}</div>
  <div style="text-align: center">
    <form id="parseform" onsubmit="parseSentence(this); return false;">
      <input id="sentenceinput" type="text" name="sentence" placeholder="Enter a sentence" style="width: 500px;" />
      <input type="submit" value="Parse">
    </form>
  </div>
  <div id="sentence" class="sentence"></div>
  <div id="parseresults"></div>
  <div id="parsestatus" class="status"></div>
  % if query:
    <script>
      document.getElementById("sentenceinput").value = "{{query}}";
      parseSentence(document.getElementById("parseform"));
    </script>
  % end

</body>
</html>
