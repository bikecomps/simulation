var res;
var data_for_maps;

function save_trans() {
    $("#load_stats").animate({right: "-100px"});
    $("#save_stats").html('Save')
        .animate({width: "40px", left: "165px"})
        .attr('onclick', 'save_results()');
    $("#stats_namer").animate({left: "0px"});
}

function save_results() {
    var stats_name = $("#stats_namer").val();
    sessionStorage[stats_name] = res;
    var opt = document.createElement('option');
    opt.innerHTML = stats_name;
    $("#stats_picker").append(opt);
    $("#stats_namer").animate({left: "-165px"});
    $("#save_stats").animate({width: "100px", left: "0px"}, function() {$(this).html('Save Results')})
        .attr('onclick', 'save_trans()');
    $("#load_stats").animate({right: "0px"});
}

function load_trans() {
    $("#save_stats").animate({top: '35px'});
    $("#load_stats").html('Load')
        .animate({width: '40px'})
        .attr('onclick', 'load_results()');
    $("#stats_picker").animate({left: '0px'});
}

function load_results() {
    var stats_name = $("#stats_picker").val();
    var desired_package = sessionStorage[stats_name];
    var desired_unpacked = desired_package.split('!?!');
    var desired = desired_unpacked[0];
    var from = desired_unpacked[1];
    var to = desired_unpacked[2];
    displaySummaryStats(JSON.parse(desired),from,to);
    $("#stats_name").html(stats_name);
    $("#load_stats").animate({width: '100px'}, function() {$(this).html('Load Results')})
        .attr('onclick', 'load_trans()');
    $("#stats_picker").animate({left: '-165px'});
    $("#save_stats").animate({top: '0px'});
}

function sliderSetup() {
	$( "#slider-range" ).slider({
		range: true,
		min: 0,
		max: 24,
		values: [ 0, 24 ],
		slide: function( event, ui ) {
			$( "#amount" ).val( ui.values[ 0 ] + ":00 - " + ui.values[ 1 ] + ":00");
			console.log("VALUES HERE: " + ui.values[0] + " and " + ui.values[1]);
		}
	});
	$( "#amount" ).val( $( "#slider-range" ).slider( "values", 0 ) + ":00 - " + $( "#slider-range" ).slider( "values", 1 ) + ":00");
}

function toHours(d)  {
	console.log(d);
	var hours = parseInt(d/3600) % 24;
	var minutes = parseInt(d/60) % 60;
	var result = (hours > 0 ? hours + " hours " : "") + (minutes > 0? minutes : "0") + " minutes";
	return result;
}

function formatDate(dateStr) {
	return (new Date(dateStr)).dateFormat("Y-m-d H:i");
}

function groupBarPlot(htmlIdName, data) {
	var margin = {top: 20, right: 20, bottom: 30, left: 40},
		width = 878, // 800 - margin.left - margin.right,
		height = 500 - margin.top - margin.bottom;
	
	var x0 = d3.scale.ordinal()
			.rangeRoundBands([0, width], .1);
	
	var x1 = d3.scale.ordinal();
	
	var y = d3.scale.linear()
			.range([height, 0]);
	
	var color = d3.scale.ordinal()
			.range(["#6b486b", "#ff8c00"]);
	
	var xAxis = d3.svg.axis()
			.scale(x0)
			.orient("bottom");
	
	var yAxis = d3.svg.axis()
			.scale(y)
			.orient("left")
			.tickFormat(d3.format(".2s"));

	var div = $("#" + htmlIdName + " div");
	div.empty();
	var svg = d3.select(div[0]).append("svg")
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
			.append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	
	var labelNames = ["Number of Departures", "Number of Arrivals"];
	
	data.forEach(function(d) {
		d.ages = labelNames.map(function(name) { return {name: name, value: +d[name]}; });
	});
	
	x0.domain(data.map(function(d) { return d.Hour; }));
	x1.domain(labelNames).rangeRoundBands([0, x0.rangeBand()]);
	y.domain([0, d3.max(data, function(d) { return d3.max(d.ages, function(d) { return d.value; }); })]);
	
        svg.append("g")
		.attr("class", "x axis")
		.attr("transform", "translate(0," + height + ")")
		.call(xAxis);
	
	svg.append("g")
		.attr("class", "y axis")
		.call(yAxis)
		.append("text")
		.attr("transform", "rotate(-90)")
		.attr("y", 6)
		.attr("dy", ".71em")
		.style("text-anchor", "end")
		.text("Frequency");
	
	var hour = svg.selectAll(".hour")
			.data(data)
			.enter().append("g")
			.attr("class", "g")
			.attr("transform", function(d) { return "translate(" + x0(d.Hour) + ",0)"; });
	
	hour.selectAll("rect")
		.data(function(d) { return d.ages; })
		.enter().append("rect")
		.attr("width", x1.rangeBand())
		.attr("x", function(d) { return x1(d.name); })
		.attr("y", function(d) { return y(d.value); })
		.attr("height", function(d) { return height - y(d.value); })
		.style("fill", function(d) { return color(d.name); });
	
	var legend = svg.selectAll(".legend")
			.data(labelNames.slice().reverse())
			.enter().append("g")
			.attr("class", "legend")
			.attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });
	
	legend.append("rect")
		.attr("x", width - 18)
		.attr("width", 18)
		.attr("height", 18)
		.style("fill", color);
	
	legend.append("text")
		.attr("x", width - 24)
		.attr("y", 9)
		.attr("dy", ".35em")
		.style("text-anchor", "end")
		.text(function(d) { return d; });
}

