# Using the Youtube API

from auth import client_id
from auth import client_secret

from googleapiclient.discovery import build
import google_auth_oauthlib
# import googleapiclient.errors
import os

# scope[0] -> read & write privilege
# scope[1] -> read-only privilege
scopes = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly"
]


class YoutubeEngine:
    def __init__(self):
        self.yt_client = self.get_client()
        self.playlists = self.get_playlists()
        self.song_collection = None

    def get_client(self):
        # disables OAuthlib's HTTP verification for local runs
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
        api_service_name = "youtube"
        api_version = "v3"

        # getting credentials and creating the API client
        credentials = google_auth_oauthlib.get_user_credentials(
            scopes[0],
            client_id,
            client_secret
        )
        client = build(
            api_service_name, api_version, credentials=credentials)

        return client

    def get_playlists(self):
        # returns a json containing data about the playlists of the user
        request = self.yt_client.playlists().list(
            part="snippet,contentDetails",
            maxResults=25,
            mine=True
        )
        response = request.execute()
        return response

    def look_up_playlist(self, playlist_name):
        for item in self.playlists["items"]:
            if item["snippet"]["title"].lower() == playlist_name.lower():
                # print("FOUND THE PLAYLIST! The id is: ")
                return item["id"]
        return -1

    # updates the song collection
    def get_songs(self, playlist_name):
        playlist_id = self.look_up_playlist(playlist_name)
        if playlist_id == -1:
            return None

        print(playlist_id)
        request = self.yt_client.playlistItems().list(
            part="snippet",
            maxResults=35,
            playlistId=playlist_id
        )
        # json containing the songs in the playlist
        response = request.execute()

        return response

    def export(self, playlist_name):
        self.song_collection = self.get_songs(playlist_name)
        # print(self.song_collection)


if __name__ == "__main__":
    youtube_engine = YoutubeEngine()
    playlist_to_export = input("Insert the name of a Youtube playlist you would like to export to Spotify: ")

    # exits the loop when the playlist is valid
    while youtube_engine.look_up_playlist(playlist_to_export) == -1:
        playlist_to_export = input("Playlist not found :(. Try another one: ")

    youtube_engine.export(playlist_to_export)

    print("Thank you for using HeardItSomewhere! See you next time!")
