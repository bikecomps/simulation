var locations;

var connections;
var map;

var openWindow;

function set_coordinates(val)
{
    j_val = val.replace(/&quot;/g,'"');
    locations=jQuery.parseJSON(j_val);
}

function initialize() {
    connections = [];
	var mapOptions = {
		zoom: 12,
		center: new google.maps.LatLng(38.904, -77.032),
		mapTypeId: google.maps.MapTypeId.ROADMAP,
		panControl: false,
		zoomControlOptions: {
			style: google.maps.ZoomControlStyle.DEFAULT
		}
	};
	map = new google.maps.Map(document.getElementById('map-canvas'),
			                  mapOptions);
    
<<<<<<< HEAD
    // Draw a logo wherever there is a bike station
  	var stationLogo = '/static/img/cbLogo-16.png';
    //console.log("length="+Object.keys(locations).length);

	var infoWindow = null;
	infoWindow = new google.maps.InfoWindow({
		content: "Hakuna Matata! You clicked a station! G'day!"
	});	

=======
    // Draw a logo wherever there is a bike station	
	var stationLogo = '/static/img/cbLogo-16.png';
    //:console.log("length="+Object.keys(locations).length);
    
>>>>>>> c1ed0f0c98f397ccc6ce046ebbde421349539fa8
    for (station=0; station < Object.keys(locations).length; station++) {
        // console.log(station + ": " + lat[station] + ", " + lng[station]);
        var stationLatLng = new google.maps.LatLng(locations[station][0], locations[station][1]);
        console.log("lat = " + locations[station][0] + "and lon = " + locations[station][1]);
        var marker = new google.maps.Marker({
            position: stationLatLng,
            map: map,
            icon: stationLogo,
<<<<<<< HEAD
			title: 'Why can you read this? You should not.'
=======
	    title: 'This is a station, as you can see.'
>>>>>>> c1ed0f0c98f397ccc6ce046ebbde421349539fa8
        });
	var infoWindow = new google.maps.InfoWindow({
		content: "Hakuna Matata?"
	});
	openWindow = infoWindow;
	bindInfoWindow(marker, map, infoWindow);	
		//var infowindow = new google.maps.InfoWindow({
			//position: stationLatLng,
			//content: marker.title
		//});
		
<<<<<<< HEAD
		//var infowindow = new google.maps.InfoWindow({
		//	position: stationLatLng,
		//	content: marker.title
		//});
		
		google.maps.event.addListener(marker, 'click', function() {
			infoWindow.setContent(this.html);
			infoWindow.open(map, this);
		});	
=======
	//google.maps.event.addListener(marker, 'click', function() {
	//	infoWindow.setContent(this.html);
	//	infowindow.open(map, this);
	//});	
>>>>>>> c1ed0f0c98f397ccc6ce046ebbde421349539fa8
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
