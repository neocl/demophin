
var maxWidth = 600,
    height = 300;

var level_dy = 25,  // vertical separation between edges
    edge_radius = 15, // rounded corner radius,
    edge_xoffset = 10, // outgoing edges aren't centered
    node_dx = 20;  // horizontal separation between nodes

var color = d3.scale.category20();

function prepareGraph(graph) {
    var nodeIdx = {}, levelIdx = {};
    graph.nodes.forEach(function(d, i) {
        nodeIdx[d.id] = i;
        levelIdx[[i,i+1].join()] = {}; // eg levelIdx["1,2"] = {}
    });
    graph.links.forEach(function(d) {
        d.target = nodeIdx[d.end];
        // start of 0 is TOP link
        if (d.start == 0) {
            d.dir = 1;  // always on top
            return;
        }
        // the rest only apply to non-TOP links
        d.source = nodeIdx[d.start];
        d.distance = Math.abs(d.source - d.target);
        // Quantifiers and undirected EQ links below preds
        d.dir = (d.rargname == "" || d.post.toUpperCase() == "H") ? -1 : 1            
    });
    graph.maxTopLevel = 0;
    graph.maxBottomLevel = 0;
    for (dist=0; dist<graph.nodes.length; dist++) {
        graph.links.forEach(function(d) {
            if (d.start == 0) return;
            if (dist != d.distance) return;
            d.level = nextAvailableLevel(d.source, d.target, d.dir, levelIdx);
            if (d.dir == 1 && graph.maxTopLevel < d.level) {
                graph.maxTopLevel = d.level;
            } else if (d.dir == -1 && graph.maxBottomLevel > d.level) {
                graph.maxBottomLevel = d.level;
            }
        });
    }
    graph.sticky = false;
}

function nextAvailableLevel(source, target, dir, lvlIdx) {
    var level, curLevel, success;
    if (source > target)
        return nextAvailableLevel(target, source, dir, lvlIdx);
    level = 0;
    curLevel = dir;
    while (level == 0) {
        success = true;
        for (var i = source; i < target; i++) {
            if (curLevel in lvlIdx[[i, i+1].join()]) {
                success = false;
                break;
            }
        }
        if (success) {
            level = curLevel;
            for (var i = source; i < target; i++) {
                lvlIdx[[i, i+1].join()][level] = true;
            }
        } else {
            curLevel += dir;
        }
    }
    return level;
}

function getPathSpec(link, graph) {
    var x1, x2, y1, y2;
    // get these first, they apply for all links
    x2 = graph.nodes[link.target].x;
    y1 = graph.nodes[link.target].bbox.height;
    if (link.start == 0) {
        y2 = y1 + (((link.dir == 1 ? graph.maxTopLevel : graph.maxBottomLevel) + 1) * level_dy);
        link.midpoint = {"x": x2,
                         "y": (y1 + y2) / 2};
        return ["M", x2, y2, "L", x2, y1].join(' ');
    }
    // the following is only for non-TOP links
    x1 = graph.nodes[link.source].x;
    y2 = y1 + (Math.abs(link.level) * level_dy - 5);
    // side-effect! calculate this while we know it
    link.midpoint = {"x": (x1 + x2) / 2,
                     "y": y2};
    if (x1 < x2) {
        x1 += edge_xoffset;
        return ["M", x1, y1 - 5,
                "L", x1, (y2 - edge_radius),
                "Q", x1, y2, (x1 + edge_radius), y2,
                "L", (x2 - edge_radius), y2,
                "Q", x2, y2, x2, y2 - edge_radius,
                "L", x2, y1].join(' ');
    } else {
        x1 -= edge_xoffset;
        return ["M", x1, y1 - 5,
                "L", x1, (y2 - edge_radius),
                "Q", x1, y2, (x1 - edge_radius), y2,
                "L", (x2 + edge_radius), y2,
                "Q", x2, y2, x2, y2 - edge_radius,
                "L", x2, y1].join(' ');
    }
}

function updateHighlights(id) {
    clearHighlights(id);
    d3.select(id).selectAll(".node.selected").each(function(d){
        var labelset = d3.set(),
            outs = d3.set(),
            ins = d3.set(),
            scopes = d3.set();
        d3.select(id).selectAll(".link")
            .classed({
                "out": function(_d) {
                    if (_d.rargname && d.id == _d.start) {
                        outs.add(_d.end);
                        return true;
                    }
                    return false;
                },
                "in": function(_d) {
                    if (_d.rargname && d.id == _d.end) {
                        ins.add(_d.start);
                        return true;
                    }
                    return false;
                },
                "labelset": function(_d) {
                    if (_d.post == "EQ" && (_d.start == d.id || _d.end == d.id)) {
                        labelset.add(_d.start);
                        labelset.add(_d.end);
                        return true;
                    }
                    return false
                },
                "scope": function(_d) {
                    if (_d.start == d.id && (_d.post == "H" || _d.post == "HEQ")) {
                        scopes.add(_d.end);
                        return true;
                    } else if (_d.end == d.id && (_d.post == "H" || _d.post == "HEQ")) {
                        return true;
                    }
                    return false;
                }
            });
        var labelAdded = true;
        while (labelAdded) {
            labelAdded = false;
            d3.select(id).selectAll(".link").each(function(_d) {
                if (_d.post == "EQ") {
                    if (labelset.has(_d.start) && !labelset.has(_d.end)) {
                        labelset.add(_d.end);
                        labelAdded = true;
                    } else if (labelset.has(_d.end) && !labelset.has(_d.start)) {
                        labelset.add(_d.start);
                        labelAdded = true;
                    }
                }
            });
        }
        d3.select(id).selectAll(".node")
            .classed({
                "out": function(_d) { return outs.has(_d.id); },
                "in": function(_d) { return ins.has(_d.id); },
                "labelset": function(_d) { return labelset.has(_d.id); },
                "scope": function(_d) { return scopes.has(_d.id); }
            });

    });
}

