var locations;

var connections;
var map;

var openWindow;

var station_markers;
var clusters;

var marker_colors;
var color_index;

function set_coordinates(val)
{
	j_val = val.replace(/&quot;/g,'"');
	locations=jQuery.parseJSON(j_val);
}


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
	marker_colors = ["CornflowerBlue","orange", "purple", "red","green"];
	color_index = 0;

	clusters = {"orange": [31016, 31017, 31018, 31019, 31020, 31021, 31022, 31023,
		31024, 31025, 31026, 31027, 31028, 31029, 31030, 31031, 31032, 31033, 31034, 31035, 
		31036, 31037, 31038, 31039, 31040, 31049, 31050, 31051, 31058, 31704, 31800],
		"blue": [31108, 31208, 31209, 31218, 31244, 31500, 31502, 31504, 31505, 31508, 
		31512, 31601, 31603, 31605, 31606, 31607, 31608, 31610, 31611, 31612, 31613, 31614, 
		31615, 31616, 31617, 31618, 31619, 31622, 31623, 31625, 31626, 31627, 31628, 31629, 
		31630, 31631, 31632, 31700, 31701, 31702, 31703, 31705, 31706, 31707, 31708, 31709, 31801, 
		31802, 31803, 31804, 31805, 31806, 31807],
		"red": [31000, 31001, 31002, 31003, 31004, 31005, 31006, 31007, 31008, 31009, 31010, 31011,
		 31012, 31013, 31041, 31042, 31043, 31044, 31045, 31046, 31047, 31048, 31052, 31053, 31055, 
		 31056, 31057, 31059, 31060, 31061],
		"green": [31014, 31015, 31054, 31100, 31101, 31102, 31103, 31104, 31105, 31106, 31107, 31109, 
		31110, 31111, 31112, 31113, 31114, 31115, 31116, 31117, 31200, 31201, 31202, 31203, 31204,
		31205, 31206, 31207, 31211, 31212, 31213, 31214, 31215, 31216, 31217, 31219, 31220, 31221,
		31222, 31223, 31224, 31225, 31226, 31227, 31228, 31229, 31230, 31231, 31232, 31233, 31234,
		31235, 31236, 31237, 31238, 31239, 31240, 31241, 31242, 31243, 31245, 31246, 31247, 31248, 
		31249, 31250, 31251, 31252, 31253, 31254, 31255, 31256, 31257, 31258, 31259, 31260, 31261, 
		31262, 31263, 31264, 31265, 31266, 31267, 31268, 31300, 31301, 31302, 31303, 31304, 31305, 31306, 
		31307, 31308, 31309, 31310, 31312, 31400, 31401, 31402, 31403, 31404, 31405, 31406, 31407, 31501, 
		31503, 31506, 31507, 31509, 31510, 31511, 31600, 31602, 31604, 31609, 31620, 31621, 31624]
	};

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
			capacity: locations[station][4]
		});
		station_markers[locations[station][2]] = marker;
		var infoWindow = new google.maps.InfoWindow({
			content: "Hakuna Matata?"
		});
		openWindow = infoWindow;
		bindInfoWindow(marker, map, infoWindow);
	}
}

function bindInfoWindow(marker, map, infoWindow) {
	google.maps.event.addListener(marker, 'click', function() {
		openWindow.close();
		infoWindow.setContent(marker.title);
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

function changeMarkerColors() {
	if (color_index == marker_colors.length-1) {
		color_index = 0;
	}
	else {
		color_index++;
	}

	console.log("Cur Marker Color:")
	console.log(marker_colors[color_index]);
	for (var m in station_markers) {
		m.setIcon({
		path: google.maps.SymbolPath.CIRCLE,
			fillColor: marker_colors[color_index],
			fillOpacity: 1.0,
			scale: 6,
			strokeColor: 'Navy',
			strokeWeight: 1
		});
	}
}

function clusterColors() {
	var dic = {};
	for (var color in clusters) {
   		for (var i=0; i < clusters[color].length; i++) {
      		dic[clusters[color][i]] = color;
   		}
	}
	for (var marker_id in dic) {
		changeMarkerColor(marker_id, dic[marker_id]);
	}
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
