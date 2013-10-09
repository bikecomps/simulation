/* Initial database structure
	Daniel Alabi and Will Martin

	We might switch to enums, not sure how hard it is to add additional 
	enums later though
*/
CREATE TABLE stations (
	id	INTEGER,
	name CHAR(100),
	capacity INTEGER,
	intersection INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(intersection) REFERENCES intersections (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE neighborhoods (
	id INTEGER,
	population INTEGER,
	.
	.
	.
	.

	PRIMARY KEY (id)
);

CREATE TABLE intersections (
	id INTEGER,
	lat DOUBLE,
	long DOUBLE,
	neighborhood INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(neighborhood) REFERENCES neighborhoods (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE roads (
	id INTEGER,
	start_intersection INTEGER,
	end_intersection INTEGER,
	name CHAR(100),
	road_type INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(start_intersection, end_intersection) REFERENCES intersections (id, id) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT FOREIGN KEY(road_type) REFERENCES road_types (id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE road_types (
	Enums?
);

CREATE TABLE trips (
	id INTEGER,
	bike_id INTEGER,
	member_type ENUM('Casual', 'Registered'),
	start_date DATE,
	end_date DATE,
	start_time TIME,
	end_time TIME,
	start_station INTEGER,
	end_station INTEGER,
	trip_type INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(start_station, end_station) REFERENCES stations (id, id) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT FOREIGN KEY(start_date, end_date) REFERENCES days (day_date, day_date) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT FOREIGN KEY(trip_type) REFERENCES trip_types (id) ON UPDATE CASCADE ON DELETE CASCADE
);

/* Could be used to store results from different simulations, add an entry and add new trips */
CREATE TABLE trip_types (
	Enums?
);

CREATE TABLE days (
	day_date DATE,
	events?
	weather?
	PRIMARY KEY (id)
);