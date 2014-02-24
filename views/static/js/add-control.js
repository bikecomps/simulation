// Modeled after https://developers.google.com/maps/documentation/javascript/examples/control-custom

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

}
