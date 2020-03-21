# Using the Youtube API
# coding=utf-8

import re
import json
import requests
import spotipy

from auth import client_id
from auth import client_secret
from auth import spotify_token

from googleapiclient.discovery import build
import google_auth_oauthlib
# import googleapiclient.errors
import os
import youtube_dl

# scope[0] -> read & write privilege
# scope[1] -> read-only privilege
scopes = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly"
]


# contains all logic related to the youtube client
class YoutubeEngine:
    def __init__(self):
        self.yt_client = self.get_client(self)
        self.playlists = self.get_playlists()

    @staticmethod
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
                return item["id"]
        return -1

    # returns a dictionary containing song data (song_name & artist)
    def get_songs(self, playlist_name, song_collection):
        playlist_id = self.look_up_playlist(playlist_name)
        if playlist_id == -1:
            return None

        request = self.yt_client.playlistItems().list(
            part="snippet",
            maxResults=35,
            playlistId=playlist_id
        )
        # json containing the songs in the playlist
        response = request.execute()

        # we need to parse the json in order to extract the data we need (song_name & artist)
        for item in response["items"]:
            id = item["snippet"]["resourceId"]["videoId"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(id)
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            # some songs might not have the song name & artist set up
            # so they will be skipped because their query would generate incorrect responses
            if video["artist"] is not None and video["track"] is not None:
                artist = re.sub(r'\W+', ' ', video["artist"])
                track = re.sub(r'\W+', ' ', video["track"])
                print(artist + "          " + track)
                song_collection[id] = {
                    "artist": artist,
                    "track": track
                }


#  contains the general logic of the app
class AppEngine:
    def __init__(self):
        self.youtube_engine = YoutubeEngine()
        self.spotify_engine = SpotifyEngine()
        self.song_collection = {}

    # the song collection gets updated
    def gather_data(self, playlist_name):
        self.youtube_engine.get_songs(playlist_name, self.song_collection)
        print(self.song_collection)

    def input_playlist(self):
        playlist_to_look_up = input("Insert the name of a Youtube playlist you would like to export to Spotify: ")
        while self.youtube_engine.look_up_playlist(playlist_to_look_up) == -1:
            playlist_to_look_up = input("Playlist not found :(. Try another one: ")
        return playlist_to_look_up

    def run(self):
        self.gather_data(self.input_playlist())
        self.export()

    def export(self):
        self.spotify_engine.add_songs_to_playlist(self.song_collection)


class SpotifyEngine:
    def __init__(self):
        self.extra = Extra()

    # creates a new playlist and returns its id
    def create_spotify_playlist(self, user_id, playlist_name):
        request = json.dumps({
            "name": playlist_name,
            "description": "Playlist imported from Youtube through HeardItSomewhere",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            user_id
        )
        response = requests.post(
            query,
            data=request,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        return response.json()["id"]

    # returns the song uris of a given song & artist
    def get_song_uri(self, track, artist):
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track".format(
            track,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response = response.json()
        # case in which no tracks are found
        if response["tracks"]["total"] == 0:
            return None
        return response["tracks"]["items"][0]["id"]

    def fetch_all_uri(self, song_collection):
        uris = []
        for key in song_collection.keys():
            uri = self.get_song_uri(song_collection[key]["track"], song_collection[key]["artist"])
            if uri is not None:
                uris.append(uri)
        return uris

    def add_songs_to_playlist(self, song_collection):
        user_id = input("Please type in your spotify user id: ")
        playlist_name = input("What would you like to call your Spotify playlist? ")
        playlist_id = self.create_spotify_playlist(user_id, playlist_name)
        uris = self.fetch_all_uri(song_collection)

        request = json.dumps(uris)
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id
        )
        response = requests.post(
            query,
            data=request,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        if response.status_code != 200:
            print("asta este!")

        response = response.json()
        print(response)
        return response


class Extra:
    def __init__(self):
        pass

    def strip_korean(self, string):
        en_list = re.findall(u'[^\uAC00-\uD7A3]', string)
        for c in string:
            if c not in en_list:
                string = string.replace(c, '')
        return string

    def strip_japanese(self, string):
        en_list = re.findall(u'[^\3040-\u309F]', string)
        for c in string:
            if c not in en_list:
                string = string.replace(c, '')
        return string

    def strip_chinese(self, string):
        en_list = re.findall(u'[^\u4E00-\u9FA5]', string)
        for c in string:
            if c not in en_list:
                string = string.replace(c, '')
        return string


if __name__ == "__main__":
    AppEngine().run()
    print("Thank you for using HeardItSomewhere! See you next time!")

