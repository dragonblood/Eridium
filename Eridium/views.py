# libraries are imported
import os
# rendering the template using render
from django.shortcuts import render
# this will be used to get the path of the media folder from settings
from django.conf import settings
# for storing the file in the desired folder, FileSystemStorage is used  
from django.core.files.storage import FileSystemStorage
# this will handle MultiValueDictKeyError using try and except
from django.utils.datastructures import MultiValueDictKeyError
# using class from models.py
from django.templatetags.static import static

from django.views import View
from django.http.response import HttpResponse
from django.middleware.csrf import get_token

from .dubber import dub

from .models import Upload

def upload(request):
	# html = """
	# 	<form method="post" enctype="multipart/form-data">
	# 		<input type='text' style='display:none;' value='%s' name='csrfmiddlewaretoken'/>
	# 		<input type="file" name="video" accept="video/*">
	# 		<button type="submit">Upload video</button>
	# 	</form>
	# """ % (get_token(request))
	if request.method == 'POST':
		video_name = request.FILES['video']
		public_uri = Upload.upload_video(video_name, video_name.name)
		basename = video_name.name.split(".")[0]
		output = "op_videos"
		source_lang = request.POST.get('source_lang')
		source_speakers = request.POST.get('source_speakers')
		target_lang = request.POST.get('target_lang')
		storage='erridium_storage'
		hints = request.POST.get('hints')
		path ="gs://"+storage+"/"+"videos/"+video_name.name

		print(public_uri, basename, "gs://"+storage+"/"+video_name.name, source_lang, target_lang, storage, hints)
		dub(path, basename, output, source_lang, source_speakers, target_lang, storage, hints)

		return HttpResponse("<video controls src='%s'/>" % (public_uri))
		
	return render(request, 'Eridium.html')

# def post(self, request):
# 	video = request.FILES['video']
# 	public_uri = Upload.upload_video(video, video.name)
# 	return HttpResponse("<img src='%s'/>" % (public_uri))
