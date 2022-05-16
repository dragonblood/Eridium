from pydub import AudioSegment
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from google.cloud import translate_v2 as translate
from google.cloud import storage
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip, TextClip
import os
import ffmpeg
import json
import tempfile
from dotenv import load_dotenv
import html

# Load config in .env file
load_dotenv()


def get_transcripts_json(gcsPath, langCode, phraseHints=[], speakerCount = 1, enhancedModel=None):
    print(speakerCount)
    """Transcribes audio files.
    Args:
        gcsPath (String): path to file in cloud storage (i.e. "gs://audio/clip.mp4")
        langCode (String): language code (i.e. "en-US", see https://cloud.google.com/speech-to-text/docs/languages)
        phraseHints (String[]): list of words that are unusual but likely to appear in the audio file.
        speakerCount (int, optional): Number of speakers in the audio. Only works on English. Defaults to None.
        enhancedModel (String, optional): Option to use an enhanced speech model, i.e. "video"
    Returns:
        list | Operation.error
    """

    # Helper function for simplifying Google speech client response
    def _jsonify(result):
        json = []
        for section in result.results:
            data = {
                "transcript": section.alternatives[0].transcript,
                "words": []
            }
            for word in section.alternatives[0].words:
                data["words"].append({
                    "word": word.word,
                    "start_time": word.start_time.total_seconds(),
                    "end_time": word.end_time.total_seconds(),
                    "speaker_tag": word.speaker_tag
                })
            json.append(data)
        return json

    client = speech.SpeechClient()  
    audio = speech.RecognitionAudio(uri=gcsPath)
    speakerCount = int(speakerCount)

    diarize = speakerCount if speakerCount > 1 else False
    print(f"Diarizing: {diarize}")
    diarizationConfig = speech.SpeakerDiarizationConfig(
        enable_speaker_diarization=speakerCount if speakerCount > 1 else False,
    )

    # In English only, we can use the optimized video model
    if langCode == "en":
        enhancedModel = "video"

    config = speech.RecognitionConfig(
        language_code="en-US" if langCode == "en" else langCode,
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        speech_contexts=[{
            "phrases": phraseHints,
            "boost": 15
        }],
        diarization_config=diarizationConfig,
        profanity_filter=True,
        use_enhanced=True if enhancedModel else False,
        model="video" if enhancedModel else None

    )
    res = client.long_running_recognize(config=config, audio=audio).result()

    return _jsonify(res)

