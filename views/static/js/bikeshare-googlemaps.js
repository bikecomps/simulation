var locations;

var connections;
var map;

var openWindow;

function set_coordinates(val)
{
    j_val = val.replace(/&quot;/g,'"');
    locations=jQuery.parseJSON(j_val);
}

function SimulationControl(controlDiv) {
    controlDiv.id = "simulation_control";
    
    var controlForm = document.createElement('form');

    var from_div = document.createElement('div');
    from_div.id = 'from_div';
    var from_input = document.createElement('input');
    from_input.type = 'text';
    from_input.id = 'from_date';
    from_input.placeholder = 'Start Date';
    from_div.appendChild(from_input);

    var to_div = document.createElement('div');
    to_div.id = 'to_div';
    var to_input = document.createElement('input');
    to_input.type = 'text';
    to_input.id = 'to_date';
    to_input.placeholder = 'End Date';
    to_div.appendChild(to_input);

    var submit = document.createElement('button');
    submit.type = 'submit';
    submit.class = 'button';
    submit.id = 'submit';
    submit.value = 'Go!';

    controlForm.appendChild(from_div);
    controlForm.appendChild(to_div);
    controlForm.appendChild(submit);

    controlDiv.appendChild(controlForm);

}

function initialize() {
    connections = [];
	var mapOptions = {
		panControl: false,
		zoomControlOptions: {
			position: google.maps.ControlPosition.TOP_LEFT
		},
		zoom: 12,
		center: new google.maps.LatLng(38.904, -77.032),
		mapTypeId: google.maps.MapTypeId.ROADMAP,
	};
	map = new google.maps.Map(document.getElementById('map_canvas'),
			                  mapOptions);

    var simControlDiv = document.createElement('div');
    var simControl = new SimulationControl(simControlDiv);

    map.controls[google.maps.ControlPosition.TOP_LEFT].push(simControlDiv);
    
    // Draw a logo wherever there is a bike station
  	var stationLogo = '/static/img/cbLogo-16.png';
    //console.log("length="+Object.keys(locations).length);

	// var infoWindow = null;
	// infoWindow = new google.maps.InfoWindow({
	//	content: "Hakuna Matata! You clicked a station! G'day!"
	// });	

    // Draw a logo wherever there is a bike station	
	var stationLogo = '/static/img/cbLogo-16.png';
    //:console.log("length="+Object.keys(locations).length);
    
    for (station=0; station < Object.keys(locations).length; station++) {
        // console.log(station + ": " + lat[station] + ", " + lng[station]);
        var stationLatLng = new google.maps.LatLng(locations[station][0], locations[station][1]);
        console.log("lat = " + locations[station][0] + "and lon = " + locations[station][1]);
        var marker = new google.maps.Marker({
            position: stationLatLng,
            map: map,
            icon: stationLogo,
	    id: locations[station][2],
	    title: locations[station][3],
            capacity: locations[station][4]
        });
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
    // console.log(connections[connections.length-1]);
}

function removeLines() {
    for (var index in connections) {
        var connection = connections[index];
        // console.log(connection);
        connection.setMap(null);        
    }
}

google.maps.event.addDomListener(window, 'load', initialize);
