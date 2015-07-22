
% if defined('grammars'):
  <p>Please select a grammar from the list below:</p>
  <ui>
  % for i, grmitem in enumerate(grammars.items()):
    % key, grm = grmitem
    % name, desc = grm['name'], grm.get('description')
    <li><a href="{{key}}">
      <strong>{{name}}</strong>
      % if desc:
      : {{desc}}
      % end
      </a></li>
  % end
  </ui>
% else:
  <p>No grammars are available.</p>
% end
