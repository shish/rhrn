function rhrn_init(div_name) {
	// initialize the map on the "map" div with a given center and zoom
	var map = new L.Map(div_name, {
		center: new L.LatLng(51.5, -0.1),
		zoom: 10
	});

	// create a CloudMade tile layer
	//var cloudmadeUrl = 'http://{s}.tile.cloudmade.com/YOUR-API-KEY/997/256/{z}/{x}/{y}.png',
	var cloudmade = new L.TileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18});

	map.addLayer(cloudmade);

	if(window.rhrn_initpos && rhrn_initpos[0] && rhrn_initpos[1]) {
		map.setView(new L.LatLng(rhrn_initpos[0], rhrn_initpos[1]), 18);
	}
	else {
		setTimeout(function() {
			loadReviews(map.getBounds());
			map.locate({setView: true});
		}, 1000);
	}
	map.on('load', function(e) {            loadReviews(map.getBounds()); });
	map.on('dragend', function(e) {         loadReviews(map.getBounds()); });
	map.on('zoomend', function(e) {         loadReviews(map.getBounds()); });
	map.on('locationfound', function(e) {   loadReviews(map.getBounds()); });
	map.on('click', function(e) {
		newReview(e.latlng);
	});

	var FaceIcon = L.Icon.extend({
		iconUrl: "/static/img/happy.png",
		//shadowUrl: '../docs/images/leaf-shadow.png',
		shadowUrl: null,
		iconSize: new L.Point(32, 32),
		//shadowSize: new L.Point(68, 95),
		iconAnchor: new L.Point(16, 16),
		popupAnchor: new L.Point(0, -16)
	});
	var happyIcon = new FaceIcon("/static/img/happy.png");
	var sadIcon = new FaceIcon("/static/img/sad.png");

	var oldMarkers = [];
	var newMarkers = [];
	var markers = new L.LayerGroup();
	map.addLayer(markers);

	var lastBBox;
	function loadReviews(bbox) {
		if(bbox.toBBoxString() == lastBBox) return;
		lastBBox = bbox.toBBoxString();

		filter = $("#filter").val();

		console.log("Loading reviews for "+bbox.toBBoxString());
		newMarkers = [];
		jQuery.getJSON("/review", {"bbox": bbox.toBBoxString(), "filter": filter}, function(e) {
			console.log("Got", e.data.length, "results");
			jQuery(e.data).each(function(idx, el) {
				// rather than clear-all and re-add-all, keep track of what's
				// currently on-screen and re-use it if possible
				if(oldMarkers.hasOwnProperty("i"+el.id)) {
					newMarkers["i"+el.id] = oldMarkers["i"+el.id];
					return;
				}

				var m = new L.Marker(new L.LatLng(el.lat, el.lon));
				m.setIcon(el.happy ? happyIcon : sadIcon);
				var comment = (el.content ? el.content : "(No comment)");
				var commands = (
					(rhrn_username == el.writer || rhrn_username == "Shish") ?
					"<p><a href='#' onclick='delReview("+el.id+"); return false;'>Delete</a>" :
					""
				);
				var tags = [];
				if(feq(el.volume, 0.0)) tags.push("Quiet");
				if(feq(el.volume, 1.0)) tags.push("Loud");
				if(feq(el.danger, 0.0)) tags.push("Safe");
				if(feq(el.danger, 1.0)) tags.push("Dangerous");
				if(feq(el.crowds, 0.0)) tags.push("Empty");
				if(feq(el.crowds, 1.0)) tags.push("Crowded");
				m.bindPopup(
					"<table class='review'><tr>"+
						"<td class='writer'>"+
							"<img src='"+el.avatar+"'>"+
							"<br>"+el.writer+
						"</td>"+
						"<td>"+
							comment+
							"<p><i>"+el.date_posted+"</i>"+
							(tags ? "<p>"+tags.join(", ") : "")+
							commands+
						"</td>"+
					"</tr></table>"
				);
				newMarkers["i"+el.id] = m;
				markers.addLayer(m);
			});

			//console.log("current", oldMarkers);
			//console.log("new", newMarkers);
			for(var id in oldMarkers) {
				if(oldMarkers.hasOwnProperty(id)) {
					if(!newMarkers.hasOwnProperty(id)) {
						markers.removeLayer(oldMarkers[id]);
						delete oldMarkers[id];
					}
				}
			}
			oldMarkers = newMarkers;
		});
	}

	function newReview(latlng) {
		$.get("/review/new", {lat: latlng.lat, lon: latlng.lng}, function(data, textstatus, xhr) {
			var popup = new L.Popup();
			popup.setLatLng(latlng);
			popup.setContent(data);
			map.openPopup(popup);
		});
	}

	function submitReview(form_id) {
		var happy = $("input:radio[name='happy']:checked").val();
		var comment = $("input[name='comment']").val();
		var lon = $("input[name='lon']").val();
		var lat = $("input[name='lat']").val();
		var anon = $("input[name='anon']:checked").val();

		var volume = $("input:radio[name='volume']:checked").val();
		var danger = $("input:radio[name='danger']:checked").val();
		var crowds = $("input:radio[name='crowds']:checked").val();

		if(!happy) {
			alert("You must pick happy or sad");
			return;
		}
		$(form_id).html("Submitting review...");

		$.ajax({
			type: "POST",
			url: "/review",
			data: {
				"happy": happy,
				"comment": comment,
				"lat": lat,
				"lon": lon,
				"volume": volume,
				"danger": danger,
				"crowds": crowds,
				"anon": anon ? "on" : ""
			},
			success: function() {
				//display message back to user here
				refreshMap();
				map.closePopup();
			}
		});
	}

	function delReview(id) {
		$.ajax({
			type: "POST",
			url: "/review/"+id,
			data: {
				"_method": "DELETE",
			},
			success: function() {
				map.closePopup();
				refreshMap();
			}
		});
	}

	function refreshMap() {
		lastBBox = null;
		loadReviews(map.getBounds());
	}

	function feq(a, b) {
		if(a == null || b == null) return false;
		return Math.abs(a-b) < 0.001;
	}

	function setView(lat, lon) {
		map.setView(new L.LatLng(lat, lon), 16);
		refreshMap();
	}

	var heat = null;
	function setHeat(type) {
		if(heat) map.removeLayer(heat);

		if(type == "happiness") {
			heat = new L.TileLayer('/tiles/happiness/{z}/{x}/{y}.png', {maxZoom: 18});
			map.addLayer(heat);
		}
		else {
			heat = null;
		}
	}

	window.submitReview = submitReview;
	window.newReview = newReview;
	window.delReview = delReview;
	window.setView = setView;
	window.refreshMap = refreshMap;
	window.setHeat = setHeat;
}

function newReview() {
	if(navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(
			function(pos) {
				window.location.href = "http://m.ratehereratenow.com/review/new?lon="+pos.coords.longitude+"&lat="+pos.coords.latitude;
			},
			function(msg) {
				alert("Unable to find location: "+msg);
			}
		);
	}
	else {
		alert("Unable to find location: GPS not supported");
	}
}

function findLocal() {
	if(navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(
			function(pos) {
				window.location.href = "http://m.ratehereratenow.com/review?lon="+pos.coords.longitude+"&lat="+pos.coords.latitude;
			},
			function(msg) {
				alert("Unable to find location: "+msg);
			}
		);
	}
	else {
		alert("Unable to find location: GPS not supported");
	}
}
