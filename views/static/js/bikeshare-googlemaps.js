var locations;

var connections;
var map;

var openWindow;

var station_markers;

var marker_colors;
var marker_cap_gradient;

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
	marker_cap_gradient = ["ED1F1D","AD1F56","5720A2","519800","82207C"]
	// light-green to dark-blue gradient?
	// marker_cap_gradient = ["16E31E","14BA3B","137C68","115385","1016B2"]


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
			alt_capacity: locations[station][4] // holds user-altered capacities
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
			'<div class="infoWindow_capacity">Capacity : <div class="infoWindow_capacity_label">' + marker.capacity +
			'</div></div>' +
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

function displayStationCountVis(station_counts, station_caps) {
	for (var station_id in station_counts) {

	}
}

function removeLines() {
	for (var index in connections) {
		var connection = connections[index];
		connection.setMap(null);
	}
}

function clusterColors() {
	var clusterMethod = $("#clustering_method").val();
	console.log(clusterMethod);
	if (!clusterMethod.length) {
		console.log("nope.");
		return;
	}

	$.ajax({
		type: "POST",
		url: "/clustering",
		data: { clustering_method: clusterMethod },
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

google.maps.event.addDomListener(window, 'load', initialize);
