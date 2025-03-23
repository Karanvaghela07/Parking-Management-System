document.addEventListener("DOMContentLoaded", function() {
    var map = L.map('map').setView([20.5937, 78.9629], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    window.searchLocation = function() {
        var query = document.getElementById("locationSearch").value;
        if (query.trim() === "") {
            alert("Please enter a city or location in India.");
            return;
        }

        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}, India`)
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    var lat = data[0].lat;
                    var lon = data[0].lon;
                    map.setView([lat, lon], 12);

                    var marker = L.marker([lat, lon]).addTo(map)
                        .bindPopup(`<b>${query}</b><br><a href='/parking?location=${query}'>View Parking Layout</a>`)
                        .openPopup();
                } else {
                    alert("Location not found. Try another city.");
                }
            })
            .catch(error => console.error("Error:", error));
    };
});
