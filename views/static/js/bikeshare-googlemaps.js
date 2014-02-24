var locations;

var connections;
var map;

var openWindow;

var station_markers;

var marker_colors;
var marker_cap_gradient;

var display_modes = {};

var popularity_maps = {};

var disappointment_maps = {};

var capacity_dict = {};

var current_display_mode;

var control_dict = {};

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

    // currently used for clustering
	marker_colors = ["blue", "orange", "green", "red", "purple", "yellow"];

	// light-green to dark-blue gradient? for grouping after sim?
	marker_cap_gradient = ["#16E31E","#14BA3B","#137C68","#115385","#1016B2"]
    
    current_display_mode = "default";

    display_modes = {
        'default': {"average":"CornFlowerBlue"},
        'by_popularity': {"low":"red", "average":"yellow", "high":"green"},
        'by_disappointments': {"average":"CornFlowerBlue","full":"yellow","empty":"black"},
        'end_modes': marker_cap_gradient
    };
    
	for (station=0; station < Object.keys(locations).length; station++) {
		var stationLatLng = new google.maps.LatLng(locations[station][0], locations[station][1]);
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
			departure: -1,
			arrival: -1,
            trip_total: -1,
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


    control_dict = {
        "View by Overall Popularity":["by_popularity", "total"],
        "View by Arrival Popularity":["by_popularity","arr"],
        "View by Departure Popularity":["by_popularity","dep"],
        "View by Disappointments":["by_disappointments", undefined],
        "View by End Capacity":["end_caps", undefined],
        "Default View":["default", undefined],
    };


    set_controls();   
}

function set_coordinates(val) {
	j_val = val.replace(/&quot;/g,'"');
	locations=jQuery.parseJSON(j_val);
}

function set_controls() {
       
    for (var c in control_dict) {
 
        var controlWrap = document.createElement('div');
        controlWrap.className = 'mapControl_wrapper';

        var controlU = document.createElement('div');
        controlU.className = 'mapControl_UI';
        controlWrap.appendChild(controlU);

        var controlT = document.createElement('div');
        controlT.className = 'mapControl_text';
        controlT.innerHTML = c;
        controlU.appendChild(controlT);

        addMapDisplayControl(controlWrap, controlU, google.maps.ControlPosition.TOP_RIGHT, c[0], c[1]);
    }
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
			'<div class="infoWindow_item"><label>Trips Completed</label>' +
			'<div class="infoWindow_item_text">Dep <div class="infoWindow_trip_number">' + marker.departure + '</div> + ' +
			'Arr <div class="infoWindow_trip_number">' + marker.arrival + '</div></div></div>' +
			'<div class="infoWindow_item"><label>Disappointments</label>' +
			'<div class="infoWindow_item_text">Dep <div class="infoWindow_disappointment_number">' + marker.dep_disappointment + '</div> + ' +
			'Arr <div class="infoWindow_disappointment_number">' + marker.arr_disappointment + '</div> = Tot <div class="infoWindow_disappointment_number">' + marker.disappointment + '</div></div></div>' + 
			'</div>';

		infoWindow.setContent(contentString);
		infoWindow.open(map, marker);
		openWindow = infoWindow;

		if (marker.departure == -1) {
			$("div.infoWindow_item").css("display", "none");
		}

		if (marker.disappointment == -1) {
			$("div.infoWindow_item").css("display", "none");
		}	
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

	console.log("CAPACITY DICTIONARY:");
	console.log(capacity_dict);

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

function addControlCustom(cDivWrapper, cUI, cFunction, mapPosition) {
        newControl = new CustomControl(cDivWrapper, cUI, cFunction);
        newControl.index = 1;
        map.controls[mapPosition].push(cDivWrapper);
        console.log(cUI, cFunction);
}

function addMapDisplayControl(cDivWrapper, cUI, mapPosition, view_mode, secondary_mode) {
        newControl = new MapControl(cDivWrapper, cUI, view_mode, secondary_mode);
        newControl.index = 1;
        map.controls[mapPosition].push(cDivWrapper);
}

function CustomControl(controlDiv, controlUI, controlFunction) {

  google.maps.event.addDomListener(controlUI, 'click', function() {
    controlFunction
  });

}

function MapControl(controlDiv, controlUI, view_mode, secondary_mode) {
 
    $.getScript("static/js/visualize-helper.js")
    .done(function(){
        google.maps.event.addDomListener(controlUI, 'click', function(e) {
            console.log(e.target.innerHTML);
            console.log(control_dict[e.target.innerHTML]);
            console.log(control_dict[e.target.innerHTML][0]);
            changeMapVis(control_dict[e.target.innerHTML][0], control_dict[e.target.innerHTML][1]);
        });
    })
    .fail(function(kqxhr, settings, exception) {
        console.log(exception);
    });

}



google.maps.event.addDomListener(window, 'load', initialize);