def parse_sentence_with_speaker(json, lang):
    """Takes json from get_transcripts_json and breaks it into sentences
    spoken by a single person. Sentences deliniated by a >= 1 second pause/
    Args:
        json (string[]): [{"transcript": "lalala", "words": [{"word": "la", "start_time": 20, "end_time": 21, "speaker_tag: 2}]}]
        lang (string): language code, i.e. "en"
    Returns:
        string[]: [{"sentence": "lalala", "speaker": 1, "start_time": 20, "end_time": 21}]
    """

    # Special case for parsing japanese words
    def get_word(word, lang):
        if lang == "ja":
            return word.split('|')[0]
        return word

    sentences = []
    sentence = {}
    for result in json:
        for i, word in enumerate(result['words']):
            wordText = get_word(word['word'], lang)
            if not sentence:
                sentence = {
                    lang: [wordText],
                    'speaker': word['speaker_tag'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time']
                }
            # If we have a new speaker, save the sentence and create a new one:
            elif word['speaker_tag'] != sentence['speaker']:
                sentence[lang] = ' '.join(sentence[lang])
                sentences.append(sentence)
                sentence = {
                    lang: [wordText],
                    'speaker': word['speaker_tag'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time']
                }
            else:
                sentence[lang].append(wordText)
                sentence['end_time'] = word['end_time']

            # If there's greater than one second gap, assume this is a new sentence
            if i+1 < len(result['words']) and word['end_time'] < result['words'][i+1]['start_time']:
                sentence[lang] = ' '.join(sentence[lang])
                sentences.append(sentence)
                sentence = {}
        if sentence:
            sentence[lang] = ' '.join(sentence[lang])
            sentences.append(sentence)
            sentence = {}

    return sentences

def translate_text(input, targetLang, sourceLang=None):
    """Translates from sourceLang to targetLang. If sourceLang is empty,
    it will be auto-detected.
    Args:
        sentence (String): Sentence to translate
        targetLang (String): i.e. "en"
        sourceLang (String, optional): i.e. "es" Defaults to None.
    Returns:
        String: translated text
    """

    translate_client = translate.Client()
    result = translate_client.translate(
        input, target_language=targetLang, source_language=sourceLang)

    return html.unescape(result['translatedText'])

def speak(text, languageCode, voiceName=None, speakingRate=1):
    """Converts text to audio
    Args:
        text (String): Text to be spoken
        languageCode (String): Language (i.e. "en")
        voiceName: (String, optional): See https://cloud.google.com/text-to-speech/docs/voices
        speakingRate: (int, optional): speed up or slow down speaking
    Returns:
        bytes : Audio in wav format
    """

    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    if not voiceName:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, name=voiceName
        )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speakingRate
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content

def speakUnderDuration(text, languageCode, durationSecs, voiceName=None):
    """Speak text within a certain time limit.
    If audio already fits within duratinSecs, no changes will be made.
    Args:
        text (String): Text to be spoken
        languageCode (String): language code, i.e. "en"
        durationSecs (int): Time limit in seconds
        voiceName (String, optional): See https://cloud.google.com/text-to-speech/docs/voices
    Returns:
        bytes : Audio in wav format
    """
    baseAudio = speak(text, languageCode, voiceName=voiceName)
    assert len(baseAudio)
    f = tempfile.NamedTemporaryFile(mode="w+b")
    f.write(baseAudio)
    f.flush()
    baseDuration = AudioSegment.from_mp3(f.name).duration_seconds
    f.close()
    ratio = baseDuration / durationSecs

    # if the audio fits, return it
    if ratio <= 1:
        return baseAudio

    # If the base audio is too long to fit in the segment...

    # round to one decimal point and go a little faster to be safe,
    ratio = round(ratio, 1)
    if ratio > 4:
        ratio = 4
    return speak(text, languageCode, voiceName=voiceName, speakingRate=ratio)

def toSrt(transcripts, charsPerLine=60):
    """Converts transcripts to SRT an SRT file. Only intended to work
    with English.
    Args:
        transcripts ({}): Transcripts returned from Speech API
        charsPerLine (int): max number of chars to write per line
    Returns:
        String srt data
    """

    """
    SRT files have this format:
    [Section of subtitles number]
    [Time the subtitle is displayed begins] –> [Time the subtitle is displayed ends]
    [Subtitle]
    Timestamps are in the format:
    [hours]: [minutes]: [seconds], [milliseconds]
    Note: about 60 characters comfortably fit on one line
    for resolution 1920x1080 with font size 40 pt.
    """

    def _srtTime(seconds):
        millisecs = seconds * 1000
        seconds, millisecs = divmod(millisecs, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%d:%d:%d,%d" % (hours, minutes, seconds, millisecs)

    def _toSrt(words, startTime, endTime, index):
        return f"{index}\n" + _srtTime(startTime) + " --> " + _srtTime(endTime) + f"\n{words}"

    startTime = None
    sentence = ""
    srt = []
    index = 1
    for word in [word for x in transcripts for word in x['words']]:
        if not startTime:
            startTime = word['start_time']

        sentence += " " + word['word']

        if len(sentence) > charsPerLine:
            srt.append(_toSrt(sentence, startTime, word['end_time'], index))
            index += 1
            sentence = ""
            startTime = None

    if len(sentence):
        srt.append(_toSrt(sentence, startTime, word['end_time'], index))

    return '\n\n'.join(srt)

def stitch_audio(sentences, audioDir, filename, outFile, storage_client, srtPath=None, overlayGain=-30, bucket_name=None):

    """Combines sentences, audio clips, and video file into the ultimate dubbed video
    Args:
        sentences (list): Output of parse_sentence_with_speaker
        audioDir (String): Directory containing generated audio files to stitch together
        movieFile (String): Path to movie file to dub.
        outFile (String): Where to write dubbed movie.
        srtPath (String, optional): Path to transcript/srt file, if desired.
        overlayGain (int, optional): How quiet to make source audio when overlaying dubs. 
            Defaults to -30.
    Returns:
       void : Writes movie file to outFile path
    """

    # # Files in the audioDir should be labeled 0.wav, 1.wav, etc.
    audioFiles = storage_client.list_blobs(bucket_name, prefix=audioDir)
    audioFiles = sorted([int(f.name.split('/')[-1].split('.')[0]) for f in audioFiles])

    # Grab the computer-generated audio file
    bucket = storage_client.bucket(bucket_name)
    # os.mkdir('temp/audio')

    segments = []
    for x in audioFiles:
        x = str(x)
        blob = bucket.blob(f"{audioDir}{x}.mp3")
        blob.download_to_filename("temp/audio/"+x+".mp3")
        # blob = bucket.get_blob(f"{audioDir}{x}.mp3")
        # file = blob.download_as_bytes()
        # file = io.BytesIO(file)
        # print(file)
        # segments = AudioSegment.from_mp3()#.export(f"{audioDir}/{x}.wav", format="wav")

        segments.append(AudioSegment.from_mp3("temp/audio/"+x+".mp3"))
        print(segments)

    # segments = [bucket.blob(os.path.join(audioDir, str(x)+".mp3")).download_to_file)) for x in audioFiles]

    # # Also, grab the original audio
    # blob = bucket.blob("videos/"+filename)
    # blob.download_to_filename(filename)
    # # file = io.BytesIO(file)
    dubbed = AudioSegment.from_file('temp/'+filename)

    # Place each computer-generated audio at the correct timestamp
    for sentence, segment in zip(sentences, segments):
        dubbed = dubbed.overlay(
            segment, position=sentence['start_time'] * 1000, gain_during_overlay=overlayGain)

    # Write the final audio to a temporary output file
    audioFile = tempfile.NamedTemporaryFile()
    dubbed.export(audioFile)
    audioFile.flush()

    # Add the new audio to the video and save it
    clip = ffmpeg.input('temp/output/'+filename)
    audio = ffmpeg.input(audioFile.name)

    # Add transcripts, if supplied
    srtPath = False
    if srtPath:
        width, height = clip.size[0] * 0.75, clip.size[1] * 0.20
        def generator(txt): return TextClip(txt, font='Georgia-Regular',
                                            size=[width, height], color='black', method="caption")
        subtitles = SubtitlesClip(
            srtPath, generator).set_pos(("center", "bottom"))
        clip = CompositeVideoClip([clip, subtitles])
    outfile = 'temp'

    # clip.write_videofile(outfile, codec='libx264', audio_codec='aac')
    try:
        out = ffmpeg.output(clip, audio, "content/static/videos/"+"dubbed"+filename, vcodec='copy', acodec='aac', strict='experimental').run(capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e


def dub(
        videoFile, basename, storageBucket, srcLang, targetLangs=[], phraseHints=[], dubSrc=False, speakerCount=1, voices={}, srt=False,
        newDir=False, genAudio=False, noTranslate=False):
    """Translate and dub a movie.
    Args:
        videoFile (String): File to dub
        outputDir (String): Directory to write output files
        srcLang (String): Language code to translate from (i.e. "fi")
        targetLangs (list, optional): Languages to translate too, i.e. ["en", "fr"]
        storageBucket (String, optional): GCS bucket for temporary file storage. Defaults to None.
        phraseHints (list, optional): "Hints" for words likely to appear in audio. Defaults to [].
        dubSrc (bool, optional): Whether to generate dubs in the source language. Defaults to False.
        speakerCount (int, optional): How many speakers in the video. Defaults to 1.
        voices (dict, optional): Which voices to use for dubbing, i.e. {"en": "en-AU-Standard-A"}. Defaults to {}.
        srt (bool, optional): Path of SRT transcript file, if it exists. Defaults to False.
        newDir (bool, optional): Whether to start dubbing from scratch or use files in outputDir. Defaults to False.
        genAudio (bool, optional): Generate new audio, even if it's already been generated. Defaults to False.
        noTranslate (bool, optional): Don't translate. Defaults to False.
    Raises:
        void : Writes dubbed video and intermediate files to outputDir
    """

    print(videoFile, basename, storageBucket, srcLang, targetLangs, phraseHints, dubSrc, speakerCount, voices, srt, newDir, genAudio, noTranslate)
    path_video ="gs://"+storageBucket+"/videos/"+videoFile
    path_audio ="gs://"+storageBucket+"/audios/"+basename+".wav"
    output = "output"

    storage_client = storage.Client()
    bucket = storage_client.bucket(storageBucket)
    #outputFiles = storage_client.list_blobs(storageBucket)
    

    # if not f"transcript.json" in outputFiles:
    #     storageBucket = storageBucket if storageBucket else os.environ['STORAGE_BUCKET']
    #     if not storageBucket:
    #         raise Exception(
    #             "Specify variable STORAGE_BUCKET in .env or as an arg")

    #     print("Transcribing audio")
    #     print("Uploading to the cloud...")
    #     bucket = storage_client.bucket(storageBucket)

    #     tmpFile = os.path.join("tmp", str(uuid.uuid4()) + ".wav")
    #     blob = bucket.blob(tmpFile)
        # Temporary upload audio file to the cloud
        # blob.upload_from_filename(os.path.join(
        #     outputDir, baseName + ".wav"), content_type="audio/wav")

    print("Transcribing...")
    transcripts = get_transcripts_json(path_audio, srcLang, phraseHints=phraseHints, speakerCount=speakerCount)

    # blob = bucket.blob("audios/")
    # json.dump(transcripts, open(os.path.join(outputDir, "transcript.json"), "w"))

    sentences = parse_sentence_with_speaker(transcripts, srcLang)
    subtitles = toSrt(transcripts)

    #store sentences as json in google cloud cloud
    destination_blob_sentences = "output/"+basename+"_sentences.json"
    blob_sentences = bucket.blob(destination_blob_sentences)
    blob_sentences.upload_from_string(json.dumps(sentences))

    #store subtitles as subtitles.srt
    destination_blob_subtitles = "output/"+basename+"_subtitles.srt"
    blob_subtitles = bucket.blob(destination_blob_subtitles)
    blob_subtitles.upload_from_string(subtitles)


    #translation to target languages
    sentence = sentences[0]
    if not noTranslate:
        print(f"Translating to {targetLangs}")
        for sentence in sentences:
            sentence[targetLangs] = translate_text(
                sentence[srcLang], targetLangs, srcLang)

        print(sentence, sentences)

        destination_blob_sentences = "output/"+basename+"_sentencesNew.json"
        blob_sentences = bucket.blob(destination_blob_subtitles)
        blob_sentences.upload_from_string(json.dumps(sentences))

    # audioDir = os.path.join(outputDir, "audioClips")
    # if not "audioClips" in outputFiles:
    #     os.mkdir(audioDir)

    # # whether or not to also dub the source language
    # if dubSrc:
    #     targetLangs += [srcLang]

    #create "audioDir/"+targetLangs[0]
    destination_blob_voices_base = "output/audioDir/"+targetLangs+"/"

    print(f"Synthesizing audio for {targetLangs}")

    for i, sentence in enumerate(sentences):
        voiceName = voices[targetLangs] if targetLangs in voices else None
        audio = speakUnderDuration(sentence[targetLangs], targetLangs, sentence['end_time'] - sentence['start_time'], voiceName=voiceName)
        blob_voices = bucket.blob(destination_blob_voices_base+f"{i}.mp3")
        blob_voices.upload_from_string(audio, content_type="audio/mp3")

    # dubbedDir = os.path.join(outputDir, "dubbedVideos")

    # if not "dubbedVideos" in outputFiles:
    #     os.mkdir(dubbedDir)

    print(f"Dubbing audio for {targetLangs}")

    stitch_audio(sentences, destination_blob_voices_base, videoFile, output, storage_client, srtPath=destination_blob_subtitles, bucket_name=storageBucket)