function clearHighlights(id) {
    d3.select(id).selectAll(".node").classed(
        {"in": false, "out": false, "labelset": false, "scope": false}
    );
    d3.select(id).selectAll(".link").classed(
        {"in": false, "out": false, "labelset": false, "scope": false}        
    );
}

function toggleSticky(id, node, d) {
    if (d.sticky) {
        d.sticky = false;
        d3.select(node).classed("selected", false);
    } else {
        d3.select(id).selectAll(".node.selected").each(function(_d) {
            _d.sticky = false;
            d3.select(this).classed("selected", false);
        });
        d.sticky = true;
        d3.select(node).classed("selected", true);
    }
    return d.sticky;
}

// // tiny path generator for an orthogonal path
// function pathgen() {
//     var gen = {},
//         x = function(x) { return x; },
//         y = function(y) { return y; };

//     gen.ortho = function(d) {
//         var x1 = x(d.x1),
//             x2 = x(d.x2),
//             height = y(d.height),
//             dir = x1 < x2 ? 1 : -1;
//         return [
//             "M", x1, 0,
//             "v", -(height-10),
//             "q", 0, -10, dir*10, -10,
//             "H", x2 - (dir*10),
//             "q", (dir*10), 0, (dir*10), +10,
//             "V", -2
//         ].join(" ");
//     };

//     gen.xscale = function(a) {
//       if (!arguments.length) return x;
//       x = a;
//       return gen;
//     }

//     gen.yscale = function(a) {
//       if (!arguments.length) return y;
//       y = a;
//       return gen;
//     }

//     return gen;
// }

// function dmrsDisplay(id, graph) {
//   arcd = d3.arcDiagram()
//     .nodeWidth(function(d) { return d.width; })
//     .separation(node_dx)
//     .nodeXOffset(function(d) { return d.width/2; })
//     .nodes(graph.nodes)
//     .links(graph.links);

//   var svg = d3.select(id).append("svg")
//     .append("svg:g");
  
//   var nodes = svg.selectAll(".node")
//       .data(arcd.nodes())
//     .enter().append("svg:g")
//       .attr("class", "node");
//   nodes.append("svg:text")
//     .attr("class", "nodeText")
//     .text(function(d) { return d.pred + d.carg ? "(" + d.carg + ")" : ""; })
//     .each(function(d) { d.width = this.getBBox().width; });

//   arcd(); // node widths are established; calculate the layout
//   // and set the width and height of the SVG
//   d3.select(id)
//     .attr("width", d3.min(maxWidth, d3.max(data.nodes, function(d) { return d.x + d.width + node_dx; })))
//     .attr("height", d3.max(data.links, function(d) { return d.level; }) * level_dy);

//   var xscale = d3.scale.linear();  // we're calculating our own widths, so just do 1-to-1
//   var yscale = d3.scale.linear()
//     .domain([0, d3.max(arcd.links().map(function(l) { return l.height; }))+1])
//     .range([0, upperHeight]);
// }

