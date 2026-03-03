import geocoder

# Get live location using IP
location = geocoder.ip("me")

if location.latlng:
    print(f"Live Location: Latitude = {location.latlng[0]}, Longitude = {location.latlng[1]}")
else:
    print("Could not determine live location.")
