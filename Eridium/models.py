from google.cloud import storage
import requests
import ffmpeg
import os
from subprocess import *
from django.conf import settings

storage_client = storage.Client()


class Prepload:
    @staticmethod
    def upload_video(video_file, filename, basename, bucket_name):

        # path to save video and audio
        destination_blob_name_video = "videos/" + filename
        destination_blob_name_audio = "audios/" + basename + ".wav"

        bucket = storage_client.bucket(bucket_name)

        # upload
        blob_video = bucket.blob(destination_blob_name_video)
        blob_video.upload_from_filename("temp/output/" + filename)

        blob_audio = bucket.blob(destination_blob_name_audio)
        blob_audio.upload_from_filename("temp/output/" + basename + ".wav")

        return None

    def handle_uploaded_file(f, filename):
        with open(filename, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

    def file_parsing(video_name, filename, basename):
        stream = ffmpeg.input('temp/' + filename)

        # audio file
        audio_file = ffmpeg.output(stream.audio, 'temp/output/' + basename + ".wav", ac=1).run(overwrite_output=True)
        # video file
        video_file = ffmpeg.output(stream.video, 'temp/output/' + filename).run(overwrite_output=True)

    def delete_files(filename, basename):
        folder_path = 'temp/audio'
        if os.path.exists(folder_path):
            print("audio does exist as it should")
            # checking whether the folder is empty or not
            if len(os.listdir(folder_path)) == 0:
                print("the no of file is not zero")
                # removing the file using the os.remove() method
                os.rmdir(folder_path)
                print("the dir has been removed")

        os.remove("temp/" + filename)
        os.remove("temp/output/" + filename)
        os.remove("temp/output/" + basename + ".wav")

    def uploadYouTube(filename):
        # upload to youtube
        url = 'https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status'
        headers = {'Authorization': 'Bearer ' + settings.YOUTUBE_API_KEY}
        data = {
            'snippet': {
                'title': filename,
                'description': 'Automatically dubbed using Project Eridium at eriridum.vipulpetkar.me',
                'tags': ['Eridium', 'Eridium'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }
        files = {'video': open('temp/dubbed' + filename, 'rb')}
        response = requests.post(url, data=data, headers=headers, files=files)
        return response.json()
