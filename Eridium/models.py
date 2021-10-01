from storages.backends.gcloud import GoogleCloudStorage
storage = GoogleCloudStorage()

class Upload:
	@staticmethod
	def upload_video(file, filename):
		try:
			target_path = '/videos/' + filename
			path = storage.save(target_path, file)
			return storage.url(path)
		except Exception as e:
			print("Failed to upload!")