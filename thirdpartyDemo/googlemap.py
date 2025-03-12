import requests
import json
import os
import sys


class GeocodeFinder:
    """
    Use Google Maps Geocoding API to find coordinates by place name
    """

    def __init__(self, api_key):
        """Initialize Geocode finder

        Args:
            api_key (str): Google Maps API key
        """
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def get_coordinates(self, place_name, region=None, language="en"):
        """
        Query coordinates by place name and print all results

        Args:
            place_name (str): Place name or address
            region (str, optional): Preferred region code, e.g., "us"
            language (str, optional): Result language, default is "en"
        """
        # Build parameters
        params = {
            "address": place_name,
            "key": self.api_key,
            "language": language
        }

        if region:
            params["region"] = region

        # Send request
        response = requests.get(self.base_url, params=params)

        # Parse response
        result = response.json()

        # Print status
        print(f"\nStatus: {result['status']}")

        if result["status"] == "OK":
            # Print all results
            print(f"\nFound {len(result['results'])} results for: {place_name}\n")

            for i, location in enumerate(result['results']):
                print(f"Result #{i + 1}:")
                print(f"  Formatted Address: {location['formatted_address']}")

                # Print coordinates
                lat = location['geometry']['location']['lat']
                lng = location['geometry']['location']['lng']
                print(f"  Coordinates: {lat}, {lng}")

                # Print location type (precise or approximate)
                location_type = location['geometry']['location_type']
                print(f"  Location Type: {location_type}")

                # Print address components
                print("  Address Components:")
                for component in location['address_components']:
                    types = ", ".join(component['types'])
                    print(f"    • {component['long_name']} ({types})")

                # Print place ID
                print(f"  Place ID: {location['place_id']}")

                # Print types
                print(f"  Types: {', '.join(location['types'])}")

                # Print viewport
                viewport = location['geometry']['viewport']
                print(f"  Viewport: Northeast {viewport['northeast']}, Southwest {viewport['southwest']}")

                # Check if there are additional location types
                if 'bounds' in location['geometry']:
                    print(f"  Bounds Available: Yes")

                # Print partial match info if available
                if 'partial_match' in location:
                    print(f"  Partial Match: {location['partial_match']}")

                print("\n" + "-" * 50 + "\n")
        else:
            # Handle error
            print(f"Query failed: {result['status']}")
            if 'error_message' in result:
                print(f"Error message: {result['error_message']}")


def main():
    """Main function to run the geocoding tool"""

    # Ask for API key if not provided
    api_key = "AIzaSyD4K_0sPAIWmIE8jandYAlaNqMSTu9jAOY"  # Use the provided API key

    # Ask for place name
    place_name = input("Enter a place name or address to geocode: ")

    # Create geocoder and get results
    try:
        geocoder = GeocodeFinder(api_key)
        geocoder.get_coordinates(place_name)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    main()