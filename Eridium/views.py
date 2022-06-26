from django.shortcuts import render
from django.http.response import HttpResponse
from .dubber import dub
from .models import Prepload
import os


def upload(request):
    if request.method == 'POST':
        video_name = request.FILES['video']
        # if video_name.size > 2000000:
        #     return HttpResponseBadRequest()

        try:
            os.mkdir('temp/audio')
        except:
            print("dir already exist")

        storage = 'erridium_storage'
        filename = video_name.name
        basename = filename.split(".")[0]

        Prepload.handle_uploaded_file(video_name, 'temp/' + filename)
        Prepload.file_parsing(video_name, filename, basename)
        Prepload.upload_video(video_name, filename, basename, storage)

        source_lang = request.POST.get('source_lang')
        source_speakers = request.POST.get('source_speakers')
        target_lang = request.POST.get('target_lang')
        hints = request.POST.get('hints')

        dub(filename, basename, storage, source_lang, target_lang, hints, speakerCount=source_speakers)
        Prepload.delete_files(filename, basename)
        return HttpResponse("<video controls src='%s'/>" % ("content/static/videos/" + "dubbed/" + filename))
        # Prepload.uploadYouTube(filename)

    return render(request, 'Eridium.html')

# def post(self, request):
# 	video = request.FILES['video']
# 	public_uri = Upload.upload_video(video, video.name)
# 	return HttpResponse("<img src='%s'/>" % (public_uri))