function dmrsDisplay(svgElem, graph) {
//  d3.json(url, function(error, graph) {
      // calculate source and target for links
      prepareGraph(graph);

      var tip = d3.select("#tooltip")
          .style("opacity", 0);

      var id = svgElem;
      var svg = d3.select(svgElem)
        .attr("height", ((graph.maxTopLevel - graph.maxBottomLevel + 3) * level_dy));
      var g = svg.append("svg:g")
          .attr("transform", "translate(0," + ((graph.maxTopLevel + 2) * level_dy) + ")");
      
      g.append("defs").append("marker")
          .attr("class", "linkend")
          .attr("id", "arrowhead")
          .attr("refX", 1) /*must be smarter way to calculate shift*/
          .attr("refY", 2)
          .attr("markerWidth", 5)
          .attr("markerHeight", 4)
          .attr("orient", "auto")
          .append("path")
              .attr("d", "M0,0 L1,2 L0,4 L5,2 Z"); //this is actual shape for arrowhead

      var x_pos = 10;
      var nodes = g.selectAll(".node").order()
          .data(graph.nodes)
        .enter().append("svg:g")
          .attr("class", "node")
          .each(function(d) {
            var vps = [];
            for (var key in d.varprops) {
              vps.push("<td>" + key + "</td><td>=</td><td>" + d.varprops[key] + "</td>");
            }
            d.tooltipText = "<table><tr>" + vps.join("</tr><tr>") + "</tr></table>";
          });
      nodes.append("svg:text")
          .attr("class", "nodeText")
          .text(function(d) {
            if (d.carg) {
              return d.pred + "(" + d.carg + ")";
            } else {
              return d.pred;
            }
          })
          .attr("x", function(d, i) {
              d.bbox = this.getBBox();
              halfLen = d.bbox.width / 2;
              x = x_pos + halfLen;
              x_pos = x + halfLen + node_dx;
              d.x = x;
              return x;
          })
          .attr("y", function(d) { return 0; })
          .attr("dy", function(d) { return d.bbox.height/5; });
      nodes.insert("svg:rect", "text")
          .attr("class", "nodeBox")
          .attr("x", function(d) { return d.x - (d.bbox.width / 2) - 2; })
          .attr("y", function(d) { return - (d.bbox.height / 2) - 2; })
          .attr("width", function(d) { return d.bbox.width + 4; })
          .attr("height", function(d) { return d.bbox.height + 4; })
          .attr("rx", 4)
          .attr("ry", 4);
      nodes.on("mouseover", function(d) {
              if (!graph.sticky) { d3.select(this).classed("selected", true) };
              updateHighlights(id);
              tip.html(d.tooltipText)
                .style("opacity", 0.8);
          })
          .on("mousemove", function(d) {
              tip.style("left", (d3.event.pageX - 10) + "px")
                .style("top", (d3.event.pageY + 15) + "px");
          })
          .on("mouseout", function(d) {
              if (!d.sticky) { d3.select(this).classed("selected", false); }
              updateHighlights(id);
              tip.style("opacity", 0);
          })
          .on("click", function(d) {
              stickyState = toggleSticky(id, this, d);
              graph.sticky = stickyState;
              updateHighlights(id);
          });

      // not working...
      svg.attr("width", d3.sum(nodes.data(), function(d) { return d.bbox.width + node_dx; }));

      var links = g.selectAll(".link").order()
          .data(graph.links)
        .enter().append("svg:g")
          .attr("class", "link");
      links.append("svg:path")
          .attr("class", function(d) {
              if (d.start == 0) {
                  return "topedge";
              } else if (d.rargname == "" && d.post == "EQ") {
                  return "eqedge";
              } else {
                  return "linkedge";
              }
          })
          .attr("d", function(d) {
              return getPathSpec(d, graph);
          })
          .attr("transform", function(d) {
              return "scale(1," + (d.dir * -1) + ")";
          })
          .style("marker-end", function(d) {
              return (d.rargname == "" && d.post == "EQ") ? "none" : "url(#arrowhead)";
          });
      links.append("svg:text")
          .attr("class", "rargname")
          .attr("x", function(d) { return d.midpoint.x; })
          .attr("y", function(d) { return d.midpoint.y * (-1 * d.dir) - 3; })
          .text(function(d) { return d.rargname + "/" + d.post; } );
//  });
}

function parseSentence(form) {
  d3.select("#parseresults").selectAll(".result").remove();
  d3.json("parse")
    .post(new FormData(form), function(error, data) {
      if (data) {
        // Push history so the URL bar changes when a new sentence is parsed.
        history.pushState(data, document.title, "parse?sentence=" + data.sentence);
        d3.select("#sentence").text('Parse results for "'+data.sentence+'"');
        showParseResults(data.result);
      } else {
        document.getElementById("parseresults").innerHTML = "Server error.";
      }
    });
}

function showParseResults(result) {
  var results = d3.select("#parseresults").selectAll(".result")
      .data(result.RESULTS)
    .enter().append("div")
      .attr("class", "result");
  dmrs = results.append("div")
    .attr("class", "dmrs");
  dmrs.append("svg")
    .attr("id", function(d, i) { return "dmrs" + i; })
    .each(function(d, i) { dmrsDisplay(this, d); });
  dmrs.append("div")
    .attr("class", "realizations")
    .append("a")
      .attr("href", "javascript:void(0)")
      .text('Generate')
      .on("click", function(d) { generateSentences(this.parentElement, d.mrs); });
  d3.select("#parsestatus").text(result.NOTES);
}

function generateSentences(elem, mrs) {
  var reals = d3.select(elem);
  reals.select("a").remove();
  reals.append("p").text("generating...");
  var fd = new FormData();
  fd.append("mrs", mrs);
  d3.json("generate")
    .post(fd, function(error, data) {
      if (data) {
        reals.select("p").remove();
        reals.append("ul").selectAll(".realization")
            .data(data.RESULTS)
          .enter().append("li")
            .attr("class", "realization")
            .text(function(d) {return d;});
      } else {
        reals.append("p")
          .text("No realizations found.")
      }
    });
}