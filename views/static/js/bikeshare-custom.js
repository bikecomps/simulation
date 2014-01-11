function sliderSetup() {
    $( "#slider-range" ).slider({
        range: true,
        min: 0,
        max: 24,
        values: [ 0, 24 ],
        slide: function( event, ui ) {
            $( "#amount" ).val( ui.values[ 0 ] + ":00 - " + ui.values[ 1 ] + ":00");
            console.log("VALUES HERE: " + ui.values[0] + " and " + ui.values[1]);
        }
    });
    $( "#amount" ).val( $( "#slider-range" ).slider( "values", 0 ) + ":00 - " + $( "#slider-range" ).slider( "values", 1 ) + ":00");

}
