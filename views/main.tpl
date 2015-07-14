<!DOCTYPE HTML>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="static/dmrs.css"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.6/d3.min.js" charset="utf-8"></script>
  <script src="static/d3.arcdiagram.js"></script>
  <script src="static/dmrs.js"></script>
  <title>{{title}}</title>
</head>
<body>
  <form method="POST" action="/">
    Sentence: <input type="text" name="sentence" value="{{sentence}}" />
    <input type="submit" value="Parse">
  </form>
  % if result is not None:
    % for i, res in enumerate(result.get('RESULTS', [])):
    <div id="dmrs{{i}}"></div>
    % end
    % for i, res in enumerate(result.get('RESULTS', [])):
    <script>
        dmrsDisplay("#dmrs{{i}}", JSON.parse('{{!res}}'));
    </script>
    % end
  % end
</body>
</html>