function wrapLabel(labels) {
	for (var i = 0; i < labels.length; i++) {
		if (labels[i].length > 30) {
			labels[i] = labels[i].substring(0,29) + "...";
		}
	}
	return labels;
}

function nonGroupBarPlot(htmlIdName, labels, counts) {
	var chart,
        width = 500, //750,
	bar_height = 20,
	height = bar_height * labels.length,
	x, y, yRangeBand,
	left_width = 250,
	gap = 2,
	extra_width = 100;
	
	x = d3.scale.linear()
		.domain([0, d3.max(counts)])
		.range([0, width]);
	
	yRangeBand = bar_height + 2 * gap;
	y = function(i) { return yRangeBand * i; };

	var div = $("#" + htmlIdName + " div");
	div.empty();
	chart = d3.select(div[0])
		.append('svg')
		.attr('class', 'chart')
		.attr('width', 878) // left_width + width + 40 + extra_width)
		.attr('height', (bar_height + gap * 2) * (labels.length + 1))
		.append("g")
		.attr("transform", "translate(10, 10)");
	
	chart.selectAll("line")
		.data(x.ticks(d3.max(counts)))
		.enter().append("line")
		.attr("x1", function(d) { return x(d) + left_width; })
		.attr("x2", function(d) { return x(d) + left_width; })
		.attr("y1", 0)
		.attr("y2", (bar_height + gap * 2) * labels.length);
	
	chart.selectAll("rect")
		.data(counts)
		.enter().append("rect")
		.attr("x", left_width)
		.attr("y", function(d, i) { return y(i) + gap; })
		.attr("width", x)
		.attr("height", bar_height);
	
	chart.selectAll("text.score")
		.data(counts)
		.enter().append("text")
		.attr("x", function(d) { return x(d) + left_width + 17; })
		.attr("y", function(d, i){ return y(i) + yRangeBand/2; } )
		.attr("dx", -5)
		.attr("dy", ".36em")
		.attr("text-anchor", "start")
		.attr('class', 'score')
		.text(String);
	
	chart.selectAll("text.name")
		.data(wrapLabel(labels))
		.enter().append("text")
		.attr("x", 0)
		.attr("y", function(d, i){ return y(i) + yRangeBand/2; } )
		.attr("dy", ".36em")
		.attr("text-anchor", "start")
		.attr('class', 'name')
		.text(String);
}

function plotKeysVals(htmlIdName, map) {
	sortedMap = [];
	for (var key in map) {
		sortedMap.push([key, map[key]]);
		console.log(sortedMap[key]);
	}
	sortedMap.sort(function(a,b){return b[1]-a[1];});
	var names = new Array();
	var counts = new Array();
	for (var i = 0; i < sortedMap.length; i++) {
		names.push(sortedMap[i][0]);
		counts.push(sortedMap[i][1]);
	}
	nonGroupBarPlot(htmlIdName, names, counts);
}

