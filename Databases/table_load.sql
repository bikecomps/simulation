-- SQL commands to 
-- create tables for our Models
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
	type ENUM('road','bike_path','highway'),
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(start_intersection, end_intersection) REFERENCES intersections (id, id) ON UPDATE CASCADE ON DELETE CASCADE
);


CREATE TABLE trips (
	id INTEGER,
	bike_id INTEGER,
	member_type ENUM('casual', 'registered'),
	start_time TIMESTAMP,
	end_time TIMESTAMP,
	start_station INTEGER,
	end_station INTEGER,
	type ENUM('training','testing','production'),
	PRIMARY KEY (id),
	CONSTRAINT FOREIGN KEY(start_station, end_station) REFERENCES stations (id, id) ON UPDATE CASCADE ON DELETE CASCADE
);
