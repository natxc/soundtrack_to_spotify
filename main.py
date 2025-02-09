import requests
import json
import base64
import webbrowser
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

def main():

    ### ------------------ Authorization ------------------  ###
    load_dotenv()

    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    SCOPES = os.getenv("SCOPES")
    SPOTIFY_API_URL = "https://api.spotify.com/v1"

    SOUNDTRACK_EMAIL = os.getenv("SOUNDTRACK_EMAIL")
    SOUNDTRACK_PASSWORD = os.getenv("SOUNDTRACK_PASSWORD")
    SOUNDTRACK_API_URL = "https://api.soundtrackyourbrand.com/v2"

    # Run the Authorization Flow for Spotify
    def get_user_authorization():
        auth_url = "https://accounts.spotify.com/authorize"
        params = {
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "show_dialog": True,
        }
        webbrowser.open(f"{auth_url}?{urlencode(params)}")
        print(
            "\n Opened Spotify login page. After login, check the URL for the `code` parameter."
        )
        print("Copy the code from the URL and paste it below:")

    def get_access_token(auth_code):
        token_url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET,
        }

        response = requests.post(token_url, headers=headers, data=data)

        if response.status_code == 200:
            tokens = response.json()
            print(
                "\n NEW ACCESS TOKEN (WITH PLAYLIST PERMISSIONS):", tokens["access_token"]
            )
            return tokens["access_token"]
        else:
            print("Failed to get access token:", response.text)
            return None

    def get_spotify_user_id(access_token):
        url = "https://api.spotify.com/v1/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user_id = response.json().get("id")
            print("Spotify User ID:", user_id)
            return user_id
        else:
            print("Failed to fetch Spotify User ID:", response.status_code, response.text)
            return None

    get_user_authorization()
    auth_code = input("\nEnter the authorization code from the URL: ").strip()
    SPOTIFY_ACCESS_TOKEN = get_access_token(auth_code)

    if SPOTIFY_ACCESS_TOKEN:
        SPOTIFY_USER_ID = get_spotify_user_id(SPOTIFY_ACCESS_TOKEN)

    # Run the Authorization Flow for Soundtrack
    login_query = {
        "query": f"""
        mutation {{
        loginUser(input: {{email: "{SOUNDTRACK_EMAIL}", password: "{SOUNDTRACK_PASSWORD}"}}) {{
            token
            refreshToken
        }}
        }}
        """
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        "https://api.soundtrackyourbrand.com/v2", headers=headers, json=login_query
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("data", {}).get("loginUser", {}).get("token")
        refresh_token = data.get("data", {}).get("loginUser", {}).get("refreshToken")

        if token:
            print("Authentication Successful!")
            print(f"Token: {token}")
            print(f"Refresh Token: {refresh_token}")
            SOUNDTRACK_API_TOKEN = refresh_token
        else:
            print("Failed to retrieve token.")
    else:
        print(f"Login failed: {response.status_code} - {response.text}")

    ### ------------------ Search for tracks on Soundtrack ------------------  ###
    def search_tracks(track_name):
        query = {
            "query": f"""
            query {{
            search(query: "{track_name}", type: track) {{
                edges {{
                node {{
                    ... on Track {{
                    id
                    title
                    artists {{
                        name
                    }}
                    }}
                }}
                }}
            }}
            }}
            """
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SOUNDTRACK_API_TOKEN}",
        }

        response = requests.post(SOUNDTRACK_API_URL, headers=headers, json=query)

        if response.status_code == 200:
            data = response.json()

            tracks = [
                {
                    "id": edge["node"]["id"],
                    "title": edge["node"]["title"],
                    "artist": ", ".join(
                        artist["name"] for artist in edge["node"]["artists"]
                    ),
                }
                for edge in data.get("data", {}).get("search", {}).get("edges", [])
            ]

            if not tracks:
                print("No tracks found.")
                return None

            print("\n Select a track:")
            for i, track in enumerate(tracks):
                print(f"{i+1}. {track['title']} - {track['artist']} (ID: {track['id']})")

            while True:
                try:
                    choice = int(input("\nEnter track number: ")) - 1
                    if 0 <= choice < len(tracks):
                        selected_track = tracks[choice]
                        print(
                            f"\n Selected Track: {selected_track['title']} - {selected_track['artist']} (ID: {selected_track['id']})"
                        )
                        return selected_track["id"]
                    else:
                        print("Invalid choice. Please select a valid number.")
                except ValueError:
                    print("Please enter a number.")

        else:
            print("Failed to search for track:", response.status_code, response.text)
            return None

    track_title = input("\nEnter track title: ")
    track_id = search_tracks(track_title)

    ### ------------------ Search for playlists on Soundtrack ------------------  ###
    def get_playlists_containing_track(track_id):
        query = {
            "query": f"""
            query {{
            search(query: "{track_id}", type: playlist) {{
                edges {{
                node {{
                    ... on Playlist {{
                    id
                    name
                    description
                    }}
                }}
                }}
            }}
            }}
            """
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SOUNDTRACK_API_TOKEN}",
        }

        response = requests.post(SOUNDTRACK_API_URL, headers=headers, json=query)

        if response.status_code == 200:
            print(response.json())
            playlists = response.json().get("data", {}).get("search", {}).get("edges", [])

            return [
                {
                    "id": p["node"]["id"],
                    "name": p["node"]["name"],
                    "description": p["node"]["description"],
                }
                for p in playlists
            ]
        else:
            print("Failed to fetch playlists:", response.status_code, response.text)
            return []

    playlists = get_playlists_containing_track(track_id)

    if not playlists:
        print("No playlists found for this track.")
        exit()

    print("\nSelect a playlist:")
    for i, playlist in enumerate(playlists):
        print(f"{i+1}. {playlist['name']}")

    playlist_choice = int(input("\nEnter playlist number: ")) - 1
    selected_playlist = playlists[playlist_choice]

    print(f"\nSelected Playlist: {selected_playlist['name']}")

    ### ------------------ Retrieve tracks from playlist ------------------  ###
    def get_tracks_from_playlist(playlist_id):
        query = {
            "query": f"""
            query {{
            playlist(id: "{playlist_id}") {{
                id
                name
                description
                tracks(first: 1000) {{  # <-- Added 'first' parameter
                edges {{
                    node {{
                    id
                    title
                    artists {{
                        name
                    }}
                    }}
                }}
                }}
            }}
            }}
            """
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SOUNDTRACK_API_TOKEN}",
        }

        response = requests.post(
            SOUNDTRACK_API_URL, headers=headers, data=json.dumps(query)
        )

        if response.status_code == 200:
            return response.json().get("data", {}).get("playlist", {}).get("tracks", [])
        else:
            print("Failed to fetch tracks:", response.status_code, response.text)
            return []

    tracks = get_tracks_from_playlist(selected_playlist["id"])

    print(f"\nFound {len(tracks['edges'])} tracks in the playlist.")

    ### ------------------ Search for tracks on Spotify ------------------  ###
    def search_spotify_track(track_name, artist_name):
        query = f"{track_name} artist:{artist_name}"
        url = f"{SPOTIFY_API_URL}/search?q={query}&type=track&limit=1"

        headers = {"Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get("tracks", {}).get("items", [])
            return items[0]["uri"] if items else None
        else:
            print("Spotify search failed:", response.status_code, response.text)
            return None

    spotify_track_uris = []
    for t in tracks["edges"]:
        track_name = t["node"]["title"]
        artist_name = t["node"]["artists"][0]["name"]  # Get first artist

        uri = search_spotify_track(track_name, artist_name)
        if uri:
            spotify_track_uris.append(uri)

    print(f"\nSearching Spotify now...")
    print(f"\n Found {len(spotify_track_uris)} matching tracks on Spotify.")

    ### ------------------ Create a Spotify playlist ------------------  ###
    def create_spotify_playlist(name, access_token, user_id): # description
        url = f"https://api.spotify.com/v1/users/{user_id}/playlists"

        payload = {
            "name": name,
    #         "description": "",
            "public": False
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            playlist_id = response.json()["id"]
            print(f" Created Spotify Playlist: {name} (ID: {playlist_id})")
            return playlist_id
        else:
            print("Failed to create Spotify playlist:", response.status_code, response.text)
            return None
    
    playlist_name = input("What would you like your playlist to be called: ")
    
    spotify_playlist_id = create_spotify_playlist(playlist_name, SPOTIFY_ACCESS_TOKEN, SPOTIFY_USER_ID)

    ### ------------------ Add tracks to Spotify playlist ------------------  ###
    def add_tracks_to_spotify_playlist(playlist_id, track_uris):
        url = f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks"

        payload = {"uris": track_uris}

        headers = {
            "Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            print("Tracks added successfully.")
        else:
            print("Failed to add tracks:", response.status_code, response.text)

    add_tracks_to_spotify_playlist(spotify_playlist_id, spotify_track_uris[:10]) # or however many they allow

    ### ------------------ Upload custom playlist image ------------------  ###
    def upload_spotify_playlist_cover(playlist_id, image_source):
        if image_source.startswith("http"):
            response = requests.get(image_source)
            if response.status_code == 200:
                image_data = response.content
            else:
                print(
                    " Failed to download image from URL:",
                    response.status_code,
                    response.text,
                )
                return
        else:
            with open(image_source, "rb") as image_file:
                image_data = image_file.read()

        encoded_image = base64.b64encode(image_data).decode("utf-8")

        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"

        headers = {
            "Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}",
            "Content-Type": "image/jpeg",
        }

        response = requests.put(url, headers=headers, data=encoded_image)

        if response.status_code == 202:
            print("Playlist cover uploaded successfully.")
        else:
            print("Failed to upload cover:", response.status_code, response.text)

    image_source = input("Enter the path or url for the image: ")

    upload_spotify_playlist_cover(
        spotify_playlist_id,
        image_source,
    )

if __name__ == "__main__":
    main()
