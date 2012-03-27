var w = 940,
    h = 500;
    //color = d3.scale.category20c();

function color(sev) {
    if (sev == "critical") {
      return "red";
    } else if (sev == "major") {
      return "orange";
    } else if (sev == "minor") {
      return "yellow";
    } else if (sev == "warning") {
      return "dodgerblue";
    } else {
      return "lime";
    }
}

var tooltip = d3.select("body")
	.append("div")
	.attr("class", "tooltip")
	.style("visibility", "hidden")
	.text("Tooltip");

var treemap = d3.layout.treemap()
    .size([w, h])
    .sticky(true)
    .value(function(d) { return d.size; });

var div = d3.select("#chart").append("div")
    .style("position", "relative")
    .style("width", w + "px")
    .style("height", h + "px");

// d3.json("./treemap.json", function(json) {
// d3.json("http://devmonsvr01.gudev.gnl/alerta/api/v1/alert-treemap.py?environment=PROD", function(json) {
d3.json("http://monitoring.gudev.gnl/alerta/api/v1/alert-treemap.py", function(json) {
  div.data([json.response.treemap]).selectAll("div")
      .data(treemap.nodes)
    .enter().append("div")
      .attr("class", "cell")
      .style("background-color", function(d) { return color(d.name); })
      .call(cell)
//      .text(function(d) { return d.children ? null : d.description; });
      .text(function(d) { return d.children ? null : d.description; })
      .on("mouseover", function(d){
	  	tooltip.text(d.children ? null : d.name + ": " + d.size)
	  	tooltip.style("visibility", "visible");
	    })
	  .on("mousemove", function(){return tooltip.style("top", (event.pageY-10)+"px").style("left",(event.pageX+10)+"px");})
	  .on("mouseout", function(){tooltip.style("visibility", "hidden");});

  d3.select("#size").on("click", function() {
    div.selectAll("div")
        .data(treemap.value(function(d) { return d.size; }))
        .transition()
        .duration(1500)
        .call(cell);

    d3.select("#size").classed("active", true);
    d3.select("#count").classed("active", false);
  });

  d3.select("#count").on("click", function() {
    div.selectAll("div")
        .data(treemap.value(function(d) {
           if (d.name == 'normal') {
             return 0;
           } else {
             return d.size
          }}))
        .transition()
        .duration(1500)
        .call(cell);

    d3.select("#size").classed("active", false);
    d3.select("#count").classed("active", true);
  });
});

function cell() {
  this
      .style("left", function(d) { return d.x + "px"; })
      .style("top", function(d) { return d.y + "px"; })
      .style("width", function(d) { return Math.max(0, d.dx - 1) + "px"; })
      .style("height", function(d) { return Math.max(0, d.dy - 1) + "px"; });
}