function displaySummaryStats(data, from, to, comp) {
	var comps = '';
	if (comp != undefined) {comps = 'comp_';}
	// set 'total_num_trips', 'total_num_disappointments',
	// 'avg_trip_time', and 'std_trip_time' 
	$("#" + comps + "total_num_trips").text(data["total_num_trips"]);
	$("#" + comps + "total_num_disappointments").text(data["total_num_disappointments"]);
	console.log(data["avg_trip_time"]);
	$("#" + comps + "avg_trip_time").text(toHours(data["avg_trip_time"]));
	$("#" + comps + "std_trip_time").text(toHours(data["std_trip_time"]));

        var value;
        // set Accuracy based on manhattan distance and euclidean distance
        value = data["man_dist_score_arr"].toFixed(2) + "%";
        $("#" + comps + "man_dist_score_arr").html(value);

        value = data["man_dist_score_dep"].toFixed(2) + "%";
        $("#" + comps + "man_dist_score_dep").html(value);

        value = data["eucl_dist_score"].toFixed(2) + "%";
        $("#" + comps + "eucl_dist_score").html(value);

	// set 'total_num_trips', 'total_num_disappointments',
	// 'avg_trip_time', and 'std_trip_time' 
	$("#" + comps + "total_num_empty_disappointments").text(data["total_num_empty_disappointments"]);
	$("#" + comps + "total_num_full_disappointments").text(data["total_num_full_disappointments"]);
	$("#" + comps + "most_disappointing_dep_station").text(data["most_disappointing_dep_station"]);
	$("#" + comps + "most_disappointing_arr_station").text(data["most_disappointing_arr_station"]);


	// set 'min_duration_trip' 
	var minTrip = data["min_duration_trip"];
	var minTripHtml = $("#" + comps + "min_duration_trip");
	minTripHtml.find(".start_station_name")
		.text(minTrip["start_station_name"]);
	minTripHtml.find(".end_station_name")
		.text(minTrip["end_station_name"]);
	minTripHtml.find(".duration")
		.text(toHours(minTrip["duration"]));
	minTripHtml.find(".start_datetime")
		.text(formatDate(minTrip["start_datetime"]));
	minTripHtml.find(".end_datetime")
		.text(formatDate(minTrip["end_datetime"]));

	// set 'max_duration_trip' 
	var maxTrip = data["max_duration_trip"];
	var maxTripHtml = $("#" + comps + "max_duration_trip");
	maxTripHtml.find(".start_station_name")
		.text(maxTrip["start_station_name"]);
	maxTripHtml.find(".end_station_name")
		.text(maxTrip["end_station_name"]);
	maxTripHtml.find(".duration")
		.text(toHours(maxTrip["duration"]));
	maxTripHtml.find(".start_datetime")
		.text(formatDate(maxTrip["start_datetime"]));
	maxTripHtml.find(".end_datetime")
		.text(formatDate(maxTrip["end_datetime"]));

	// plot 'num_arrivals_per_station'
	plotKeysVals("num_arrivals_per_station", 
				 data["num_arrivals_per_station"]);
	
	// plot 'num_departures_per_station'
	plotKeysVals("num_departures_per_station",
				 data["num_departures_per_station"]);
	groupBarPlot("num_trips_per_hour",
				 data["num_trips_per_hour"]);
}

var in_comp_mode = false;

var flexy_tables =
    "#overall_trip_stats, \
     #disappointment_stats,\
     #min_duration_trip,\
     #max_duration_trip,\
     #comp_overall_trip_stats,\
     #comp_disappointment_stats,\
     #comp_min_duration_trip,\
     #comp_max_duration_trip"

