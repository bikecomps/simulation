function changeMapVis() {
	for (station_id in station_markers) {
		if (station_id in data_for_maps["simulated_station_caps"]) {
			
			s_cap = data_for_maps["simulated_station_caps"][station_id];
			s_final_count = data_for_maps["final_station_counts"][station_id];
			s_percentage = s_final_count/s_cap;


			station_markers[station_id].departure = data_for_maps["num_departures_per_station"][station_id];
			station_markers[station_id].arrival = data_for_maps["num_arrivals_per_station"][station_id];	
			station_markers[station_id].disappointment = data_for_maps["num_disappointments_per_station"][station_id];
			station_markers[station_id].dep_disappointment = data_for_maps["num_dep_disappointments_per_station"][station_id];
			station_markers[station_id].arr_disappointment = data_for_maps["num_arr_disappointments_per_station"][station_id];

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
}

/*
function changeMapVis(display_mode) {
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
}
