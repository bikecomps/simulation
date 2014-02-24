
// Modeled after HomeControl

var dc = new google.maps.LatLng(38.904, -77.032);

/**
 * Takes a wrapper div (controlDiv) with a div inside (controlUI) 
 * which, when clicked on, will execute controlFunction.
 */

function CustomControl(controlDiv, controlUI, controlFunction) {

  // Setup the click event listeners: simply set the map to
  // Chicago
  google.maps.event.addDomListener(controlUI, 'click', function() {
    controlFunction()
  });

  console.log("added dom in CustomControl:");
  console.log(controlUI);
}
/*
function initialize() {
  var mapDiv = document.getElementById('map-canvas');
  var mapOptions = {
    zoom: 12,
    center: dc
  }
  map = new google.maps.Map(mapDiv, mapOptions);

  // Create the DIV to hold the control and
  // call the HomeControl() constructor passing
  // in this DIV.
  var homeControlDiv = document.createElement('div');
  var homeControl = new HomeControl(homeControlDiv, map);

  homeControlDiv.index = 1;
  map.controls[google.maps.ControlPosition.TOP_RIGHT].push(homeControlDiv);
}
*/
