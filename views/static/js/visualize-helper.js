function changeMapVis() {
//need to put in view_mode arg
//    var categories = display_modes[view_mode];

    groupByPopularity("arrival");

/*

	for (station_id in station_markers) {
		if (station_id in data_for_maps["simulated_station_caps"]) {
			
			s_cap = data_for_maps["simulated_station_caps"][station_id];
			s_final_count = data_for_maps["final_station_counts"][station_id];
			s_percentage = s_final_count/s_cap;	
			var s_color;
			if (s_percentage <= .2) {
				s_color = marker_cap_gradient[0];
			} else if (s_percentage <= .4) {
				s_color = marker_cap_gradient[1];
			} else if (s_percentage <=.6) {
				s_color = marker_cap_gradient[2];
			} else if (s_percentage <= .8) {
				s_color = marker_cap_gradient[3];
			} else {
				s_color = marker_cap_gradient[4];
			}
	
			station_markers[station_id].setIcon({
			path: google.maps.SymbolPath.CIRCLE,
				fillColor: s_color,
				fillOpacity: 1.0,
				scale: 6,
				strokeColor: "Navy",
				strokeWeight: 1
			});
		}
	}
*/
}

function groupByPopularity(popularity_type) {

        var myDict = data_for_maps[popularity_maps[popularity_type]];
        console.log(myDict);
        var sortable = [];
        for (var stat in myDict) {
            sortable.push([stat, myDict[stat]]);
        }
        sortable.sort(function(a,b){return b[1] - a[1]});
        // this should be improved to take into account the average number of trips per station
        var max = sortable[0][1];
        console.log(sortable);
        console.log(max);
   
        console.log(station_markers);
        for (station_id in station_markers) {
            var s_color;
            var current_marker = station_markers[station_id];
            if (current_marker.title in myDict) {
                
                if (myDict[current_marker.title] <= (max - myDict[current_marker.title])/4) {
                    s_color = display_modes["by_popularity"]["low"];
                }
                else if (myDict[current_marker.title] <= 3*(max - myDict[current_marker.title]/4)) {
                    s_color = display_modes["by_popularity"]["average"];
                }
                else {
                    s_color = display_modes["by_popularity"]["high"];
                }
            }
            else {
                s_color = "CornFlowerBlue";
            }
            console.log(s_color);
	    	station_markers[station_id].setIcon({
	        	path: google.maps.SymbolPath.CIRCLE,
	    		fillColor: s_color,
	    		fillOpacity: 1.0,
	    		scale: 6,
		    	strokeColor: "Navy",
	    		strokeWeight: 1
		    });	
        }
}

