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
    return (d/60.0).toFixed(2) + " hours";
}

function formatDate(dateStr) {
    return (new Date(dateStr)).dateFormat("m-d-Y H:i");
}

function barPlot(htmlIdName, labels, counts) {
    var chart,
        width = 1000,
        bar_height = 20,
        height = bar_height * labels.length,
        x, y, yRangeBand,
        left_width = 100,
        gap = 2,
        extra_width = 100;
    
    x = d3.scale.linear()
        .domain([0, d3.max(counts)])
        .range([0, width]);
    
    yRangeBand = bar_height + 2 * gap;
    y = function(i) { return yRangeBand * i; };
    
    chart = d3.select($("#" + htmlIdName + " div")[0])
        .append('svg')
        .attr('class', 'chart')
        .attr('width', left_width + width + 40 + extra_width)
        .attr('height', (bar_height + gap * 2) * (labels.length + 1))
        .append("g")
        .attr("transform", "translate(10, 20)");
    
    chart.selectAll("line")
        .data(x.ticks(d3.max(counts)))
        .enter().append("line")
        .attr("x1", function(d) { return x(d) + left_width; })
        .attr("x2", function(d) { return x(d) + left_width; })
        .attr("y1", 0)
        .attr("y2", (bar_height + gap * 2) * labels.length);
    
    chart.selectAll(".rule")
        .data(x.ticks(d3.max(counts)))
        .enter().append("text")
        .attr("class", "rule")
        .attr("x", function(d) { return x(d) + left_width; })
        .attr("y", 0)
        .attr("dy", -6)
        .attr("text-anchor", "middle")
        .attr("font-size", 10)
        .text(String);
    
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
        .attr("x", function(d) { return x(d) + left_width; })
        .attr("y", function(d, i){ return y(i) + yRangeBand/2; } )
        .attr("dx", -5)
        .attr("dy", ".36em")
        .attr("text-anchor", "end")
        .attr('class', 'score')
        .text(String);
    
    chart.selectAll("text.name")
        .data(labels)
        .enter().append("text")
        .attr("x", left_width / 2)
        .attr("y", function(d, i){ return y(i) + yRangeBand/2; } )
        .attr("dy", ".36em")
        .attr("text-anchor", "middle")
        .attr('class', 'name')
        .text(String);

}

function plotKeysVals(htmlIdName, map) {
    var ids = Object.keys(map);
    var counts = new Array(ids.length);
    for (var i = 0; i < ids.length; i++) {
        counts[i] = map[ids[i]];
    }
    barPlot(htmlIdName, ids, counts);
}

function displaySummaryStats(data, from, to) {
    $("#results > h4").text(
        "Displaying Summary Stats for trips generated from " + 
        from + " to " + to
    );

    // set 'total_num_trips', 'total_num_disappointments',
    // 'avg_trip_time', and 'std_trip_time' 
    $("#total_num_trips").text(data["total_num_trips"]);
    $("#total_num_disappointments").text(data["total_num_disappointments"]);
    $("#avg_trip_time").text(toHours(data["avg_trip_time"]));
    $("#std_trip_time").text(toHours(data["std_trip_time"]));

    // set 'min_duration_trip' 
    var minTrip = data["min_duration_trip"];
    var minTripHtml = $("#min_duration_trip");
    minTripHtml.find(".start_station_id")
        .text(minTrip["start_station_id"]);
    minTripHtml.find(".end_station_id")
        .text(minTrip["end_station_id"]);
    minTripHtml.find(".duration")
        .text(toHours(minTrip["duration"]));
    minTripHtml.find(".start_datetime")
        .text(formatDate(minTrip["start_datetime"]));
    minTripHtml.find(".end_datetime")
        .text(formatDate(minTrip["end_datetime"]));

    // set 'max_duration_trip' 
    var maxTrip = data["max_duration_trip"];
    var maxTripHtml = $("#max_duration_trip");
    maxTripHtml.find(".start_station_id")
        .text(maxTrip["start_station_id"]);
    maxTripHtml.find(".end_station_id")
        .text(maxTrip["end_station_id"]);
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
}

function processStatsForm() {
    var from = $("#from_date").val().trim(),
        to = $("#to_date").val().trim(),
        currentDate = (new Date()).dateFormat("m-d-Y H:i");

    if (!from.length) {
        from = currentDate;
    }
    if (!to.length) {
        to = currentDate;
    }

    $.ajax({
        type: "POST",
        url: "/stats",
        data: { start: from, end: to },
        beforeSend: function() {
            $("#results").hide();
            $("#loading").show();
        },
        success: function(data) {
            displaySummaryStats(JSON.parse(data), from, to);
            $("#loading").hide();
		    $("#results").show();
        }
    });
}
