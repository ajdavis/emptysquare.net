var imageId = 0;

/* Change the visible image.
 * @param delta:   	     	An integer; go forward or backward in the image list
 *                      	by this number of photos.
 * @param next_set_url:		Where to go after the final image
 */
function navigate(delta, next_set_url) {
	imageId += delta;
	navigateToImageId(next_set_url);
}

/* Show the proper image after updating imageId.
 * @param next_set_url:		Where to go after the final image
 */
function navigateToImageId(next_set_url) {
    var blank = '<img src="/static/images/blank.gif" height="9px" width="14px" />';
	
    /**
	 * Clamp imageId to [0, photos.length), set URL's hash anchor, or maybe
	 * navigate to next set
	 */
    if (imageId < 0) {
		imageId = 0;
	} else if (imageId < photos['photo'].length) {
		// Support back button or bookmarking by setting image index (1-based) in URL,
		// like http://emptysquare.net/photography/lower-east-side/#5/
		// TODO: don't set URL if it's already correct
		// TODO: here's where the favicon disappears, fix that
		parts = document.location.href.split('#');
		document.location = parts[0] + '#' + (imageId + 1) + '/';
	} else {
		// Navigate to the next set
		document.location.href = document.location.href.replace(/(http:\/\/.*?)(\/.+\/)/, "$1" + next_set_url);
		return false;
	}
    
    /**
	 *  Show or hide the left and right arrows depending on current position in
     * list of photos
	 */
    if (imageId == 0) $("#navLeft").html(blank);
    else $("#navLeft").html('<img src="/static/images/goleft.gif" height="9px" width="14px" />');
    
    if (imageId == photos['photo'].length - 1) $("#navRight").html(blank);
    else $("#navRight").html('<img src="/static/images/goright.gif" height="9px" width="14px" />');
    
    /**
	 * Update the displayed image id
	 */
    $("#navIndex").html("" + (imageId + 1));
    
	// I've decided descriptions are superfluous
    //$("#imageDescription").html(photos['photo'][imageId].description);
	//$("#imageTitle").html(photos['photo'][imageId].title);
    
	/**
	 * Show the image
	 */
	setImage(photos['photo'][imageId].image);
	
	/** Update the URL for the Facebook Like button -- the like button ignores
	 * everything after the #, so change the URL from something like
	 * http://emptysquare.net/photography/fritz-christina/#1/
	 * to:
	 * http://emptysquare.net/photography/fritz-christina/1/
	 */
	$('#open_graph_image_property').attr('content', photos['photo'][imageId]['source']);
	
	var location = document.location.href.split('#')[0] + (imageId+1) + '/';
	
	$('#fb_like_button_container').empty().append(
		'<fb:like href="'
		+ location
		+ '" show_faces="false" width="225" font="arial"></fb:like>'
	);
	
	// If Facebook's Javascript SDK is loaded, make it re-parse the Like button
	// FBXML.  Else, wait for the FB SDK to load; it'll parse the FBXML then.
	if (typeof(FB) != 'undefined') {
		FB.XFBML.parse(document.getElementById('fb_like_button_container'));
	}
	
	
	
	
	// $("#tweet_button").attr(
	// 	'href',
	// 	'http://twitter.com/home?status=' + location
	// );
	
    return false;
}

/* Show a photo
 * @param image:	An Image object
 */
function setImage(image) {
	$("#imageContainer").empty().append(image);
}

/* Preload all photos in the photos array
 * @param preload_image_id:	Which image to preload, or -1 for all photos
 * @param onload_function:	Function to call when image has loaded
 */
function preloadImage(preload_image_id, onload_function) {
	var imageObj = new Image();
	imageObj.imageId = preload_image_id;
	photos['photo'][preload_image_id].image = imageObj;
	
	$(imageObj).load(function() {
		// As soon as image loads, show it if it's the current image
		if (onload_function) onload_function();
		if (imageId == this.imageId) {
			setImage(this);
		}
	});
	
	// Trigger a preload
	imageObj.src = photos['photo'][preload_image_id]['source'];
}

/* Call this in $(document).ready()
 * @param set_name:  	A string, the name of this set of photos,
 *                      e.g. "portraits", or "rock stars"
 * @param photos:       An array of objects, not the actual photos but
 *                      information about them
 * @param next_set_url: Where to go after this page
 */
function onReady(set_name, photos, next_set_url) {
	// Are we at a URL with a image index greater than 1, e.g.:
	// http://emptysquare.net/photography/lower-east-side/#5/
	parts = document.location.href.split('#');
	
	// URL's image index is 1-based, our internal index is 0-based
	if (parts.length > 1) {
		imageId = parseInt(parts[1].replace('/', '')) - 1;
		if (imageId < 0) imageId = 0;
		if (imageId >= photos['photo'].length) imageId = photos['photo'].length - 1;
	} else {
		imageId = 0;
	}
	
	// Load current image first to maximize speed, then load remaining photos
	preloadImage(imageId, function() {
		for (var i = 0; i < photos['photo'].length; i++) {
			// Don't load the current image twice
			if (i != imageId) {
				preloadImage(i, null);
			}
		}
	});
	
	function navForward()  { navigate(+1, next_set_url); }
	function navBackward() { navigate(-1, next_set_url); }
    
    // Event handlers
    $("#navLeft").click(navBackward);
    $("#navRight, #imageContainer").click(navForward);
	
	navigateToImageId(next_set_url);
}
