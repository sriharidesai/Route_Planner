import tkinter as tk
from tkinter import messagebox
import requests
import folium
import webbrowser
import geocoder
import numpy as np
from sklearn.cluster import KMeans
from geopy.geocoders import Nominatim
import openrouteservice
from PIL import Image, ImageTk

# OpenRouteService API Key (Get from https://openrouteservice.org/sign-up/)
ORS_API_KEY = "5b3ce3597851110001cf62486695a7adefb840c6bf2bae220febafaf"
client = openrouteservice.Client(key=ORS_API_KEY)

def get_live_location():
    """Get user's live location using IP-based geolocation."""
    g = geocoder.ip("me")
    return g.latlng  # Returns [latitude, longitude]

def get_famous_places(city):
    """Fetch famous monuments & landmarks from OpenStreetMap using Overpass API."""
    geolocator = Nominatim(user_agent="your_project_name")
    location = geolocator.geocode(city, timeout=10)  # Timeout to avoid hanging

    if not location:
        print("City not found! Please check the city name.")
        return []

    lat, lon = location.latitude, location.longitude

    query = f"""
    [out:json];
    area[name="{city}"]->.searchArea;
    (
      node["tourism"="attraction"](area.searchArea);
      node["historic"="monument"](area.searchArea);
      node["historic"="memorial"](area.searchArea);
      node["heritage"="1"](area.searchArea);
    );
    out center;
    """
    url = "http://overpass-api.de/api/interpreter"

    try:
        response = requests.get(url, params={'data': query}, timeout=10)  # Timeout handling
        response.raise_for_status()  # Check HTTP errors
        
        if response.text.strip() == "":
            print("Empty response received from API.")
            return []

        data = response.json()
        places = []
        
        for element in data.get("elements", []):
            if "tags" in element and "name" in element["tags"]:
                place_name = element["tags"]["name"]
                lat, lon = element["lat"], element["lon"]
                rating = float(element["tags"].get("rating", 0))  # Get rating (if available)
                places.append((place_name, lat, lon, rating))
        
        # Sort by ratings (higher first), pick top 10
        places = sorted(places, key=lambda x: x[3], reverse=True)[:10]
        return places

    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {e}")
        return []

def sort_by_distance(start_location, places):
    """Sort places by shortest distance from the starting point."""
    distances = []
    for place in places:
        lat, lon = place[1], place[2]
        distance = np.linalg.norm(np.array(start_location) - np.array([lat, lon]))
        distances.append((distance, place))
    
    sorted_places = [place for _, place in sorted(distances)]
    return sorted_places

def get_shortest_route(start_location, places):
    """Find the shortest route using OpenRouteService."""
    coordinates = [[start_location[1], start_location[0]]] + [[lng, lat] for _, lat, lng, _ in places]
    
    try:
        route = client.directions(coordinates=coordinates, profile="driving-car", format="geojson")
        return route
    except openrouteservice.exceptions.ApiError as e:
        print(f"OpenRouteService Error: {e}")
        return None

def plot_map(start_location, places, route):
    """Plot the travel route on an interactive map."""
    map_object = folium.Map(location=start_location, zoom_start=12)
    folium.Marker(start_location, tooltip="Current Location", icon=folium.Icon(color='green')).add_to(map_object)

    for place in places:
        folium.Marker([place[1], place[2]], tooltip=place[0]).add_to(map_object)

    if route:
        folium.PolyLine([(coord[1], coord[0]) for coord in route['features'][0]['geometry']['coordinates']], 
                        color="red", weight=2.5).add_to(map_object)

    map_object.save("route_map.html")
    webbrowser.open("route_map.html")

def start_navigation():
    """Handle UI button click: fetch location, find places, calculate route."""
    city = city_entry.get()
    if not city:
        messagebox.showerror("Error", "Please enter a city")
        return

    messagebox.showinfo("Fetching Data", "Getting live location and fetching routes...")
    
    start_location = get_live_location()
    places = get_famous_places(city)

    if not places:
        messagebox.showerror("Error", "No famous places found in this city")
        return

    sorted_places = sort_by_distance(start_location, places)
    route = get_shortest_route(start_location, sorted_places)

    # Display travel list
    travel_list_text = "Travel Order:\n\n"
    for idx, place in enumerate(sorted_places, 1):
        travel_list_text += f"{idx}. {place[0]} (Rating: {place[3]})\n"

    messagebox.showinfo("Travel Order", travel_list_text)

    plot_map(start_location, sorted_places, route)


def create_ui():
    """Create the graphical user interface."""
    global city_entry
    root = tk.Tk()
    root.title("Smart Travel Route Planner")
    root.geometry("400x300")

    # Load Background Image
    bg_image = Image.open("rp2.jpg")  # Change to your image file
    bg_image = bg_image.resize((650, 550))   # Resize to fit window
    bg_photo = ImageTk.PhotoImage(bg_image)

    # Set Background
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.place(relwidth=1, relheight=1)  # Cover full window

    # Add Widgets on top of Background
    tk.Label(root, text="Enter City:", bg="white").pack(pady=5)
    city_entry = tk.Entry(root)
    city_entry.pack(pady=5)

    tk.Button(root, text="Find Route", command=start_navigation).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_ui()
