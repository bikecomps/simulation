var locations;

var connections;
var map;

var openWindow;

var station_markers;

var marker_colors;
var marker_cap_gradient;

var capacity_dict = {};

function initialize() {
	connections = [];
	var mapOptions = {
		panControl: false,
		minZoom: 4,
				maxZoom: 17,
				scrollwheel: false,
				zoomControlOptions: {
			position: google.maps.ControlPosition.RIGHT_TOP
		},
		zoom: 12,
		center: new google.maps.LatLng(38.904, -77.032),
		mapTypeId: google.maps.MapTypeId.ROADMAP,
	};
	map = new google.maps.Map(document.getElementById('map_canvas'),
							  mapOptions);
	
	station_markers = {};
	marker_colors = ["blue", "orange", "green", "red", "purple", "yellow"];
	// red, red-purple, purple, blue-purple, blue
	//marker_cap_gradient = ["ED5A1D","C34E31","843D50","452B6E","1B2083"]
	// light-green to dark-blue gradient?
	marker_cap_gradient = ["#16E31E","#14BA3B","#137C68","#115385","#1016B2"]


	for (station=0; station < Object.keys(locations).length; station++) {
		var stationLatLng = new google.maps.LatLng(locations[station][0], locations[station][1]);
		// console.log("lat = " + locations[station][0] + "and lon = " + locations[station][1]);
		var marker = new google.maps.Marker({
			position: stationLatLng,
			map: map,
			icon: {
				path: google.maps.SymbolPath.CIRCLE,
				fillColor: 'CornflowerBlue',
				fillOpacity: 1.0,
				scale: 6,
				strokeColor: 'Navy',
				strokeWeight: 1
			},
			id: locations[station][2],
			title: locations[station][3],
			capacity: locations[station][4],
			alt_capacity: locations[station][4],
			disappointment: -1,
			dep_disappointment: -1,
			arr_disappointment: -1
		});
		station_markers[locations[station][2]] = marker;
		var infoWindow = new google.maps.InfoWindow({
			content: "Hakuna Matata?",
			maxWidth: 300
		});
		openWindow = infoWindow;
		bindInfoWindow(marker, map, infoWindow);
	}
}

function set_coordinates(val) {
	j_val = val.replace(/&quot;/g,'"');
	locations=jQuery.parseJSON(j_val);
}

function bindInfoWindow(marker, map, infoWindow) {
	google.maps.event.addListener(marker, 'click', function() {
		openWindow.close();

		var contentString = '<div class="infoWindow_wrapper">' + 
			'<div class="infoWindow_id">' + marker.id + '</div>' +
			'<div class="infoWindow_title">' + marker.title + '</div>' +
			'<div class="infoWindow_capacity"><label class="left inline infoWindow_capacity_label">Capacity</label><input type="text" id="infoWindow_capacity_text" value="' + marker.alt_capacity + '" />' +  
			'<a class="button tiny" id="infoWindow_capacity_button" onclick="appendCapacityChange(' + marker.id +
			'); return false;">Save</a></div>' +
			'<div class="infoWindow_disappointment"><label>Disappointments</label>' +
			'<div class="infoWindow_disappointment_text">Dep ' + marker.dep_disappointment + ' + ' +
			'Arr ' + marker.arr_disappointment + ' = Tot ' + marker.disappointment + '</div></div>' + 
			'</div>';

		//console.log("MARKER CAPACITY FOR STA #" + marker.id + " = " + marker.capacity);
		infoWindow.setContent(contentString);
		infoWindow.open(map, marker);
		openWindow = infoWindow;	
	});
}

function addLine(fromStation, toStation, color) {
	var pathCoords = [
		new google.maps.LatLng(locations[fromStation][0], locations[fromStation][1]),
		new google.maps.LatLng(locations[toStation][0], locations[toStation][1])
	];
	var connection = new google.maps.Polyline({
		path: pathCoords,
		geodesic: true,
		strokeColor: color,
		strokeOpacity: 0.7,
		strokeWeight: 2
	});
	connections.push(connection);
	connection.setMap(map);
}

function removeLines() {
	for (var index in connections) {
		var connection = connections[index];
		connection.setMap(null);
	}
}

function appendCapacityChange(id) {
	var newCapacity = $('#infoWindow_capacity_text').val(); //get
	$('#infoWindow_capacity_text').val(newCapacity); //set

	console.log("CAPACITY FOR STA #" + id + " IS UPDATED TO "+ newCapacity);		

	station_markers[id].alt_capacity = newCapacity;

	capacity_dict[id] = newCapacity;

	//capacity_dict.push({
	//	key: id,
	//	value: newCapacity
	//});

	console.log("CAPACITY DICTIONARY:");
	console.log(capacity_dict);

	//$.ajax({
	//	type: "POST",
	//	url: "/unified",
	//	data: { capacity_dict: capacity_dictionary },
	//	error: function() {
	//		console.log("AJAX is not happy about your capacity_dictionary.");
	//	}
	//});
}

function clusterColors() {
	var clusterMethod = $("#clustering_method").val();
        var startDate = $("#start_date").val();
        var endDate = $("#end_date").val();
	console.log(clusterMethod);
	if (!clusterMethod.length || !startDate.length || !endDate.length) {
		console.log("nope.");
		return;
	}

	$.ajax({
		type: "POST",
		url: "/clustering",
		data: { start_date: startDate, 
			end_date: endDate, 
			clustering_method: clusterMethod },
		beforeSend: function() {
			$("#loading_div").show();
		},
		success: function(data) {
			var jsond = JSON.parse(data);
			for (var num in jsond) {
				jsond[marker_colors[num]] = jsond[num];
				delete jsond[num];
			}
			var dic = {};
			for (var color in jsond) {
				for (var i=0; i < jsond[color].length; i++) {
					dic[jsond[color][i]] = color;
				}
			}
			for (var marker_id in dic) {
				changeMarkerColor(marker_id, dic[marker_id]);
			}
			$("#loading_div").hide();
		},
		error: function() {
			console.log("ajax error while clustering");
		}
	});
}

function changeMarkerColor(marker_id, color) {
	m = station_markers[marker_id];
	m.setIcon({
	path: google.maps.SymbolPath.CIRCLE,
		fillColor: color,
		fillOpacity: 1.0,
		scale: 6,
		strokeColor: 'Navy',
		strokeWeight: 1
	});
} 

var oDiv = document.createElement('div');
console.log("oDiv?");
$.getScript("/static/js/map-overlay.js")
    .done(function(script, textStatus) {
        console.log("hello");
        overlay = new OptionsOverlay(map, oDiv);
        overlay.onAdd();
        overlay.setSizeAndPos("100px","100px", "relative");
        overlay.show();
        console.log("should be showing now");
       
    })
    .fail(function(jqxhr, settings, exception) {
        console.log("error");
        console.log(exception);
        console.log(jqxhr);
        console.log(settings);
    });

google.maps.event.addDomListener(window, 'load', initialize);
