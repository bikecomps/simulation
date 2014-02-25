function changeMapVis(view_mode, secondary_mode) {

    console.log("in change map vis");
    console.log(data_for_maps);
    console.log(view_mode);
    console.log(secondary_mode);

    if (typeof data_for_maps == 'undefined') {
        return;
    }

    view_mode = typeof view_mode !== 'undefined' ? view_mode : "default";
    console.log(data_for_maps);

    var num_stations = Object.keys(data_for_maps["num_departures_per_station"]).length;
    var mean;
    var s_dev;

    switch(view_mode) {
        case "default":
            break;
        case "by_popularity":
            mean = data_for_maps["avg_trips"];
            s_dev = data_for_maps["std_trips"];
            break;
        case "by_disappointments":
            mean = data_for_maps["avg_disappointments"];
            s_dev = data_for_maps["std_disappointments"];
            break;
        case "end_caps":
            break;
    }

    console.log("mean and s_dev");
    console.log(mean);
    console.log(s_dev);

	for (station_id in station_markers) {
		if (station_id in data_for_maps["simulated_station_caps"]) {
			
			s_cap = data_for_maps["simulated_station_caps"][station_id];
			s_final_count = data_for_maps["final_station_counts"][station_id];
			s_percentage = s_final_count/s_cap;
			station_markers[station_id].departure = data_for_maps["num_departures_per_station"][data_for_maps["station_name_dict"][station_id]];
			station_markers[station_id].arrival = data_for_maps["num_arrivals_per_station"][data_for_maps["station_name_dict"][station_id]];	
			station_markers[station_id].trip_total = station_markers[station_id].departure + station_markers[station_id].arrival;
            station_markers[station_id].disappointment = data_for_maps["num_disappointments_per_station"][station_id];
			station_markers[station_id].dep_disappointment = data_for_maps["num_dep_disappointments_per_station"][station_id];
			station_markers[station_id].arr_disappointment = data_for_maps["num_arr_disappointments_per_station"][station_id];

            var s_color; 

            switch(view_mode) {
                case "default":
                    s_color = "CornFlowerBlue";
                    break;
                case "by_popularity":
                    s_color = colorByPopularity(station_markers[station_id], secondary_mode, mean, s_dev);
                    break;
                case "by_disappointments":
                    s_color = colorByDisappointment(station_markers[station_id], mean, s_dev);
                    break;
                case "end_caps": {
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
                    break;
                }
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
}

function colorByPopularity(marker, pop_type, mean, s_dev) {

    pop_type = typeof pop_type !== 'undefined' ? pop_type : "total";

    var score;
    switch(pop_type) {
        case "total":
            score = (marker.trip_total - mean) / s_dev['total'];
            break;
        case "arr":
            score = (marker.arrival - mean) / s_dev['arr'];
            break;
        case "dep":
            score = (marker.departure - mean) / s_dev['dep'];
            break;
    }

    if (score < -1.0) {
        return display_modes['by_popularity']['low']; 
    }
    else if (score > 1.0) {
        return display_modes['by_popularity']['high'];
    }
    else {
        return display_modes['by_popularity']['average'];
    }
}

function colorByDisappointment(marker, mean, s_dev) {

    t_score = (marker.disappointment - mean['total']) / s_dev['total'];
    a_score = (marker.arr_disappointment - mean['arr']) / s_dev['arr'];
    d_score = (marker.dep_disappointment - mean['dep']) / s_dev['dep'];
//    console.log("marker,score:");
//    console.log(marker);
//    console.log(t_score + " " + a_score + " " + d_score); 
    if (a_score < 1.0 && d_score < 1.0 && t_score > 1.0) {
        window.alert(marker.id + " " + t_score + " " + a_score + " " + d_score);
    }
    if (a_score > 1.0 && a_score > d_score) {
       return display_modes['by_disappointments']['full']; 
    }
    else if (d_score > 1.0 && d_score > a_score) {
        return display_modes['by_disappointments']['empty'];
    }
    else if (t_score > 1.0) {
         return 'red';
    }
    else {
        return display_modes['by_disappointments']['average'];
    }

}

