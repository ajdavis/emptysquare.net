var imageId = 0;

/* Set imageId from the current URL
 * @return:                            false if browser must navigate to a new URL  
 */
function parse_imageId() {
	// URL is like http://emptysquare.net/photography/lower-east-side/#5/
	// fragment from http://benalman.com/code/projects/jquery-bbq/examples/fragment-basic/
	var fragment = $.param.fragment();
	if (fragment.length) {
		// URL's image index is 1-based, our internal index is 0-based
		imageId = parseInt(fragment.replace(/\//g, '')) - 1;
		if (imageId < 0 || isNaN(imageId)) imageId = 0;
	} else {
		imageId = 0;
	}
}

/* Show the proper image after updating imageId.
 * @param next_set_url:		Where to go after the final image
 */
function navigateToImageId(next_set_url) {
	var blank = '<img src="/static/images/blank.gif" height="9px" width="14px" />';
	
	parse_imageId();
	
	/**
	 *  Show or hide the left and right arrows depending on current position in
	 * list of photos - recall that our internal imageId is 0-indexed, but
	 * we use 1-based indices in the URL
	 */
	if (imageId == 0) {
		$("#navLeft").html(blank).removeAttr('href');
	} else {
		var navLeftHref = '#' + imageId + '/';
		
		// See http://benalman.com/code/projects/jquery-bbq/examples/fragment-advanced/
		$("#navLeft")
		.html('<img src="/static/images/goleft.gif" height="9px" width="14px" />')
		.attr('href', navLeftHref);
	}
	
	var navRightHref = null;
	if (imageId >= photos['photo'].length - 1) {
		navRightHref = next_set_url;
		$("#navRight").html(blank);
	} else {
		navRightHref = '#' + (imageId+2) + '/';
		
		$("#navRight").html('<img src="/static/images/goright.gif" height="9px" width="14px" />');
	}
	
	$("#navRight").attr('href', navRightHref);
	// Clicking the image container has same effect as right arrow
	$("#imageContainer a").attr('href', navRightHref);
	
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
	
	/** Update the URL for the Tweet Button -- change the URL from something like
	 * http://emptysquare.net/photography/fritz-christina/#1/
	 * to:
	 * http://emptysquare.net/photography/fritz-christina/1/
	 */
	var location = document.location.href.split('#')[0] + (imageId+1) + '/';
	var tweet_button = $('#tweet_button_container');
	
	tweet_button.html(
	'<a href="http://twitter.com/share" class="twitter-share-button" data-count="horizontal" data-via="jessejiryudavis">Tweet</a><script type="text/javascript" src="http://platform.twitter.com/widgets.js"></script>'
	);
	/** Update the URL for the Facebook Like button -- the like button ignores
	 * everything after the #, so change the URL from something like
	 * http://emptysquare.net/photography/fritz-christina/#1/
	 * to:
	 * http://emptysquare.net/photography/fritz-christina/1/
	 */
	$('#open_graph_image_property').attr('content', photos['photo'][imageId]['source']);
	
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
	
	/** Update the Flickr URL
	 */
	$('#flickr_link_container a').attr('href', photos['photo'][imageId]['flickr_url']);
	
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
	$("#imageContainer a").empty().append(image);
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
	// Order is critical here
	
	// Uses jQuery-BBQ
	// From http://benalman.com/code/projects/jquery-bbq/examples/fragment-basic/
	$(window).bind('hashchange', function(e) {
		navigateToImageId(next_set_url);
	})
	
	// Set the global imageId
	parse_imageId();
	
	// Load current image first to maximize speed, then load remaining photos
	preloadImage(imageId, function() {
		for (var i = 0; i < photos['photo'].length; i++) {
			// Don't load the current image twice
			if (i != imageId) {
				preloadImage(i, null);
			}
		}
	});
	
	// Since the event is only triggered when the hash changes, we need to trigger
	// the event now, to handle the hash the page may have loaded with.
	$(window).trigger( 'hashchange' );
}