function toggle_comps() {
    if (in_comp_mode != true) {
        var slider = $('#stats_slider');
        var left_pos = parseInt(slider.css('left'),10);
        slider.animate({left: '50%'},600, function() {
            $('#stats_panel, #comp_stats_panel').css('width', '50%');
            $('#stats_panel').animate({left: '20px', right: '', top: '100px'});
            $(flexy_tables).addClass('large-12');
            $(flexy_tables).removeClass('large-6');
            $('#comp_stats_panel').css('display', 'inline');
            if (left_pos == 660) {map.panBy(320,0);}
        });
        in_comp_mode = true;
    }
    else {
        $('#stats_panel').css('width', '100%')
            .css('right', '20px')
            .css('left', '');
        $('#comp_stats_panel').css('display', 'none');
        $(flexy_tables).addClass('large-6');
        $(flexy_tables).removeClass('large-12');
        in_comp_mode = false;
    }
}

function updateProgressBar(currentTime, percentProgress, isError) {
    var loadingDiv = $("#loading_div");
    if (isError) {
        loadingDiv.find("#error_alert").show();
        return;
    }

    loadingDiv.find("#error_alert").hide();
    
    // update simulation time
    loadingDiv.find("#current_time").html(currentTime);

    // update progress bar
    var progressbar = $( "#progressbar" );

    var value = parseInt(percentProgress);
    if (value == 0) {
	progressbar.progressbar("option", "value", false);	
	progressbar.find(".progress-label").html("Loading...");
    } else {
	progressbar.progressbar( "value", value);
    }
}

function pollProgress(hasZero, currentUrl) {
    var hasHundred = false;
    var hasError = false;
    setTimeout(function() {
        $.ajax({
            url: currentUrl,
            type: "GET",
            success: function(data) {
                if (data.percent_progress == 0) {
                    hasZero = true;
                }
                if (hasZero) {
                    updateProgressBar(data.current_time, data.percent_progress);
                    hasHundred = data.percent_progress == 100;
                }
            },
            complete: function() {
                if (!hasHundred && !hasError) {
                    pollProgress(hasZero, currentUrl);
                }
            }
            , error: function() {
                hasError = true;
                updateProgressBar(null, null, true);
            }
        });
    }, 100);
}

function processStatsForm() {
	var from = $("#from_date").val().trim(),
		to = $("#to_date").val().trim(),
		currentDate = (new Date()).dateFormat("Y-m-d H:i");
	console.log("dict from within processStatsForm():");
	console.log(typeof capacity_dict);
	console.log(capacity_dict);

	capacity_dict_string = JSON.stringify(capacity_dict);

	if (!from.length) {
		from = currentDate;
	}
	if (!to.length) {
		to = currentDate;
	}
	var datatosend = { start: from, end: to, capacity: capacity_dict_string};
	$.ajax({
	    type: "POST",
	    url: "/unified",
	    data: datatosend,
	    beforeSend: function() {
	        $("#stats_slider").animate({left: 20});

	        console.log("=== DATA ===");
	        console.log(datatosend);

                // initialize 'loading_div'
                var loadingDiv = $("#loading_div");            
                var progressbar = $("#progressbar");
                progressbar.progressbar("option", "value", false);            
                progressbar.find(".progress-label").html("Loading...");
                loadingDiv.find("#current_time").html("");
             	progressbar.find(".ui-progressbar-value").css({
                    "background" : "#" + Math.floor( Math.random() * 16777215 ).toString(16)
                });
                loadingDiv.find("#error_alert").hide();
                var slider_left_pos = parseInt($("#stats_slider").css('left'),10);
                if (slider_left_pos == 660) {map.panBy(320,0);}
                loadingDiv.show();
                pollProgress(false, "http://cmc307-04.mathcs.carleton.edu:3001");
            },

	    success: function(data) {
                res = data.concat('!?!',from,'!?!',to);
                var jsond = JSON.parse(data);
                data_for_maps = jsond;
                if (Object.keys(jsond).length == 0) {
                    updateProgressBar(null, null, true);
                    return;
                }

                $("#stats_name").html('Summary for most recent simulation:');
                $("#stats_range").html(from + ' to ' + to);
                $("#loading_div").hide();
                $("#stats_slider").animate({left: 660});
                displaySummaryStats(jsond, from, to);
                map.panBy(-320,0);

		console.log(data_for_maps);	
		$.getScript("static/js/visualize-helper.js", function(){changeMapVis();});
            },

                error: function() {
                    updateProgressBar(null, null, true);
                }
	});	
}
